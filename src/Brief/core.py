from .config import *
from .utils import *
from .graph import *

from typing import Type, Optional, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_tavily  import TavilySearch
#langgraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
#from langgraph.types import interrupt
#plot graph
from IPython.display import Image, display
from langgraph.types import Checkpointer

class Brief:
    """
    Define the state of the graph
    """

    def __init__(
        self,
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
        
        """
        
        """

        # Pass parameters 
        self.chat_model = chat_model
        self.mmchat_model = mmchat_model
        self.max_try = max_retry
        self.name = name
        self.config_schema = config_schema
        self.checkpointer = checkpointer
        self.store = store
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug

        # Initial agent graph
        try:
            self.graph = create_brief_agent(
                chat_model = self.chat_model,
                code_model = self.mmchat_model,
                max_retry = self.max_try,
                name = self.name,
                config_schema = self.config_schema,
                checkpointer = self.checkpointer,
                store = self.store,
                interrupt_before = self.interrupt_before,
                interrupt_after = self.interrupt_after,
                debug = self.debug,
                )
        except Exception as e:
            print(f'Brief failed to initiate due to:\n{e}')
        
    
    def Run(
        self,
        task: str,
        input_wrap: dict, # project path, background and language, report template
        project_id: str = "p01",
        ):
        """
        """

        # Pass parameters
        self.task = task
        self.project_id = project_id
        beief.config.PRPJECT_ID = self.project_id
        self.project_path = input_wrap['project_path']
        self.background = input_wrap['background']
        self.output_lang = input_wrap['output_lang']
        self.report_template = input_wrap['report_template']

        # Pass agent input
        agent_input = {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "background": self.background,
            "output_lang": self.output_lang,
            "report_template": self.report_template,
            }
        
        # Run agent
        output_state = self.graph.invoke(agent_input)

        # Parse result
        report_md = output_state['report_md']
        report_dict = output_state['report_dict']

        return report_md, report_dict
    
    def draw_graph(self):
        i = 0 
        while i < self.max_try:
            try:
                display(Image(self.graph.get_graph(xray=1).draw_mermaid_png()))
                break
            except Exception as e:
                i += 1
                if i == self.max_try:
                    print(f"Error draw agent due to: \n{e}")