# config.py
# Configuration file for the variant annotation extraction process

# URLs
CLINICAL_VARIANTS_URL = "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip"
VARIANT_ANNOTATIONS_URL = "https://api.pharmgkb.org/v1/download/file/data/variantAnnotations.zip"

# File paths
VAR_DRUG_ANN_PATH = "./data/variantAnnotations/var_drug_ann.tsv"
CHECKPOINT_PATH = "./data/api_processing_checkpoint.json"
OUTPUT_CSV_PATH = "./data/variant_extraction/merged.csv"
DF_NEW_CSV_PATH = "./data/variant_extraction/df_new.csv"
WHOLE_CSV_PATH = "./data/variant_extraction/wholecsv.csv"

# NCBI email
ENTREZ_EMAIL = "aron7628@gmail.com"

# API settings
OPENAI_MODEL = "gpt-4o-2024-08-06"

# JSON schema
SCHEMA_TEXT = '''
{
    "type": "object",
    "properties": {
        "gene": {"type": "string", "description": "The specific gene related to the drug response or phenotype (e.g., CYP3A4).", "examples": ["CYP2C19", "UGT1A3"]},
        "variant/haplotypes": {"type": "string", "description": "full star allele including gene, full rsid, or full haplotype", "example": ["CYP2C19*17"]},
        "drug(s)": {"type": "string", "description": "The drug(s) that are influenced by the gene variant(s).", "examples": ["abrocitinib", "mirabegron"]},
        "phenotype category": {"type": "string", "description": "Describes the type of phenotype related to the gene-drug interaction (e.g., Metabolism/PK, toxicity).", "enum": ["Metabolism/PK", "Efficacy", "Toxicity", "Other"], "examples": ["Metabolism/PK"]},
        "significance": {"type": "string", "description": "The level of importance or statistical significance of the gene-drug interaction.", "enum": ["significant", "not significant", "not stated"], "examples": ["significant", "not stated"]},
        "metabolizer types": {"type": "string", "description": "Indicates the metabolizer status of the patient based on the gene variant.", "enum": ["poor", "intermediate", "extensive", "ultrarapid"], "examples": ["poor", "extensive"]},
        "specialty population": {"type": "string", "description": "Refers to specific populations where this gene-drug interaction may have different effects.", "examples": ["healthy individuals", "African American", "pediatric"], "default": "Not specified"},
        "PMID": {"type": "integer", "description": "PMID from source spreadsheet", "example": 123345}
    },
    "required": ["gene", "variant/haplotyptes", "drug(s)", "phenotype category", "significance", "metabolizer types", "PMID"]
}
'''

# System message template
SYSTEM_MESSAGE_TEMPLATE = (
    "You are tasked with extracting information from scientific articles to assist in genetic variant annotation. "
    "Focus on identifying key details related to genetic variants, including but not limited to:\n"
    "- Variant identifiers (e.g., rsIDs, gene names, protein changes like p.Val600Glu, or DNA changes like c.1799T>A).\n"
    "- Associated genes, transcripts, and protein products.\n"
    "- Contextual information such as clinical significance, population frequency, or related diseases and drugs.\n"
    "- Methodologies or evidence supporting the findings (e.g., experimental results, population studies, computational predictions).\n\n"
    "Your output must be in the form of an array of JSON objects adhering to the following schema:\n"
    "{schema}\n\n"
    "Each JSON object should include:\n"
    "1. A unique variant identifier.\n"
    "2. Relevant metadata (e.g., associated gene, protein change, clinical significance).\n"
    "3. Contextual evidence supporting the variant's importance.\n\n"
    "Ensure the extracted information is accurate and directly relevant to variant annotation. "
    "When extracting, prioritize structured data, avoiding ambiguous or irrelevant information."
)