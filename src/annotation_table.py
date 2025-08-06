from pydantic import BaseModel, Field
from typing import List
from src.inference import PMCIDGenerator


class AnnotationRelationship(BaseModel):
    """Model for a single pharmacogenomic relationship"""

    gene: str = Field(description="Gene name")
    polymorphism: str = Field(description="Genetic polymorphism/variant")
    relationship_effect: str = Field(description="Relationship or effect description")
    p_value: str = Field(description="Statistical p-value")
    citations: List[str] = Field(
        default=[], description="List of supporting sentences from the text"
    )
    p_value_citations: List[str] = Field(
        default=[],
        description="List of supporting sentences from the text for the p-value",
    )


class AnnotationTable(BaseModel):
    """Model for the complete pharmacogenomic relationships table"""

    relationships: List[AnnotationRelationship] = Field(
        description="List of pharmacogenomic relationships"
    )


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

        self.prompt = """
What are all the pharmacogenomic relationships found in this paper?
Output your response in markdown table format with nothing except the table. The columns should be Gene, Polymorphism, Relationship/Effect, and p-value.
Make sure that every polymorphism gets its own row, even if they have the same effect/p-value.
"""

    def generate_table_json(self) -> AnnotationTable:
        """
        Generate pharmacogenomic relationships as structured JSON.

        Returns:
            PharmacogenomicTable: Structured data containing all relationships
        """
        # Generate structured response using Pydantic model
        structured_prompt = """
What are all the pharmacogenomic relationships found in this paper?
Please extract all pharmacogenomic relationships and format them as structured data with the following fields for each relationship:
- gene: The gene name
- polymorphism: The genetic polymorphism or variant
- drug: The drug name if a drug is part of this relationship. If a drug is not part of this association, fill this field with "None".
- relationship_effect: Description of the relationship or effect
- p_value: The statistical p-value. If confidence intervals are provided, display that information here as well.

Return the data as a JSON object with a 'relationships' array containing all the pharmacogenomic relationships found.
Make sure that every polymorphism/relationship gets its own entry, even if they have the same effect/p-value.
"""

        response = self.generator.generate(
            input_prompt=structured_prompt, response_format=AnnotationTable
        )

        return response

    def generate_table_markdown(self) -> str:
        """
        Generate pharmacogenomic relationships as markdown table.

        Returns:
            str: Markdown formatted table
        """
        return self.generator.generate(self.prompt)

    def convert_markdown_to_json(self, markdown_table: str) -> AnnotationTable:
        """
        Convert a markdown table to structured JSON format.

        Args:
            markdown_table: Markdown formatted table string

        Returns:
            PharmacogenomicTable: Structured data
        """

        lines = markdown_table.strip().split("\n")
        # Skip header and separator rows, filter out empty lines
        data_lines = [
            line for line in lines[2:] if line.strip() and not line.startswith("|-")
        ]

        relationships = []
        for line in data_lines:
            # Split by | and clean up
            cells = [
                cell.strip() for cell in line.split("|")[1:-1]
            ]  # Remove empty first/last
            if len(cells) >= 4:
                relationships.append(
                    AnnotationRelationship(
                        gene=cells[0],
                        polymorphism=cells[1],
                        relationship_effect=cells[2],
                        p_value=cells[3],
                    )
                )

        return AnnotationTable(relationships=relationships)

    def print_table_markdown(self, data: AnnotationTable) -> None:
        """
        Print a PharmacogenomicTable as a clean markdown table.

        Args:
            data: PharmacogenomicTable object to print
        """
        if not data.relationships:
            print("No pharmacogenomic relationships found.")
            return

        # Print header
        print("| Gene | Polymorphism | Relationship/Effect | p-value |")
        print("|------|-------------|---------------------|---------|")

        # Print each relationship
        for rel in data.relationships:
            print(
                f"| {rel.gene} | {rel.polymorphism} | {rel.relationship_effect} | {rel.p_value} |"
            )
