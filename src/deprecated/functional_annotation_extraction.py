"""
Extract detailed functional annotation information for variants with functional associations.
"""

from typing import List
from loguru import logger
from pydantic import BaseModel
from src.deprecated.variants import Variant, FunctionalAnnotation, FunctionalAnnotationList
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from src.utils import get_article_text
from src.config import DEBUG
import json
import time
import random


KEY_QUESTION = """
For the following variants that have been identified as having functional associations, extract detailed mechanistic annotation information.

Variants: {variants}

Extract the following information for each variant:

Term: Variant/Haplotypes
- Content: The specific genetic variant studied
- Example: CYP2C19*1, CYP2C19*17, rs72552763, CYP2B6*1, CYP2B6*6

Term: Gene
- Content: Gene symbol associated with the variant
- Example: CYP2C19, CYP2B6, SLC22A1

Term: Drug(s)
- Content: Substrate or compound used in the functional assay
- Example: normeperidine, bupropion, warfarin, voriconazole, ranitidine

Term: Phenotype Category
- Content: Type of functional outcome measured (EXACTLY ONE: "Metabolism/PK", "Efficacy", or leave empty)
- Example: Metabolism/PK (for enzyme kinetics), Efficacy (for cellular response)

Term: Significance
- Content: Statistical significance of functional differences (EXACTLY ONE: "yes", "no", "not stated")
- Example: yes (for significant activity differences), not stated (for descriptive studies)

Term: Notes
- Content: Key experimental details, methodology, quantitative results
- Example: "Clearance was 26.57% of wild-type. CYP2C19 variants expressed in Sf21 insect cells..."

Term: Sentence
- Content: Standardized description of the functional relationship
- Format: "[Variant] is associated with [increased/decreased] [functional outcome] [experimental context] as compared to [reference variant]"
- Example: "CYP2C19 *17/*17 is associated with increased formation of normeperidine as compared to CYP2C19 *1/*1 + *1/*17."

Term: Alleles
- Content: Specific allele or genotype tested
- Example: *17/*17, *1/*1, del, A

Term: Specialty Population
- Content: Age-specific populations (rarely applicable to functional studies, usually empty)

Term: Assay type
- Content: Laboratory method or experimental system used
- Example: in human liver microsomes, hydroxylation assay, crystal structure prediction, Cells

Term: Metabolizer types
- Content: Phenotype classification if applicable (rarely used in functional studies)
- Example: Usually empty

Term: isPlural
- Content: Grammar helper for sentence construction (EXACTLY ONE: "Is", "Are")
- Example: Is

Term: Is/Is Not associated
- Content: Direction of functional association (EXACTLY ONE: "Associated with", "Not associated with")

Term: Direction of effect
- Content: Whether the variant increases or decreases function (EXACTLY ONE: "increased", "decreased")
- Example: increased (for enhanced activity), decreased (for reduced activity)

Term: Functional terms
- Content: Specific functional outcome measured
- Example: formation of, activity of, clearance of, transport of, affinity to, catalytic activity of

Term: Gene/gene product
- Content: Specific gene or protein being functionally assessed
- Example: CYP2C19, CYP2B6, CYP2C9

Term: When treated with/exposed to/when assayed with
- Content: Experimental substrate context
- Example: when assayed with, of, or leave empty

Term: Multiple drugs And/or
- Content: Logical connector for multiple substrates (EXACTLY ONE: "and", "or", or leave empty)

Term: Cell type
- Content: Cell line or tissue system used for the assay
- Example: in 293FT cells, expressed in COS-7 cells, Sf21 insect cells, in insect microsomes

Term: Comparison Allele(s) or Genotype(s)
- Content: Reference variant for comparison
- Example: *1/*1 + *1/*17, *1, GAT

Term: Comparison Metabolizer types
- Content: Reference metabolizer status (usually empty for functional studies)
"""

OUTPUT_QUEUES = """
For each variant, extract all the above information and provide it in structured format. Generate a unique Variant Annotation ID using timestamp + random numbers.

For each variant, provide:
- All required fields filled with appropriate values or left empty if not applicable
- Ensure controlled vocabulary compliance for categorical fields
- Extract direct quotes from the article to support the annotations
"""


def extract_functional_annotations(
    variants: List[Variant], article_text: str = None, pmcid: str = None
) -> List[FunctionalAnnotation]:
    """
    Extract detailed functional annotation information for variants with functional associations.
    Processes each variant individually for better control and cleaner extraction.

    Args:
        variants: List of variants that have functional associations
        article_text: The text of the article
        pmcid: The PMCID of the article

    Returns:
        List of FunctionalAnnotation objects with detailed information
    """
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)
    variant_id_list = [variant.variant_id for variant in variants]

    logger.info(
        f"Extracting functional annotations for {len(variants)} variants individually: {variant_id_list}"
    )

    all_annotations = []

    for variant in variants:
        logger.info(f"Processing variant: {variant.variant_id}")

        class SingleFunctionalAnnotation(BaseModel):
            functional_annotation: FunctionalAnnotation

        prompt_variables = PromptVariables(
            article_text=article_text,
            key_question=KEY_QUESTION.format(variants=[variant]),
            output_queues=OUTPUT_QUEUES,
            output_format_structure=SingleFunctionalAnnotation,
        )

        prompt_generator = GeneratorPrompt(prompt_variables)
        generator_prompt = prompt_generator.hydrate_prompt()

        generator = Generator(model="gpt-4o-mini", temperature=0.1)
        response = generator.prompted_generate(generator_prompt)

        parser = Parser(model="gpt-4o-mini", temperature=0.1)
        parser_prompt = ParserPrompt(
            input_prompt=response,
            output_format_structure=SingleFunctionalAnnotation,
            system_prompt=generator_prompt.system_prompt,
        )
        parsed_response = parser.prompted_generate(parser_prompt)

        try:
            parsed_data = json.loads(parsed_response)

            if isinstance(parsed_data, dict) and "functional_annotation" in parsed_data:
                annotation_data = parsed_data["functional_annotation"]
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

            annotation = FunctionalAnnotation(**annotation_data)
            all_annotations.append(annotation)
            logger.info(
                f"Successfully extracted functional annotation for variant {variant.variant_id}"
            )

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(
                f"Failed to parse functional annotation response for variant {variant.variant_id}: {e}"
            )
            continue

    logger.info(
        f"Successfully extracted {len(all_annotations)} functional annotations from {len(variants)} variants"
    )
    return all_annotations
