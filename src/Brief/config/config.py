import yaml

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


    
def load_yaml_config(yaml_path):
    config_mappings = [
        ("llm_config", llm_config),
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

    if default_keys:
        print("Following keys are using default:\n" + default_keys + "\n")


