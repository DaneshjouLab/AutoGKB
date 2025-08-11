from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Any, List
from dataclasses import dataclass, field
from loguru import logger
from Bio import Entrez
import requests



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
        super().__init__()
        self.register_handler(self.lookup_star_allele)

    def name(self):
        return "Star Allele Normalizer"

    def lookup_star_allele(self, raw: str) -> Optional[NormalizationResult]:
        """
        Normalize a star allele (e.g., CYP2D6*4) using the Clinical Tables API.
        Returns a NormalizationResult with detailed metadata.
        """
        query = raw.strip()
        if not query:
            logger.debug("Empty star allele input, skipping.")
            return None

        try:
            alleles = self.fetch_star_alleles(query, max_results=1)
            if not alleles:
                logger.debug("No star allele found for input: %s", query)
                return None

            allele_data = alleles[0]

            return NormalizationResult(
                raw_input=raw,
                normalized_output=allele_data.get("StarAlleleName", query),
                entity_type="variant",
                source="PharmVar/Clinical Tables",
                metadata=allele_data,
            )

        except Exception as exc:
            logger.warning("Star allele lookup failed for '%s': %s", raw, exc)
            return None

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

def extract_variants_from_annotations():
    """
    Extract and normalize variants from annotation files.
    This demonstrates the core functionality for mapping variants to normalized ontologies.
    """
    import json
    import os
    import re
    from typing import Set, List, Dict, Any

    # Initialize normalizers
    rsid_normalizer = RSIDNormalizer(email="test@example.com")
    star_normalizer = StarAlleleNormalizer()

    annotation_dir = (
        "data/annotations"
    )
    if not os.path.exists(annotation_dir):
        print(f"❌ Annotation directory not found: {annotation_dir}")
        return

    variants_found: Set[str] = set()
    normalized_results: List[Dict[str, Any]] = []

    print("🔍 Scanning annotation files for variants...")

    # Scan all annotation files
    for filename in os.listdir(annotation_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(annotation_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Extract polymorphisms from annotations
            if "annotations" in data and "relationships" in data["annotations"]:
                for relationship in data["annotations"]["relationships"]:
                    polymorphism = relationship.get("polymorphism", "")

                    # Extract rsIDs (rs followed by numbers)
                    rsids = re.findall(r"rs\d+", polymorphism)
                    variants_found.update(rsids)

                    # Extract star alleles (gene*number pattern)
                    star_alleles = re.findall(r"[A-Z0-9]+\*\d+", polymorphism)
                    variants_found.update(star_alleles)

        except Exception as e:
            print(f"⚠️  Error processing {filename}: {e}")

    print(f"📊 Found {len(variants_found)} unique variants")

    # Normalize each variant
    for variant in variants_found:
        print(f"\n🧬 Processing variant: {variant}")

        result = None
        normalizer_used = None

        # Try rsID normalization first
        if variant.startswith("rs"):
            result = rsid_normalizer.normalize(variant)
            normalizer_used = "RSIDNormalizer"

        # Try star allele normalization if rsID didn't work
        if not result and "*" in variant:
            result = star_normalizer.normalize(variant)
            normalizer_used = "StarAlleleNormalizer"

        if result:
            print(f"✅ {normalizer_used} successful:")
            print(f"   Raw: {result.raw_input}")
            print(f"   Normalized: {result.normalized_output}")
            print(f"   Source: {result.source}")
            print(f"   Type: {result.entity_type}")

            normalized_results.append(
                {
                    "raw_variant": variant,
                    "normalizer": normalizer_used,
                    "result": result,
                }
            )
        else:
            print(f"❌ No normalization found for {variant}")

    print(
        f"\n📈 Summary: {len(normalized_results)}/{len(variants_found)} variants successfully normalized"
    )
    return normalized_results


def test_individual_normalizers():
    """Test each normalizer with sample data"""
    print("\n" + "=" * 50)
    print("🧪 TESTING INDIVIDUAL NORMALIZERS")
    print("=" * 50)

    # Test RSIDNormalizer
    print("\n🧬 Testing RSIDNormalizer:")
    rsid_normalizer = RSIDNormalizer(email="test@example.com")
    test_rsids = ["rs1799853", "rs1057910", "rs9923231"]

    for rsid in test_rsids:
        print(f"\n Testing {rsid}:")
        result = rsid_normalizer.normalize(rsid)
        if result:
            print(f"  ✅ Found: {result.normalized_output} from {result.source}")
        else:
            print(f"  ❌ Not found")

    # Test StarAlleleNormalizer
    print("\n⭐ Testing StarAlleleNormalizer:")
    star_normalizer = StarAlleleNormalizer()
    test_alleles = ["CYP2D6*4", "CYP2C9*2", "CYP2C9*3"]

    for allele in test_alleles:
        print(f"\n Testing {allele}:")
        result = star_normalizer.normalize(allele)
        if result:
            print(f"  ✅ Found: {result.normalized_output} from {result.source}")
            if result.metadata:
                activity = result.metadata.get("InVivoEnzymeActivity")
                if activity:
                    print(f"  📊 Activity: {activity}")
        else:
            print(f"  ❌ Not found")


if __name__ == "__main__":
    pass

    print("🎯 AutoGKB Variant Ontology Normalization System")
    print("=" * 60)

    # Test individual normalizers first
    test_individual_normalizers()

    # Then demonstrate with real annotation data
    print("\n" + "=" * 50)
    print("📋 PROCESSING ANNOTATION DATA")
    print("=" * 50)

    results = extract_variants_from_annotations()

    if results:
        print(f"\n🎉 Successfully processed annotation data!")
        print(f"   Normalized {len(results)} variants")
    else:
        print("\n⚠️  No results from annotation processing")
