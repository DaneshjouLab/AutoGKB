from pydantic import BaseModel
from typing import List

class Variant(BaseModel):
    """Variant."""

    variant_id: str
    gene: str | None = None
    allele: str | None = None
    evidence: str | None = None


class VariantList(BaseModel):
    """List of variants."""

    variant_list: List[Variant]