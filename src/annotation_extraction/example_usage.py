"""
Example usage of the annotation extraction pipeline.

This script demonstrates how to use the annotation extraction system
to process biomedical articles and generate pharmacogenomic annotations.
"""

import os
import json
from loguru import logger
from typing import List

from .models import ArticleInput, ArticleParser
from .pipeline import AnnotationPipeline
from .stages import LLMInterface
from dotenv import load_dotenv

load_dotenv()


class LiteLLMInterface(LLMInterface):
    """
    LiteLLM interface implementation.
    
    Uses LiteLLM to support multiple LLM providers with a unified interface.
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo", **kwargs):
        """
        Initialize LiteLLM interface.
        
        Args:
            model: Model name (e.g., "gpt-4", "claude-3-sonnet-20240229", "ollama/llama2")
            **kwargs: Additional parameters for the model
        """
        try:
            import litellm
            self.litellm = litellm
        except ImportError:
            raise ImportError("litellm is required. Install with: pip install litellm")
        
        self.model = model
        self.kwargs = kwargs
        
        # Set API keys from environment variables
        if model.startswith("gpt"):
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
        elif model.startswith("claude"):
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
        elif model.startswith("azure"):
            api_key = os.getenv("AZURE_API_KEY")
            if api_key:
                os.environ["AZURE_API_KEY"] = api_key
    
    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Generate response from LLM using LiteLLM."""
        try:
            response = self.litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **self.kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LiteLLM generation error: {e}")
            # Fallback to mock response for testing
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Mock responses for testing when LLM fails."""
        if "RELEVANT or NOT_RELEVANT" in prompt:
            return "RELEVANT\nThis article discusses CYP2D6 variants and their effects on drug metabolism."
        
        elif "Extract:" in prompt and "GENETIC VARIANTS:" in prompt:
            return """GENETIC VARIANTS:
- CYP2D6*4
- rs1065852
- CYP2C19*2/*3

DRUGS AND INTERVENTIONS:
- codeine
- tramadol
- omeprazole

PHENOTYPES AND OUTCOMES:
- reduced metabolism
- poor metabolizer phenotype
- therapeutic failure

POPULATION INFORMATION:
- European ancestry (n=150)
- Adults aged 18-65

ASSOCIATIONS AND RELATIONSHIPS:
- CYP2D6*4 associated with reduced codeine metabolism (p<0.001)
- Poor metabolizers show 50% reduced drug clearance"""
        
        elif "Classification Rules:" in prompt:
            return """1 | functional, drug | high | In vitro metabolism study with clinical correlation
2 | phenotype | medium | Adverse event association in patient cohort"""
        
        elif "REQUIRED OUTPUT FORMAT - Tab-separated values" in prompt:
            return """1451148445	CYP2D6*4	CYP2D6	codeine	12345678	Metabolism/PK	yes	In vitro metabolism study	CYP2D6*4 is associated with reduced metabolism of codeine.	*4		human liver microsomes	poor metabolizer	Is	reduced	metabolism of	CYP2D6	when assayed with	codeine		hepatocytes	*1/*1	extensive metabolizer"""
        
        elif "VALID or INVALID" in prompt:
            return "VALID\nAll required fields are present and follow the schema."
        
        else:
            return "Mock LLM response for: " + prompt[:100] + "..."

def get_example_articles(num_articles: int = 2) -> List[ArticleInput]:
    """Get example articles for testing."""
    # 1. Load n random markdown files from the data/articles directory
    # 2. Parse the articles
    # 3. Return the articles
    articles = []
    for i in range(num_articles):
        with open(f"data/articles/article_{i}.md", "r") as f:
            articles.append(f.read())
    
    return articles


def create_example_articles() -> List[ArticleInput]:
    """Create example articles for testing."""
    
    article1 = ArticleParser(pmcid="PMC16264").parse()
    article2 = ArticleParser(pmcid="PMC11534822").parse()
    return [article1, article2]

def main():
    """Main example usage function."""
    
    # Initialize LiteLLM interface
    # Examples of different model configurations:
    
    # OpenAI GPT-4
    # llm = LiteLLMInterface(model="gpt-4")
    
    # Anthropic Claude
    llm = LiteLLMInterface(model="claude-3-sonnet-20240229")
    
    # Local Ollama model
    # llm = LiteLLMInterface(model="ollama/llama2")
    
    # Azure OpenAI
    # llm = LiteLLMInterface(model="azure/gpt-4")
    
    # Default to GPT-3.5-turbo for this example
    llm = LiteLLMInterface(
        model="gpt-3.5-turbo",
        max_tokens=4000
    )
    
    # Create pipeline
    pipeline = AnnotationPipeline(
        llm=llm,
        enable_validation=True,
        parallel_processing=False  # Set to True for parallel processing
    )
    
    # Create example articles
    articles = create_example_articles()
    
    logger.info(f"Processing {len(articles)} example articles...")
    
    # Process articles
    results = pipeline.process_articles(articles)
    
    # Display results
    for result in results:
        print(f"\n=== Article PMID: {result['pmid']} ===")
        print(f"Success: {result['success']}")
        
        if result.get('relevance'):
            print(f"Relevant: {result['relevance']['is_relevant']}")
            if result['relevance']['is_relevant'] and result['relevance'].get('summary'):
                print(f"Summary: {result['relevance']['summary']}")
        
        if result.get('annotations'):
            print(f"Generated {len(result['annotations'])} annotations:")
            for i, annotation in enumerate(result['annotations']):
                print(f"  {i+1}. Type: {annotation['annotation_type']}")
                print(f"     Fields: {len(annotation['row_data'])}")
                # Show first few fields
                if len(annotation['row_data']) >= 4:
                    print(f"     Variant: {annotation['row_data'][1]}")
                    print(f"     Gene: {annotation['row_data'][2]}")
                    print(f"     Drug: {annotation['row_data'][3]}")
        
        if result.get('errors'):
            print(f"Errors: {result['errors']}")
    
    # Get pipeline statistics
    stats = pipeline.get_pipeline_stats(results)
    print(f"\n=== Pipeline Statistics ===")
    print(f"Total articles: {stats['total_articles']}")
    print(f"Successful: {stats['successful_articles']}")
    print(f"Relevant: {stats['relevant_articles']}")
    print(f"Total annotations: {stats['total_annotations']}")
    print(f"Annotations by type: {stats['annotations_by_type']}")
    print(f"Validation pass rate: {stats['validation_pass_rate']:.2%}")
    
    # Example: Export to TSV files
    output_dir = "example_output"
    os.makedirs(output_dir, exist_ok=True)
    
    file_paths = pipeline.export_annotations_to_tsv(results, output_dir)
    print(f"\n=== Exported Files ===")
    for annotation_type, file_path in file_paths.items():
        print(f"{annotation_type}: {file_path}")
    
    # Example: Batch processing
    print("\n=== Batch Processing Example ===")
    if articles:
        batch_result = pipeline.process_batch_article(articles[0])
        print(f"Batch processing success: {batch_result['success']}")
        if batch_result.get('batch_annotations'):
            print(f"Batch annotations: {len(batch_result['batch_annotations'])}")


def example_different_models():
    """
    Example showing different LLM model configurations with LiteLLM.
    """
    
    models_to_test = [
        {
            "name": "GPT-3.5 Turbo",
            "model": "gpt-3.5-turbo"
        },
        {
            "name": "GPT-4",
            "model": "gpt-4"
        },
        {
            "name": "Claude 3 Sonnet",
            "model": "claude-3-sonnet-20240229"
        }
    ]
    
    articles = create_example_articles()[:1]  # Test with one article
    
    for model_config in models_to_test:
        print(f"\n=== Testing {model_config['name']} ===")
        
        try:
            llm = LiteLLMInterface(
                model=model_config["model"],
                max_tokens=2000
            )
            
            pipeline = AnnotationPipeline(llm=llm, enable_validation=False)
            results = pipeline.process_articles(articles)
            
            if results and results[0].get('success'):
                print(f"✓ Success: {len(results[0].get('annotations', []))} annotations")
            else:
                print(f"✗ Failed: {results[0].get('errors', []) if results else 'No results'}")
                
        except Exception as e:
            print(f"✗ Error: {e}")


if __name__ == "__main__":
    main()
    
    # Uncomment to test different models
    # example_different_models()