#!/usr/bin/env python3
"""
Simple test to verify the new annotation components can be imported and instantiated.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all new components can be imported successfully."""
    
    try:
        from src.variants import PhenotypeAnnotation, FunctionalAnnotation
        from src.variants import PhenotypeAnnotationList, FunctionalAnnotationList
        print("✅ Data models imported successfully")
        
        from src.components.phenotype_annotation_extraction import extract_phenotype_annotations
        from src.components.functional_annotation_extraction import extract_functional_annotations
        print("✅ Extraction functions imported successfully")
        
        phenotype_data = {
            "variant_annotation_id": 123456789,
            "variant_haplotypes": "HLA-B*35:08",
            "pmid": 29238301,
            "phenotype_category": "Toxicity",
            "significance": "no",
            "notes": "Test notes",
            "sentence": "Test sentence",
            "is_is_not_associated": "Not associated with"
        }
        
        functional_data = {
            "variant_annotation_id": 123456790,
            "variant_haplotypes": "CYP2C19*17",
            "pmid": 29236753,
            "phenotype_category": "Metabolism/PK",
            "significance": "yes",
            "notes": "Test functional notes",
            "sentence": "Test functional sentence",
            "is_is_not_associated": "Associated with"
        }
        
        phenotype_annotation = PhenotypeAnnotation(**phenotype_data)
        functional_annotation = FunctionalAnnotation(**functional_data)
        
        print("✅ Data model instances created successfully")
        print(f"   Phenotype annotation ID: {phenotype_annotation.variant_annotation_id}")
        print(f"   Functional annotation ID: {functional_annotation.variant_annotation_id}")
        
        from src.components.variant_association_pipeline import run_variant_association_pipeline
        print("✅ Pipeline import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n🎉 All tests passed! New annotation components are ready.")
    else:
        print("\n💥 Tests failed - check implementation.")
        sys.exit(1)
