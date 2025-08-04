"""
Extract detailed drug annotation information for variants with drug associations.
"""

from typing import List, Optional, Dict
from loguru import logger
from pydantic import BaseModel
from src.deprecated.variants import Variant, QuotedStr, QuotedList
from src.deprecated.all_associations import (
    VariantAssociation,
    get_all_associations,
    AssociationType,
)
from src.prompts import PromptHydrator, GeneratorPrompt
from src.inference import Generator, Parser
from src.utils import get_article_text
from src.config import DEBUG
import json
import os

"""
Terms:
- Drug(s): 
- Phenotype Category
- Association Significane
- Sentence Summary (get examples)
- Specialty Populations
- Notes: 3-4 sentence summary of the results of the study in relation to these variant and the found association.

Explain your reasoning step by step by including the term, a one sentence explanation, and an exact quote from the article that details where
"""


class PhenotypeAnnotation(BaseModel):
    associated_drugs: QuotedList
    association_significance: QuotedStr
    meatbolizer_info: Optional[QuotedStr]
    specialty_populations: QuotedStr
    sentence_summary: str
    notes: Optional[str]


def get_association_background_prompt(variant_association: VariantAssociation):
    background_prompt = ""
    background_prompt += f"Variant ID: {variant_association.variant.content}\n"
    background_prompt += (
        f"Association Summary: {variant_association.association_summary}\n"
    )
    return background_prompt


KEY_QUESTION = """
This article contains information on the following variant association:
{association_background}

We are interested in completing a Phenotype Annotation report that is specifically interested in associations between genetic variants 
and adverse drug reactions, toxicities, or clinical outcomes that represent:
- Toxicity/Safety outcomes
- Clinical phenotypes/adverse events

Term: Drug(s)
- Content: Nme(s) of the drug(s) associated with the variant as part of this association along with a one sentence
description of the results. Convert the drug names to their generic before outputting if possible but include the original term in parentheses. 

Term: Phenotype Category
- Content: Type of clinical outcome studied (EXACTLY ONE: "Efficacy", "Metabolism/PK", "Toxicity", "Dosage", "Other")
- Example: Efficacy

Term: Significance
- Content: Was this association statistically significant? Describe the author's reported p-value or relevant statistical values.

Term: Specialty Population
- Content: Was an age-specific population studied as part of this association? (EXACTLY ONE: "Pediatric", "Geriatric", "No", or "Unknown")

Term: Sentence
- Content: One sentence summary of the association. Make sure to include the following information roughly by following this 
rough format: "[Genotype/Allele/Variant] is [associated with/not associated with] [increased/decreased] [outcome] [drug context] [population context]"
- Example: "HLA-B *35:08 is not associated with likelihood of Maculopapular Exanthema, severe cutaneous adverse reactions or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy."

Term: Notes
- Content: Any additional key study details, methodology, or important context
- Example: The allele was not significant when comparing allele frequency in cases of severe cutaneous adverse reactions (SCAR), Stevens-Johnson Syndrome (SJS) and Maculopapular Exanthema (MPE) (1/15) and controls (individuals without AEs who took lamotrigine) (0/50). The allele was significant when comparing between cases (1/15) and the general population (1/986)."
"""

OUTPUT_QUEUES = """
For each variant, extract all the above information and provide it in structured format

For each variant, provide:
- All required fields filled with appropriate values or left empty if not applicable
- Ensure controlled vocabulary compliance for categorical fields
- Extract direct quotes from the article to support the annotations
"""


def get_phenotype_annotation(variant_association: VariantAssociation | Dict):
    if isinstance(variant_association, dict):
        variant_association = VariantAssociation(**variant_association)
    prompt = GeneratorPrompt(
        input_prompt=PromptHydrator(
            prompt_template=KEY_QUESTION,
            prompt_variables={
                "association_background": get_association_background_prompt(
                    variant_association
                ),
            },
            system_prompt=None,
            output_format_structure=PhenotypeAnnotation,
        ),
        output_format_structure=PhenotypeAnnotation,
    ).get_hydrated_prompt()
    generator = Generator(model="gpt-4o")
    return generator.generate(prompt)


def test_phenotype_annotations():
    """
    Output the extracted variant associations to a file
    """
    pmcid = "PMC11730665"
    article_text = get_article_text(pmcid)
    logger.info(f"Got article text {pmcid}")
    associations = get_all_associations(article_text)

    # Save associations
    file_path = f"data/extractions/{pmcid}/associations.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(associations, f, indent=4)
    logger.info(f"Saved to file {file_path}")

    logger.info(f"Found {len(associations)} associations")
    associations = [VariantAssociation(**association) for association in associations]
    phenotype_annotations = []
    for association in associations:
        if association.association_type == AssociationType.PHENOTYPE:
            phenotype_annotation = get_phenotype_annotation(association)
            phenotype_annotations.append(phenotype_annotation)

    logger.info(f"Got drug annotations for {len(phenotype_annotations)} associations")
    file_path = f"data/extractions/{pmcid}/phenotype_annotation.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(phenotype_annotations, f, indent=4)
    logger.info(f"Saved to file {file_path}")


if __name__ == "main":
    test_phenotype_annotations()
