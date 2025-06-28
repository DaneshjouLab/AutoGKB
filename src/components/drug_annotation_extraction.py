"""
Extract detailed drug annotation information for variants with drug associations.
"""

from typing import List
from loguru import logger
from src.variants import Variant, DrugAnnotation, DrugAnnotationList
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from src.utils import get_article_text
from src.config import DEBUG
import json
import time
import random


KEY_QUESTION = """
For the following variants that have been identified as having drug associations, extract detailed pharmacogenomic annotation information.

Variants: {variants}

Extract the following information for each variant:

Term: Variant/Haplotypes
- Content: The specific genetic variant mentioned in the study
- Example: rs2909451, CYP2C19*1, CYP2C19*2, *1/*18

Term: Gene
- Content: Gene symbol associated with the variant
- Example: DPP4, CYP2C19, KCNJ11

Term: Drug(s)
- Content: Generic drug name(s) studied
- Example: sitagliptin, clopidogrel, aspirin

Term: Phenotype Category
- Content: Type of clinical outcome studied (EXACTLY ONE: "Efficacy", "Metabolism/PK", "Toxicity", "Dosage", "Other")
- Example: Efficacy

Term: Significance
- Content: Whether the association was statistically significant (EXACTLY ONE: "yes", "no", "not stated")
- Example: yes

Term: Notes
- Content: Key study details, methodology, or important context
- Example: "Patients with the rs2909451 TT genotype in the study group exhibited a median HbA1c improvement of 0.57..."

Term: Sentence
- Content: Standardized description of the genetic association
- Format: "[Genotype/Allele] is [associated with/not associated with] [increased/decreased] [outcome] [drug context] [population context]"
- Example: "Genotype TT is associated with decreased response to sitagliptin in people with Diabetes Mellitus, Type 2."

Term: Alleles
- Content: Specific allele or genotype if different from Variant/Haplotypes field
- Example: TT, *1/*18, del/del

Term: Specialty Population
- Content: Age-specific populations (EXACTLY ONE: "Pediatric", "Geriatric", or leave empty)

Term: Metabolizer types
- Content: CYP enzyme phenotype categories
- Example: intermediate metabolizer, poor metabolizer

Term: Is/Is Not associated
- Content: Direction of association (EXACTLY ONE: "Associated with", "Not associated with")

Term: Direction of effect
- Content: Whether the effect increases or decreases the outcome (EXACTLY ONE: "increased", "decreased", or leave empty)

Term: Side effect/efficacy/other
- Content: Specific outcome descriptor
- Example: response to, risk of, likelihood of

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


def extract_drug_annotations(
    variants: List[Variant], article_text: str = None, pmcid: str = None
) -> List[DrugAnnotation]:
    """
    Extract detailed drug annotation information for variants with drug associations.

    Args:
        variants: List of variants that have drug associations
        article_text: The text of the article
        pmcid: The PMCID of the article

    Returns:
        List of DrugAnnotation objects with detailed information
    """
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)
    variant_id_list = [variant.variant_id for variant in variants]

    prompt_variables = PromptVariables(
        article_text=article_text,
        key_question=KEY_QUESTION.format(variants=variants),
        output_queues=OUTPUT_QUEUES,
        output_format_structure=DrugAnnotationList,
    )

    logger.info(f"Extracting drug annotations for variants {variant_id_list}")
    prompt_generator = GeneratorPrompt(prompt_variables)
    generator_prompt = prompt_generator.hydrate_prompt()

    generator = Generator(model="gpt-4o-mini", temperature=0.1)
    response = generator.prompted_generate(generator_prompt)

    parser = Parser(model="gpt-4o-mini", temperature=0.1)
    parser_prompt = ParserPrompt(
        input_prompt=response,
        output_format_structure=DrugAnnotationList,
        system_prompt=generator_prompt.system_prompt,
    )
    parsed_response = parser.prompted_generate(parser_prompt)

    try:
        parsed_data = json.loads(parsed_response)

        if isinstance(parsed_data, dict) and "drug_annotations" in parsed_data:
            annotation_data = parsed_data["drug_annotations"]
        elif isinstance(parsed_data, list):
            annotation_data = parsed_data
        else:
            annotation_data = [parsed_data]

        annotations = []
        for item in annotation_data:
            if "variant_annotation_id" not in item or not item["variant_annotation_id"]:
                item["variant_annotation_id"] = int(
                    str(int(time.time())) + str(random.randint(100000, 999999))
                )
            annotations.append(DrugAnnotation(**item))

        return annotations

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Failed to parse drug annotation response for variants {variants}: {e}"
        )
        return []
