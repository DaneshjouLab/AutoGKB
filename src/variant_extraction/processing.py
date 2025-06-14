# processing.py
import os
import pandas as pd
import tqdm
import json
from openai import OpenAI
from tqdm import tqdm
from src.variant_extraction.config import SCHEMA_TEXT, SYSTEM_MESSAGE_TEMPLATE, OPENAI_MODEL

def clean_enum_list(enum_list):
    """Clean and normalize enumeration lists."""
    cleaned_list = [x for x in enum_list if pd.notna(x)]
    split_list = [item.strip() for sublist in cleaned_list for item in sublist.split(',')]
    return list(set(split_list))

def load_and_prepare_data(file_path):
    """Load and prepare the variant annotation DataFrame."""
    df = pd.read_csv(file_path, sep='\t')
    phenotype_category_enum = clean_enum_list(df['Phenotype Category'].unique().tolist())
    significance_enum = clean_enum_list(df['Significance'].unique().tolist())
    metabolizer_types_enum = clean_enum_list(df['Metabolizer types'].unique().tolist())
    specialty_population_enum = clean_enum_list(df['Population types'].unique().tolist())
    return df, {
        'phenotype_category': phenotype_category_enum,
        'significance': significance_enum,
        'metabolizer_types': metabolizer_types_enum,
        'specialty_population': specialty_population_enum
    }

def create_schema(enum_values):
    """Create JSON schema for API calls."""
    return {
        "type": "object",
        "properties": {
            "genes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "gene": {"type": "string"},
                        "variant": {"type": "string", "description": "can be in the form of a star allele, rsid"},
                        "drug(s)": {"type": "string"},
                        "phenotype category": {"type": "string", "enum": enum_values['phenotype_category']},
                        "significance": {"type": "string", "enum": ["significant", "not significant", "not stated"]},
                        "metabolizer types": {"type": "string", "enum": enum_values['metabolizer_types']},
                        "specialty population": {"type": "string"}
                    },
                    "required": ["gene", "variant", "drug(s)", "phenotype category", "significance", "metabolizer types", "specialty population"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["genes"],
        "additionalProperties": False
    }

def create_messages(content_text, schema_text, custom_template=None):
    """Create API messages from templates."""
    system_message = custom_template or SYSTEM_MESSAGE_TEMPLATE
    system_message = system_message.format(schema=schema_text)
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": content_text}
    ]

def call_api(client, messages, schema):
    """Make an API call using the provided messages and schema."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "gene_array_response", "schema": schema, "strict": True}
        }
    )
    return json.loads(response.choices[0].message.content)

def load_checkpoint(checkpoint_path):
    """Load checkpoint data."""
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
            return set(checkpoint.get('processed_pmids', [])), checkpoint.get('results', [])
    return set(), []

def save_checkpoint(checkpoint_path, processed_pmids, results):
    """Save checkpoint data."""
    with open(checkpoint_path, 'w') as f:
        json.dump({"processed_pmids": list(processed_pmids), "results": results}, f)

def process_responses(df, client, schema_text, schema, checkpoint_path, custom_template=None):
    """Process DataFrame rows and fetch API responses."""
    processed_pmids, results = load_checkpoint(checkpoint_path)
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing API responses"):
        pmid = row['PMID']
        if pmid in processed_pmids:
            continue
        print(row)
        content_text = row['Content_text']
        try:
            messages = create_messages(content_text, schema_text, custom_template)
            extracted_data = call_api(client, messages, schema)
            for gene_info in extracted_data.get('genes', []):
                gene_info['PMID'] = pmid
                results.append(gene_info)
            processed_pmids.add(pmid)
            save_checkpoint(checkpoint_path, processed_pmids, results)
        except Exception as e:
            print(f"Error processing PMID {pmid}: {e}")
    return results