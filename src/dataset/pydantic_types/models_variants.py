from pydantic import BaseModel, Field
from typing import Union, List
from .models_evidence import Evidence



class RSId(BaseModel):
    rsid: str = Field(description="An rsID (e.g., rs1801133) identifying a single nucleotide polymorphism from dbSNP.")
    evidence: List[Evidence] = Field( description="List of quoted strings from the article supporting the rsID.")

class Haplotype(BaseModel):
    haplotype: str = Field( description="Named haplotype (e.g., CYP2D6*4 or HLA-DRB1*15:01).")
    evidence: List[Evidence] = Field(description="List of quoted strings from the article supporting the haplotype.")

class ProteinVariant(BaseModel):
    protein_change: str = Field( description="Protein-level variant (e.g., p.Val600Glu).")
    evidence: List[Evidence] = Field( description="List of quoted strings from the article supporting the protein change.")

class CDNAVariant(BaseModel):
    cdna_change: str = Field( description="cDNA-level variant (e.g., c.35delG).")
    evidence: List[Evidence] = Field( description="List of quoted strings from the article supporting the cDNA variant.")

class GenomicVariant(BaseModel):
    genomic_change: str = Field( description="Genomic-level variant (e.g., g.123456A>T).")
    evidence: List[Evidence] = Field( description="List of quoted strings from the article supporting the genomic variant.")

class StarAlleleCombo(BaseModel):
    combo: str = Field( description="Star allele combination (e.g., *1/*3 or CYP2C9*2/*2).")
    evidence: List[Evidence] = Field( description="List of quoted strings from the article supporting the star allele combo.")
# class Variants(BaseModel):
#     variants: List[Union[
#         RSId,
#         Haplotype,
#         ProteinVariant,
#         CDNAVariant,
#         GenomicVariant,
#         StarAlleleCombo
#     ]] = Field( description="List of variant mentions, each of a specific type.")

class Variant(BaseModel):
    variant: str = Field(
        description="The name or identifier of the variant (e.g., rs1801133, p.Val600Glu, CYP2D6*4)."
    )
    evidence: List[Evidence] = Field(
        description="List of quoted strings from the article that support the variant mention."
    )
class Variants(BaseModel):
    variants:List[Union[Variant,None]]