from typing import Dict
from loguru import logger
import litellm
import re
import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from typing import List
from src.prompts import HydratedPrompt

load_dotenv()


class LLMInterface:
    """LLM Interface implemented by Generator and Parser classes"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    def prompted_generate(self, HydratedPrompt: HydratedPrompt, temperature: float = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        return self.generate(HydratedPrompt.input_prompt, HydratedPrompt.system_prompt, temp, HydratedPrompt.output_format_structure)

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


class Generator(LLMInterface):
    """Generator Class"""

    debug_mode = False

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

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
        self.model = model
        self.temperature = temperature

        if self.debug_mode:
            litellm.set_verbose = True

    def generate(
        self,
        prompt: str,
        response_format: BaseModel,
        system_prompt: str = None,
        temperature: float = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        # Check if system prompt is provided
        if system_prompt is not None and system_prompt != "":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            logger.warning("No system prompt provided. Using default system prompt. System prompts recommended for parsing.")
            messages = [
                {"role": "system", "content": "Your job is to parse the response into a structured output. Please provide your response in the exact format specified by the response_format parameter."},
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

            

class Variant(BaseModel):
    """Variant."""

    variant_id: str
    gene: str | None = None
    allele: str | None = None
    evidence: str | None = None

    # TODO: Add field validation for gene and allele


class VariantList(BaseModel):
    """List of variants."""

    variant_list: List[Variant]


class StrEntry(BaseModel):
    """String entry."""

    text: str
    reason: str
    quote: str


class EnumEntry(BaseModel):
    """Enum entry."""

    options: List[str]
    text: str
    reason: str
    quote: str

    @field_validator("text")
    @classmethod
    def validate_text_in_options(cls, v: str, info) -> str:
        if "options" in info.data and v not in info.data["options"]:
            raise ValueError(f"Text {v} not in options {info.data['options']}")
        return v


class VarDrugResponse(BaseModel):
    """Response from VarDrug."""

    variant_id: StrEntry
    drug_id: StrEntry
    effect: StrEntry
    evidence: StrEntry


class VarPhenoResponse(BaseModel):
    """Response from VarPheno."""

    variant_id: StrEntry
    phenotype: StrEntry
    evidence: StrEntry


class VarFAResponse(BaseModel):
    """Response from VarFA."""

    variant_id: StrEntry
    phenotype: StrEntry
    evidence: StrEntry


class VarDrugParser(LLMInterface):
    """LLM interface that parses a VarDrug response into a dictionary."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        super().__init__(model, temperature)
        if self.debug_mode:
            litellm.set_verbose = True

    def generate(self, prompt: str, temperature: float = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            structured_output=True,
            temperature=temp,
        )
        return response.choices[0].message.content
