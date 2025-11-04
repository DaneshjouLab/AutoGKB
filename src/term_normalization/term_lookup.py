"""
Wrapper lookup for Variant and Drug Search
"""

from src.term_normalization.variant_search import VariantLookup
from src.term_normalization.drug_search import DrugLookup
from typing import Optional, List
from src.term_normalization.variant_search import VariantSearchResult
from src.term_normalization.drug_search import DrugSearchResult
from enum import Enum
import shutil
import json
import os
from loguru import logger
from pathlib import Path


class TermType(Enum):
    VARIANT = "variant"
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
        if term_type == TermType.VARIANT:
            return self.lookup_variant(term, threshold=threshold, top_k=top_k)
        elif term_type == TermType.DRUG:
            return self.lookup_drug(term, threshold=threshold, top_k=top_k)


def normalize_annotation(input_annotation: Path, output_annotation: Path):
    """
    Take a JSON file with a single annotation and normalize the terms using the TermLookup class.
    Output a new JSON file with the normalized terms.

    Args:
        input_annotation (Path): Path to the raw annotation file
        output_annotation (Path): Path to the output file
    """
    # Load the annotations file
    annotations = None
    try:
        with open(input_annotation, "r") as f:
            annotations = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load annotations file: {e}")
        return

    # Initialize the TermLookup class
    term_lookup = TermLookup()

    # Iterate through the annotations and normalize the terms
    annotation_types = ["var_pheno_ann", "var_fa_ann", "var_drug_ann"]
    saved_mappings = {}

    # Iterate through each annotation type
    for ann_type in annotation_types:
        if ann_type in annotations:
            # Iterate through each annotation in the list
            for annotation in annotations[ann_type]:
                # Normalize Variant/Haplotypes if present
                if (
                    "Variant/Haplotypes" in annotation
                    and annotation["Variant/Haplotypes"]
                ):
                    variant_term = annotation["Variant/Haplotypes"]
                    results = term_lookup.search(
                        variant_term, term_type=TermType.VARIANT
                    )
                    if results:
                        saved_mappings[variant_term] = results[0].to_dict()
                        annotation["Variant/Haplotypes_normalized"] = results[0].id

                # Normalize Drug(s) if present
                if "Drug(s)" in annotation and annotation["Drug(s)"]:
                    drug_term = annotation["Drug(s)"]
                    results = term_lookup.search(drug_term, term_type=TermType.DRUG)
                    if results:
                        saved_mappings[drug_term] = results[0].to_dict()
                        annotation["Drug(s)_normalized"] = results[0].id

    # Add saved mappings to annotations
    annotations["term_mappings"] = saved_mappings

    # Save the normalized annotations to a file
    try:
        os.makedirs(output_annotation.parent, exist_ok=True)
        with open(output_annotation, "w") as f:
            json.dump(annotations, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save annotations file: {e}")
        return

    logger.info(f"Successfully normalized annotations file: {output_annotation}")


if __name__ == "__main__":
    input_annotation = Path("data/example_annotation.json")
    output_annotation = Path("data/example_annotation_normalized.json")
    normalize_annotation(input_annotation, output_annotation)
