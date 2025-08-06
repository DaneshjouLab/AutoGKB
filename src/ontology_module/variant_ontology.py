from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Any, List
from dataclasses import dataclass, field
import logging
from Bio import Entrez
import requests

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    raw_input: str
    normalized_output: str
    entity_type: str  # e.g. "variant", "gene", "drug", etc.
    source: str  # where the normalized info came from
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizationResult":
        return cls(
            raw_input=data["raw_input"],
            normalized_output=data["normalized_output"],
            entity_type=data.get("entity_type", "unknown"),
            source=data["source"],
            metadata=data.get("metadata", {}),
        )


class BaseNormalizer(ABC):
    def __init__(self):
        self._handlers: list[Callable[[str], Optional[dict]]] = []

    def register_handler(self, handler: Callable[[str], Optional[dict]]):
        self._handlers.append(handler)

    def normalize(self, raw: str) -> Optional["NormalizationResult"]:
        for handler in self._handlers:
            try:
                result = handler(raw)
                if result:
                    return result  # Assuming result is already a NormalizedEntity
            except Exception as e:
                logger.exception(
                    f"Handler '{handler.__name__}' failed on input: '{raw}'"
                )
        return None

    @abstractmethod
    def name(self) -> str:
        pass


class RSIDNormalizer(BaseNormalizer):
    def __init__(self, email: str, api_key: Optional[str] = None):
        super().__init__()
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key

        self.register_handler(self.lookup_dbsnp)
        self.register_handler(self.lookup_pharmgkb_id)

    def name(self) -> str:
        return "RSIDNormalizer"

    def lookup_dbsnp(self, raw: str) -> Optional[NormalizationResult]:
        rsid = raw.lower().strip()
        if not rsid.startswith("rs") or not rsid[2:].isdigit():
            return None

        try:
            handle = Entrez.esummary(db="snp", id=rsid[2:], retmode="json")
            response = handle.read()
            handle.close()

            # Convert JSON string to Python dict
            import json

            data = json.loads(response)

            record = data.get("result", {}).get(rsid[2:])
            if not record:
                return None

            return NormalizationResult(
                raw_input=raw,
                normalized_output=rsid,
                entity_type="variant",
                source="dbSNP",
                metadata=record,
            )

        except Exception:
            logger.exception(f"lookup_dbsnp failed for {raw}")
            return None

    def lookup_pharmgkb_id(self, raw: str) -> Optional[NormalizationResult]:
        logger.debug(f"Looking up PharmGKB variant by symbol: {raw}")

        base_url = "https://api.pharmgkb.org/v1/data/variant"
        params = {"symbol": raw.strip(), "view": "max"}

        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(
                    f"PharmGKB lookup failed ({response.status_code}) for {raw}"
                )
                return None

            data = response.json()
            records = data.get("data", [])
            if not records:
                logger.info(f"No PharmGKB variant match for symbol: {raw}")
                return None

            variant = records[0]

            # Extract only required fields
            normalized_output = variant.get("id")
            entity_type = "variant"
            source = "PharmGKB"

            # Remove known fields so everything else is dumped into metadata
            metadata = {k: v for k, v in variant.items() if k not in {"id"}}

            return NormalizationResult(
                raw_input=raw,
                normalized_output=normalized_output,
                entity_type=entity_type,
                source=source,
                metadata=metadata,
            )

        except Exception:
            logger.exception(f"PharmGKB symbol lookup failed for {raw}")
            return None


class StarAlleleNormalizer(BaseNormalizer):
    API_URL = "https://clinicaltables.nlm.nih.gov/api/star_alleles/v3/search"

    def __init__(self):
        pass

    def name(self):
        return "Star Allele Normalizer"

    def fetch_star_alleles(
        self, query: str, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetches all star allele records matching the query string from the PharmVar-backed Clinical Tables API.
        Returns a list of dictionaries, one per allele, with all available fields populated.
        """
        fields = [
            "StarAlleleName",
            "GenBank",
            "ProteinAffected",
            "cDNANucleotideChanges",
            "GeneNucleotideChange",
            "XbaIHaplotype",
            "RFLP",
            "OtherNames",
            "ProteinChange",
            "InVivoEnzymeActivity",
            "InVitroEnzymeActivity",
            "References",
            "ClinicalPhenotype",
            "Notes",
        ]

        params = {"terms": query, "count": max_results, "ef": ",".join(fields)}

        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return []

        try:
            total_count, allele_names, extra_fields, *_ = response.json()
        except Exception as e:
            logger.error(f"Failed to parse API response: {e}")
            return []

        results = []
        for i, allele in enumerate(allele_names):
            allele_info = {"StarAlleleName": allele}
            for field, values in extra_fields.items():
                allele_info[field] = values[i] if i < len(values) else None
            results.append(allele_info)

        return results

    # def fetch_star_alleles(self, term: str) -> list[dict]:
    #     """
    #     Searches for star alleles matching a term and retrieves full metadata for each.

    #     Args:
    #         term (str): The star allele search string (e.g., "CYP2D6*4").

    #     Returns:
    #         list[dict]: Each dict contains all metadata fields for a matched star allele.
    #     """
    #     base_url = "https://clinicaltables.nlm.nih.gov/api/star_alleles/v3/search"
    #     fields = [
    #         "StarAlleleName", "GenBank", "ProteinAffected", "cDNANucleotideChanges",
    #         "GeneNucleotideChange", "ProteinChange", "OtherNames",
    #         "InVivoEnzymeActivity", "InVitroEnzymeActivity", "References",
    #         "ClinicalPhenotype", "Notes"
    #     ]

    #     params = {
    #         "terms": term,
    #         "ef": ",".join(fields),
    #         "maxList": "50"
    #     }

    #     response = requests.get(base_url, params=params)
    #     response.raise_for_status()
    #     data = response.json()

    #     if not data or len(data) < 3:
    #         return []

    #     codes = data[1]
    #     extra_fields = data[2]

    #     results = []
    #     for i, code in enumerate(codes):
    #         allele_data = {field: extra_fields.get(field, [None])[i] for field in fields}
    #         results.append(allele_data)

    #     return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    normalizer = StarAlleleNormalizer()
    data = normalizer.fetch_star_alleles("CYP2D6*4")

    for record in data:
        print("\n--- Star Allele Record ---")
        for k, v in record.items():
            print(f"{k}: {v}")
