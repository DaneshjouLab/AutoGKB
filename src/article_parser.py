from loguru import logger
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
@dataclass
class ArticleInput:
    """Input article data."""
    title: str
    article_text: str
    pmid: str
    pmcid: Optional[str] = None

class MarkdownParser:
    """
    Convert Markdown article text or PMCID to ArticleInput.
    
    Args:
        text: Optional[str] = None
        pmcid: Optional[str] = None
        remove_references: bool = True
    """
    def __init__(self, text: Optional[str] = None, pmcid: Optional[str] = None, remove_references: bool = True):
        self.text = text
        self.pmcid = pmcid
        self.remove_references = remove_references
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