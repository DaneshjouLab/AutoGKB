from pydantic import BaseModel
from typing import List


class Variant(BaseModel):
    """Variant."""

    variant_id: str
    gene: str | None = None
    allele: str | None = None
    evidence: str | None = None


class VariantList(BaseModel):
    """List of variants."""

    variant_list: List[Variant]


class DrugAnnotation(BaseModel):
    """Drug annotation with detailed pharmacogenomic information."""

    variant_annotation_id: int
    variant_haplotypes: str
    gene: str | None = None
    drugs: str
    pmid: int
    phenotype_category: str
    significance: str
    notes: str
    sentence: str
    alleles: str | None = None
    specialty_population: str | None = None
    metabolizer_types: str | None = None
    is_plural: str | None = None
    is_is_not_associated: str
    direction_of_effect: str | None = None
    side_effect_efficacy_other: str | None = None
    phenotype: str | None = None
    multiple_phenotypes_and_or: str | None = None
    when_treated_with_exposed_to: str | None = None
    multiple_drugs_and_or: str | None = None
    population_types: str | None = None
    population_phenotypes_or_diseases: str | None = None
    multiple_phenotypes_or_diseases_and_or: str | None = None
    comparison_alleles_or_genotypes: str | None = None
    comparison_metabolizer_types: str | None = None


class DrugAnnotationList(BaseModel):
    """List of drug annotations for structured output."""

    drug_annotations: List[DrugAnnotation]
