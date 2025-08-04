

from typing import Optional
import logging
from .variant_ontology import BaseNormalizer, NormalizationResult

import requests

# how to use, you have thew following, 


logger = logging.getLogger(__name__)

class DrugNormalizer(BaseNormalizer):
    """Normalizes drug names, and connect to common ID's per use."""

    def __init__(self):
        super().__init__()
        
        self.register_handler(self.lookup_drug_pubchem)
        


        #TODO: insert logic to handle base generic instead of what we have 

        
        self.register_handler(self.lookup_drug_pharmgkb)
        # register the pubchem first before I register the other. 

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
                metadata=entry  # Store the entire returned dictionary
            )

        except requests.RequestException as exc:
            logger.warning("PharmGKB request failed for '%s': %s", raw, exc)
        except Exception as exc:
            logger.warning("Unexpected error during PharmGKB lookup for '%s': %s", raw, exc)

        return None