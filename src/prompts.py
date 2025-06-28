from typing import Optional, Type, List, Union
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

GENERATOR_PROMPT_TEMPLATE = """
You are an expert pharmacogenomics researcher reading and extracting key information from the following article:

{article_text}

{key_question}

{output_queues}
"""


class PromptVariables(BaseModel):
    """Input variables for prompt generation.

    Members:
        article_text: The text of the article.
        key_question: The key question to answer.
        output_queues: The output queues to use.
        system_prompt: The system prompt to use.
        output_format_structure: The output format structure to use.
    """

    article_text: str
    key_question: str
    output_queues: Optional[str] = None
    system_prompt: Optional[str] = None
    output_format_structure: Optional[Union[Type[BaseModel], List[Type[BaseModel]]]] = (
        None
    )


class HydratedPrompt(BaseModel):
    """Final prompt with system and input components."""

    system_prompt: Optional[str] = None
    input_prompt: str
    output_format_structure: Optional[Type[BaseModel]] = None


class GeneratorPrompt:
    def __init__(self, prompt_variables: PromptVariables):
        self.prompt_template = GENERATOR_PROMPT_TEMPLATE
        self.prompt_variables = prompt_variables

    def hydrate_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        return HydratedPrompt(
            system_prompt=self.prompt_variables.system_prompt,
            input_prompt=self.prompt_template.format(
                **self.prompt_variables.model_dump()
            ),
            output_format_structure=self.prompt_variables.output_format_structure,
        )


class ParserPrompt:
    """Parser prompt generator."""

    def __init__(
        self,
        input_prompt: str,
        output_format_structure: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ):
        self.input_prompt = input_prompt
        self.output_format_structure = output_format_structure
        self.system_prompt = system_prompt
        if self.system_prompt is None or self.system_prompt == "":
            self.system_prompt = "Your job is to parse the response into a structured output. Please provide your response in the exact format specified. If something is not clear, leave the value as None"
        if self.input_prompt is None or self.input_prompt == "":
            logger.error("Input prompt is required for parser prompt.")
            raise ValueError("Input prompt is required for parser prompt.")
        if self.output_format_structure is None:
            logger.error("Output format structure is required for parser prompt.")
            raise ValueError("Output format structure is required for parser prompt.")

    def hydrate_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        return HydratedPrompt(
            system_prompt=self.system_prompt,
            input_prompt=self.input_prompt,
            output_format_structure=self.output_format_structure,
        )
