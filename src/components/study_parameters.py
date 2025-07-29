from pydantic import BaseModel
from typing import List, Optional
from src.inference import PMCIDGenerator
from loguru import logger
import os
import json


class StudyParameters(BaseModel):
    summary: str
    study_type: str
    participant_info: str
    study_design: str  
    study_results: str
    allele_frequency: str
    additional_resource_links: List[str]
    summary_citations: Optional[List[str]] = None
    study_type_citations: Optional[List[str]] = None
    participant_info_citations: Optional[List[str]] = None
    study_design_citations: Optional[List[str]] = None
    study_results_citations: Optional[List[str]] = None
    allele_frequency_citations: Optional[List[str]] = None





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
        return self.generator.generate(prompt)
    
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

        Your output should be a string similar to these examples: "case/control, GWAS", "Cohort, replication", etc. Do not include a descriptor that's not included in the list above."""
        
        return self.generator.generate(prompt)
    
    def get_participant_info(self) -> str:
        """Extract participant information with explanation."""
        prompt = """What are the details about the participants in this study? Include age, gender, ethnicity, pre-existing conditions and any other relevant characteristics. Also breakdown this information by study group if applicable. Don't use bullets points, use plain text. Keep response length to one paragraph."""
        
        return self.generator.generate(prompt)
    
    def get_study_design(self) -> str:
        """Extract study design information with explanation."""
        prompt = """Describe the study design, including the study population, sample size, and any other relevant details about how the study was conducted. Don't use bullets points, use plain text. Keep response length to one paragraph."""
        
        return self.generator.generate(prompt)
    
    def get_study_results(self) -> str:
        """Extract study results with explanation."""
        prompt = """What are the main study results and findings? Pay key attention to report any ratio statistics (hazard ratio, odds ratio, etc.) and p-values. Don't use bullets points, use plain text. Keep response length to one paragraph."""
        
        return self.generator.generate(prompt)
    
    def get_allele_frequency(self) -> str:
        """Extract allele frequency information with explanation."""
        prompt = """What information is provided about allele frequencies of variants in the study population? Include the allele frequency in the studied cohorts and experiments if relevant. Don't use bullets points, use plain text. Keep response length to one paragraph."""
        
        return self.generator.generate(prompt)
    
    def get_additional_resource_links(self) -> List[str]:
        """Extract additional resource links."""
        prompt = """What additional resources or links are provided in the study, such as study protocols or data? This should not include other papers or references, but solely information that pertains to the design/execution of this study. Return as a list of links/resources."""
        
        response = self.generator.generate(prompt)
        # Parse the response to extract links if it's a string
        if isinstance(response, str):
            # Simple parsing - look for URLs or split by newlines
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return lines
        return response if isinstance(response, list) else []
    
    def generate_all_parameters(self) -> StudyParameters:
        """Generate all study parameters using separate questions."""
        logger.info(f"Extracting study parameters for {self.pmcid}")
        
        return StudyParameters(
            summary=self.get_summary(),
            study_type=self.get_study_type(),
            participant_info=self.get_participant_info(),
            study_design=self.get_study_design(),
            study_results=self.get_study_results(),
            allele_frequency=self.get_allele_frequency(),
            additional_resource_links=self.get_additional_resource_links()
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
        print(f"   {study_parameters.summary}")
        
        print(f"\n🧬 STUDY TYPE:")
        print(f"   {study_parameters.study_type}")
        
        print(f"\n👥 PARTICIPANT INFO:")
        print(f"   {study_parameters.participant_info}")
        
        print(f"\n🔬 STUDY DESIGN:")
        print(f"   {study_parameters.study_design}")
        
        print(f"\n📊 STUDY RESULTS:")
        print(f"   {study_parameters.study_results}")
        
        print(f"\n🧬 ALLELE FREQUENCY:")
        print(f"   {study_parameters.allele_frequency}")
        
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
