from loguru import logger
import litellm
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel
from abc import ABC, abstractmethod
from src.prompts import HydratedPrompt
import json

load_dotenv()

LMResponse = str | BaseModel | List[str] | List[BaseModel]

"""
TODO:
Refactor this. Things that change from inference to inference are
- system prompt
- whether or not previous_responses are taken

Look into Archon fomratting for taking in previous responses
 
Add retry for connection errors
"""


class LLMInterface(ABC):
    """LLM Interface implemented by Generator and Parser classes"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    def prompted_generate(
        self, hydrated_prompt: HydratedPrompt, temperature: Optional[float] = None
    ) -> str:
        """
        Added by default to all subclasses. Converts the general generate method into one
        that accepts a HydratedPrompt.
        """
        temp = temperature if temperature is not None else self.temperature
        return self.generate(
            hydrated_prompt.input_prompt,
            hydrated_prompt.system_prompt,
            temp,
            hydrated_prompt.output_format_structure,
        )

    def generate(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        """Generate a response from the LLM."""
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt},
            ]
        else:
            logger.warning("No system prompt provided. Using default value")
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": input_prompt},
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


class Generator(LLMInterface):
    """Generator Class"""

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

    def _generate_single(
        self,
        input_prompt: str | HydratedPrompt,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: LMResponse = None,
    ) -> str:
        if isinstance(input_prompt, HydratedPrompt):
            if input_prompt.system_prompt is not None and input_prompt.system_prompt != "":
                system_prompt = input_prompt.system_prompt
            if input_prompt.output_format_structure is not None and response_format is None:
                response_format = input_prompt.output_format_structure
            input_prompt = input_prompt.input_prompt

        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt},
            ]
        else:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": input_prompt},
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
        response_content = response.choices[0].message.content
        if isinstance(response_content, str) and response_format is not None:
            try:
                response_content = json.loads(response_content)
            except:
                logger.warning(f"Response content was not a valid JSON string. Returning string")
        return response_content

    def generate(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
        samples: Optional[int] = 1,
    ) -> LMResponse:
        """
        Generate a response from the LLM.
        """
        responses = []
        for _ in range(samples):
            response = self._generate_single(
                input_prompt=input_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                response_format=response_format,
            )
            responses.append(response)
        if len(responses) == 1:
            return responses[0]

        return responses


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
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant whose job is to parse the response into a structured output.",
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


class Fuser(LLMInterface):

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

    def generate(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt},
            ]
        else:
            logger.warning("")
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant who fuses multiple responses into a comprehensive final response",
                },
                {"role": "user", "content": input_prompt},
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
