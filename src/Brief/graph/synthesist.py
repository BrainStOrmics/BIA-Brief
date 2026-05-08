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
    
    def node_synthesist(state: State):
        """Process single image and generate caption + section summary."""
        # Pass inputs
        background = state['background']
        output_lang = state['output_lang']
        figure_id = state['figure_id']
        image_path = state['image_path']
        script_path = state['script_path']

        # Check image file
        if not check_image_exists(image_path):
            raise FileNotFoundError(f"Image file {image_path} does not exist.")
        pic_64, pic_mime_type = image_to_base64_for_llm(image_path)

        # Check script file
        script_content = ""
        if script_path:
            if check_file_exists(script_path):
                script_content = read_code_file(script_path)
            else:
                logger.debug("Script file not found: %s, skipping.", script_path)

        # Load prompt template
        prompt, input_vars = load_prompt_template('synthesist')

        # Build message with image and text
        human_input = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        f"Write a figure title and explanation for the following image. "
                        f"Use identifier '{figure_id}' in the title. " + script_content
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{pic_mime_type};base64,{pic_64}"}
                },
            ]
        )

        message = [
            SystemMessage(content=prompt.format(
                background=background,
                output_lang=output_lang,
                figure_id=figure_id,
            )),
            human_input
        ]

        # Invoke LLM with retry
        chain = mmchat_model | JsonOutputParser()
        for attempt in range(max_retry):
            try:
                json_output = chain.invoke(message)
                caption_title = json_output.get('caption_title', '')
                caption_body = json_output.get('caption_body', '')
                caption = json_output.get('caption', '')
                section_summary = json_output.get('section_summary', '')

                # Fallback: build caption from title + body
                if not caption and (caption_title or caption_body):
                    caption = " ".join(part for part in [caption_title, caption_body] if part)

                logger.debug(
                    "Generated for %s: title=%d chars, summary=%d chars",
                    figure_id, len(caption_title), len(section_summary)
                )
                return {
                    "caption_title": caption_title,
                    "caption_body": caption_body,
                    "caption": caption,
                    "section_summary": section_summary,
                }

            except Exception as e:
                if attempt >= max_retry - 1:
                    logger.exception("Failed after %d attempts for %s", max_retry, figure_id)
                    raise
                logger.debug("Retry %d/%d for %s: %s", attempt + 1, max_retry, figure_id, e)

        return {}

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
