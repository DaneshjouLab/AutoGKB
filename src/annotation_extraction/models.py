"""
Data models for the annotation extraction pipeline.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from enum import Enum
from loguru import logger
from pathlib import Path
class AnnotationType(Enum):
    FUNCTIONAL = "functional"
    DRUG = "drug"
    PHENOTYPE = "phenotype"


class PhenotypeCategory(Enum):
    METABOLISM_PK = "Metabolism/PK"
    EFFICACY = "Efficacy"
    TOXICITY = "Toxicity"
    DOSAGE = "Dosage"
    OTHER = "Other"


class Significance(Enum):
    YES = "yes"
    NO = "no"
    NOT_STATED = "not stated"


class SpecialtyPopulation(Enum):
    PEDIATRIC = "Pediatric"
    GERIATRIC = "Geriatric"


class Direction(Enum):
    INCREASED = "increased"
    DECREASED = "decreased"


class Association(Enum):
    IS = "Is"
    IS_NOT = "Is Not"
    ARE = "Are"
    ARE_NOT = "Are Not"


@dataclass
class ArticleInput:
    """Input article data."""
    title: str
    article_text: str
    pmid: str
    pmcid: Optional[str] = None


class ArticleParser:
    """Convert Markdown article text or PMCID to ArticleInput.
    
    Args:
        text: Optional[str] = None
        pmcid: Optional[str] = None
        remove_references: bool = True
    """
    def __init__(self, text: Optional[str] = None, pmcid: Optional[str] = None, remove_references: bool = True):
        self.text = text
        self.pmcid = pmcid
        if not self.text and not self.pmcid:
            logger.error("Either text or pmcid must be provided.")
            raise ValueError("Either text or pmcid must be provided.")
        if self.text and self.pmcid:
            logger.error("Only one of text or pmcid can be provided.")
            raise ValueError("Only one of text or pmcid can be provided.")
        if self.pmcid:
            logger.info(f"Getting article text from PMCID: {self.pmcid}")
            self.text = self.get_article_text()
        if self.remove_references:
            self.remove_references_section()
    
    def get_article_text(self) -> str:
        """Get article text from PMCID."""
        article_path = Path("data") / "articles" / f"{self.pmcid}.md"
        if not article_path.exists():
            logger.error(f"Article not found: {article_path}")
            raise FileNotFoundError(f"Article not found: {article_path}")
        with open(article_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def parse_title(self) -> str:
        """Parse the title from the markdown text."""
        lines = self.text.split("\n")
        if not lines:
            return ""
        title = lines[0].strip()
        if title.startswith("# "):
            title = title[2:].strip()
        return title
    
    def remove_references_section(self):
        """
        Removes the references section from article text.
            
        Returns:
            str: Article text with references section removed
            (Looks for ## References section and removes it and everything after)
        """
        # Split the text into sections
        sections = self.text.split("##")
        
        # Find the index of the References section
        ref_index = -1
        for i, section in enumerate(sections):
            if section.strip().startswith("References"):
                ref_index = i
                break
        
        # If references section found, remove it and everything after
        if ref_index != -1:
            sections = sections[:ref_index]
            self.text = "##".join(sections)
        
        logger.info(f"Removed References section from article text")
    
    def parse_pmid(self) -> str:
        """Parse the PMID from the markdown text."""
        lines = self.text.split("\n")
        
        # Look for PMID in metadata section
        for line in lines:
            if line.strip().startswith("**PMID:**"):
                pmid = line.replace("**PMID:**", "").strip()
                return pmid
        
        return ""
    
    def parse_pmcid(self) -> str:
        """Parse the PMCID from the markdown text."""
        if self.pmcid:
            return self.pmcid
        lines = self.text.split("\n")
        
        # Look for PMCID in metadata section
        for line in lines:
            if line.strip().startswith("**PMCID:**"):
                pmcid = line.replace("**PMCID:**", "").strip()
                return pmcid
        
        return ""
    
    def parse(self) -> ArticleInput:
        """Parse the article text into an ArticleInput."""
        return ArticleInput(
            title=self.parse_title(),
            article_text=self.text,
            pmid=self.parse_pmid(),
            pmcid=self.parse_pmcid(),
        )

@dataclass
class RelevanceResult:
    """Result of relevance screening."""
    is_relevant: bool
    summary: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class ExtractedEntity:
    """Single extracted entity."""
    entity_type: str
    value: str
    context: str
    supporting_text: str


@dataclass
class ExtractedEntities:
    """All extracted entities from an article."""
    genetic_variants: List[ExtractedEntity]
    drugs: List[ExtractedEntity]
    phenotypes: List[ExtractedEntity]
    population_info: List[ExtractedEntity]
    associations: List[ExtractedEntity]


@dataclass
class Relationship:
    """Variant-outcome relationship."""
    variant: str
    gene: str
    drug: Optional[str]
    phenotype: str
    association_type: str
    evidence_text: str
    statistical_measures: Optional[Dict[str, Union[str, float]]]


@dataclass
class ClassificationResult:
    """Result of annotation type classification."""
    relationship: Relationship
    annotation_types: List[AnnotationType]
    confidence: float
    evidence_summary: str


@dataclass
class AnnotationRow:
    """Generated annotation row for TSV output."""
    annotation_type: AnnotationType
    row_data: List[str]
    fields: List[str]
    
    def to_tsv(self) -> str:
        """Convert to TSV format."""
        return "\t".join(self.row_data)


@dataclass
class ValidationResult:
    """Result of quality validation."""
    is_valid: bool
    errors: List[str]
    corrected_row: Optional[AnnotationRow] = None
    confidence_score: Optional[float] = None