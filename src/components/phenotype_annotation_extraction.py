"""
Extract detailed phenotype annotation information for variants with phenotype associations.
"""

from typing import List
from loguru import logger
from pydantic import BaseModel
from src.variants import Variant, PhenotypeAnnotation, PhenotypeAnnotationList
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from src.utils import get_article_text
from src.config import DEBUG
import json
import time
import random


KEY_QUESTION = """
For the following variants that have been identified as having phenotype associations, extract detailed pharmacogenomic annotation information.

Variants: {variants}

Extract the following information for each variant:

Term: Variant/Haplotypes
- Content: The specific genetic variant mentioned in the study
- Example: HLA-B*35:08, rs1801272, UGT1A1*28

Term: Gene
- Content: Gene symbol associated with the variant
- Example: HLA-B, CYP2A6, UGT1A1

Term: Drug(s)
- Content: Drug(s) that caused or were involved in the phenotype
- Example: lamotrigine, sacituzumab govitecan, empty for disease predisposition

Term: Phenotype Category
- Content: Type of phenotype or outcome studied (EXACTLY ONE: "Toxicity", "Efficacy", "Metabolism/PK", "Dosage", "Other")
- Example: Toxicity

Term: Significance
- Content: Whether the association was statistically significant (EXACTLY ONE: "yes", "no", "not stated")
- Example: yes

Term: Notes
- Content: Key study details, statistics, methodology
- Example: "The allele was not significant when comparing allele frequency in cases..."

Term: Sentence
- Content: Standardized description of the genetic-phenotype association
- Format: "[Variant] is [associated with/not associated with] [increased/decreased] [phenotype outcome] [drug context] [population context]"
- Example: "HLA-B *35:08 is not associated with likelihood of Maculopapular Exanthema, severe cutaneous adverse reactions or Stevens-Johnson Syndrome when treated with lamotrigine in people with Epilepsy."

Term: Alleles
- Content: Specific allele or genotype if different from main variant field
- Example: *35:08, AA + AT, *1/*28 + *28/*28

Term: Specialty Population
- Content: Age-specific populations (EXACTLY ONE: "Pediatric", "Geriatric", or leave empty)

Term: Metabolizer types
- Content: CYP enzyme phenotype when applicable
- Example: ultrarapid metabolizer, intermediate activity

Term: isPlural
- Content: Grammar helper for sentence construction (EXACTLY ONE: "Is", "Are")
- Example: Is (for single allele), Are (for combined genotypes)

Term: Is/Is Not associated
- Content: Direction of statistical association (EXACTLY ONE: "Associated with", "Not associated with")

Term: Direction of effect
- Content: Whether the variant increases or decreases the phenotype (EXACTLY ONE: "increased", "decreased", or leave empty)

Term: Side effect/efficacy/other
- Content: Specific outcome descriptor
- Example: likelihood of, risk of

Term: Phenotype
- Content: Primary phenotype with standardized prefix
- Example: Side Effect:Maculopapular Exanthema, Disease:Epilepsy

Term: Multiple phenotypes And/or
- Content: Logical connector for multiple phenotypes (EXACTLY ONE: "and", "or", or leave empty)

Term: When treated with/exposed to/when assayed with
- Content: Drug administration context
- Example: when treated with, when exposed to

Term: Multiple drugs And/or
- Content: Logical connector for multiple drugs (EXACTLY ONE: "and", "or", or leave empty)

Term: Population types
- Content: Descriptor of study population
- Example: in people with

Term: Population Phenotypes or diseases
- Content: Disease/condition context with standardized prefix
- Example: Disease:Epilepsy, Other:Diabetes Mellitus, Type 2

Term: Multiple phenotypes or diseases And/or
- Content: Logical connector for multiple conditions (EXACTLY ONE: "and", "or", or leave empty)

Term: Comparison Allele(s) or Genotype(s)
- Content: Reference genotype used for comparison
- Example: *1/*1, C

Term: Comparison Metabolizer types
- Content: Reference metabolizer status for comparison
- Example: normal metabolizer
"""

OUTPUT_QUEUES = """
For each variant, extract all the above information and provide it in structured format. Generate a unique Variant Annotation ID using timestamp + random numbers.

For each variant, provide:
- All required fields filled with appropriate values or left empty if not applicable
- Ensure controlled vocabulary compliance for categorical fields
- Extract direct quotes from the article to support the annotations
"""


def extract_phenotype_annotations(
    variants: List[Variant], article_text: str = None, pmcid: str = None
) -> List[PhenotypeAnnotation]:
    """
    Extract detailed phenotype annotation information for variants with phenotype associations.
    Processes each variant individually for better control and cleaner extraction.

    Args:
        variants: List of variants that have phenotype associations
        article_text: The text of the article
        pmcid: The PMCID of the article

    Returns:
        List of PhenotypeAnnotation objects with detailed information
    """
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)
    variant_id_list = [variant.variant_id for variant in variants]

    logger.info(
        f"Extracting phenotype annotations for {len(variants)} variants individually: {variant_id_list}"
    )

    all_annotations = []

    for variant in variants:
        logger.info(f"Processing variant: {variant.variant_id}")

        class SinglePhenotypeAnnotation(BaseModel):
            phenotype_annotation: PhenotypeAnnotation

        prompt_variables = PromptVariables(
            article_text=article_text,
            key_question=KEY_QUESTION.format(variants=[variant]),
            output_queues=OUTPUT_QUEUES,
            output_format_structure=SinglePhenotypeAnnotation,
        )

        prompt_generator = GeneratorPrompt(prompt_variables)
        generator_prompt = prompt_generator.hydrate_prompt()

        generator = Generator(model="gpt-4o-mini", temperature=0.1)
        response = generator.prompted_generate(generator_prompt)

        parser = Parser(model="gpt-4o-mini", temperature=0.1)
        parser_prompt = ParserPrompt(
            input_prompt=response,
            output_format_structure=SinglePhenotypeAnnotation,
            system_prompt=generator_prompt.system_prompt,
        )
        parsed_response = parser.prompted_generate(parser_prompt)

        try:
            parsed_data = json.loads(parsed_response)

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
                f"Successfully extracted phenotype annotation for variant {variant.variant_id}"
            )

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(
                f"Failed to parse phenotype annotation response for variant {variant.variant_id}: {e}"
            )
            continue

    logger.info(
        f"Successfully extracted {len(all_annotations)} phenotype annotations from {len(variants)} variants"
    )
    return all_annotations
