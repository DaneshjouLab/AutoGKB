from pydantic import BaseModel
from typing import List, Optional, Any
import requests
from src.ontology.search_utils import (
    calc_similarity,
    general_search,
    general_search_comma_list,
)
import pandas as pd
from loguru import logger


class DrugSearchResult(BaseModel):
    raw_input: str
    id: str
    name: str
    url: str
    score: float


# RxNorm Helpers
def get_first_rxnorm_candidate(data):
    """
    Get the first candidate object with RXNORM as the source.

    Args:
        data (dict): The response data dictionary

    Returns:
        dict or None: First candidate with RXNORM source, or None if not found
    """
    candidates = data.get("approximateGroup", {}).get("candidate", [])

    for candidate in candidates:
        if candidate.get("source") == "RXNORM":
            return candidate

    return None


def rxnorm_search(drug_name: str) -> Optional[DrugSearchResult]:
    url = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
    params = {"term": drug_name, "maxEntries": 1}
    response = requests.get(url, params=params, timeout=5)
    if response.status_code == 200:
        data = response.json()
        candidate = get_first_rxnorm_candidate(data)
        if candidate:
            rxcui = candidate["rxcui"]
            url = f"https://ndclist.com/rxnorm/rxcui/{rxcui}"
            name = candidate["name"]
            score = calc_similarity(drug_name, name)
            return DrugSearchResult(
                raw_input=drug_name, id=f"RXN{rxcui}", name=name, url=url, score=score
            )
    return DrugSearchResult(
        raw_input=drug_name, id="", name="Not Found", url="", score=0
    )


def rxcui_to_pa_id(raw_input: str, rxcui: str) -> Optional[List[DrugSearchResult]]:
    """
    Convert a RXCUI to a PharmGKB Accession Id using the 'RxNorm Identifiers' column in drugs.tsv.
    """
    local_path = "clinpgx_data/drugs/drugs.tsv"
    df = pd.read_csv(local_path, sep="\t")
    results = general_search(
        df, rxcui, "RxNorm Identifiers", "PharmGKB Accession Id", threshold=0.8, top_k=1
    )
    # Convert to DrugSearchResult
    if results:
        return [
            DrugSearchResult(
                raw_input=raw_input,
                id=result["PharmGKB Accession Id"],
                name=result["Name"],
                url=f"https://www.clinpgx.org/chemical/{result['PharmGKB Accession Id']}",
                score=result["score"],
            )
            for result in results
        ]
    return []


class DrugLookup(BaseModel):
    """
    Lookup class for drugs
    Uses ClinPGx and RxNorm to find drug information

    Usage:
    drug_lookup = DrugLookup()
    drug_lookup.search("aspirin")
    """

    data_path: str = "data/lookup_data/drugs/drugs.tsv"

    def _clinpgx_drug_name_search(
        self, drug_name: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[DrugSearchResult]]:
        df = pd.read_csv(self.data_path, sep="\t")
        results = general_search(
            df,
            drug_name,
            "Name",
            "PharmGKB Accession Id",
            threshold=threshold,
            top_k=top_k,
        )
        if results:
            return [
                DrugSearchResult(
                    raw_input=drug_name,
                    id=result["PharmGKB Accession Id"],
                    name=result["Name"],
                    url=f"https://www.clinpgx.org/chemical/{result['PharmGKB Accession Id']}",
                    score=result["score"],
                )
                for result in results
            ]
        return []

    def _clinpgx_drug_alternatives_search(
        self, drug_name: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[DrugSearchResult]]:
        """
        Checks generic names and trade names for the drug
        """
        df = pd.read_csv(self.data_path, sep="\t")
        results = general_search_comma_list(
            df,
            drug_name,
            "Generic Names",
            "PharmGKB Accession Id",
            threshold=threshold,
            top_k=top_k,
        )
        results.extend(
            general_search_comma_list(
                df,
                drug_name,
                "Trade Names",
                "PharmGKB Accession Id",
                threshold=threshold,
                top_k=top_k,
            )
        )
        if results:
            return [
                DrugSearchResult(
                    raw_input=drug_name,
                    id=result["PharmGKB Accession Id"],
                    name=result["Name"],
                    url=f"https://www.clinpgx.org/chemical/{result['PharmGKB Accession Id']}",
                    score=result["score"],
                )
                for result in results
            ]
        return []

    def clinpgx_lookup(
        self, drug_name: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[DrugSearchResult]]:
        """
        Main search function that tries name search first, then alternatives search if scores are too low.
        """
        # First try name search
        name_results = self._clinpgx_drug_name_search(
            drug_name, threshold=threshold, top_k=top_k
        )

        # If we have good results from name search, return them
        if name_results and any(result.score >= threshold for result in name_results):
            return name_results

        # Otherwise, try alternatives search
        alternatives_results = self._clinpgx_drug_alternatives_search(
            drug_name, threshold=threshold, top_k=top_k
        )

        # Return the best results between name and alternatives
        all_results = (name_results or []) + (alternatives_results or [])
        if all_results:
            # Sort by score and return top_k
            all_results.sort(key=lambda x: x.score, reverse=True)
            return all_results[:top_k]

        return []

    def rxnorm_lookup(self, drug_name: str) -> Optional[List[DrugSearchResult]]:
        """
        Search using RxNorm and convert results back to PharmGKB format using RxCUI to PA ID mapping.
        """
        # Get RxNorm result
        rxnorm_result = rxnorm_search(drug_name)

        # If no result or empty result, return empty list
        if not rxnorm_result or not rxnorm_result.id or rxnorm_result.id == "":
            return []

        # Extract RxCUI from the ID (remove "RXN" prefix)
        if rxnorm_result.id.startswith("RXN"):
            rxcui = rxnorm_result.id[3:]  # Remove "RXN" prefix
        else:
            rxcui = rxnorm_result.id

        # Convert RxCUI to PharmGKB PA ID
        pharmgkb_results = rxcui_to_pa_id(drug_name, rxcui)

        return pharmgkb_results if pharmgkb_results else []

    def search(
        self, drug_name: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[DrugSearchResult]]:
        # Try ClinPGx first
        results = self.clinpgx_lookup(drug_name, threshold=threshold, top_k=top_k)
        if results:
            return results
        logger.warning("No strong results from ClinPGx, trying RxNorm")
        # If no results from ClinPGx, try RxNorm
        return self.rxnorm_lookup(drug_name)
