from typing import Dict
from loguru import logger

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
