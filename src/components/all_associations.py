from src.inference import Generator, Fuser
from src.variants import QuotedStr
from src.prompts import GeneratorPrompt, ArticlePrompt
from src.utils import get_article_text
from loguru import logger
import json
from typing import List, Optional, Dict
from src.config import DEBUG
from pydantic import BaseModel
import enum
import os


class AssociationType(enum.Enum):
    DRUG = "Drug Association"
    PHENOTYPE = "Phenotype Association"
    FUNCTIONAL = "Functional Analysis"


class VariantAssociation(BaseModel):
    variant: QuotedStr
    gene: QuotedStr | None = None
    allele: QuotedStr | None = None
    association_type: AssociationType
    association_summary: str


class VariantAssociationList(BaseModel):
    association_list: List[VariantAssociation]


VARIANT_LIST_KEY_QUESTION = """
In this article, find all studied associations between genetic variants (ex. rs113993960, CYP1A1*1, etc.) and a drug, phenotype, or functional analysis result. 
Include information on the gene group and allele (if present).
"""

VARIANT_LIST_OUTPUT_QUEUES = """
Your output format should be a list of associations with the following attributes:
Variant: The Variant / Haplotypes (ex. rs2909451, CYP2C19*1, CYP2C19*2, *1/*18, etc.)
Summary: One sentence summary of the association finding for this variant.
Gene: The gene group of the variant (ex. DPP4, CYP2C19, KCNJ11, etc.)
Allele: Specific allele or genotype if different from variant (ex. TT, *1/*18, del/del, etc.).
Association Type: The type of associations the variant has in the article from the options Drug, Phenotype, or Functional. One variant may have multiple association types. More information on how to determine this below.
Quotes: A direct quote from the article that mentions this specific variant and its found association. Output the exact text where this variant is discussed (ideally in the methodology, abstract, or results section).
More than one quote can be outputted if that would be helpful but try to keep the total number fewer than 3.

For each term except for Summary make sure to keep track of and output the exact quotes where that information is found/can be deduced.

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


def get_all_associations(article_text: str) -> List[Dict]:
    """
    Extract all variant associations from the article
    """
    prompt = GeneratorPrompt(
        input_prompt=ArticlePrompt(
            article_text=article_text,
            key_question=VARIANT_LIST_KEY_QUESTION,
            output_queues=VARIANT_LIST_OUTPUT_QUEUES,
        ),
        output_format_structure=VariantAssociationList,
    ).get_hydrated_prompt()
    generator = Generator(model="gpt-4o", samples=2)
    responses = generator.generate(prompt)
    logger.info(f"Fusing {len(responses)} Responses")

    fuser = Fuser(model="gpt-4o", temperature=0.1)
    fused_response = fuser.generate(responses, response_format=VariantAssociationList)

    return fused_response.association_list


def test_all_associations():
    """
    Output the extracted variant associations to a file
    """
    pmcid = "PMC4737107"
    article_text = get_article_text(pmcid)
    logger.info(f"Got article text {pmcid}")
    associations = get_all_associations(article_text)
    logger.info("Extracted associations")
    file_path = f"data/extractions/all_associations/{pmcid}.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump([assoc.model_dump(mode='json') for assoc in associations], f, indent=4)
    logger.info(f"Saved to file {file_path}")


if __name__ == "__main__":
    test_all_associations()
