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

GENERATOR_PROMPT_TEMPLATE = """
You are an expert pharmacogenomics researcher reading and extracting key information from the following article:

{article_text}

{key_question}

{output_queues}
"""


class ArticlePrompt(BaseModel):
    """Input variables for prompt generation.

    Members:
        article_text: The text of the article.
        key_question: The key question to answer.
        output_queues: The output queues to use.
    """

    article_text: str
    key_question: str
    output_queues: Optional[str] = None

    def get_hydrated_prompt(self) -> str:
        """Get the input prompt."""
        self.article_text = self.get_article_text()
        return GENERATOR_PROMPT_TEMPLATE.format(
            article_text=self.article_text,
            key_question=self.key_question,
            output_queues=self.output_queues,
        )
    
    # If article_text is a pmcid, get the article text from the file
    def get_article_text(self) -> str:
        """Get the article text."""
        if self.article_text.startswith("PMC"):
            return get_article_text(self.article_text)
        return self.article_text


class HydratedPrompt(BaseModel):
    """Final prompt with system and input components."""

    system_prompt: Optional[str] = None
    input_prompt: str
    output_format_structure: Optional[Type[BaseModel]] = None


class GeneratorPrompt:
    def __init__(self, input_prompt: str | ArticlePrompt, output_format_structure: Type[BaseModel], system_prompt: Optional[str] = None):
        self.input_prompt = input_prompt
        if isinstance(input_prompt, ArticlePrompt):
            self.input_prompt = input_prompt.get_hydrated_prompt()
        self.output_format_structure = output_format_structure
        self.system_prompt = system_prompt

    def hydrate_prompt(self) -> HydratedPrompt:
        """Hydrate the prompt."""
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

    def hydrate_prompt(self) -> HydratedPrompt:
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

    def hydrate_prompt(self) -> HydratedPrompt:
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
