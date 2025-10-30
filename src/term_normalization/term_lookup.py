"""
Wrapper lookup for Variant and Drug Search
"""

from src.ontology.variant_search import VariantLookup
from src.ontology.drug_search import DrugLookup
from typing import Optional, List
from src.ontology.variant_search import VariantSearchResult
from src.ontology.drug_search import DrugSearchResult
from enum import Enum


class TermType(Enum):
    POLYMORPHISM = "polymorphism"
    DRUG = "drug"


class TermLookup:
    def __init__(self):
        self.variant_search = VariantLookup()
        self.drug_search = DrugLookup()

    def lookup_variant(
        self, variant: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        return self.variant_search.search(variant, threshold=threshold, top_k=top_k)

    def lookup_drug(
        self, drug: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[DrugSearchResult]]:
        return self.drug_search.search(drug, threshold=threshold, top_k=top_k)

    def search(
        self, term: str, term_type: TermType, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]] | Optional[List[DrugSearchResult]]:
        if term_type == TermType.POLYMORPHISM:
            return self.lookup_variant(term, threshold=threshold, top_k=top_k)
        elif term_type == TermType.DRUG:
            return self.lookup_drug(term, threshold=threshold, top_k=top_k)
