

from typing import Optional
import logging
from variant_ontology import BaseNormalizer,NormalizationResult

import requests

# how to use, you have thew following, 



class DrugNormalizer(BaseNormalizer):
    """Normalizes drug names using PubChem API."""

    def __init__(self):
        super().__init__()

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
                    "canonical_smiles": props.get("CanonicalSMILES")
                }
            )

        except requests.RequestException as exc:
            logger.warning("Request failed for '%s': %s", raw, exc)
        except Exception as exc:
            logger.warning("Unexpected error for '%s': %s", raw, exc)

        return None
    
    def 