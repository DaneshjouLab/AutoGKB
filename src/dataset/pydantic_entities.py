
"""
variant_entities.py

Atomic and composite Pydantic schemas for variant-level annotations in the PharmGKB knowledge extraction pipeline.

This module defines structured representations for genetic entities such as genes, variants (rsIDs),
haplotypes (e.g., star alleles), and gene phenotype groups (e.g., "poor metabolizers").
It also provides compositional schemas for expressing validated annotations, suitable for use in
LLM-based extraction pipelines, structured JSON output, and clinical variant analysis.

Each schema is grounded in PharmGKB’s variant annotation specification and supports validation
compatible with OpenAI tool calling via `model_json_schema()`.

Includes:
- Gene (HGNC symbol)
- Variant (dbSNP rsID)
- Haplotype (star allele)
- GenePhenotypeGroup (e.g. "intermediate activity")
- VariantOrHaplotypeGroup (composite list)
- Drug (PharmGKB-standardized)
- PMID (PubMed ID with format enforcement)
- Significance (categorical)
- AnnotatedEntity (composed variant-drug-gene record)
- VariantAnnotationSentence (structured sentence object)


"""

from typing import List, Union
from pydantic import BaseModel, Field, field_validator, constr
import re

class Variant(BaseModel):
    """
    dbSNP rsID involved in the association.
    """
    rsid: constr(strip_whitespace=True, min_length=3) = Field(
        ..., description="dbSNP rsID (e.g. rs12345) involved in the association."
    )

    @field_validator("rsid")
    @classmethod
    def must_be_rsid(cls, v: str) -> str:
        if not re.fullmatch(r"rs\d{1,}", v):
            raise ValueError("Variant rsID must start with 'rs' followed by digits")
        return v
    
class Haplotype(BaseModel):
    """
    Named haplotype involved in the association (e.g. star allele such as CYP2C19*2).
    """
    name: constr(strip_whitespace=True, min_length=2) = Field(
        ..., description="PharmGKB-standardized haplotype name, e.g. CYP2D6*4 or TPMT*3A."
    )

    @field_validator("name")
    @classmethod
    def valid_star_format(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9]+[*][\w+.\-]+", v):
            raise ValueError("Haplotype must follow format like 'CYP2C19*2'")
        return v
    


class VariantOrHaplotypeGroup(BaseModel):
    """
    One or more entities used in the association, including variants, haplotypes, or gene phenotype groups.
    """
    items: List[Union["Variant", "Haplotype", GenePhenotypeGroup]] = Field(
        ..., 
        description="List of rsIDs, haplotype names, or gene phenotype groups."
    )

    