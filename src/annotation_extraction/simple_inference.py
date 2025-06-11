from typing import Dict
from loguru import logger
import litellm
from .inference import LLMInterface
import re
import os
from dotenv import load_dotenv
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
    
    def remove_references(self) -> str:
        """Remove references from the prompt."""
        return re.sub(r'\[[0-9]+\]', '', self.prompt)
    
    def remove_references_section(self) -> str:
        """
        Removes the references section from article text.
            
        Returns:
            str: Article text with references section removed
            (Looks for ## References section and removes it and everything after)
        """
        # Split the text into sections
        sections = self.prompt.split("##")
        
        # Find the index of the References section
        ref_index = -1
        for i, section in enumerate(sections):
            if section.strip().startswith("References"):
                ref_index = i
                break
        
        # If references section found, remove it and everything after
        if ref_index != -1:
            sections = sections[:ref_index]
            return "##".join(sections)
        
        return self.prompt

    
    def get_prompt(self) -> str:
        return self.prompt



class SimpleLLM(LLMInterface):
    """Simple LLM interface that just returns the prompt."""
    debug_mode = False
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):

        self.model = model
        self.temperature = temperature
        
        if self.debug_mode:
            litellm.set_verbose = True
        
    def generate(self, prompt: str, temperature: float = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        response = litellm.completion(model=self.model, messages=[{"role": "user", "content": prompt}], temperature=temp)
        return response.choices[0].message.content