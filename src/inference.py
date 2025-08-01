import enum
from loguru import logger
import litellm
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel
from abc import ABC, abstractmethod
from src.prompts import HydratedPrompt
import json
from src.utils import parse_structured_response
from tqdm import tqdm

load_dotenv()

LMResponse = str | dict | List[str] | List[dict] | BaseModel | List[BaseModel]

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

class PMCIDGenerator(LLMInterface):
    """
    PMCIDGenerator Class
    Used to generate responses about a PMCID article by automatically hydrating prompts with article content
    """
    
    debug_mode = False
    
    def __init__(self, model: str = "gpt-4.1", temperature: float = 0.1, pmcid: str = None, samples: int = 1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True
        self.pmcid = pmcid
        self.samples = samples
        self.system_prompt = "You are a helpful assistant who responds to a user's question about a PubMed article."

    def _generate_single(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        """Generate a single response with PMCID article content automatically hydrated."""
        from src.prompts import ArticlePrompt
        
        # Auto-hydrate the prompt with PMCID article content
        if self.pmcid:
            article_prompt = ArticlePrompt(
                article_text=self.pmcid,
                key_question=input_prompt,
                system_prompt=system_prompt or self.system_prompt,
                output_format_structure=response_format
            )
            hydrated_prompt = article_prompt.get_hydrated_prompt()
            
            # Use the hydrated prompt components
            input_prompt = hydrated_prompt.input_prompt
            system_prompt = hydrated_prompt.system_prompt
            if response_format is None and hydrated_prompt.output_format_structure:
                response_format = hydrated_prompt.output_format_structure

        temp = temperature if temperature is not None else self.temperature
        
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_prompt},
            ]
        else:
            messages = [
                {"role": "system", "content": self.system_prompt},
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
        return parse_structured_response(response_content, response_format)

    def generate(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        """
        Generate a response from the LLM with PMCID article content automatically hydrated.
        """
        responses = []
        for _ in range(self.samples):
            response = self._generate_single(
                input_prompt=input_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                response_format=response_format,
            )
            responses.append(response)
        
        if len(responses) == 1:
            return responses[0]

        return parse_structured_response(responses, response_format)

class Generator(LLMInterface):
    """Generator Class"""

    debug_mode = False

    def __init__(
        self, model: str = "gpt-4.1", temperature: float = 0.1, samples: int = 1
    ):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True
        self.samples = samples

    def _generate_single(
        self,
        input_prompt: str | HydratedPrompt,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: LMResponse = None,
    ) -> LMResponse:
        if isinstance(input_prompt, HydratedPrompt):
            if (
                input_prompt.system_prompt is not None
                and input_prompt.system_prompt != ""
            ):
                system_prompt = input_prompt.system_prompt
            if (
                input_prompt.output_format_structure is not None
                and response_format is None
            ):
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
        return parse_structured_response(response_content, response_format)

    def generate(
        self,
        input_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        """
        Generate a response from the LLM.
        """
        responses = []
        for _ in tqdm(range(self.samples), desc=f"Generating {self.samples} Responses"):
            response = self._generate_single(
                input_prompt=input_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                response_format=response_format,
            )
            responses.append(response)
        if len(responses) == 1:
            return responses[0]

        return parse_structured_response(responses, response_format)


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
        raw_response = response.choices[0].message.content
        return parse_structured_response(raw_response, response_format)


class Fuser(LLMInterface):
    """
    Fuser Class
    Used to fuse multiple responses into a final set of responses, removing duplicates and unreasonable responses
    """

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

        self.system_prompt = (
            "You are a helpful assistant who fuses multiple responses into a comprehensive final response. You will "
            "be given a list of responses and you will merge the responses into a final set of responses while removing "
            "duplicates, responses that are extremely similar, and responses that are not reasonable."
        )

    def generate(
        self,
        input_prompt: str | List[str],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_format: Optional[BaseModel] = None,
    ) -> LMResponse:
        temp = temperature if temperature is not None else self.temperature
        if system_prompt is not None and system_prompt != "":
            self.system_prompt = system_prompt
        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {"role": "user", "content": f"Here are the responses: {input_prompt}"},
        ]
        try:
            completion_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temp,
            }
            if response_format is not None:
                completion_kwargs["response_format"] = response_format
            response = litellm.completion(**completion_kwargs)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise e
        raw_response = response.choices[0].message.content
        return parse_structured_response(raw_response, response_format)
