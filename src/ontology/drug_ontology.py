from typing import Optional
from loguru import logger
from .variant_ontology import BaseNormalizer, NormalizationResult

import requests

# how to use, you have thew following,
<<<<<<< HEAD:src/ontology/drug_ontology.py

=======
>>>>>>> origin/main:src/ontology_module/drug_ontology.py




class DrugNormalizer(BaseNormalizer):
    """Normalizes drug names, and connect to common ID's per use."""

    def __init__(self):
        super().__init__()

        self.register_handler(self.lookup_drug_pubchem)

        # TODO: insert logic to handle base generic instead of what we have

        self.register_handler(self.lookup_drug_pharmgkb)
<<<<<<< HEAD:src/ontology/drug_ontology.py
        self.register_handler(self.lookup_drug_rxnorm)
=======
>>>>>>> origin/main:src/ontology_module/drug_ontology.py
        # register the pubchem first before I register the other.

    def name(self):
        return "Drug Normalizer"

    def lookup_drug_pubchem(self, raw: str) -> Optional[NormalizationResult]:
        """
        Normalize a raw drug name via PubChem, return structured result.
        """
        query = raw.strip()
        if not query:
            logger.debug("Empty drug input, skipping.")
            return None

        try:
            # Step 1: Fetch CID
            cid_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/cids/JSON"
            cid_resp = requests.get(cid_url, timeout=5)
            cid_resp.raise_for_status()
            cid_data = cid_resp.json()
            cid_list = cid_data.get("IdentifierList", {}).get("CID", [])
            if not cid_list:
                logger.debug("No CID found for input: %s", query)
                return None
            cid = cid_list[0]

            # Step 2: Fetch chemical properties
            prop_url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
                f"{cid}/property/IUPACName,MolecularFormula,CanonicalSMILES/JSON"
            )
            prop_resp = requests.get(prop_url, timeout=5)
            prop_resp.raise_for_status()
            prop_data = prop_resp.json()
            props = prop_data["PropertyTable"]["Properties"][0]

            return NormalizationResult(
                raw_input=raw,
                normalized_output=props.get("IUPACName", query),
                entity_type="drug",
                source="PubChem",
                metadata={
                    "cid": cid,
                    "molecular_formula": props.get("MolecularFormula"),
                    "canonical_smiles": props.get("CanonicalSMILES"),
                },
            )

        except requests.RequestException as exc:
            logger.warning("Request failed for '%s': %s", raw, exc)
        except Exception as exc:
            logger.warning("Unexpected error for '%s': %s", raw, exc)

        return None

    def get_generic_from_brand_pubchem(self, raw: str) -> Optional[str]:
        """
        Resolves a brand name to a generic (IUPAC) name using PubChem.
        Returns the normalized_output from lookup_drug_pubchem, or None.
        """
        result = self.lookup_drug_pubchem(raw)
        if result:
            return result.normalized_output
        return None

    def lookup_drug_pharmgkb(self, raw: str) -> Optional[NormalizationResult]:
        """
        Lookup drug info from PharmGKB using its REST API.
        Returns all available metadata without filtering.
        """
        query = raw.strip().lower()
        if not query:
            logger.debug("Empty drug input for PharmGKB lookup.")
            return None

        try:
            url = (
                "https://api.pharmgkb.org/v1/data/chemical"
                f"?name={requests.utils.quote(query)}&view=max"
            )
            headers = {"accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            results = data.get("data", [])
            if not results:
                logger.debug("No PharmGKB chemical match found for: %s", query)
                return None

            entry = results[0]  # Always take the first match

            return NormalizationResult(
                raw_input=raw,
                normalized_output=entry.get("name", raw),
                entity_type="drug",
                source="PharmGKB",
                metadata=entry,  # Store the entire returned dictionary
            )

        except requests.RequestException as exc:
            logger.warning("PharmGKB request failed for '%s': %s", raw, exc)
        except Exception as exc:
            logger.warning(
                "Unexpected error during PharmGKB lookup for '%s': %s", raw, exc
            )

        return None

    def lookup_drug_rxnorm(self, raw: str) -> Optional[NormalizationResult]:
        """
        Resolves a drug name (brand or generic) using the RxNorm API.
        Returns a NormalizationResult with the generic name and RxNorm metadata.
        """
        query = raw.strip()
        if not query:
            logger.debug("Empty drug input for RxNorm lookup.")
            return None

        try:
            # Step 1: Get RxCUI for input name
            rxcui_url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={requests.utils.quote(query)}"
            rxcui_resp = requests.get(rxcui_url, timeout=5)
            rxcui_resp.raise_for_status()
            rxcui_data = rxcui_resp.json()
            rxcui_list = rxcui_data.get("idGroup", {}).get("rxnormId", [])
            if not rxcui_list:
                logger.debug("No RxCUI found for input: %s", query)
                return None
            rxcui = rxcui_list[0]

            # Step 2: Get related ingredient (generic) names from RxCUI
            related_url = (
                f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=IN"
            )
            related_resp = requests.get(related_url, timeout=5)
            related_resp.raise_for_status()
            related_data = related_resp.json()

            concepts = related_data.get("relatedGroup", {}).get("conceptGroup", [])
            ingredients = []
            for group in concepts:
                if group.get("tty") == "IN":
                    for concept in group.get("conceptProperties", []):
                        ingredients.append(concept.get("name"))

            if not ingredients:
                logger.debug("No generic (IN) concept found for RxCUI: %s", rxcui)
                return None

            return NormalizationResult(
                raw_input=raw,
                normalized_output=ingredients[0],  # first generic match
                entity_type="drug",
                source="RxNorm",
                metadata={"rxcui": rxcui, "generic_candidates": ingredients},
            )

        except requests.RequestException as exc:
            logger.warning("RxNorm request failed for '%s': %s", raw, exc)
        except Exception as exc:
            logger.warning("Unexpected error in RxNorm lookup for '%s': %s", raw, exc)

        return None


def test_lookup_pubchem():
    normalizer = DrugNormalizer()
    drug = "Imatinib"
    result = normalizer.lookup_drug_pubchem(drug)

    print(f"\n[PubChem] Input: {drug}")
    if result is None:
        print("❌ No result returned.")
    else:
        print("✅ Result:")
        print(f"  Raw:         {result.raw_input}")
        print(f"  Normalized:  {result.normalized_output}")
        print(f"  Source:      {result.source}")
        print(f"  Entity Type: {result.entity_type}")
        print(f"  CID:         {result.metadata.get('cid')}")
        print(f"  SMILES:      {result.metadata.get('canonical_smiles')}")
        assert isinstance(result, NormalizationResult)
        assert result.source == "PubChem"
        assert result.entity_type == "drug"
        assert "canonical_smiles" in result.metadata


def test_lookup_pharmgkb():
    normalizer = DrugNormalizer()
    drug = "Gleevec"  # Brand name for Imatinib
    print("TEST LOOKUP PHARMGKB")
    generic = normalizer.get_generic_from_brand_pubchem("Gleevec")
    print(generic)
    result = normalizer.lookup_drug_pharmgkb(drug)

    print(f"\n[PharmGKB] Input: {drug}")
    if result is None:
        print("❌ No result returned.")
    else:
        print("✅ Result:")
        print(f"  Raw:         {result.raw_input}")
        print(f"  Normalized:  {result.normalized_output}")
        print(f"  Source:      {result.source}")
        print(f"  Entity Type: {result.entity_type}")
        print(f"  PharmGKB ID: {result.metadata.get('id')}")
        print(f"  Brand Names: {result.metadata.get('brandNames')}")
        assert isinstance(result, NormalizationResult)
        assert result.source == "PharmGKB"
        assert result.entity_type == "drug"
        assert "id" in result.metadata


<<<<<<< HEAD:src/ontology/drug_ontology.py
def extract_drugs_from_annotations():
    """
    Extract and normalize drugs from annotation files.
    This demonstrates drug normalization from real annotation data.
    """
    import json
    import os
    import re
    from typing import Set, List, Dict, Any

    drug_normalizer = DrugNormalizer()

    annotation_dir = (
        "/Users/shloknatarajan/stanford/research/daneshjou/AutoGKB/data/annotations"
    )
    if not os.path.exists(annotation_dir):
        print(f"❌ Annotation directory not found: {annotation_dir}")
        return

    drugs_found: Set[str] = set()
    normalized_results: List[Dict[str, Any]] = []

    print("🔍 Scanning annotation files for drugs...")

    # Common drug name patterns to look for
    drug_patterns = [
        r"\b(?:warfarin|imatinib|gleevec|sitagliptin|gliclazide|metformin|edoxaban)\b",
        r"\b\w+mab\b",  # monoclonal antibodies
        r"\b\w+ine\b",  # many drugs end in -ine
        r"\b\w+ol\b",  # many drugs end in -ol
    ]

    # Scan all annotation files
    for filename in os.listdir(annotation_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(annotation_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Extract drugs from title and content
            text_content = data.get("title", "") + " "

            # Also check study parameters for drug mentions
            if "study_parameters" in data:
                for section in data["study_parameters"].values():
                    if isinstance(section, dict) and "content" in section:
                        if isinstance(section["content"], str):
                            text_content += section["content"] + " "
                        elif isinstance(section["content"], list):
                            text_content += (
                                " ".join(str(item) for item in section["content"]) + " "
                            )

            # Apply drug patterns
            for pattern in drug_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                drugs_found.update(match.lower() for match in matches)

        except Exception as e:
            print(f"⚠️  Error processing {filename}: {e}")

    print(f"📊 Found {len(drugs_found)} potential drug names")

    # Normalize each drug
    for drug in drugs_found:
        if len(drug) < 3:  # Skip very short matches
            continue

        print(f"\n💊 Processing drug: {drug}")

        result = drug_normalizer.normalize(drug)

        if result:
            print(f"✅ Normalization successful:")
            print(f"   Raw: {result.raw_input}")
            print(f"   Normalized: {result.normalized_output}")
            print(f"   Source: {result.source}")
            print(f"   Type: {result.entity_type}")

            if result.metadata:
                if "cid" in result.metadata:
                    print(f"   PubChem CID: {result.metadata['cid']}")
                if "molecular_formula" in result.metadata:
                    print(f"   Formula: {result.metadata['molecular_formula']}")

            normalized_results.append({"raw_drug": drug, "result": result})
        else:
            print(f"❌ No normalization found for {drug}")

    print(
        f"\n📈 Summary: {len(normalized_results)}/{len(drugs_found)} drugs successfully normalized"
    )
    return normalized_results


def test_drug_normalizers():
    """Test drug normalizer with sample data"""
    print("\n" + "=" * 50)
    print("🧪 TESTING DRUG NORMALIZERS")
    print("=" * 50)

    drug_normalizer = DrugNormalizer()
    test_drugs = ["imatinib", "Gleevec", "warfarin", "sitagliptin", "metformin"]

    for drug in test_drugs:
        print(f"\n💊 Testing {drug}:")
        result = drug_normalizer.normalize(drug)
        if result:
            print(f"  ✅ Found: {result.normalized_output} from {result.source}")
            if result.metadata:
                if "cid" in result.metadata:
                    print(f"  🆔 PubChem CID: {result.metadata['cid']}")
                if "molecular_formula" in result.metadata:
                    print(f"  🧪 Formula: {result.metadata['molecular_formula']}")
        else:
            print(f"  ❌ Not found")


if __name__ == "__main__":
    pass

    print("🎯 AutoGKB Drug Ontology Normalization System")
    print("=" * 60)

    # Test individual drug normalizers first
    test_drug_normalizers()

    # Then demonstrate with real annotation data
    print("\n" + "=" * 50)
    print("📋 PROCESSING ANNOTATION DATA FOR DRUGS")
    print("=" * 50)

    results = extract_drugs_from_annotations()

    if results:
        print(f"\n🎉 Successfully processed annotation data!")
        print(f"   Normalized {len(results)} drugs")
    else:
        print("\n⚠️  No results from annotation processing")
=======
if __name__ == "__main__":
    test_lookup_pubchem()

    test_lookup_pharmgkb()
    normalizer = DrugNormalizer()
    result = normalizer.lookup_drug_rxnorm("Gleevec")
    print(result.normalized_output)  # → "imatinib"
>>>>>>> origin/main:src/ontology_module/drug_ontology.py
