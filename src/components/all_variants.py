from src.inference import Variant, VariantList, Generator
from src.prompts import PromptGenerator
from src.article_parser import MarkdownParser
from loguru import logger
import json

VARIANT_LIST_PROMPT = """
You are an expert pharmacogenomics researcher reading and extracting annotations from the following article:

{article_text}

From this article, note down ALL discussed variants/haplotypes (ex. rs113993960, CYP1A1*1, etc.). Include information on the gene group and allele (if present). Your output format should be a list of the variants with the following attributes:
Variant: The Variant / Haplotypes (ex. rs2909451, CYP2C19*1, CYP2C19*2, *1/*18, etc.)
Gene: The gene group of the variant (ex. DPP4, CYP2C19, KCNJ11, etc.)
Allele: Specific allele or genotype if different from variant (ex. TT, *1/*18, del/del, etc.)
"""


def extract_variants_list(
    article_text: str = None,
    pmcid: str = None,
    model: str = "gpt-4o",
    temperature: float = 0.1,
    debug: bool = False,
) -> VariantList:
    """Extract a list of variants from an article.
    Args:
        article_text: The text of the article.
        PMCID: The PMCID of the article.

    Returns:
        A list of variants.
    """
    if article_text is None and pmcid is None:
        logger.error("Either article_text or pmcid must be provided.")
        raise ValueError("Either article_text or pmcid must be provided.")

    if article_text is not None and pmcid is not None:
        logger.warning("Both article_text and PMCID are provided. Using article_text.")

    if article_text is None:
        article_text = MarkdownParser(pmcid=pmcid).get_article_text()

    if debug:
        logger.debug(f"Model: {model}, Temperature: {temperature}")
        logger.debug(f"PMCID: {pmcid}")

    model = Generator(model=model, temperature=temperature)
    prompt_generator = PromptGenerator(
        VARIANT_LIST_PROMPT, {"article_text": article_text}
    )
    prompt = prompt_generator.get_prompt()
    output = model.generate(prompt, response_format=VariantList)
    variant_list = json.loads(output)["variant_list"]
    # variant_list_strs = [i['variant_id'] for i in variant_list]
    return variant_list
