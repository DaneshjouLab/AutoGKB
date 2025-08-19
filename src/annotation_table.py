from pydantic import BaseModel, Field
from typing import List
from src.inference import PMCIDGenerator
from enum import Enum
from src.ontology.term_lookup import TermLookup, TermType
import loguru

logger = loguru.logger


class LinkedString(BaseModel):
    value: str
    link: str


class AnnotationRelationship(BaseModel):
    """Model for a single pharmacogenomic relationship with links"""

    gene: str = Field(description="Gene name")
    polymorphism: LinkedString = Field(
        description="Genetic polymorphism/variant (either a star allele or rsID)"
    )
    drug: LinkedString = Field(description="Drug name")
    relationship_effect: str = Field(description="Relationship or effect description")
    p_value: str = Field(description="Statistical p-value")
    citations: List[str] = Field(
        default=[], description="List of supporting sentences from the text"
    )
    p_value_citations: List[str] = Field(
        default=[],
        description="List of supporting sentences from the text for the p-value",
    )


class UnlinkedAnnotationRelationship(BaseModel):
    """Model for a single pharmacogenomic relationship"""

    gene: str = Field(description="Gene name")
    polymorphism: str = Field(
        description="Genetic polymorphism/variant (either a star allele or rsID)"
    )
    drug: str = Field(description="Drug name")
    relationship_effect: str = Field(description="Relationship or effect description")
    p_value: str = Field(description="Statistical p-value")


class UnlinkedAnnotationTable(BaseModel):
    """Model for the complete pharmacogenomic relationships table"""

    relationships: List[UnlinkedAnnotationRelationship] = Field(
        description="List of pharmacogenomic relationships"
    )


class AnnotationTable(BaseModel):
    """Model for the complete pharmacogenomic relationships table"""

    relationships: List[AnnotationRelationship] = Field(
        description="List of pharmacogenomic relationships"
    )


def add_links(
    unlinked_annotation: UnlinkedAnnotationRelationship,
) -> AnnotationRelationship:
    term_lookup = TermLookup()

    # Search for polymorphism link with error handling
    polymorphism_results = term_lookup.search(
        unlinked_annotation.polymorphism, TermType.POLYMORPHISM
    )
    polymorphism_link = (
        polymorphism_results[0].url
        if polymorphism_results and len(polymorphism_results) > 0
        else "No Match Found"
    )

    # Search for drug link with error handling
    drug_results = term_lookup.search(unlinked_annotation.drug, TermType.DRUG)
    drug_link = (
        drug_results[0].url
        if drug_results and len(drug_results) > 0
        else "No Match Found"
    )

    linked_annotation = AnnotationRelationship(
        gene=unlinked_annotation.gene,
        polymorphism=LinkedString(
            value=unlinked_annotation.polymorphism, link=polymorphism_link
        ),
        drug=LinkedString(value=unlinked_annotation.drug, link=drug_link),
        relationship_effect=unlinked_annotation.relationship_effect,
        p_value=unlinked_annotation.p_value,
        citations=[],
        p_value_citations=[],
    )
    logger.debug(f"Added drug link: {drug_link} to {unlinked_annotation.drug}")
    logger.debug(
        f"Added polymorphism link: {polymorphism_link} to {unlinked_annotation.polymorphism}"
    )
    return linked_annotation


def add_links_to_table(
    unlinked_annotation_table: UnlinkedAnnotationTable,
) -> AnnotationTable:
    linked_annotation_table = AnnotationTable(
        relationships=[
            add_links(rel) for rel in unlinked_annotation_table.relationships
        ]
    )
    return linked_annotation_table


class AnnotationTableGenerator:
    """
    Generator for extracting pharmacogenomic relationships from PMC articles
    and formatting them as structured JSON data.
    """

    def __init__(self, pmcid: str, model: str = "gpt-4.1"):
        """
        Initialize the generator with a PMCID and model.

        Args:
            pmcid: PubMed Central ID
            model: LLM model to use for generation
        """
        self.pmcid = pmcid
        self.generator = PMCIDGenerator(pmcid=pmcid, model=model)

    def generate_table_json(self) -> AnnotationTable:
        """
        Generate pharmacogenomic relationships as structured JSON.

        Returns:
            AnnotationTable: Structured data containing all relationships
        """

        structured_prompt = """
What are all the pharmacogenomic relationships found in this paper?
Please extract all pharmacogenomic relationships and format them as structured data with the following fields for each relationship:
- gene: The gene name
- polymorphism: The genetic polymorphism or variant (either a star allele or rsID). Don't include the nucleotides (ex. rs2909451 TT should just be rs2909451).
- drug: The drug name if a drug is part of this relationship. If a drug is not part of this association, fill this field with "None".
- relationship_effect: Description of the relationship or effect
- p_value: The statistical p-value. If confidence intervals are provided, display that information here as well.

Return the data as a JSON object with a 'relationships' array containing all the pharmacogenomic relationships found.
Make sure that every polymorphism/relationship gets its own entry, even if they have the same effect/p-value.
"""

        response = self.generator.generate(
            input_prompt=structured_prompt, response_format=UnlinkedAnnotationTable
        )
        response = add_links_to_table(response)

        return response

    def print_table_markdown(self, data: AnnotationTable) -> None:
        """
        Print an AnnotationTable as a clean markdown table.

        Args:
            data: AnnotationTable object to print
        """
        if not data.relationships:
            print("No pharmacogenomic relationships found.")
            return

        # Print header
        print("| Gene | Polymorphism | Drug | Relationship/Effect | p-value |")
        print("|------|--------------|------|---------------------|---------|")

        # Print each relationship
        for rel in data.relationships:
            print(
                f"| {rel.gene} | {rel.polymorphism.value} | {rel.drug.value} | {rel.relationship_effect} | {rel.p_value} |"
            )
