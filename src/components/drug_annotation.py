"""
Extract detailed drug annotation information for variants with drug associations.
"""

from typing import Optional, Dict
from loguru import logger
from pydantic import BaseModel
from src.variants import QuotedStr, QuotedList
from src.components.all_associations import VariantAssociation, get_all_associations, AssociationType
from src.prompts import GeneratorPrompt, PromptHydrator
from src.inference import Generator
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

class DrugAnnotation(BaseModel):
    associated_drugs: QuotedList
    association_significance: QuotedStr
    meatbolizer_info: Optional[QuotedStr]
    specialty_populations: QuotedStr
    sentence_summary: str
    notes: Optional[str]

def get_association_background_prompt(variant_association: VariantAssociation):
    background_prompt = ""
    background_prompt += f"Variant ID: {variant_association.variant.content}\n"
    background_prompt += f"Association Summary: {variant_association.association_summary}\n"
    return background_prompt

"""
Old Terms
Term: Variant/Haplotypes
- Content: The specific genetic variant mentioned in the study
- Exampls: rs2909451, CYP2C19*1, CYP2C19*2, *1/*18

Term: Gene
- Content: HGNC symbol for the gene involved in the association. Typically the variants will be within the gene
boundaries, but occasionally this will not be true. E.g. the variant in the annotation may be upstream of the gene but
is reported to affect the gene's expression or otherwise associated with the gene.
- Exampls: DPP4, CYP2C19, KCNJ11
"""

KEY_QUESTION = """
This article contains information on the following variant association:
{association_background}

We are trying to complete a Drug Annotation report that is speciically interested in associations between genetic variants and
pharmacological parameters or clinical drug response measures.

For this association, use the article the find the following additional information for us to get a complete undestanding of the findings:

Term: Drug(s)
- Content: Nme(s) of the drug(s) associated with the variant as part of this association along with a one sentence
description of the results. Convert the drug names to their generic before outputting if possible but include the original term in parentheses. 

Term: Phenotype Category
- Content: Type of clinical outcome studied (EXACTLY ONE: "Efficacy", "Metabolism/PK", "Toxicity", "Dosage", "Other")
- Example: Efficacy

Term: Metabolizer Info (Optional)
- Content: If the study describes a metabolism relationship, describe the CYP enzyme phenotype categories and how they were created/defined.
For example, if the study references a "poor metabolizer" define poor metabolizer as well as the reference metabolizer types. If
the study is not metabolism related, output None or ignore this term.

Term: Significance
- Content: Was this association statistically significant? Describe the author's reported p-value or relevant statistical values.

Term: Specialty Population
- Content: Was an age-specific population studied as part of this association? (EXACTLY ONE: "Pediatric", "Geriatric", "No", or "Unknown")

Term: Sentence
- Content: One sentence summary of the association. Make sure to include the following information roughly by following this 
rough format: "[Genotype/Allele/Variant] is [associated with/not associated with] [increased/decreased] [outcome] [drug context] [population context]"
- Example: "Genotype TT is associated with decreased response to sitagliptin in people with Diabetes Mellitus, Type 2."

Term: Notes
- Content: Any additional key study details, methodology, or important context
- Example: "Patients with the rs2909451 TT genotype in the study group exhibited a median HbA1c improvement of 0.57..."
"""

OUTPUT_QUEUES = """
For each variant, extract all the above information and provide it in structured format

For each variant, provide:
- All required fields filled with appropriate values or left empty if not applicable
- Ensure controlled vocabulary compliance for categorical fields
- Extract direct quotes from the article to support the annotations
"""

def get_drug_annotation(variant_association: VariantAssociation | Dict):
    if isinstance(variant_association, dict):
        variant_association = VariantAssociation(**variant_association)
    prompt = GeneratorPrompt(
        input_prompt=PromptHydrator(
            prompt_template=KEY_QUESTION,
            prompt_variables={
                "association_background": get_association_background_prompt(variant_association),
            },
            system_prompt=None,
            output_format_structure=DrugAnnotation,
        ),
        output_format_structure=DrugAnnotation,
    ).get_hydrated_prompt()
    generator = Generator(model="gpt-4o")
    return generator.generate(prompt)

def test_drug_annotations():
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
    drug_annotations = []
    for association in associations:
        if association.association_type == AssociationType.DRUG:
            drug_annotation = get_drug_annotation(association)
            drug_annotations.append(drug_annotation)
    
    logger.info(f"Got drug annotations for {len(drug_annotations)} associations")
    file_path = f"data/extractions/{pmcid}/drug_annotation.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(drug_annotations, f, indent=4)        
    logger.info(f"Saved to file {file_path}")

if __name__ == "__main__":
    test_drug_annotations()