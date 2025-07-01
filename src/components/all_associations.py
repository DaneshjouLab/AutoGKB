from src.inference import Generator
from src.variants import QuotedStr
from src.prompts import GeneratorPrompt, PromptVariables
from src.utils import get_article_text
from loguru import logger
import json
from typing import List, Optional
from src.config import DEBUG
from pydantic import BaseModel
import enum


class AssocationType(enum.ENUM):
    DRUG = "Drug Association"
    PHENOTYPE = "Phenotype Association"
    FUNCTIONAL = "Functional Analysis"


class VariantAssociation(BaseModel):
    variant: QuotedStr
    gene: QuotedStr | None = None
    allele: QuotedStr | None = None
    association_type: List[AssocationType]
    quotes: List[str]

class VariantAssociationList(BaseModel):
    association_list = List[VariantAssociation]

VARIANT_LIST_KEY_QUESTION = """
In this article, find all studied associations between genetic variants (ex. rs113993960, CYP1A1*1, etc.) and a drug, phenotype, or functional analysis result. 
Include information on the gene group and allele (if present).
"""

VARIANT_LIST_OUTPUT_QUEUES = """
Your output format should be a list of the variants with the following attributes:
Variant: The Variant / Haplotypes (ex. rs2909451, CYP2C19*1, CYP2C19*2, *1/*18, etc.)
Gene: The gene group of the variant (ex. DPP4, CYP2C19, KCNJ11, etc.)
Allele: Specific allele or genotype if different from variant (ex. TT, *1/*18, del/del, etc.).
Association Type: The type(s) of associations the variant has in the article from the options Drug, Phenotype, or Functional. More information on how to determine this below.
Summary: One sentence summary of the association finding for this variant.
Quotes: REQUIRED - A direct quote from the article that mentions this specific variant and its found association. Output the exact text where this variant is discussed (ideally in the methodology, abstract, or results section).
More than one quote can be outputted if that would be helpful but try to keep the total number fewer than 3.

For each term make sure to keep track of and output the exact quote where that information is found. If there isn't an exact quote but you still believe the extraction 
to be correct, simply write "Explanation: <explanation" in the quote field.

To determine the Association Type:

A variant has a Drug association when the article reports associations between the genetic variant and
pharmacological parameters or clinical drug response measures that specifically relate to:
- Pharmacokinetic/Pharmacodynamic Parameters
- Clinical phenotypes/adverse events (Drug toxicity, organ dysfunction, treatment response phenotypes, disease outcomes when treated with drugs)

A variant has a Phenotype association when the article reports associations between genetic variants and adverse drug reactions, toxicities, or clinical outcomes that represent:
- Toxicity/Safety outcomes
- Clinical phenotypes/adverse events

A variant has a Functional association when the article contains in vitro or mechanistic functional studies that directly measure how the variant affects:
- Enzyme/transporter activity (e.g., clearance, metabolism, transport)
- Binding affinity (e.g., protein-drug interactions)
- Functional properties (e.g., uptake rates, kinetic parameters like Km/Vmax)

The key distinction is mechanistic functional studies typically get Functional associations vs clinical association studies get Phenotype and Drug associations but Functional.
Examples:
- "Cardiotoxicity when treated with anthracyclines" → Phenotype
- "Decreased clearance of methotrexate" → Drug
- "Decreased enzyme activity in cell culture" → Functional
- "Variant affects drug clearance/response" —> Drug
- "Variant affects adverse events/toxicity outcomes" —> Phenotype
- "Variant affects protein function in laboratory studies" —> Functional
"""


def extract_all_associations(
    article_text: Optional[str] = None,
    pmcid: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.1,
) -> List[VariantAssociation]:
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

    generator = Generator(model=model, temperature=temperature)
    prompt_variables = PromptVariables(
        article_text=article_text,
        key_question=VARIANT_LIST_KEY_QUESTION,
        output_queues=VARIANT_LIST_OUTPUT_QUEUES,
        output_format_structure=VariantAssociationList,
    )
    prompt_generator = GeneratorPrompt(prompt_variables)
    hydrated_prompt = prompt_generator.hydrate_prompt()
    logger.info(f"Extracting all variants")
    output = generator.prompted_generate(hydrated_prompt)
    if DEBUG:
        logger.debug(f"Raw LLM output: {output}")
    parsed_output = json.loads(output)
    if DEBUG:
        logger.debug(f"Parsed output: {parsed_output}")
    variant_list = [
        VariantAssociation(**variant_data) for variant_data in parsed_output["variant_list"]
    ]
    logger.info(f"Found {len(variant_list)} variants")
    return variant_list


def main(
    pmcid: str,
    model: str = "gpt-4o",
    temperature: float = 0.1,
    output: Optional[str] = None,
):
    """Main function to demonstrate variant extraction functionality."""
    try:
        # Extract variants
        variants = extract_all_associations(
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
