from pydantic import BaseModel, Field
from typing import Union, List,Optional,Literal
from .models_evidence import Evidence


class StudyType(BaseModel):
  """Study Type indicates type of study instance. 
  can range from meta-analysis to trios to other, 
  Properties:
  study_type: Str
  study_type_evidence: Str
  """
  study_type:str=Field(description=("A study label " 
                                    "that identifies the methological design of the study " 
                                    "from which the variant=entity association was derived. "
                                    "Should reflect the structure reported in the article's methods section. "
                                    "Use to contextualize evidence and link study-level annotations."))
  study_type_evidence:list[Evidence]=Field(description=(
      "A list of evidence entities supporting "
      "the study type entity. "
      "Must be an exact string. "
  ))


class StudyOverview(BaseModel):
  
  hypothesis:str
  claim:str
  cohort_description:str
  statistical_testing:str
  summarized_sentence:str



class StatisticalResult(BaseModel):
    primary_variable: str = Field(..., description="The main variable tested (e.g. genotype, allele, biomarker).")
    comparison_group: Optional[str] = Field(None, description="The group or condition used as comparison (e.g. wild-type, control).")
    
    test_type: Optional[str] = Field(None, description="The statistical test used (e.g. t-test, ANOVA, regression).")
    p_value: Optional[float] = Field(None, description="The reported p-value of the test.")
    effect_size: Optional[float] = Field(None, description="Reported effect size (e.g., mean difference, odds ratio).")
    effect_size_type: Optional[Literal["mean_diff", "odds_ratio", "hazard_ratio", "beta", "correlation"]] = Field(
        None, description="Type of effect size if specified."
    )
    confidence_interval: Optional[str] = Field(
        None,
        description="Confidence interval as a string (e.g., '95% CI 1.1–3.4') or extracted values."
    )
    direction: Optional[Literal["increased", "decreased", "no_change"]] = Field(
        None,
        description="Reported direction of association."
    )
    significance_threshold: Optional[float] = Field(
        0.05,
        description="The significance threshold used in the study."
    )
    n_total: Optional[int] = Field(None, description="Total number of subjects in the analysis.")
    n_per_group: Optional[dict] = Field(None, description="Sample sizes per group if available.")

    evidence: List[Evidence] = Field(..., description="Direct quote or string excerpt from the article supporting this statistical result.")
    summary:str = Field(..., description="Summary sentence of the statisical test and insight in consolidated form.")
     
