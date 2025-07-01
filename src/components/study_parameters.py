from pydantic import BaseModel
from src.variants import QuotedStr
from typing import List


class StudyParameters(BaseModel):
    summary: str
    study_type: QuotedStr
    participant_info: QuotedStr
    study_design: QuotedStr
    study_results: QuotedStr
    allele_frequency: QuotedStr
    additional_resource_links: List[str]


KEY_QUESTION = """
We are interested in creating a summary of the study design of this article. From the article, we want to extract the following information:

Term: Study Type
- Content: The type of study conducted (e.g., case-control, cohort, cross-sectional, GWAS etc.) as well as if the study was
prospective, retrospective, a meta-analysis, a replication study, or a combination of these.
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
Unknown: Unclassified or missing study type.
Prospective: Study designed to follow subjects forward in time.
Retrospective: Uses existing records to look backward at exposures and outcomes.
Replication: Repeating a study to confirm findings.

- Example: case/control, replication (Replication analysis within a case/control design)

Term: Participant Information
- Content: Details about the participants, including age, gender, ethnicity, pre-existing conditions and any other relevant characteristics.
Also breakdown this information by study group if applicable.

Term: Study Design
- Content: A description of the study design, including the study population, sample size, and any other relevant details

Term: Study Results
- Content: A description of the study results, including the main findings and any other relevant details. Pay key attention to report the 
ratio statistic (hazard ratio, odds ratio, etc.) and p-value.

Term: Allele Frequency
- Content: Information related to the allele frequency of the variant in the study population. This should include the allele frequency in the studied
cohorts and experiments if relevant.

Term: Additional Resource Links
- Content: Any additional resources or links provided in the study, such as the study protocol or data. This should not include other papers
merely references, but solely information that pertains to the design/execution of this study.
"""

OUTPUT_QUEUES = """
Provide info for these terms explaining your reasoning and providing quotes directly from the article to support your claim. Quotes are not needed for the summary
and Additional Resource Links. Make sure to follow the output schema carefully.
"""
