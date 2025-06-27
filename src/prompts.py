from typing import Dict, Optional, Type
from loguru import logger
from pydantic import BaseModel

"""
This module is used to generate prompts for the LLM.
The variables that go into the prompt template are:
- system prompt
- article text
- key question
- output queues
- output format
"""

PROMPT_TEMPLATE = """
You are an expert pharmacogenomics researcher reading and extracting key information from the following article:

{article_text}

{key_question}

{output_queues}
"""


class PromptVariables(BaseModel):
    """Input variables for prompt generation."""

    article_text: str
    key_question: str
    output_queues: Optional[str] = None
    system_prompt: Optional[str] = None
    output_format_structure: Optional[Type[BaseModel]] = None


class HydratedPrompt(BaseModel):
    """Final prompt with system and input components."""

    system_prompt: Optional[str] = None
    input_prompt: str
    output_format_structure: Optional[Type[BaseModel]] = None


class PromptGenerator:
    def __init__(self, prompt_variables: PromptVariables):
        self.prompt_template = PROMPT_TEMPLATE
        self.prompt_variables = prompt_variables

    def hydrate_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        return HydratedPrompt(
            system_prompt=self.prompt_variables.system_prompt,
            input_prompt=self.prompt_template.format(**self.prompt_variables),
            output_format_structure=self.prompt_variables.output_format_structure,
        )
