from src.inference import Generator
from src.variants import Variant, VariantList
from src.prompts import GeneratorPrompt, PromptVariables
from src.utils import get_article_text
from loguru import logger
import json
from typing import List
from src.config import DEBUG

VARIANT_LIST_KEY_QUESTION = """From this article, note down ALL discussed variants/haplotypes (ex. rs113993960, CYP1A1*1, etc.). Include information on the gene group and allele (if present).
Make sure they variant has a studied association (likely discussed in the methodology or results section), not simply mentioned as background information.
"""

VARIANT_LIST_OUTPUT_QUEUES = """Your output format should be a list of the variants with the following attributes:
Variant: The Variant / Haplotypes (ex. rs2909451, CYP2C19*1, CYP2C19*2, *1/*18, etc.)
Gene: The gene group of the variant (ex. DPP4, CYP2C19, KCNJ11, etc.)
Allele: Specific allele or genotype if different from variant (ex. TT, *1/*18, del/del, etc.)
Evidence: REQUIRED - A direct quote from the article that mentions this specific variant. Find the exact text where this variant is discussed in the methodology or results section.

IMPORTANT: You MUST include the evidence field for every variant. Do not leave it empty or null.
"""


def extract_all_variants(
    article_text: str = None,
    pmcid: str = None,
    model: str = "gpt-4o",
    temperature: float = 0.1,
) -> List[Variant]:
    """Extract a list of variants from an article.
    Args:
        article_text: The text of the article.
        PMCID: The PMCID of the article.

    Returns:
        A list of variants.
    """
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)

    if DEBUG:
        logger.debug(f"Model: {model}, Temperature: {temperature}")
        logger.debug(f"PMCID: {pmcid}")

    model = Generator(model=model, temperature=temperature)
    prompt_variables = PromptVariables(
        article_text=article_text,
        key_question=VARIANT_LIST_KEY_QUESTION,
        output_queues=VARIANT_LIST_OUTPUT_QUEUES,
        output_format_structure=VariantList,
    )
    prompt_generator = GeneratorPrompt(prompt_variables)
    hydrated_prompt = prompt_generator.hydrate_prompt()
    logger.info(f"Extracting all variants")
    output = model.prompted_generate(hydrated_prompt)
    if DEBUG:
        logger.debug(f"Raw LLM output: {output}")
    parsed_output = json.loads(output)
    if DEBUG:
        logger.debug(f"Parsed output: {parsed_output}")
    variant_list = [
        Variant(**variant_data) for variant_data in parsed_output["variant_list"]
    ]
    logger.info(f"Found {len(variant_list)} variants")
    return variant_list


def main(
    pmcid: str, model: str = "gpt-4o", temperature: float = 0.1, output: str = None
):
    """Main function to demonstrate variant extraction functionality."""
    try:
        # Extract variants
        variants = extract_all_variants(
            pmcid=pmcid, model=model, temperature=temperature
        )

        # Print results
        print(f"Found {len(variants)} variants:")
        for i, variant in enumerate(variants, 1):
            print(f"{i}. Variant: {variant.variant_id}")
            print(f"   Gene: {variant.gene}")
            print(f"   Allele: {variant.allele}")
            print(f"   Evidence: {variant.evidence}")
            print()

        # Save to file if output path specified
        if output:
            with open(output, "w") as f:
                json.dump({"variants": variants}, f, indent=2)
            print(f"Results saved to {output}")

    except Exception as e:
        logger.error(f"Error extracting variants: {e}")
        raise
