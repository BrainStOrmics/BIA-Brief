import logging
from ..utils import *
from ..prompts import load_prompt_template
from ..config import *
from synthesist import create_synthesist_agent
from thesis import create_thesis_agent  

from typing import TypedDict, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
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

    async def node_filemanager(state:State):
        """Manages file system operations and environment profiles."""
        logger.debug("START node_filemanager")
        
        # Pass and update inputs from state
        project_id = state['project_id']
        project_path = state['project_path']
        background = state['background']
        output_lang = state['output_lang']
        report_template = state['report_template']

        
        source_data_dir = state.get('source_data_dir', file_config.SOURCE_DATA_DIR)
        file_config.SOURCE_DATA_DIR = source_data_dir

        logger.debug(f"Project ID: {project_id}, Session ID: {session_id}, Source Dir: {source_data_dir}")

        # Parse subgraph inputs
        fm_input = {
            "task_id": task_id,
            "session_id": session_id,
            "source_data_dir": source_data_dir,
            "max_iter": file_config.MAX_ITER,
        }
        
        # Get reference using file manager subgraph
        logger.info("Invoking filemanager subgraph...")
        try:
            filemanager_state = await filemanager_subgraph.ainvoke(
                fm_input,
                config = config_schema)
            # Pass output
            data_files = filemanager_state['data_files']
            env_profiles = filemanager_state['env_profiles']
            logger.info("Successfully retrieved data files and environment profiles.")
            logger.debug(f"Data files found: {data_files}")
        except Exception as e:
            logger.exception("Error dealing with file system.")
            raise  
        
        # Pass env_profiles to config
        ghostcoder_config.ENV_PROF = env_profiles

        logger.debug("END node_filemanager")
        # Return 
        return {
            "data_files": data_files,
            "env_profiles": env_profiles,
            "filemanager_state": filemanager_state,
            "n_iter" : 0,
        }

    def node_task_parser(state:State):
        """"""
        logger.debug("START node_task_parser")

        # Pass inputs
        task_description = state['task_description']
        previous_codeblock = state.get('previous_codeblock', "")
        improvements = state.get('improvements', "")
        n_iter = state.get('n_iter', 0)

        logger.debug(f"Parsing task for iteration {n_iter}.")

        # Parse human input
        human_input = ""
        if len(improvements) > 1:
            task_instruction = state['task_instruction']
            execution_outstr = state['execution_outstr']
            generated_codeblock = state['generated_codeblock']
            human_input += f"## Critique for previous round of code generation and execution  \nYou have provided the user with a one-time task instruction, as follow:\n{task_instruction}\n"
            human_input += f"### Improvements  \nThe improvements suggested by the users are:\n{improvements}\n"
            human_input += f"### Results  \nAnd the following is the execution result of the code generated by this instruction:\n{execution_outstr}\n" 
            human_input += f"### Code  \nAbove results were produced by the following code:\n{generated_codeblock}\n"
        if len(previous_codeblock) > 1:
            human_input += f"## Codes for previous step:  \n---------\n{previous_codeblock}\n---------\n"

        # Call prompt template
        prompt, input_vars = load_prompt_template('ghostcoder.task_parse')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_description = task_description)),
            HumanMessage(content=human_input)
        ]

        # Generate task instruction with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        logger.info("Generating task instruction with LLM...")
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                task_instruction =  json_output['instruction']
                criteria = json_output['criteria']
                logger.info("Successfully generated task instruction and criteria.")
                logger.debug(f"Instruction: {task_instruction}")
                logger.debug(f"Criteria: {criteria}")
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Failed to generate task instruction after multiple retries.")
                    raise  
        logger.debug("END node_task_parser")
        return {
            "task_instruction": task_instruction,
            "criteria": criteria,
            }


    def node_retriever(state:State):
        """"""
        logger.debug("START node_retriever")

        # Pass inputs
        
        
        if ghostcoder_config.DB_RETRIEVE:
            retriever_input = {
                "task_description": state['task_description']
                }
            # Get reference using Retriever subgraph
            logger.info("Invoking retriever subgraph...")

            i = 0
            while i < max_retry:
                try:
                    retriever_state = retriever_subgraph.invoke(
                        retriever_input,
                        config = config_schema)
                    # Pass output
                    ref_codeblocks = retriever_state['ref_codeblocks']
                    logger.info("Successfully retrieved reference code blocks.")
                    logger.debug(f"Retrieved {len(ref_codeblocks)} code blocks.")
                    break
                except Exception as e:
                    i+=1
                    logger.info(str(i),"times retry get ref code blocks with retriever subgraph...")
                    if i == max_retry:
                        logger.exception("Failed to get reference code.")
                        raise  
        else:
            logger.info("Skipping retriever node as Retriever is disabled in config.")
            ref_codeblocks = ""
            retriever_state = {}

        logger.debug("END node_retriever")
        return {
            "ref_codeblocks":ref_codeblocks,
            "retriever_state":retriever_state,
            }
    
    async def node_data_perception_coder(state:State):
        """"""
        logger.debug("START node_data_perception_coder") 

        dp_instruction = """
### **Actions & Tools**
The method for inspecting the file is determined by its type and context. Follow these rules in order of priority:

1.  **For Large-Scale Bioinformatics Files (e.g., `.fastq`, `.fq.gz`, `.bam`, `.sam`):**
    -   **Action:** Do not attempt to read or load the file content. These files are typically too large for simple inspection.
    -   **Code:** Write a simple script that **prints the provided filename** to standard output to confirm its presence and acknowledge it as an input.

2.  **For R-Native Data Files (e.g., `.rds`, `.rda`, `.rdata`):**
    -   **Action:** You **must** use the `R` language.
    -   **Code:** Use `readRDS()` (for `.rds`) or `load()` (for `.rda`/`.rdata`) to import the data, then use the `str()` function to print a detailed summary of the primary object's structure.

3.  **For Python-Native or HDF5-Based Files (e.g., `.h5ad`, `.pkl`, `.h5`):**
    -   **Action:** You **must** use the `Python` language.
    -   **Code:** Use the appropriate specialized library to load the object (`anndata`/`scanpy` for `.h5ad`, `pickle` for `.pkl`, `h5py` for generic `.h5`). Print the loaded object itself to display its default summary.

4.  **For Generic Tabular/Text Files (e.g., `.csv`, `.tsv`, `.txt`):**
    -   **Action:** The language choice depends on the context of other files in the analysis.
        -   **If accompanied by R-native files (`.rds`/`.rda`):** Use `R`. Load the data (e.g., with `read.csv()`) and inspect it with `str()` and `head()` for consistency.
        -   **If accompanied by Python-native files (`.h5ad`/`.pkl`):** Use `Python` with the `pandas` library. Load the data and inspect it with `.info()` and `.head()` for consistency.
        -   **If no other files are present (standalone case):** Default to using `Python` with `pandas`. Load the data and inspect it with `.info()` and `.head()`.

### **Expected Output**
-   The code should not create or save any new files.
-   The entire output should be the requested metadata printed to standard output (stdout).
-   The stdout must contain the relevant structural information (or just the filename for large files) as determined by the rules above.
"""

        # Pass inputs
        data_files = state['data_files']

        # Parse data perception task
        task_instruction = f"### Purpose\nTo inspect a given data file to understand its structure, format, and content (metadata) before performing any analysis. This helps prevent errors and inform the next steps of the workflow. The choice of tool and language will be adapted based on the file type and the context of other available data.:\n - Data files:\n{str(data_files)}\n" 

        # Pass subgraph inputs
        coder_input = {
            "task_instruction"  : task_instruction,
            "data_perception"   : "Your mission is to precept data based on data files names.",
            "ref_codeblocks"    : "",
            "previous_codeblock": "",
            }

        if ghostcoder_config.ALLOW_DATA_PERCEPTION:
            # Generate bioinformatics code with coder subgraph
            logger.info("Invoking coder subgraph for data perception...")
            i = 0
            while i < max_retry:
                try:
                    coder_state = await coder_subgraph.ainvoke(
                        coder_input,
                        config = config_schema
                        )
                    # Pass output
                    generated_codeblock = coder_state['generated_codeblock'][-1]
                    execution_outstr = coder_state['execution_outstr'][-1]
                    logger.info("Data perception complete.")
                    logger.debug(f"Perception output: {execution_outstr}")
                    break
                except Exception as e:
                    i+=1
                    logger.info(str(i),"times retry get data perception with coder subgraph...")
                    if i == max_retry:
                        logger.exception(f"Failed to get data perception due to:\n{e}")
                        raise  
            data_perception = execution_outstr
        
        # Pass output without in line data perception 
        else:
            logger.info("Data perception is disabled in config.")
            generated_codeblock = ""
            try: 
                data_perception = state['data_perception']
                logger.infor(f"Using given data information{data_perception}.")
            except:
                data_perception = "Data perception is not available."
                logger.infor("Data information is not available.")
            coder_state = {}

        logger.debug("END node_data_perception_coder")
        # Return 
        return {
            "generated_codeblock_4dp":generated_codeblock,
            "data_perception": execution_outstr,
            "dp_coder_state":coder_state
            }

    async def node_task_coder(state:State):
        """"""
        logger.debug("START node_task_coder")

        # Pass inputs
        coder_input = {
            "task_instruction"  :state['task_instruction'],
            "data_perception"   :state['data_perception'],
            "ref_codeblocks"    : state['ref_codeblocks'],
            "previous_codeblock": state['previous_codeblock'],
            "env_profiles"      : state["env_profiles"],
            }
        logger.debug(f"Coder input instruction: {state['task_instruction']}")

        logger.info("Invoking coder subgraph for task execution...")
        i = 0
        while i < max_retry:
            try:
                # Generate bioinformatics code with coder subgraph
                coder_state = await coder_subgraph.ainvoke(
                    coder_input,
                    config = config_schema
                    )

                # Pass output
                generated_codeblock = coder_state['generated_codeblock'][-1]
                execution_outstr = coder_state['execution_outstr'][-1]
                logger.info("Task execution complete.")
                logger.debug(f"Task output: {execution_outstr}")
                break2
            except Exception as e:
                i+=1
                logger.info(str(i),"times retry get task execution with coder subgraph...")
                if i == max_retry:
                    logger.exception(f"Failed to get task execution due to:\n{e}")
                    raise  
        
        logger.debug("END node_task_coder")
        return {
            "generated_codeblock":generated_codeblock,
            "execution_outstr": execution_outstr,
            "coder_state":coder_state
            }


    def node_evaluator(state:State):
        """"""
        logger.debug("START node_evaluator")

        # Pass inputs
        task_description = state['task_description']
        task_instruction = state['task_instruction']
        generated_codeblock = state['generated_codeblock']
        execution_outstr = state['execution_outstr']
        criteria = state['criteria']

        human_input =  f"## Instruction in last round: \n{task_instruction}\n"
        human_input += f"## Evaluation criteria: \n{criteria}\n"
        human_input += f"## Execution results: \n{execution_outstr}\n"
        human_input += f"## Produced by following code: \n{generated_codeblock}\n"

        # Call prompt template
        prompt, input_vars = load_prompt_template('ghostcoder.eval')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_description=task_description)),
            HumanMessage(content=human_input)
        ]

        # Generate task instruction with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        logger.info("Evaluating generated code with LLM...")
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                eval_decision =  json_output['decision']
                improvements = json_output['improvements']
                logger.info(f"Evaluation decision: {eval_decision}")
                logger.debug(f"Suggested improvements: {improvements}")
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Failed to generate evaluation after multiple retries.")
                    raise  

        # update iteration 
        n_iter = state['n_iter'] + 1
        logger.debug(f"Incrementing iteration count to {n_iter}.")

        logger.debug("END node_evaluator")
        return {
            "eval_decision": eval_decision, 
            "improvements": improvements,
            "n_iter": n_iter,
        }
    


    #----------------
    # Define conditional edges
    #----------------
    
    def router_use_RAG(state:State):
        logger.debug("START router_use_RAG")
        if ghostcoder_config.DB_RETRIEVE:
            logger.debug("Router decision: RAG")
            return "RAG"
        else:
            logger.debug("Router decision: continue (skip RAG)")
            return "continue"

    def router_eval(state:State):
        logger.debug("START router_eval")
        n_iter = state['n_iter']
        decision = state['eval_decision'].lower()

        if n_iter < ghostcoder_config.MAX_ITER:
            if decision == 'refine instruction':
                logger.debug(f"Router decision: regen_instruc, n_iter={n_iter}")
                return "regen_instruc"
            elif decision == 'regenerate code':
                logger.debug(f"Router decision: coder, n_iter={n_iter}")
                return "coder"
            else:
                logger.debug(f"Router decision: output (success), n_iter={n_iter}")
                return "output"
        else:
            logger.debug(f"Router decision: output (max iterations reached), n_iter={n_iter}")
            return "output"
        
    #----------------
    # Compile graph
    #----------------
    logger.info("Compiling Ghostcoder agent graph...")

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("File manager", node_filemanager)
    builder.add_node("Task parser", node_task_parser)
    builder.add_node("DataCoder",node_data_perception_coder)
    builder.add_node("Retriever", node_retriever)
    builder.add_node("Coder",node_task_coder)
    builder.add_node("Evaluator",node_evaluator)
    # builder.add_node("Output parser",node_output_parser)
    # builder.add_node("Update env",node_update_env)
    # add edges
    builder.add_edge(START, "File manager")
    builder.add_edge("File manager", "Task parser")
    builder.add_conditional_edges(
        "Task parser", 
        router_use_RAG,
        {
            "RAG"       : "Retriever", 
            "continue"  : "DataCoder"
        }
    )
    builder.add_edge("Retriever","DataCoder")
    builder.add_edge("DataCoder","Coder")
    builder.add_edge("Coder", "Evaluator")
    builder.add_conditional_edges(
        "Evaluator", 
        router_eval,
        {
            "regen_instruc" : "Task parser", 
            "coder"         : "Coder",
            "output"        : END#"Output parser",
        }
    )
    # builder.add_edge("Output parser", END)

    logger.info("Graph compilation complete.")
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )