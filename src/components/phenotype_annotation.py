"""
Extract detailed drug annotation information for variants with drug associations.
"""

from typing import List, Optional
from loguru import logger
from pydantic import BaseModel
from src.variants import Variant, QuotedStr, QuotedList
from src.components.all_associations import VariantAssociation
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from src.utils import get_article_text
from src.config import DEBUG
import json
import time
import random

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
    background_prompt += f"Association Summary: {variant_association.association_summary.content}\n"
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


def extract_phenotype_annotations(
    variants: List[Variant], article_text: str = None, pmcid: str = None
) -> List[PhenotypeAnnotation]:
    """
    Extract detailed drug annotation information for variants with drug associations.
    Processes each variant individually for better control and cleaner extraction.

    Args:
        variants: List of variants that have drug associations
        article_text: The text of the article
        pmcid: The PMCID of the article

    Returns:
        List of DrugAnnotation objects with detailed information
    """
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)
    variant_id_list = [variant.variant_id for variant in variants]

    logger.info(
        f"Extracting drug annotations for {len(variants)} variants individually: {variant_id_list}"
    )

    all_annotations = []

    for variant in variants:
        logger.info(f"Processing variant: {variant.variant_id}")

        prompt_variables = PromptVariables(
            article_text=article_text,
            key_question=KEY_QUESTION.format(variants=[variant]),
            output_queues=OUTPUT_QUEUES,
            output_format_structure=PhenotypeAnnotation,
        )

        prompt_generator = GeneratorPrompt(prompt_variables)
        generator_prompt = prompt_generator.hydrate_prompt()

        generator = Generator(model="gpt-4o-mini", temperature=0.1)
        response = generator.prompted_generate(generator_prompt)

        parser = Parser(model="gpt-4o-mini", temperature=0.1)
        parser_prompt = ParserPrompt(
            input_prompt=response,
            output_format_structure=PhenotypeAnnotation,
            system_prompt=generator_prompt.system_prompt,
        )
        parsed_response = parser.prompted_generate(parser_prompt)

        try:
            parsed_data = json.loads(parsed_response)

            # Handle different response formats
            if isinstance(parsed_data, dict) and "phenotype_annotation" in parsed_data:
                annotation_data = parsed_data["phenotype_annotation"]
            elif isinstance(parsed_data, dict):
                annotation_data = parsed_data
            else:
                logger.warning(
                    f"Unexpected response format for variant {variant.variant_id}: {parsed_data}"
                )
                continue

            if (
                "variant_annotation_id" not in annotation_data
                or not annotation_data["variant_annotation_id"]
            ):
                annotation_data["variant_annotation_id"] = int(
                    str(int(time.time())) + str(random.randint(100000, 999999))
                )

            annotation = PhenotypeAnnotation(**annotation_data)
            all_annotations.append(annotation)
            logger.info(
                f"Successfully extracted annotation for variant {variant.variant_id}"
            )

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(
                f"Failed to parse drug annotation response for variant {variant.variant_id}: {e}"
            )
            continue

    logger.info(
        f"Successfully extracted {len(all_annotations)} drug annotations from {len(variants)} variants"
    )
    return all_annotations
