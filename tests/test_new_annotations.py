#!/usr/bin/env python3
"""
Test script for the new phenotype and functional annotation extraction components.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.components.variant_association_pipeline import run_variant_association_pipeline
from loguru import logger

def test_phenotype_functional_extraction():
    """Test the new phenotype and functional annotation extraction."""
    
    test_pmcid = "PMC5712579"  # This has phenotype annotations based on the sample data
    
    logger.info(f"Testing variant association pipeline with PMCID: {test_pmcid}")
    
    try:
        result = run_variant_association_pipeline(pmcid=test_pmcid)
        
        if result:
            logger.info("Pipeline execution successful!")
            logger.info(f"Drug associations: {len(result.get('drug_associations', []))}")
            logger.info(f"Phenotype associations: {len(result.get('phenotype_associations', []))}")
            logger.info(f"Functional associations: {len(result.get('functional_associations', []))}")
            logger.info(f"Drug annotations: {len(result.get('drug_annotations', []))}")
            logger.info(f"Phenotype annotations: {len(result.get('phenotype_annotations', []))}")
            logger.info(f"Functional annotations: {len(result.get('functional_annotations', []))}")
            
            if 'phenotype_annotations' in result and 'functional_annotations' in result:
                logger.info("✅ New annotation types successfully integrated into pipeline!")
                return True
            else:
                logger.error("❌ New annotation types missing from pipeline result")
                return False
        else:
            logger.error("❌ Pipeline returned None")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        return False

if __name__ == "__main__":
    success = test_phenotype_functional_extraction()
    if success:
        print("✅ Test passed - new annotation extraction components working!")
    else:
        print("❌ Test failed - check logs for details")
        sys.exit(1)
