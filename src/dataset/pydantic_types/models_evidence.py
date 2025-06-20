


from pydantic import BaseModel, Field


# the followin gshould be looked at and then more, 

class Evidence(BaseModel):
    evidence: str = Field(
        description=(
            "A quoted string taken verbatim from the source article that provides evidence "
            "for a specific entity, relationship, or assertion described in the annotation. "
            "The string must be found exactly or partially within the article text to be valid."
        )
    )