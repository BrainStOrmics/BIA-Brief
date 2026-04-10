import logging
from ..utils import *
from ..prompts import load_prompt_template

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


#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_synthesist_agent(
    mmchat_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "synthesist_subgraph",
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
        figure_id: str
        image_path: str
        script_path: str
        
        #generated
        caption_title: str
        caption_body: str
        caption: str
        section_summary: str

    #----------------
    # Define nodes
    #----------------
    
    def node_synthesist(state:State):
        """
        """
        logger.debug("START node_synthesist")
        logger.info("============Brief============\nStarting synthesist subagent...\n")
        # Pass inputs
        background = state['background']
        output_lang = state['output_lang']
        figure_id = state['figure_id']
        image_path = state['image_path']
        script_path = state['script_path']

        # Check pic file
        logger.info("Get picture...")
        if not check_image_exists(image_path):
            logger.debug("Image file: %s does not exist.", image_path)
            raise FileNotFoundError(f"Image file {image_path} does not exist.")
        else:
            pic_64, pic_mime_type = image_to_base64_for_llm(image_path)

        # Check script file
        logger.info("Get script...")
        script_content = "The code to generate the following image is as follows:\n"
        if len(script_path) == 0:
            logger.info("No script file provided, skip.")
            script_content = ""
        else:
            if check_file_exists(script_path):
                script_content += read_code_file(script_path) + '\n'
            else: 
                logger.info("Could not find script file in",script_path,", skip.")
                script_content = ""
        
        # Call prompt template
        prompt, input_vars = load_prompt_template('synthesist')
        logger.debug(
            "Using prompt:\n--------prompt--------\n"+
            str(prompt)+
            "\n----------------")

        # Parse human input
        human_input = HumanMessage(
            content = [
            {
                "type": "text",
                "text": (
                    "Write a figure title and a separate figure explanation for the following image. "
                    f"Use the exact figure identifier '{figure_id}' as the title numbering. "
                    + script_content
                )
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{pic_mime_type};base64,{pic_64}"}
            },
        ]
        )

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                background = background,
                output_lang = output_lang,
                figure_id = figure_id,
                )),
            human_input
        ]

        # Chose code run env by llm
        chain = mmchat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                # Parse outputs
                caption_title = json_output.get('caption_title', '')
                caption_body = json_output.get('caption_body', '')
                caption = json_output['caption']
                section_summary = json_output['section_summary']
                if not caption:
                    caption_parts = [part for part in [caption_title, caption_body] if part]
                    caption = " ".join(caption_parts)
                # To log
                logger.info(
                    "".join([
                        "LLM response:\n----------------",
                        "\ncaption_title:", caption_title,
                        "\ncaption_body:", caption_body,
                        "\ncaption:",caption,
                        "\nsection_summary:",section_summary,
                        "\n----------------",
                    ])
                    )
                break

            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception with"+str(i)+"tries:\n")
                    raise
                else:
                    logger.debug("Get exception when parsing env:\n"+str(e))
        logger.debug("END node_synthesist")
        return{
            "caption_title": caption_title,
            "caption_body": caption_body,
            "caption": caption,
            "section_summary": section_summary,
        }

    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Synthesist", node_synthesist)
    # add edges
    builder.add_edge(START, "Synthesist")
    builder.add_edge("Synthesist", END)
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
