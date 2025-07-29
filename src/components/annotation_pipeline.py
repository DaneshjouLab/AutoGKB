from src.components.annotation_table import AnnotationTableGenerator
from src.components.citation_generator import CitationGenerator
from src.components.study_parameters import get_study_parameters
from src.utils import get_article_text, is_pmcid, get_title
from loguru import logger
from pathlib import Path
import os

class AnnotationPipeline:
    def __init__(self, pmcid: str, citation_approach: str = "lm"):
        if not is_pmcid(pmcid):
            logger.error(f"Invalid PMCID: {pmcid}")
        self.pmcid = pmcid
        self.citation_approach = citation_approach
        self.article_text = get_article_text(pmcid)
        self.title = get_title(self.article_text)
        self.study_parameters = {}
        self.annotations = None

    def print_info(self):
        annotation_count = len(self.annotations.relationships) if self.annotations else 0
        
        logger.info(f"Created {annotation_count} Annotations")

    def generate_final_structure(self):
        return {
            "pmcid": self.pmcid,
            "title": self.title,
            "study_parameters": self.study_parameters,
            "annotations": self.annotations,
        }

    def run(self, save_path: str = "data/annotations"):
        logger.info("Getting Study Parameters")
        self.study_parameters = get_study_parameters(self.article_text)

        # Generate annotations using AnnotationTableGenerator
        annotation_generator = AnnotationTableGenerator(self.pmcid)
        
        logger.info("Generating Annotations")
        self.annotations = annotation_generator.generate_table_json()

        # Generate citations for annotations
        citation_generator = CitationGenerator(self.pmcid, approach=self.citation_approach)
        logger.info(f"Adding Citations to Annotations using {self.citation_approach} approach")
        self.annotations = citation_generator.add_citations_to_annotations(self.annotations)

        self.print_info()

        final_structure = self.generate_final_structure()
        logger.info("Generated complete annotation")

        if save_path:
            file_path = Path(save_path) / f"{self.pmcid}.json"
            import os
            import json

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            try:
                with open(file_path, "w") as f:
                    json.dump(final_structure, f, indent=4, default=lambda obj: obj.model_dump() if hasattr(obj, 'model_dump') else str(obj))
                logger.info(f"Saved annotations to {file_path}")
            except Exception as e:
                logger.error(f"Error saving annotations: {e}")
        return final_structure

def copy_markdown(pmcid: str):
    file_path = Path(f"data/articles/{pmcid}.md")
    with open(file_path, "r") as f:
        data = f.read()
    
    new_file_path = Path(f"data/markdown/{pmcid}.md")
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
    with open(new_file_path, "w") as f:
        f.write(data)

if __name__ == "__main__":
    pmcids = [
        "PMC5728534",
        "PMC11730665",
        "PMC5712579",
        "PMC4737107",
        "PMC5749368"
    ]
    for pmcid in pmcids:
        logger.info(f"Processing {pmcid}")
        pipeline = AnnotationPipeline(pmcid, citation_approach="local")
        pipeline.run()
    for pmcid in pmcids:
        copy_markdown(pmcid)
