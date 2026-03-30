import logging

from pathlib import Path
from ..utils import *
from ..prompts import load_prompt_template
from ..config import *
from .synthesist import create_synthesist_agent
from .thesis import create_thesis_agent  

import operator
from typing import TypedDict, Optional, Type, Any, Annotated, Literal
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END, Send
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.pregel import RetryPolicy

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)
def create_brief_agent(
    chat_model: LanguageModelLike,
    mmchat_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "brief",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledStateGraph:

    #----------------
    # TODO: Optimize agent framework
    #----------------6

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        project_id: str
        project_path: str
        background: str
        output_lang: str
        report_template: str

        #parameters
        # n_iter: int

        #generated
        pic_abs_dirs: list[str]
        script_abs_dir: str
        captions: Annotated[dict, operator.add]
        session_summaries: Annotated[dict, operator.add]
        conclusion: str
        discussion: str
        key_takeaways: list[str]

    #----------------
    # Load subgraphs
    #----------------

    # Get crawler subgraph 
    logger.debug("Loading synthesist subgraph.")
    synthesist_agent = create_synthesist_agent(
        mmchat_model = chat_model, 
        max_retry = max_retry,
        name =  "synthesist_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )

    logger.debug("Loading thesis subgraph.")
    thesis_agent = create_thesis_agent(
        chat_model = chat_model, 
        max_retry = max_retry,
        name =  "thesis_agent",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )
    
    #----------------
    # Define nodes
    #----------------

    def node_filemanager(state:State):
        """Manages file system operations and environment profiles."""
        logger.debug("START node_filemanager")
        
        # Pass and update inputs from state
        project_id = state['project_id']
        project_path = state['project_path']
        background = state['background']

        # Orgnize project files
        file_tree = tree_dir(project_path)
        abs_path = Path(project_path).absolute()
        
        # Get all pic and script paths with LLM
        #
        # Not yet finish
        #

        
        return{
            "pic_abs_dirs": pic_abs_dirs,
            "script_abs_dir": script_abs_dir,
        }

    async def node_summary_section(state:State):
        # Pass inputs
        background = state['background']
        pic_abs_dir = state['pic_abs_dirs']
        script_abs_dir = state['script_abs_dir']
        output_lang = state['output_lang']

        # Parse subgraph inputs
        synthesist_input = {
            "background": background,
            "output_lang": output_lang,
            "image_path": pic_abs_dir,
            "script_abs_dir": script_abs_dir,
            }
        
        # Get section summary with synthesist subgraph
        logger.info("Invoking synthesist subgraph...")
        try:
            synthesist_state = await synthesist_agent.ainvoke(
                synthesist_input,
                config = config_schema)
            # Pass output
            caption = synthesist_state['caption']
            section_summary = synthesist_state['section_summary']
            logger.info("Successfully retrieved section summary with synthesist subgraph.")
            logger.debug(f"Section summary found: {section_summary}")
        except Exception as e:
            logger.exception("Error dealing with file system.")
            raise  

        # Parse subgraph output
        caption_dict = {
            "pic_path": pic_abs_dir
            "caption": caption,
        }
        section_summar_dict = {
            "pic_path": pic_abs_dir
            "section_summary": section_summary,
        }

        logger.debug("END node_summary_section")
        return {
            "captions": caption_dict,
            "session_summaries": section_summar_dict,
        }

    def node_generate_thesis(state:State):
        logger.debug("START node_generate_thesis")
        # Pass inputs
        background = state['background']
        output_lang = state['output_lang']
        session_summaries = state['session_summaries']
        pic_abs_dir = state['pic_abs_dirs']

        # Orgnize session summary sequence by pic path
        session_summaries_list = []
        for pic_path in pic_abs_dir:
            session_summaries_list.append(session_summaries[pic_path])

        # Parse subgraph inputs
        thesis_input = {
            "background": background,
            "output_lang": output_lang,
            "session_summaries": session_summaries_list,
        }

        # Call thesis subgraph
        thesis_state = thesis_agent.invoke(
            thesis_input,
            config = config_schema)
        
        # Parse subgraph output
        conclusion = thesis_state['conclusion']
        discussion = thesis_state['discussion']
        key_takeaways = thesis_state['key_takeaways']
        logger.debug(f"Thesis found: {conclusion, discussion, key_takeaways}")

        logger.debug("END node_generate_thesis")
        return {
            "conclusion": conclusion,
            "discussion": discussion,
            "key_takeaways": key_takeaways,
        }

    def node_generate_report(state:State):
        """
        load template and produce pdf
        """
        # Pass inputs
        report_template = state['report_template']
        conclusion = state['conclusion']
        discussion = state['discussion']
        key_takeaways = state['key_takeaways']

        # Open report template
        #
        # Not yet finish
        # 

        # Parse report 
        #
        # Not yet finish
        #

        # Output report.pdf
        #
        # Not yet finish
        #


        return {
            # Not yet finish
        }

    # def node_refine(state:State):
    #     """"""
    #     logger.debug("START node_refine")

    #     # Pass inputs
    #     conclusion = state['conclusion']
    #     discussion = state['discussion']
    #     key_takeaways = state['key_takeaways']

    #     # Refine thesis
    #     #
    #     # Not yet finish
    #     #

    #     # Call prompt template
    #     prompt, input_vars = load_prompt_template('refine_thesis')

    #     # Construct input message
    #     message = [
    #         SystemMessage(content=prompt.format()),
    #         HumanMessage(content=human_input)
    #     ]

    #     # Generate task instruction with llm
    #     chain = chat_model | JsonOutputParser()
    #     i = 0
    #     logger.info("Evaluating and refining thesis with LLM...")
    #     while i < max_retry:
    #         try:
    #             json_output = chain.invoke(message)
    #             conclusion = json_output['conclusion']
    #             discussion = json_output['discussion']
    #             key_takeaways = json_output['key_takeaways']
    #             break
    #         except Exception as e:
    #             i+=1
    #             if i == max_retry:
    #                 logger.exception("Failed to refine after multiple retries.")
    #                 raise  

    #     # update iteration 
    #     n_iter = state['n_iter'] + 1
    #     logger.debug(f"Incrementing iteration count to {n_iter}.")

    #     logger.debug("END node_evaluator")
    #     return {
    #         "conclusion": conclusion,
    #         "discussion": discussion,
    #         "key_takeaways": key_takeaways,
    #         "n_iter": n_iter,
    #     }
    


    #----------------
    # Define conditional edges
    #----------------
    def map_to_synthesist(state:State):
        return [
            Send(
                "Summary sections",
                {
                    "pic_abs_dirs": p,
                    "background": state['background'],
                    "script_abs_dir": state['script_abs_dir'],
                    "output_lang": state['output_lang']
                }) for p in state["pic_abs_dirs"] 
        ]
        
    #----------------
    # Compile graph
    #----------------
    logger.info("Compiling Ghostcoder agent graph...")

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("File manager", node_filemanager)
    builder.add_node("Summary sections", node_summary_section)
    builder.add_node("Generate thesis",node_generate_thesis)
    builder.add_node("Generate report", node_generate_report)
    #builder.add_node("Refine",node_refine)
    # add edges
    builder.add_edge(START, "File manager")
    builder.add_conditional_edges(
        "File manager", 
        map_to_synthesist,
        ["Summary sections"]
    )
    builder.add_edge("Summary sections","Generate thesis")
    builder.add_edge("Generate thesis","Generate report")
    builder.add_edge("Generate report", END)
    
    logger.info("Graph compilation complete.")
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )