import logging
from ..utils import *
from ..prompts import load_prompt_template
from ..config import brief_config

from typing import TypedDict, Annotated, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy
#from langgraph.types import interrupt
#Autogen executors
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_thesis_agent(
    chat_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "thesis_subgraph",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledStateGraph:

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        background: str
        output_lang: str
        section_summaries: list[str]
        
        #generated
        conclusion: str
        discussion: str
        key_takeaways: list[str]

    #----------------
    # Define nodes
    #----------------
    
    def node_thesis(state:State):
        """
        """
        logger.debug("START node_thesis")
        logger.info("============Brief============\nStarting thesis subagent...\n")
        # Pass inputs
        background = state['background']
        output_lang = state['output_lang']
        section_summary_list = state['image_path']

        # Re-format sections
        section_summary = "\n###Section summaries for this research/project:\n========\n"
        i = 0
        for summ in section_summary_list:
            section_summary += "\n#### Section #"+str(i)+": "
            section_summary += summ
            i+=1
        section_summary += "\n========"

        # Call prompt template
        prompt, input_vars = load_prompt_template('thesis')
        logger.debug(
            "Using prompt:\n--------prompt--------\n"+
            str(prompt)+
            "\n----------------")

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                background = background,
                output_lang = output_lang,
                )),
            HumanMessage(content=section_summary)
        ]

        # Chose code run env by llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                # Parse outputs
                discussion = json_output['discussion']
                conclusion = json_output['conclusion']
                key_takeaways = json_output['key_takeaways']
                # To log
                log_str = "".join([
                        "LLM response:\n----------------",
                        "\nConclusion:\n",conclusion,
                        "\nDiscussion:\n",discussion,
                        "\nKey Takeaways:\n",
                        ]
                    )
                i = 0
                for tw in key_takeaways:
                    log_str += "\n    #"+str(i)+": " + tw
                    i+=1
                log_str+="\n----------------",
                logger.info(log_str)
                break

            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception with"+str(i)+"tries:\n")
                else:
                    logger.debug("Get exception when parsing env:\n"+str(e))
        logger.debug("END node_thesis")
        return{
            "discussion": discussion,
            "conclusion": conclusion,
            "key_takeaways": key_takeaways,
        }

    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Thesis", node_thesis)
    # add edges
    builder.add_edge(START, "Thesis")
    builder.add_edge("Thesis", END)
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
