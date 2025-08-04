from abc import ABC, abstractmethod
from typing import Callable,Dict, Optional, Any
from dataclasses import dataclass, field
import logging
from Bio import Entrez
import requests

logger = logging.getLogger(__name__)

@dataclass
class NormalizationResult:
    raw_input: str
    normalized_output: str
    entity_type: str         # e.g. "variant", "gene", "drug", etc.
    source: str              # where the normalized info came from
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizationResult":
        return cls(
            raw_input=data["raw_input"],
            normalized_output=data["normalized_output"],
            entity_type=data.get("entity_type", "unknown"),
            source=data["source"],
            metadata=data.get("metadata", {})
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
                logger.exception(f"Handler '{handler.__name__}' failed on input: '{raw}'")
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
                metadata=record
            )

        except Exception:
            logger.exception(f"lookup_dbsnp failed for {raw}")
            return None

    def lookup_pharmgkb_id(self, raw: str) -> Optional[NormalizationResult]:
        logger.debug(f"Looking up PharmGKB variant by symbol: {raw}")

        base_url = "https://api.pharmgkb.org/v1/data/variant"
        params = {
            "symbol": raw.strip(),
            "view": "max"
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"PharmGKB lookup failed ({response.status_code}) for {raw}")
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
                metadata=metadata
            )

        except Exception:
            logger.exception(f"PharmGKB symbol lookup failed for {raw}")
            return None
        
class StarAlleleNormalizer(BaseNormalizer):
    

    def __init__(self):
        pass
    def name(self):
        return "Star Allele Normalizer"
    

    def 
    

        
    


