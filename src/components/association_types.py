"""
Given a list of variants and the article text, determine the type of association (drug, phenotype, functional association)
"""

from src.components.all_variants import Variant
from typing import List
from src.prompts import PromptVariables, GeneratorPrompt, ParserPrompt
from src.inference import Generator, Parser
from pydantic import BaseModel

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


KEY_QUESTION = """
For the variant {variant_id}, determine what type of association(s) is being studied by the article. The options are Drug, Phenotype, and Functional.

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

Variant Drug Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Phenotype Association: (Y/N)
Explanation: (Reason)
Quote:(Quote)

Variant Functional Association: (Y/N)
Explanation: (Reason)
"""

def determine_association_type(variant: Variant, article_text: str) -> AssociationType:
    prompt_variables = PromptVariables(
        article_text=article_text,
        key_question=KEY_QUESTION,
        output_queues=OUTPUT_QUEUES,
        output_format_structure=AssociationType,
    )
    prompt_generator = GeneratorPrompt(prompt_variables)
    generator_prompt = prompt_generator.hydrate_prompt()
    generator = Generator(model="gpt-4o-mini", temperature=0.1)
    response = generator.prompted_generate(generator_prompt)
    parser = Parser(model="gpt-4o-mini", temperature=0.1)
    parser_prompt = ParserPrompt(input_prompt=response, output_format_structure=AssociationType, system_prompt=generator_prompt.system_prompt)
    parsed_response = parser.prompted_generate(parser_prompt)
    return parsed_response
