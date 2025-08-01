from src.utils import get_article_text, get_title
from src.components.annotation_table import AnnotationRelationship
from litellm import completion
from loguru import logger
import re
from typing import List

"""
Goal: Get citations for a pharmacogenomic relationship or study parameter from the article text. Uses a larger model (like o3) on the whole article text
rather than running a smaller model on each sentence.

"""

# Prompts
annotation_citation_prompt = """
Pharmacogenomic Relationship:
- Gene: {annotation.gene}
- Polymorphism: {annotation.polymorphism}  
- Proposed Effect: {annotation.relationship_effect}
- P-value: {annotation.p_value}

From the following article text, find the top 3 sentences from the article that are most relevant to and support the proposed effect of the pharmacogenomic relationship. 
Article text:
"{article_text}"

If a table provides the support warranting of being in the top 3, return the table header (## Table X: ..., etc.) as your sentence. Make sure to include a sentence or table in your top 3 responses if it has the p-value for the relationship.
Output the exact sentences from the article text in a numbered list with each sentence on a new line. No other text.
"""

study_parameters_citation_prompt = """

Parameter Type: {parameter_type}
Proposed Parameter Value: {parameter_content}

From the following article text, find the top 3 sentences from the article that are most relevant to and support the proposed parameter value.
Article text:
"{article_text}"

If a table provides the support warranting of being in the top 3, return the table header (## Table X: ..., etc.) as your sentence.
Output the exact sentences from the article text in a numbered list with each sentence on a new line. No other text.
"""

class OneShotCitations:
    def __init__(self, pmcid: str):
        self.pmcid = pmcid
        self.article_text = get_article_text(pmcid, for_citations=True)
        self.title = get_title(self.article_text)

    def get_annotation_citations(self, annotation: AnnotationRelationship, model: str = "openai/gpt-4.1") -> List[str]:
        """
        Get citations for a pharmacogenomic relationship using the whole article text with a language model.
        
        Args:
            annotation: The annotation relationship to find citations for
            model: The language model to use for citation generation
            
        Returns:
            List of top 3 most relevant sentences
        """
        prompt = annotation_citation_prompt.format(
            annotation=annotation,
            article_text=self.article_text
        )
        
        try:
            completion_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            
            response = completion(**completion_kwargs)
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response to extract sentences from the list format
            citations = self._parse_citation_list(response_text)
            
            logger.info(f"Found {len(citations)} citations for {annotation.gene}-{annotation.polymorphism}")
            return citations[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Error getting citations for annotation: {e}")
            return []

    def get_study_parameter_citations(self, parameter_type: str, parameter_content: str, model: str = "openai/gpt-4.1") -> List[str]:
        """
        Get citations for a study parameter using the whole article text with a language model.
        
        Args:
            parameter_type: The type of parameter (summary, study_type, etc.)
            parameter_content: The content of the parameter to find citations for
            model: The language model to use for citation generation
            
        Returns:
            List of top 3 most relevant sentences
        """
        prompt = study_parameters_citation_prompt.format(
            parameter_type=parameter_type,
            parameter_content=parameter_content,
            article_text=self.article_text
        )
        
        try:
            completion_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            
            response = completion(**completion_kwargs)
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response to extract sentences from the list format
            citations = self._parse_citation_list(response_text)
            
            logger.info(f"Found {len(citations)} citations for {parameter_type}")
            return citations[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Error getting citations for parameter: {e}")
            return []

    def _parse_citation_list(self, response_text: str) -> List[str]:
        """
        Parse the citation list from the model response.
        
        Args:
            response_text: Raw response from the language model
            
        Returns:
            List of extracted sentences
        """
        citations = []
        
        # Try to extract sentences from numbered list format
        lines = response_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove list markers (1., 2., -, *, etc.)
            cleaned_line = re.sub(r'^[\d\-\*•]+[\.)\s]*', '', line).strip()
            
            # Remove quotes if present
            cleaned_line = cleaned_line.strip('"\'')
            
            if cleaned_line and len(cleaned_line) > 20:  # Only keep substantial sentences
                citations.append(cleaned_line)
        
        # If no structured list found, try to split by common delimiters
        if not citations:
            # Try splitting by periods followed by capital letters (sentence boundaries)
            potential_sentences = re.split(r'\. [A-Z]', response_text)
            for i, sentence in enumerate(potential_sentences):
                sentence = sentence.strip()
                if i < len(potential_sentences) - 1:  # Re-add period except for last
                    sentence += '.'
                if len(sentence) > 20:
                    citations.append(sentence)
        
        return citations

if __name__ == "__main__":
    pmcid = "PMC11730665"
    one_shot_citations = OneShotCitations(pmcid)
    
    # Example usage
    from src.components.annotation_table import AnnotationRelationship
    
    test_annotation = AnnotationRelationship(
        gene="CYP2C9",
        polymorphism="rs1057910 GG",
        relationship_effect="Patients with the GG genotype had a trend toward lower efficacy of sitagliptin and higher efficacy of gliclazide, likely due to slower metabolism of gliclazide.",
        p_value=".464",
        citations=[]
    )
    
    # Test study parameters from the actual annotations data
    test_study_params = [
        {
            "parameter_type": "summary",
            "parameter_content": "This study aimed to compare the efficacy and safety of sitagliptin versus gliclazide, both combined with metformin, in treatment-naive patients with type 2 diabetes mellitus (T2DM) and glucotoxicity. Conducted as a single-center, randomized, controlled noninferiority trial, it involved 129 participants who were treated for 12 weeks. The results demonstrated that sitagliptin was noninferior to gliclazide in reducing glycated hemoglobin levels, with sitagliptin achieving faster glycemic targets and greater weight reductions, while genetic polymorphisms significantly influenced drug efficacy, underscoring the importance of personalized medicine."
        },
        {
            "parameter_type": "study_type",
            "parameter_content": "Clinical trial, GWAS, prospective"
        },
        {
            "parameter_type": "study_design",
            "parameter_content": "The study was a single-center, prospective, randomized, controlled, noninferiority trial conducted at Nanfang Hospital of Southern Medical University. It included 129 treatment-naive patients with type 2 diabetes mellitus (T2DM) and glucotoxicity, characterized by fasting plasma glucose (FPG) levels of ≥ 200 mg/dL and glycated hemoglobin (HbA1c) ≥ 9.0%. Participants were randomized into two groups: one receiving sitagliptin plus metformin (n = 66) and the other receiving gliclazide plus metformin (n = 63) for the first 4 weeks, followed by metformin monotherapy for an additional 8 weeks."
        },
        {
            "parameter_type": "participant_info", 
            "parameter_content": "The study included 129 treatment-naive patients with type 2 diabetes mellitus (T2DM) and glucotoxicity, aged between 18 and 70 years, with a body mass index (BMI) ranging from 18 to 30 kg/m². The participants were recruited from Nanfang Hospital of Southern Medical University, suggesting a predominantly Chinese ethnicity, although the article does not explicitly state the ethnic composition."
        }
    ]
    
    print(f"Testing OneShotCitations with PMCID: {pmcid}")
    print(f"Getting citations for: {test_annotation.gene} {test_annotation.polymorphism}")
    
    citations = one_shot_citations.get_annotation_citations(test_annotation)
    
    print(f"\nFound {len(citations)} citations for annotation:")
    for i, citation in enumerate(citations, 1):
        print(f"{i}. {citation}")
        print()
    
    # Test study parameter citations
    print("Testing study parameter citations:")
    for param in test_study_params:
        print(f"\nGetting citations for {param['parameter_type']}:")
        param_citations = one_shot_citations.get_study_parameter_citations(
            param['parameter_type'], 
            param['parameter_content']
        )
        print(f"Found {len(param_citations)} citations:")
        for i, citation in enumerate(param_citations, 1):
            print(f"{i}. {citation}")
        print()