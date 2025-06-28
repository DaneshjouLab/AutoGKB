from loguru import logger
import litellm
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel
from abc import ABC, abstractmethod
from src.prompts import HydratedPrompt

load_dotenv()


class LLMInterface(ABC):
    """LLM Interface implemented by Generator and Parser classes"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    def prompted_generate(
        self, hydrated_prompt: HydratedPrompt, temperature: float = None
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        return self.generate(
            hydrated_prompt.input_prompt,
            hydrated_prompt.system_prompt,
            temp,
            hydrated_prompt.output_format_structure,
        )

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        response_format: BaseModel = None,
    ) -> str:
        """Generate a response from the LLM."""
        pass


class Generator(LLMInterface):
    """Generator Class"""

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        response_format: BaseModel = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                response_format=response_format,
                temperature=temp,
            )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise e
        return response.choices[0].message.content


class Parser(LLMInterface):
    """Parser Class"""

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        response_format: BaseModel = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            logger.warning(
                "No system prompt provided. Using default system prompt. System prompts recommended for parsing."
            )
            messages = [
                {
                    "role": "system",
                    "content": "Your job is to parse the response into a structured output. Please provide your response in the exact format specified by the response_format parameter.",
                },
                {"role": "user", "content": prompt},
            ]
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                response_format=response_format,
                temperature=temp,
            )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise e
        return response.choices[0].message.content
