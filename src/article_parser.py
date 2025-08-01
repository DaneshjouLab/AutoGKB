from loguru import logger
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from typing import List

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

    def __init__(
        self,
        text: Optional[str] = None,
        pmcid: Optional[str] = None,
        remove_references: bool = True,
        for_citations: bool = False,
    ):
        self.text = text
        self.pmcid = pmcid
        self.remove_references = remove_references
        self.for_citations = for_citations

        if not self.text and not self.pmcid:
            logger.error("Either text or pmcid must be provided.")
            raise ValueError("Either text or pmcid must be provided.")
        if self.text and self.pmcid:
            logger.error("Only one of text or pmcid can be provided.")
            raise ValueError("Only one of text or pmcid can be provided.")
        if self.pmcid:
            self.text = self.get_article_text()
        if self.remove_references:
            self.remove_sections(["References", "Acknowledgments"])
        if self.for_citations:
            self.remove_sections(["Introduction", "Background", "Metadata", "Abstract", "Acknowledgements", "References", "Author Contributions", "Contributor Information", "Funding"])

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

    def remove_section(self, section_name: str):
        """
        Removes the introduction section from article text.
        
        Removes sections where ## and Introduction appear on the same line
        """
        # Split the text into lines
        lines = self.text.split("\n")
        
        # Find the start of Introduction section
        intro_start = -1
        for i, line in enumerate(lines):
            # Check if line starts with ## and contains Introduction
            if line.strip().startswith("##") and section_name.lower() in line.lower():
                intro_start = i
                break
        
        # If no introduction found, return original text
        if intro_start == -1:
            return
            
        # Find the next section start
        next_section = -1
        for i in range(intro_start + 1, len(lines)):
            if lines[i].strip().startswith("##"):
                next_section = i
                break
        
        # Remove the introduction section
        if next_section != -1:
            # Remove from intro start to next section
            self.text = "\n".join(lines[:intro_start] + lines[next_section:])
        else:
            # If no next section, just remove from intro to end
            self.text = "\n".join(lines[:intro_start])
    
    def remove_sections(self, section_names: List[str]):
        """
        Removes the sections from article text.
        """
        for section_name in section_names:
            self.remove_section(section_name)

    def remove_acknowledgements(self):
        """
        Removes the acknowledgements section from article text.
        
        (Looks for ## Acknowledgements section and removes it)
        """
        # Split the text into sections
        sections = self.text.split("##")
        
        # Find and remove the Acknowledgements section
        filtered_sections = []
        for section in sections:
            section_name = section.strip().lower()
            if not (section_name.startswith("acknowledgements") or 
                   section_name.startswith("acknowledgments")):
                filtered_sections.append(section)
        
        self.text = "##".join(filtered_sections)

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

def test():
    parser = MarkdownParser(pmcid="PMC11730665", for_citations=True)
    print(parser.text)

if __name__ == "__main__":
    test()