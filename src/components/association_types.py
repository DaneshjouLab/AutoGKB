"""
Given a list of variants and the article text, determine the type of association (drug, phenotype, functional association)
"""

from src.components.all_variants import Variant
from typing import List
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from pydantic import BaseModel
from src.utils import get_article_text
from loguru import logger


class AssociationType(BaseModel):
    """
    Association type.
    """
    variant: Variant
    drug_association: bool
    drug_association_explanation: str
    drug_association_quote: str
    phenotype_association: bool
    phenotype_association_explanation: str
    phenotype_association_quote: str
    functional_association: bool
    functional_association_explanation: str
    functional_association_quote: str

class AssociationTypeList(BaseModel):
    """
    List of association types for structured output.
    """
    association_types: List[AssociationType]


KEY_QUESTION = """
For the following variants, determine what type of association(s) is being studied by the article. The options are Drug, Phenotype, and Functional.
Variants: {variants}

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

OUTPUT_QUEUES = """
Using this information, decide which out of the 3 annotations the variant should receive with a one sentence summary explanation for the decision along with a sentence/quote from the article that indicates why this is true. It is possible there is more than one Annotation/association per variant

Variant Object: (variant)
Variant Drug Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Phenotype Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Functional Association: (Y/N)
Explanation: (Reason)
"""

def get_association_types(variants: List[Variant], article_text: str = None, pmcid: str = None) -> List[AssociationType]:
    article_text = get_article_text(pmcid=pmcid, article_text=article_text)
    variant_id_list = [variant.variant_id for variant in variants]
    prompt_variables = PromptVariables(
        article_text=article_text,
        key_question=KEY_QUESTION.format(variants=variants),
        output_queues=OUTPUT_QUEUES,
        output_format_structure=AssociationTypeList,
    )
    logger.info(f"Determining association type for variants {variant_id_list}")
    prompt_generator = GeneratorPrompt(prompt_variables)
    generator_prompt = prompt_generator.hydrate_prompt()
    
    # Step 1: Generate the analysis
    generator = Generator(model="gpt-4o-mini", temperature=0.1)
    response = generator.prompted_generate(generator_prompt)
    
    # Step 2: Parse the response into structured format
    parser = Parser(model="gpt-4o-mini", temperature=0.1)
    parser_prompt = ParserPrompt(
        input_prompt=response, 
        output_format_structure=AssociationTypeList, 
        system_prompt=generator_prompt.system_prompt
    )
    parsed_response = parser.prompted_generate(parser_prompt)
    
    # Parse the string response into AssociationType objects
    try:
        import json
        parsed_data = json.loads(parsed_response)
        
        # Handle different response formats
        if isinstance(parsed_data, dict) and 'association_types' in parsed_data:
            association_data = parsed_data['association_types']
        elif isinstance(parsed_data, list):
            association_data = parsed_data
        else:
            association_data = [parsed_data]
            
        # Convert to AssociationType objects
        return [AssociationType(**item) for item in association_data]
        
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse response for variants {variants}: {e}")
        return None

def list_association_types(association_type: AssociationType, debug: bool = False) -> List[str]:
    association_types = []
    if association_type.drug_association:
        association_types.append("Drug")
        if debug:
            logger.debug(f"Drug Association: {association_type.drug_association}")
            logger.debug(f"Drug Association Explanation: {association_type.drug_association_explanation}")
            logger.debug(f"Drug Association Quote: {association_type.drug_association_quote}")
    if association_type.phenotype_association:
        association_types.append("Phenotype")
        if debug:
            logger.debug(f"Phenotype Association: {association_type.phenotype_association}")
            logger.debug(f"Phenotype Association Explanation: {association_type.phenotype_association_explanation}")
            logger.debug(f"Phenotype Association Quote: {association_type.phenotype_association_quote}")
    if association_type.functional_association:
        association_types.append("Functional")
        if debug:
            logger.debug(f"Functional Association: {association_type.functional_association}")
            logger.debug(f"Functional Association Explanation: {association_type.functional_association_explanation}")
            logger.debug(f"Functional Association Quote: {association_type.functional_association_quote}")
    logger.info(f"Variant: {association_type.variant.variant_id} has association types: {association_types}")
    return association_types