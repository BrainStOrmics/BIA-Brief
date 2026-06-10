import os
import re


def load_prompt_template(prompt_name: str):
    """Load a prompt template from a Markdown file.

    Args:
        prompt_name: The name of the prompt template file (without extension).

    Returns:
        template: The raw template string with <<var>> placeholders.
        input_vars: List of input variable names found in the template.
    """
    template_path = os.path.join(os.path.dirname(__file__), f"{prompt_name}.md")

    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            template = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt template '{prompt_name}.md' not found in {os.path.dirname(__file__)}")
    except Exception as e:
        raise ValueError(f"Error reading prompt template: {e}")

    input_vars = re.findall(r"<<([^>>]+)>>", template)

    return template, input_vars


def render_prompt(template: str, **kwargs) -> str:
    """Render a prompt template by replacing <<var>> placeholders with values.

    Args:
        template: Raw template string with <<var>> placeholders.
        **kwargs: Variable name to value mappings.

    Returns:
        Rendered template string.
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"<<{key}>>", str(value))
    return result
