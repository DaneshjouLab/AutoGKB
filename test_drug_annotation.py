"""
Test script to verify the drug annotation extraction functionality.
"""

from src.components.variant_association_pipeline import run_variant_association_pipeline
from src.variants import Variant
from src.components.drug_annotation_extraction import extract_drug_annotations
import json

def test_drug_annotation_extraction():
    """Test the drug annotation extraction with sample data."""
    
    sample_article_text = """

    This study investigated the association between HLA alleles and lamotrigine-induced cutaneous adverse drug reactions in Thai patients with epilepsy.

    We analyzed 15 cases with severe cutaneous adverse reactions (SCAR), Stevens-Johnson Syndrome (SJS), or Maculopapular Exanthema (MPE) and 50 controls who took lamotrigine without adverse events.

    HLA-A*02:07 was more frequent in cases (5/15) than in controls (3/50). The allele was significantly associated when grouping together severe cutaneous adverse reactions, Stevens-Johnson Syndrome, or Maculopapular Exanthema (p < 0.05). HLA-A*02:07 is associated with increased risk of Maculopapular Exanthema, severe cutaneous adverse reactions or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy.

    HLA-B*15:02 showed significant association with increased likelihood of Maculopapular Exanthema or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy (p < 0.01).
    """
    
    sample_variants = [
        Variant(variant_id="HLA-A*02:07", gene="HLA-A", allele="*02:07", evidence="Associated with increased risk"),
        Variant(variant_id="HLA-B*15:02", gene="HLA-B", allele="*15:02", evidence="Significant association")
    ]
    
    print("Testing drug annotation extraction...")
    print(f"Sample variants: {[v.variant_id for v in sample_variants]}")
    
    try:
        annotations = extract_drug_annotations(sample_variants, sample_article_text)
        print(f"Successfully extracted {len(annotations)} drug annotations")
        
        for i, annotation in enumerate(annotations):
            print(f"\nAnnotation {i+1}:")
            print(f"  Variant: {annotation.variant_haplotypes}")
            print(f"  Gene: {annotation.gene}")
            print(f"  Drug: {annotation.drugs}")
            print(f"  Phenotype Category: {annotation.phenotype_category}")
            print(f"  Significance: {annotation.significance}")
            print(f"  Sentence: {annotation.sentence}")
            
    except Exception as e:
        print(f"Error during drug annotation extraction: {e}")
        return False
    
    return True

def test_full_pipeline():
    """Test the full pipeline with drug annotation extraction."""
    
    sample_pmcid = "PMC5712579"
    
    print("\nTesting full pipeline...")
    
    try:
        result = run_variant_association_pipeline(pmcid=sample_pmcid)
        
        print(f"Pipeline results:")
        print(f"  Drug associations: {len(result.get('drug_associations', []))}")
        print(f"  Phenotype associations: {len(result.get('phenotype_associations', []))}")
        print(f"  Functional associations: {len(result.get('functional_associations', []))}")
        print(f"  Drug annotations: {len(result.get('drug_annotations', []))}")
        
        if result.get('drug_annotations'):
            print("\nFirst drug annotation:")
            annotation = result['drug_annotations'][0]
            print(f"  Variant: {annotation.variant_haplotypes}")
            print(f"  Gene: {annotation.gene}")
            print(f"  Drug: {annotation.drugs}")
            
    except Exception as e:
        print(f"Error during full pipeline test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting drug annotation extraction tests...")
    
    success1 = test_drug_annotation_extraction()
    success2 = test_full_pipeline()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
