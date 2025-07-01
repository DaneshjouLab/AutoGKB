"""
Extract detailed drug annotation information for variants with drug associations.
"""

from typing import List, Optional, Dict
import os
from loguru import logger
from pydantic import BaseModel
from src.variants import Variant, QuotedStr, QuotedList
from src.components.all_associations import (
    VariantAssociation,
    get_all_associations,
    AssociationType,
)
from src.prompts import PromptHydrator, GeneratorPrompt
from src.inference import Generator
from src.utils import get_article_text
from src.config import DEBUG
import json

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


class FunctionalAnnotation(BaseModel):
    associated_drugs: QuotedList
    association_significance: QuotedStr
    specialty_populations: QuotedStr
    assay_type: QuotedStr
    cell_type: QuotedStr
    sentence_summary: str
    notes: Optional[str]


def get_association_background_prompt(variant_association: VariantAssociation):
    background_prompt = ""
    background_prompt += f"Variant ID: {variant_association.variant.content}\n"
    background_prompt += (
        f"Association Summary: {variant_association.association_summary.content}\n"
    )
    return background_prompt


KEY_QUESTION = """
This article contains information on the following variant association:
{association_background}

We are interested in completing a Functional Annotation report that is specifically interested in associations between genetic variants 
and in-vitro outcomes such as:
- Enzyme/transporter activity (e.g., clearance, metabolism, transport)
- Binding affinity (e.g., protein-drug interactions)
- Functional properties (e.g., uptake rates, kinetic parameters like Km/Vmax)

Term: Drug(s)
- Content: Nme(s) of the drug(s) associated with the variant as part of this association along with a one sentence
description of the results. Convert the drug names to their generic before outputting if possible but include the original term in parentheses. 

Term: Phenotype Category
- Content: Type of clinical outcome studied (EXACTLY ONE: "Efficacy", "Metabolism/PK", "Toxicity", "Dosage", "Other: <short description>")

Term: Assay Type
- Content: Laboratory method or experimental system used to measure this association.
- Example: hydroxylation assay, crystal structure prediction, etc.

Term: Cell Type
- Content: The cell type(s) used in the assay for this association. Include species context if available
- Example: insect microsomes, human hepatocytes, E. coli DH5alpha, etc.

Term: Significance
- Content: Was this association statistically significant? Describe the author's reported p-value or relevant statistical values.

Term: Sentence
- Content: One sentence summary of the association. Make sure to include the following information roughly by following this 
rough format: "[Genotype/Allele/Variant] is [associated with/not associated with] [increased/decreased] [outcome] [drug context] [population context]"
- Example: "Genotype TT is associated with decreased response to sitagliptin in people with Diabetes Mellitus, Type 2."

Term: Notes
- Content: Any additional key study details, methodology, or important context
- Example: "TPMT protein levels were comparable between TPMT*3C and TPMT*1 when expressed in yeast. Comparable results were seen in COS-1 cells. mRNA levels were comparable between *3C and *1 in yeast."
"""

OUTPUT_QUEUES = """
For each variant, extract all the above information and provide it in structured format

For each variant, provide:
- All required fields filled with appropriate values or left empty if not applicable
- Ensure controlled vocabulary compliance for categorical fields
- Extract direct quotes from the article to support the annotations
"""


def get_functional_annotation(variant_association: VariantAssociation | Dict):
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
            output_format_structure=FunctionalAnnotation,
        ),
        output_format_structure=FunctionalAnnotation,
    ).get_hydrated_prompt()
    generator = Generator(model="gpt-4o")
    return generator.generate(prompt)


def test_functional_annotations():
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
    functional_annotations = []
    for association in associations:
        if association.association_type == AssociationType.FUNCTIONAL:
            functional_annotation = get_functional_annotation(association)
            functional_annotations.append(functional_annotation)

    logger.info(f"Got drug annotations for {len(functional_annotations)} associations")
    file_path = f"data/extractions/{pmcid}/functional_annotation.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(functional_annotations, f, indent=4)
    logger.info(f"Saved to file {file_path}")


if __name__ == "main":
    test_functional_annotations()
