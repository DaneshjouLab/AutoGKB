"""
For an article
1. Extract all variants
2. Determine the association type for each variant

Final output:
- Dictionary of
{
"drug_associations": List[Variant],
"phenotype_associations": List[Variant],
"functional_associations": List[Variant],
}
"""

from typing import Dict, List, Optional
from loguru import logger
from src.components.all_variants import extract_all_variants
from src.components.association_types import get_association_types, AssociationType
from src.utils import get_article_text
from src.variants import Variant

from src.config import DEBUG

class VariantAssociationPipeline:
    """Pipeline to extract variants and determine their association types from an article."""
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
    
    def process_article(
        self, 
        article_text: str = None, 
        pmcid: str = None
    ) -> Dict[str, List[Variant]]:
        """
        Process an article to extract variants and determine their association types.
        
        Args:
            article_text: The text of the article
            pmcid: The PMCID of the article
            
        Returns:
            Dictionary with lists of variants for each association type
        """
        # Get article text
        article_text = get_article_text(pmcid=pmcid, article_text=article_text)
        
        # Step 1: Extract all variants
        logger.info("Step 1: Extracting variants from article")
        variants = extract_all_variants(article_text, pmcid)
        logger.info(f"Extracted {len(variants)} variants: {[v.variant_id for v in variants]}")
        
        if not variants:
            logger.warning("No variants found in article")
            return {
                "drug_associations": [],
                "phenotype_associations": [],
                "functional_associations": []
            }
        
        # Step 2: Determine association types for all variants
        logger.info("Step 2: Determining association types for variants")
        association_types_result = get_association_types(variants, article_text, pmcid)
        
        if association_types_result is None:
            logger.error("Failed to determine association types")
            return {
                "drug_associations": [],
                "phenotype_associations": [],
                "functional_associations": []
            }
        
        # Step 3: Categorize variants by association type
        logger.info("Step 3: Categorizing variants by association type")
        result = self._categorize_variants(variants, association_types_result)
        
        logger.info(f"Final categorization: {len(result['drug_associations'])} drug, "
                   f"{len(result['phenotype_associations'])} phenotype, "
                   f"{len(result['functional_associations'])} functional associations")
        
        return result
    
    def _categorize_variants(
        self, 
        variants: List[Variant], 
        association_types: List[AssociationType]
    ) -> Dict[str, List[Variant]]:
        """
        Categorize variants based on their association types.
        
        Args:
            variants: List of variants
            association_types: List of association type results
            
        Returns:
            Dictionary with variants categorized by association type
        """
        drug_associations = []
        phenotype_associations = []
        functional_associations = []
        
        # Create a mapping from variant_id to association_type for easy lookup
        variant_to_association = {
            assoc.variant.variant_id: assoc for assoc in association_types
        }
        
        for variant in variants:
            association = variant_to_association.get(variant.variant_id)
            
            if association is None:
                logger.warning(f"No association type found for variant {variant.variant_id}")
                continue
            
            # Categorize based on association types
            if association.drug_association:
                drug_associations.append(variant)
                if DEBUG:
                    logger.debug(f"Variant {variant.variant_id} has drug association: {association.drug_association_explanation}")
            
            if association.phenotype_association:
                phenotype_associations.append(variant)
                if DEBUG:
                    logger.debug(f"Variant {variant.variant_id} has phenotype association: {association.phenotype_association_explanation}")
            
            if association.functional_association:
                functional_associations.append(variant)
                if DEBUG:
                    logger.debug(f"Variant {variant.variant_id} has functional association: {association.functional_association_explanation}")
        
        return {
            "drug_associations": drug_associations,
            "phenotype_associations": phenotype_associations,
            "functional_associations": functional_associations
        }


def run_variant_association_pipeline(
    article_text: str = None, 
    pmcid: str = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1
) -> Dict[str, List[Variant]]:
    """
    Convenience function to run the variant association pipeline.
    
    Args:
        article_text: The text of the article
        pmcid: The PMCID of the article
        model: The LLM model to use
        temperature: The temperature for LLM generation
        
    Returns:
        Dictionary with lists of variants for each association type
    """
    pipeline = VariantAssociationPipeline(model=model, temperature=temperature)
    return pipeline.process_article(article_text=article_text, pmcid=pmcid)
    
    