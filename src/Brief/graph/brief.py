import logging
from pathlib import Path

from ..utils import *
from ..config import *
from .synthesist import create_synthesist_agent
from .thesis import create_thesis_agent  
from .report import create_report_agent

import operator
from typing import TypedDict, Optional, Type, Any, Annotated
#langchain
from langchain_core.language_models import LanguageModelLike
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore

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
        template_fields: dict[str, Any]

        #parameters
        # n_iter: int

        #generated
        pic_abs_dirs: list[str]
        script_abs_dir: str
        captions: Annotated[list[dict[str, str]], operator.add]
        section_summaries: Annotated[list[dict[str, str]], operator.add]
        conclusion: str
        discussion: str
        key_takeaways: list[str]
        report_md: str
        report_dict: dict[str, Any]
        

    #----------------
    # Load subgraphs
    #----------------

    # Get crawler subgraph 
    logger.debug("Loading synthesist subgraph.")
    synthesist_agent = create_synthesist_agent(
        mmchat_model = mmchat_model,
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

    logger.debug("Loading report subgraph.")
    report_agent = create_report_agent(
        chat_model = chat_model,
        max_retry = max_retry,
        name = "report_subgraph",
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
        
        # Get all pic and script paths with LLM
        filemanager_state = discover_project_files(project_path)
        pic_abs_dirs = filemanager_state["pic_abs_dirs"]
        script_abs_dir = filemanager_state["script_abs_dir"]
        logger.debug("END node_filemanager")

        
        return{
            "pic_abs_dirs": pic_abs_dirs,
            "script_abs_dir": script_abs_dir,
        }

    def node_summary_section(state:State):
        # Pass inputs
        background = state['background']
        pic_abs_dirs = state['pic_abs_dirs']
        script_abs_dir = state['script_abs_dir']
        output_lang = state['output_lang']

        caption_items = []
        section_summary_items = []

        for index, pic_abs_dir in enumerate(pic_abs_dirs, start=1):
            figure_id = f"Figure {index}"

            synthesist_input = {
                "background": background,
                "output_lang": output_lang,
                "figure_id": figure_id,
                "image_path": pic_abs_dir,
                "script_path": script_abs_dir,
            }

            logger.info("Invoking synthesist subgraph for: %s", pic_abs_dir)
            try:
                synthesist_state = synthesist_agent.invoke(
                    synthesist_input,
                    config=config_schema,
                )
                caption_title = synthesist_state.get('caption_title', '')
                caption_body = synthesist_state.get('caption_body', '')
                caption = synthesist_state['caption']
                section_summary = synthesist_state['section_summary']
            except Exception:
                logger.exception("Error invoking synthesist subgraph for image: %s", pic_abs_dir)
                raise

            caption_items.append({
                "image_path": pic_abs_dir,
                "caption_title": caption_title,
                "caption_body": caption_body,
                "caption": caption,
            })
            section_summary_items.append({
                "image_path": pic_abs_dir,
                "section_summary": section_summary,
            })

        logger.debug("END node_summary_section")
        return {
            "captions": caption_items,
            "section_summaries": section_summary_items,
        }

    def node_generate_thesis(state:State):
        logger.debug("START node_generate_thesis")
        # Pass inputs
        background = state['background']
        output_lang = state['output_lang']
        section_summaries = state['section_summaries']
        pic_abs_dirs = state['pic_abs_dirs']

        summary_map = {
            item.get("image_path", ""): item.get("section_summary", "")
            for item in section_summaries
        }

        # Organize section summary sequence by pic path
        section_summaries_list = []
        for pic_path in pic_abs_dirs:
            section_summaries_list.append(summary_map.get(pic_path, ""))

        # Parse subgraph inputs
        thesis_input = {
            "background": background,
            "output_lang": output_lang,
            "section_summaries": section_summaries_list,
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
        project_id = state['project_id']
        project_path = state['project_path']
        background = state['background']
        output_lang = state['output_lang']
        report_template = state['report_template']
        pic_abs_dirs = state['pic_abs_dirs']
        captions = state['captions']
        section_summaries = state['section_summaries']
        conclusion = state['conclusion']
        discussion = state['discussion']
        key_takeaways = state['key_takeaways']

        report_state = report_agent.invoke(
            {
                "project_id": project_id,
                "project_path": project_path,
                "background": background,
                "output_lang": output_lang,
                "report_template": report_template,
                "pic_abs_dirs": pic_abs_dirs,
                "captions": captions,
                "section_summaries": section_summaries,
                "conclusion": conclusion,
                "discussion": discussion,
                "key_takeaways": key_takeaways,
            },
            config=config_schema,
        )

        report_md = report_state.get("report_md", "")
        if not report_md:
            raise ValueError("Report agent did not return report_md.")

        report_output_path = Path(project_path).expanduser().resolve() / "local_tests" / "output" / "auto_report.md"
        report_output_path.parent.mkdir(parents=True, exist_ok=True)
        report_output_path.write_text(report_md, encoding="utf-8")

        report_dict = {
            "project_id": project_id,
            "project_path": project_path,
            "output_lang": output_lang,
            "report_template": report_template,
            "report_output_path": str(report_output_path),
            "report_md": report_md,
            "report_state": report_state,
            "captions": captions,
            "section_summaries": section_summaries,
            "discussion": discussion,
            "conclusion": conclusion,
            "key_takeaways": key_takeaways,
        }

        logger.info("Saved markdown report to: %s", report_output_path)

        return {
            "report_md": report_md,
            "report_dict": report_dict,
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
    builder.add_edge("File manager", "Summary sections")
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