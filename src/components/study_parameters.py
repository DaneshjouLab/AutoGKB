from pydantic import BaseModel
from src.variants import QuotedStr
from typing import List
from src.prompts import GeneratorPrompt, ArticlePrompt
from src.inference import Generator
from src.utils import get_article_text
from loguru import logger
import os
import json


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
Term: Summary
- Content: A short 2-3 sentence summary of the study motivation, design, and results.

Term: Study Type
- Content: A short description of the type of study conducted with attributes separated by commas (e.g., case-control, cohort, cross-sectional, GWAS etc.) as well as if the study was
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

Here are composite examples:
Composite examples:
Case/control, GWAS: A GWAS using a case/control design.
Clinical trial, GWAS: GWAS performed within a clinical trial.
Cohort, GWAS: GWAS performed within a cohort study.
Case/control, meta-analysis: Meta-analysis of case/control studies.
Cohort, meta-analysis: Meta-analysis of cohort studies.
Case/control, clinical trial: Clinical trial data analyzed using case/control logic.
Cohort, clinical trial: Cohort study derived from or embedded in a clinical trial.
Case/control, replication: Replication analysis within a case/control design.
Cohort, replication: Replication analysis using cohort data.
Clinical trial, replication: Replication of findings using clinical trial data.
Meta-analysis, GWAS: Meta-analysis combining GWAS data.
Cohort, prospective: Forward-looking cohort study.
Cohort, retrospective: Historical cohort study.
Prospective, retrospective: Studies using both forward-looking and retrospective components.
Case/control, prospective/retrospective: Case/control design with a time dimension.
Meta-analysis, replication: Meta-analysis focused on replicated findings.
Linkage, trios: Linkage analysis involving family trios.
Retrospective, linkage, trios: Combined design using retrospective data, linkage, and trios.
Case series, trios: Trio-based case series.
Cohort, case/control: Study combining cohort and case/control features.
Cohort, case/control, replication: Cohort-based case/control study with replication.
Clinical trial, meta-analysis, replication: Meta-analysis of clinical trials with replication.

Your output should be a string similar to the composite examples (ex. "case/control, GWAS", "Cohort, replication", etc.).

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


def get_study_parameters(article_text):
    prompt = GeneratorPrompt(
        input_prompt=ArticlePrompt(
            article_text=article_text,
            key_question=KEY_QUESTION,
            output_queues=OUTPUT_QUEUES,
        ),
        output_format_structure=StudyParameters,
    ).get_hydrated_prompt()
    generator = Generator(model="gpt-4o")
    return generator.generate(prompt)


def test_study_parameters():
    """
    Output the extracted variant associations to a file
    """
    pmcid = "PMC11730665"
    article_text = get_article_text(pmcid)
    logger.info(f"Got article text {pmcid}")

    study_parameters = get_study_parameters(article_text=article_text)

    # Save associations
    file_path = f"data/extractions/{pmcid}/study_parameters.jsonl"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(study_parameters, f, indent=4)
    logger.info(f"Saved to file {file_path}")


if __name__ == "main":
    test_study_parameters()
