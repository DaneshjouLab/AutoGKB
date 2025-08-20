from pydantic import BaseModel
from typing import List, Optional, Union
from src.inference import PMCIDGenerator
from loguru import logger
import os
import json
import re


class ParameterWithCitations(BaseModel):
    """Model for a parameter with its content and citations"""

    content: Union[str, List[str]]  # Can store either string or list of strings
    citations: Optional[List[str]] = None


class ParameterItemWithCitations(BaseModel):
    """Model for a single parameter item with its own citations"""

    content: str
    citations: Optional[List[str]] = None


class ParameterWithItemCitations(BaseModel):
    """Model for a parameter containing multiple items, each with their own citations"""

    items: List[ParameterItemWithCitations]


def parse_bullets_to_list(text: str) -> List[str]:
    """Parse bulleted text into a list of strings."""
    if not text or not text.strip():
        return []

    # Split by common bullet patterns
    lines = text.strip().split("\n")
    bullets = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common bullet markers (•, -, numbers) but preserve markdown asterisks
        cleaned_line = re.sub(r"^[\s]*[\•\-\d+\.\)\]\s]+[\s]*", "", line)
        # Also remove standalone asterisks that are bullet markers (not part of markdown)
        cleaned_line = re.sub(r"^[\s]*\*[\s]+", "", cleaned_line)

        if cleaned_line:
            bullets.append(cleaned_line)

    # If no bullets were found, return the original text as a single item
    return bullets if bullets else [text.strip()]


class StudyParameters(BaseModel):
    summary: ParameterWithCitations
    study_type: ParameterWithCitations
    participant_info: ParameterWithItemCitations
    study_design: ParameterWithItemCitations
    study_results: ParameterWithItemCitations
    allele_frequency: ParameterWithCitations
    additional_resource_links: List[str]


bulleted_output_queue = "Format the response as a bulleted list. Keep each bullet point concise (1-2 sentences maximum). If the format of the response is term: value, then have the term bolded (**term**) and the value in plain text. Do not include any other text and use markdown formatting for your response."


class StudyParametersGenerator:
    """
    Generator for extracting study parameters from PMC articles
    using separate questions for each parameter.
    """

    def __init__(self, pmcid: str, model: str = "gpt-4o"):
        """
        Initialize the generator with a PMCID and model.

        Args:
            pmcid: PubMed Central ID
            model: LLM model to use for generation
        """
        self.pmcid = pmcid
        self.generator = PMCIDGenerator(pmcid=pmcid, model=model)

    def get_summary(self) -> str:
        """Extract a short 2-3 sentence summary of the study."""
        prompt = "Provide a short 2-3 sentence summary of the study motivation, design, and results."
        output_queues = (
            "Format the response as a short paragraph without using any bullet points."
        )
        return self.generator.generate(prompt + output_queues)

    def get_study_type(self) -> str:
        """Extract the study type with explanation."""
        prompt = """What type of study is this? Provide a short description of the type of study conducted with attributes separated by commas (e.g., case-control, cohort, cross-sectional, GWAS etc.) as well as if the study was prospective, retrospective, a meta-analysis, a replication study, or a combination of these.
        
        Here are descriptions of the major types:
        GWAS: Genome-Wide Association Study; analyzes genetic variants across genomes to find associations with traits or diseases.
        Case/control: Compares individuals with a condition (cases) to those without (controls) to identify associated factors.
        Cohort: Observes a group over time to study incidence, causes, and prognosis of disease; can be prospective or retrospective.
        Clinical trial: Interventional study where participants are assigned treatments and outcomes are measured.
        Case series: Descriptive study tracking patients with a known exposure or treatment; no control group.
        Cross sectional: Observational study measuring exposure and outcome simultaneously in a population.
        Meta-analysis: Combines results from multiple studies to identify overall trends using statistical techniques.
        Linkage: Genetic study mapping loci associated with traits by analyzing inheritance patterns in families.
        Trios: Genetic study involving parent-offspring trios to identify de novo mutations.
        Unknown: Unclassified or missing study type.
        Prospective: Study designed to follow subjects forward in time.
        Retrospective: Uses existing records to look backward at exposures and outcomes.
        Replication: Repeating a study to confirm findings.

        Your output should be a string similar to these examples: "case/control, GWAS", "Cohort, replication", etc. Do not include a descriptor that's not included in the list above.
        If the study type is not clear, return "Unknown".
        Don't include any other text or formatting (e.g. don't include quotation marks in your response)."""

        return self.generator.generate(prompt)

    def get_participant_info(self) -> List[str]:
        """Extract participant information with explanation."""
        prompt = """What are the details about the participants in this study? Include age, gender, ethnicity, pre-existing conditions and any other relevant characteristics. Also breakdown this information by study group if applicable."""
        output_queues = bulleted_output_queue
        response = self.generator.generate(prompt + output_queues)
        return parse_bullets_to_list(response)

    def get_study_design(self) -> List[str]:
        """Extract study design information with explanation."""
        prompt = """Describe the study design, including the study population, sample size, and any other relevant details about how the study was conducted."""
        output_queues = bulleted_output_queue
        response = self.generator.generate(prompt + output_queues)
        return parse_bullets_to_list(response)

    def get_study_results(self) -> List[str]:
        """Extract study results with explanation."""
        prompt = """What are the main study results and findings? Pay key attention to report any ratio statistics (hazard ratio, odds ratio, etc.) and p-values."""
        output_queues = bulleted_output_queue
        response = self.generator.generate(prompt + output_queues)
        return parse_bullets_to_list(response)

    def get_allele_frequency(self) -> List[str]:
        """Extract allele frequency information with explanation."""
        prompt = """What information is provided about allele frequencies of variants in the study population? Include the allele frequency in the studied cohorts and experiments if relevant."""
        output_queues = bulleted_output_queue
        response = self.generator.generate(prompt + output_queues)
        return parse_bullets_to_list(response)

    def get_additional_resource_links(self) -> List[str]:
        """Extract additional resource links."""
        prompt = """What additional resources or links are provided in the study, such as study protocols or data? This should not include other papers or references, but solely information that pertains to the design/execution of this study. Return as a list of links/resources in markdown format."""

        response = self.generator.generate(prompt)
        # Parse the response to extract links if it's a string
        if isinstance(response, str):
            # Simple parsing - look for URLs or split by newlines
            lines = [line.strip() for line in response.split("\n") if line.strip()]
            return lines
        return response if isinstance(response, list) else []

    def generate_all_parameters(self) -> StudyParameters:
        """Generate all study parameters using separate questions."""
        logger.info(f"Extracting study parameters for {self.pmcid}")

        participant_items = [
            ParameterItemWithCitations(content=item)
            for item in self.get_participant_info()
        ]
        study_design_items = [
            ParameterItemWithCitations(content=item) for item in self.get_study_design()
        ]
        study_results_items = [
            ParameterItemWithCitations(content=item)
            for item in self.get_study_results()
        ]

        return StudyParameters(
            summary=ParameterWithCitations(content=self.get_summary()),
            study_type=ParameterWithCitations(content=self.get_study_type()),
            participant_info=ParameterWithItemCitations(items=participant_items),
            study_design=ParameterWithItemCitations(items=study_design_items),
            study_results=ParameterWithItemCitations(items=study_results_items),
            allele_frequency=ParameterWithCitations(
                content=self.get_allele_frequency()
            ),
            additional_resource_links=self.get_additional_resource_links(),
        )


def get_study_parameters(pmcid: str, model: str = "gpt-4o") -> StudyParameters:
    """Generate study parameters for a given PMCID using separate questions."""
    generator = StudyParametersGenerator(pmcid=pmcid, model=model)
    return generator.generate_all_parameters()


def test_study_parameters():
    """
    Extract and print study parameters to console
    """
    pmcid = "PMC11730665"
    print(f"\n🔬 Extracting study parameters for {pmcid}...")
    print("=" * 60)

    try:
        study_parameters = get_study_parameters(pmcid=pmcid)

        # Print results in a formatted way
        print(f"\n📋 STUDY PARAMETERS FOR {pmcid}")
        print("=" * 60)

        print(f"\n📝 SUMMARY:")
        print(f"   {study_parameters.summary.content}")

        print(f"\n🧬 STUDY TYPE:")
        print(f"   {study_parameters.study_type.content}")

        print(f"\n👥 PARTICIPANT INFO:")
        if hasattr(study_parameters.participant_info, "items"):
            for i, item in enumerate(study_parameters.participant_info.items, 1):
                print(f"   • {item.content}")
                if item.citations:
                    for j, citation in enumerate(item.citations, 1):
                        print(f"     Citation {j}: {citation[:100]}...")
        else:
            if isinstance(study_parameters.participant_info.content, list):
                for i, item in enumerate(study_parameters.participant_info.content, 1):
                    print(f"   • {item}")
            else:
                print(f"   {study_parameters.participant_info.content}")

        print(f"\n🔬 STUDY DESIGN:")
        if hasattr(study_parameters.study_design, "items"):
            for i, item in enumerate(study_parameters.study_design.items, 1):
                print(f"   • {item.content}")
                if item.citations:
                    for j, citation in enumerate(item.citations, 1):
                        print(f"     Citation {j}: {citation[:100]}...")
        else:
            if isinstance(study_parameters.study_design.content, list):
                for i, item in enumerate(study_parameters.study_design.content, 1):
                    print(f"   • {item}")
            else:
                print(f"   {study_parameters.study_design.content}")

        print(f"\n📊 STUDY RESULTS:")
        if hasattr(study_parameters.study_results, "items"):
            for i, item in enumerate(study_parameters.study_results.items, 1):
                print(f"   • {item.content}")
                if item.citations:
                    for j, citation in enumerate(item.citations, 1):
                        print(f"     Citation {j}: {citation[:100]}...")
        else:
            if isinstance(study_parameters.study_results.content, list):
                for i, item in enumerate(study_parameters.study_results.content, 1):
                    print(f"   • {item}")
            else:
                print(f"   {study_parameters.study_results.content}")

        print(f"\n🧬 ALLELE FREQUENCY:")
        if isinstance(study_parameters.allele_frequency.content, list):
            for i, item in enumerate(study_parameters.allele_frequency.content, 1):
                print(f"   • {item}")
        else:
            print(f"   {study_parameters.allele_frequency.content}")

        print(f"\n🔗 ADDITIONAL RESOURCES:")
        if study_parameters.additional_resource_links:
            for i, link in enumerate(study_parameters.additional_resource_links, 1):
                print(f"   {i}. {link}")
        else:
            print("   None found")

        print("\n" + "=" * 60)
        print("✅ Study parameters extraction completed!")

        # Also save to file
        file_path = f"data/extractions/{pmcid}/study_parameters.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(study_parameters.model_dump(), f, indent=4)
        logger.info(f"Saved to file {file_path}")

    except Exception as e:
        logger.error(f"Error extracting study parameters: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_study_parameters()
