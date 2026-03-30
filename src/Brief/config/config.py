import os
import yaml

current_file_path  = os.path.abspath(__file__)

# LLM Configuration
class llm_config:
    CHAT_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    MULTIMODAL_CHAT_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    MODELS = {
        "chat_model" : None,
        "mmchat_model" : None,
    }
    ENABLE_THINKING = True
    ENABLE_SEARCH = False

# Agent Configuration
## Brief
class brief_config:
    PROJECT_ID = "p01"

# class synthesist_config:

# class thesis_config:



    
def load_yaml_config(yaml_path):
    config_mappings = [
        ("llm_config", llm_config),
        ("brief_config", brief_config),
    ]

    with open(yaml_path,'r') as f:
        config = yaml.safe_load(f)
    default_keys = ""
    for config_key, cls in config_mappings:
        for sub_key, sub_value in config[config_key].items():
            try:
                setattr(cls, sub_key, sub_value)
            except:
                default_keys += config_key + "\n"

    print("Following keys are using default:\n"+default_keys+"\n\n")


