from pydantic import BaseModel
from src.load_data import load_raw_variant_annotations

"""
Denotes a class for a variant annotation (row in var_drug_ann.tsv)
"""

class VariantAnnotation(BaseModel):
    variant_annotation_id: str
    variant_haplotypes: str
    gene: str
    drug: str
    pmid: str
    phenotype_category: str
    significance: str
    notes: str
    sentence: str
    alleles: str
    specialty_population: str
    metabolizer_types: str
    phenotype_category: str
    significance: str
    notes: str
    sentence: str
    alleles: str
    specialty_population: str
    metabolizer_types: str
    is_plural: str
    is_associated: str
    direction_of_effect: str
    pd_pk_terms: str
    multiple_drugs_and_or: str
    population_types: str
    population_phenotypes_or_diseases: str
    multiple_phenotypes_or_diseases_and_or: str
    comparison_alleles_or_genotypes: str
    comparison_metabolizer_types: str
    

    
"""
1. Load the ground truth variants
2. Load the extracted variants
3. Calculate the niave difference between an extracted variant and the ground truth variant on Variant Annotation ID
"""

