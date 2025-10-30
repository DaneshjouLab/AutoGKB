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
from pathlib import Path


class VariantSearchResult(BaseModel):
    raw_input: str
    id: str
    name: str
    url: str
    score: float


def pgkb_star_allele_search(
    star_allele: str, threshold: float = 0.8, top_k: int = 1
) -> Optional[List[VariantSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/haplotype?symbol="
    response = requests.get(base_url + star_allele)
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(star_allele, data["data"][0]["symbol"])
        if data["data"]:
            return [
                VariantSearchResult(
                    raw_input=star_allele,
                    id=result["id"],
                    name=result["symbol"],
                    url=f"https://www.clinpgx.org/haplotype/{result['id']}",
                    score=score,
                )
                for result in data["data"]
            ]
    return []


def pgkb_rsid_search(
    rsid: str, threshold: float = 0.8, top_k: int = 1
) -> Optional[List[VariantSearchResult]]:
    base_url = "https://api.pharmgkb.org/v1/data/variant?symbol="
    response = requests.get(base_url + rsid.strip())
    if response.status_code == 200:
        data = response.json()
        score = calc_similarity(rsid, data["data"][0]["symbol"])
        if data["data"]:
            return [
                VariantSearchResult(
                    raw_input=rsid,
                    id=result["id"],
                    name=result["symbol"],
                    url=f"https://www.clinpgx.org/variant/{result['id']}",
                    score=score,
                )
                for result in data["data"]
            ]
    return []


class VariantLookup(BaseModel):
    """
    Lookup class for variants
    Uses PharmGKB (local and API access) to find variant information

    Usage:
    variant_lookup = VariantLookup()
    variant_lookup.search("rs12345")
    """

    # Base data directory; expects TSV at `<data_dir>/term_lookup_info/variants.tsv`
    data_dir: Path = Path("data")

    def _data_path(self) -> Path:
        return self.data_dir / "term_lookup_info" / "variants.tsv"

    def _clinpgx_variant_search(
        self, variant: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for variants
        1. Searches through the Variant Name column for similarity
        2. Searches through comma separated Synonyms column for similarity
        """
        df = pd.read_csv(self._data_path(), sep="\t")
        results = general_search(
            df, variant, "Variant Name", "Variant ID", threshold=threshold, top_k=top_k
        )
        results.extend(
            general_search_comma_list(
                df, variant, "Synonyms", "Variant ID", threshold=threshold, top_k=top_k
            )
        )
        results.sort(key=lambda x: x["score"], reverse=True)
        if results:
            return [
                VariantSearchResult(
                    raw_input=variant,
                    id=result["Variant ID"],
                    name=result["Variant Name"],
                    url=f"https://www.clinpgx.org/variant/{result['Variant ID']}",
                    score=result["score"],
                )
                for result in results[:top_k]
            ]
        return []

    def star_lookup(
        self, star_allele: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for star alleles
        """
        results = pgkb_star_allele_search(star_allele, threshold=threshold, top_k=top_k)
        results.extend(
            self._clinpgx_variant_search(star_allele, threshold=threshold, top_k=top_k)
        )
        results.sort(key=lambda x: x.score, reverse=True)
        if results:
            return results[:top_k]
        return []

    def rsid_lookup(
        self, rsid: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        """
        Search flow for rsids
        """
        results = pgkb_rsid_search(rsid, threshold=threshold, top_k=top_k)
        results.extend(
            self._clinpgx_variant_search(rsid, threshold=threshold, top_k=top_k)
        )
        results.sort(key=lambda x: x.score, reverse=True)
        if results:
            return results[:top_k]
        return []

    def search(
        self, variant: str, threshold: float = 0.8, top_k: int = 1
    ) -> Optional[List[VariantSearchResult]]:
        # Check if it starts with "rs"
        if variant.strip().startswith("rs"):
            return self.rsid_lookup(variant, threshold=threshold, top_k=top_k)
        else:
            return self.star_lookup(variant, threshold=threshold, top_k=top_k)
