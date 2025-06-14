from typing import Dict
from loguru import logger
import litellm
from .inference import LLMInterface
import re
import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from typing import List
load_dotenv()

class PromptGenerator:
    def __init__(self, prompt_template: str, replacements: Dict[str, str]):
        self.prompt_template = prompt_template
        self.replacements = replacements
        self.validate_replacements()
        self.prompt = self.generate_prompt()
    
    def validate_replacements(self) -> bool:
        """Validate that all replacement keys are present in the prompt template."""
        all_valid = True
        for key in self.replacements:
            if key not in self.prompt_template:
                logger.warning(f"Replacement key {key} not found in prompt template.")
                all_valid = False
        return all_valid

    def generate_prompt(self) -> str:
        return self.prompt_template.format(**self.replacements)
    
    def get_prompt(self) -> str:
        return self.prompt
    
    def get_prompt_template(self) -> str:
        return self.prompt_template
    
class SimpleLLM(LLMInterface):
    """Simple LLM interface that just returns as response to the prompt."""
    debug_mode = False
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        
        if self.debug_mode:
            litellm.set_verbose = True
        
    def generate(self, prompt: str, temperature: float = None, response_format: BaseModel = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        response = litellm.completion(model=self.model, messages=[{"role": "user", "content": prompt}], response_format=response_format, temperature=temp)
        return response.choices[0].message.content

class Variant(BaseModel):
    """Variant."""
    variant_id: str
    gene: str | None = None
    allele: str | None = None

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

    @field_validator('text')
    @classmethod
    def validate_text_in_options(cls, v: str, info) -> str:
        if 'options' in info.data and v not in info.data['options']:
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
        response = litellm.completion(model=self.model, messages=[{"role": "user", "content": prompt}], structured_output=True, temperature=temp)
        return response.choices[0].message.content
