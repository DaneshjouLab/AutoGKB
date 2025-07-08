from src.components.all_associations import get_all_associations, AssociationType
from src.components.drug_annotation import get_drug_annotation
from src.components.phenotype_annotation import get_phenotype_annotation
from src.components.functional_annotation import get_functional_annotation
from src.components.study_parameters import get_study_parameters
from src.utils import get_article_text, is_pmcid, get_title
from typing import Optional
from loguru import logger
from pathlib import Path


class AnnotationPipeline:
    def __init__(self, pmcid: str):
        if not is_pmcid(pmcid):
            logger.error(f"Invalid PMCID: {pmcid}")
        self.pmcid = pmcid
        self.article_text = get_article_text(pmcid)
        self.title = get_title(self.article_text)
        self.all_associations = []
        self.study_parameters = {}
        self.drug_annotations = []
        self.phenotye_annotations = []
        self.functional_annotations = []

    def print_info(self):
        logger.info(f"Found {len(self.all_associations)} associations")
        logger.info(f"Created {len(self.drug_annotations)} Drug Annotations")
        logger.info(f"Created {len(self.phenotye_annotations)} Phenotype Annotations")
        logger.info(
            f"Created {len(self.functional_annotations)} Functional Annotations"
        )

    def generate_final_structure(self):
        return {
            "pmcid": self.pmcid,
            "title": self.title,
            "study_parameters": self.study_parameters,
            "drug_annotations": self.drug_annotations,
            "phenotype_annotations": self.phenotye_annotations,
            "functional_annotations": self.functional_annotations,
        }

    def run(self, save_path: str = "data/annotations"):
        logger.info("Getting Study Parameters")
        self.study_parameters = get_study_parameters(self.article_text)

        logger.info("Getting All Associations")
        self.all_associations = get_all_associations(self.article_text)

        for association in self.all_associations:
            if association.association_type == AssociationType.DRUG:
                self.drug_annotations.append(get_drug_annotation(association))
            if association.association_type == AssociationType.PHENOTYPE:
                self.phenotye_annotations.append(get_phenotype_annotation(association))
            if association.association_type == AssociationType.FUNCTIONAL:
                self.functional_annotations.append(
                    get_functional_annotation(association)
                )

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


if __name__ == "__main__":
    pipeline = AnnotationPipeline("PMC11730665")
    pipeline.run()
