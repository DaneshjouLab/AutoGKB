from typing import Optional, Type, List, Union
from loguru import logger
from pydantic import BaseModel
from src.utils import get_article_text

"""
This module is used to generate prompts for the LLM.
The variables that go into the prompt template are:
- system prompt
- article text
- key question
- output queues
- output format
"""

ARTICLE_PROMPT_TEMPLATE = """
You are an expert pharmacogenomics researcher reading and extracting key information from the following article:

{article_text}

{key_question}

{output_queues}
"""


class HydratedPrompt(BaseModel):
    """Final prompt with system and input components."""

    system_prompt: Optional[str] = None
    input_prompt: str
    output_format_structure: Optional[Type[BaseModel]] = None


class PromptHydrator(BaseModel):
    """Prompt hydrator."""

    prompt_template: str
    prompt_variables: dict
    system_prompt: Optional[str] = None
    output_format_structure: Optional[Type[BaseModel]] = None

    def get_hydrated_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        # Check to make sure all prompt_variables are in the prompt_template
        for key, value in self.prompt_variables.items():
            if key not in self.prompt_template:
                logger.warning(f"Prompt variable {key} not found in prompt template")

        input_prompt = self.prompt_template.format(**self.prompt_variables)
        return HydratedPrompt(
            system_prompt=self.system_prompt,
            input_prompt=input_prompt,
            output_format_structure=self.output_format_structure,
        )


class ArticlePrompt(PromptHydrator):
    """Input variables for prompt generation.

    Members:
        article_text: The text of the article or PMC ID.
        key_question: The key question to answer.
        output_queues: The output queues to use.
    """

    def __init__(
        self,
        article_text: str,
        key_question: str,
        output_queues: Optional[str] = None,
        system_prompt: Optional[str] = None,
        output_format_structure: Optional[Type[BaseModel]] = None,
    ) -> None:
        # First initialize the parent class with base attributes
        super().__init__(
            prompt_template=ARTICLE_PROMPT_TEMPLATE,
            prompt_variables={},  # Start with empty dict
            system_prompt=system_prompt,
            output_format_structure=output_format_structure,
        )

        # Set article text and update prompt variables
        self._article_text = article_text
        self.prompt_variables.update(
            {
                "article_text": self.article_text,
                "key_question": key_question,
                "output_queues": output_queues or "",
            }
        )

    @property
    def article_text(self) -> str:
        """Get the article text, fetching from file if PMC ID is provided."""
        if self._article_text.startswith("PMC"):
            return get_article_text(self._article_text)
        return self._article_text

    def get_hydrated_prompt(self) -> HydratedPrompt:
        """Get the hydrated prompt with resolved article text."""
        return super().get_hydrated_prompt()


class GeneratorPrompt:
    def __init__(
        self,
        input_prompt: str | ArticlePrompt,
        output_format_structure: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ):
        self.input_prompt = input_prompt
        self.output_format_structure = output_format_structure
        self.system_prompt = system_prompt

    def get_hydrated_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        if isinstance(self.input_prompt, PromptHydrator):
            hydrated = self.input_prompt.get_hydrated_prompt()
            self.input_prompt = hydrated.input_prompt
            if not self.system_prompt and hydrated.system_prompt:
                self.system_prompt = hydrated.system_prompt
            if not self.output_format_structure and hydrated.output_format_structure:
                self.output_format_structure = hydrated.output_format_structure

        return HydratedPrompt(
            system_prompt=self.system_prompt,
            input_prompt=self.input_prompt,
            output_format_structure=self.output_format_structure,
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

    def get_hydrated_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
        return HydratedPrompt(
            system_prompt=self.system_prompt,
            input_prompt=self.input_prompt,
            output_format_structure=self.output_format_structure,
        )


class FuserPrompt:
    def __init__(
        self,
        previous_responses: List[str],
        input_prompt: Optional[str] = None,
        output_format_structure: Optional[Type[BaseModel]] = None,
        system_prompt: Optional[str] = None,
    ):
        self.previous_responses = previous_responses
        self.input_prompt = input_prompt
        self.output_format_structure = output_format_structure
        self.system_prompt = system_prompt
        self.complete_prompt = ""

    def get_hydrated_prompt(self) -> HydratedPrompt:
        for i, response in enumerate(self.previous_responses):
            self.complete_prompt += f"Response {i}\n"
            self.complete_prompt += response
        if self.input_prompt:
            self.complete_prompt += self.input_prompt
        return HydratedPrompt(
            system_prompt=self.system_prompt,
            input_prompt=self.complete_prompt,
            output_format_structure=self.output_format_structure,
        )
