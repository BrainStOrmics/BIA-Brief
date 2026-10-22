from langchain_openai import ChatOpenAI
from ..config import *

def setup_LLMs() -> None:
    """
    Initialize and configure all Large Language Models for the BIA-Ghostcoder system.
    
    This function sets up three types of models essential for bioinformatics analysis:
    - Chat model: For natural language understanding and task interpretation
    - Code model: For generating bioinformatics analysis code
    - Embedding model: For vector similarity search in code retrieval
    
    The function handles multiple embedding providers (DashScope, OpenAI) with fallback
    mechanisms to ensure robust model initialization even if some services are unavailable.
    
    Returns:
        None: Models are stored in the global llm_config.MODELS dictionary.
    """
    # Initialize chat model for natural language processing and task understanding
    try:
        chat_model = ChatOpenAI(
            api_key=llm_config.CHAT_MODEL_API['api'],
            base_url=llm_config.CHAT_MODEL_API['url'],
            model=llm_config.CHAT_MODEL_API['model'],
            temperature=0,  # Deterministic output for consistent behavior
            max_retries=3,  # Robust error handling for network issues
            extra_body = {
                "enable_thinking": llm_config.ENABLE_THINKING,
                "enable_search": llm_config.ENABLE_SEARCH,
            }
        )
    except Exception as e:
        # Graceful degradation - system can still function without chat model
        print(f"Warning: Failed to initialize chat model: {e}")
        chat_model = None

    # Store chat model in global configuration for system-wide access
    llm_config.MODELS['chat_model'] = chat_model

    # Initialize multi-modal chat model with base_64 pic imput
    try:
        mmchat_model = ChatOpenAI(
            api_key=llm_config.MULTIMODAL_CHAT_MODEL_API['api'],
            base_url=llm_config.MULTIMODAL_CHAT_MODEL_API['url'],
            model=llm_config.MULTIMODAL_CHAT_MODEL_API['model'],
            temperature=0,  # Deterministic code generation for reproducibility
            max_retries=3,  # Robust error handling for network issues
            extra_body = {
                "enable_thinking": llm_config.ENABLE_THINKING,
                "enable_search": llm_config.ENABLE_SEARCH,
            }
        )
    except Exception as e:
        # Graceful degradation - system can still function without code model
        print(f"Warning: Failed to initialize Multimoda model: {e}")
        mmchat_model = None

    # Store code model in global configuration
    llm_config.MODELS['mmchat_model'] = mmchat_model
