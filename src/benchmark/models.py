"""
Language model interface and prompting system for the benchmarking framework.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger



@dataclass
class ModelResponse:
    """Response from a language model."""
    content: str
    model_name: str
    timestamp: float
    metadata: Dict[str, Any]
    raw_response: Optional[Any] = None


class LanguageModelInterface(ABC):
    """Abstract interface for language models."""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """Generate response from the model."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is available."""
        pass


class OpenAIModel(LanguageModelInterface):
    """OpenAI GPT model interface."""
    
    def __init__(self, model_name: str = "gpt-4", api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, **kwargs)
        self.api_key = api_key
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package required for OpenAI models")
    
    def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_tokens", 4000),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            return ModelResponse(
                content=response.choices[0].message.content,
                model_name=self.model_name,
                timestamp=time.time(),
                metadata={
                    "usage": response.usage.dict() if response.usage else {},
                    "finish_reason": response.choices[0].finish_reason
                },
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Error generating response from {self.model_name}: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        if not self.api_key:
            return False
        try:
            self.client.models.list()
            return True
        except Exception:
            return False


class AnthropicModel(LanguageModelInterface):
    """Anthropic Claude model interface."""
    
    def __init__(self, model_name: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, **kwargs)
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required for Anthropic models")
    
    def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """Generate response using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_tokens", 4000),
                **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
            )
            
            return ModelResponse(
                content=response.content[0].text,
                model_name=self.model_name,
                timestamp=time.time(),
                metadata={
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    },
                    "stop_reason": response.stop_reason
                },
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Error generating response from {self.model_name}: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        if not self.api_key:
            return False
        try:
            # Simple test call
            self.client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False


class MockModel(LanguageModelInterface):
    """Mock model for testing purposes."""
    
    def __init__(self, model_name: str = "mock-model", **kwargs):
        super().__init__(model_name, **kwargs)
    
    def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """Generate mock response."""
        # Simple mock response that tries to extract basic info
        mock_content = '''
        {
            "pmcid": "PMC1234567",
            "article_title": "Mock Article",
            "gene": "CYP2C9",
            "drugs": "warfarin",
            "significance": "yes",
            "direction_of_effect": "decreased",
            "phenotype_category": "Dosage",
            "sentence": "Mock sentence describing the association.",
            "alleles": "CT",
            "comparison_alleles_or_genotypes": "CC"
        }
        '''
        
        return ModelResponse(
            content=mock_content.strip(),
            model_name=self.model_name,
            timestamp=time.time(),
            metadata={"mock": True},
            raw_response=None
        )
    
    def is_available(self) -> bool:
        """Mock model is always available."""
        return True


class PharmacogenomicPromptBuilder:
    """Builds prompts for pharmacogenomic extraction tasks."""
    
    def __init__(self, schema: Dict[str, str], categorical_fields: Dict[str, List[str]]):
        self.schema = schema
        self.categorical_fields = categorical_fields
    
    def build_extraction_prompt(self, article_content: str) -> str:
        """Build prompt for extracting pharmacogenomic annotations."""
        schema_description = self._format_schema()
        examples = self._get_examples()
        
        prompt = f"""
You are a pharmacogenomics expert tasked with extracting structured information from scientific articles. 

Your task is to analyze the following article and extract pharmacogenomic associations in the specified JSON format.

## Schema Description:
{schema_description}

## Important Guidelines:
1. Extract only information that is explicitly stated in the article
2. Use exact values from the categorical fields when applicable
3. For significance, use "yes" if statistically significant, "no" if explicitly not significant, "not stated" if unclear
4. For direction_of_effect, use "increased", "decreased", or null
5. Generate a structured sentence that captures the main finding
6. If multiple associations are described, focus on the primary/most significant one

## Examples:
{examples}

## Article to Analyze:
{article_content}

## Your Response:
Please provide the extracted information as a valid JSON object:
"""
        
        return prompt
    
    def _format_schema(self) -> str:
        """Format schema description for the prompt."""
        schema_lines = []
        for field, description in self.schema.items():
            if field in ['variant_annotation_id', 'pmid', 'article_path']:
                continue  # Skip metadata fields
            
            line = f"- {field}: {description}"
            
            # Add categorical options
            if field in self.categorical_fields:
                options = self.categorical_fields[field]
                if None in options:
                    options = [str(opt) if opt is not None else "null" for opt in options]
                line += f" (Options: {', '.join(str(opt) for opt in options)})"
            
            schema_lines.append(line)
        
        return '\n'.join(schema_lines)
    
    def _get_examples(self) -> str:
        """Get example extractions for few-shot prompting."""
        examples = [
            {
                "context": "Study found that patients with CYP2C9*3 variant required 25% lower warfarin doses compared to wild-type.",
                "output": {
                    "gene": "CYP2C9",
                    "drugs": "warfarin",
                    "variant_haplotypes": "CYP2C9*3",
                    "significance": "yes",
                    "direction_of_effect": "decreased",
                    "phenotype_category": "Dosage",
                    "sentence": "CYP2C9*3 is associated with decreased dose of warfarin compared to wild-type.",
                    "alleles": "*3",
                    "comparison_alleles_or_genotypes": "wild-type"
                }
            },
            {
                "context": "No significant association was found between rs123456 and response to drug X in this population.",
                "output": {
                    "variant_haplotypes": "rs123456",
                    "drugs": "drug X",
                    "significance": "no",
                    "direction_of_effect": None,
                    "phenotype_category": "Efficacy",
                    "sentence": "rs123456 is not associated with response to drug X.",
                    "is_is_not_associated": "Not associated with"
                }
            }
        ]
        
        example_text = ""
        for i, example in enumerate(examples, 1):
            example_text += f"\nExample {i}:\n"
            example_text += f"Context: {example['context']}\n"
            example_text += f"Output: {json.dumps(example['output'], indent=2)}\n"
        
        return example_text
    
    def build_validation_prompt(self, extraction: Dict[str, Any], article_content: str) -> str:
        """Build prompt for validating extractions."""
        prompt = f"""
Please validate the following pharmacogenomic extraction against the source article.

## Extraction to Validate:
{json.dumps(extraction, indent=2)}

## Source Article:
{article_content[:2000]}...

## Validation Task:
1. Check if the extracted information is accurate and supported by the article
2. Identify any missing key information
3. Flag any potential errors or inconsistencies

Please provide a validation report in JSON format with:
- "is_valid": boolean
- "confidence_score": 0-1
- "issues": list of identified problems
- "suggestions": list of improvements
"""
        return prompt


def create_model(model_name: str, **kwargs) -> LanguageModelInterface:
    """Factory function to create language model instances."""
    if model_name.startswith("gpt"):
        return OpenAIModel(model_name, **kwargs)
    elif model_name.startswith("claude"):
        return AnthropicModel(model_name, **kwargs)
    elif model_name == "mock":
        return MockModel(model_name, **kwargs)
    else:
        raise ValueError(f"Unsupported model: {model_name}")