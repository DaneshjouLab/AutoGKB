'''
Aaron's original code, with minor cleaning and reformatting.
No major changes were made to the logic or structure.
'''

import requests
import zipfile
import io
import pandas as pd
from openai import OpenAI
import time
from Bio import Entrez
import os
import json
import random
from bs4 import BeautifulSoup
import tqdm

url = "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip"

# Download the zip file
try:
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for bad status codes

    # Unpack the zip file
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall("clinicalVariants")
        print("Successfully downloaded and unpacked the zip file.")

except requests.exceptions.RequestException as e:
    print(f"Error downloading the file: {e}")
except zipfile.BadZipFile as e:
    print(f"Error unpacking the zip file: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

url = "https://api.pharmgkb.org/v1/download/file/data/variantAnnotations.zip"


# Download the zip file
try:
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for bad status codes

    # Unpack the zip file
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall("variantAnnotations")
        print("Successfully downloaded and unpacked the zip file.")

except requests.exceptions.RequestException as e:
    print(f"Error downloading the file: {e}")
except zipfile.BadZipFile as e:
    print(f"Error unpacking the zip file: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

## Loading the data

var_drug_ann = "/content/variantAnnotations/var_drug_ann.tsv"
df_var_drug_ann = pd.read_csv(var_drug_ann, sep='\t')

## Get unique values
phenotype_category_enum = df_var_drug_ann['Phenotype Category'].unique().tolist()
significance_enum = df_var_drug_ann['Significance'].unique().tolist()
metabolizer_types_enum = df_var_drug_ann['Metabolizer types'].unique().tolist()
specialty_population_enum = df_var_drug_ann['Population types'].unique().tolist()

## Get PMCID

# Email for NCBI
Entrez.email = "aron7628@gmail.com"

# Step 1: Function to get PMCID from PMID
def get_pmcid_from_pmid(pmid, retries=3):
    for attempt in range(retries):
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            if record and 'LinkSetDb' in record[0] and record[0]['LinkSetDb']:
                pmcid = record[0]['LinkSetDb'][0]['Link'][0]['Id']
                return pmcid
            else:
                print(f"No PMCID found for PMID {pmid}.")
                return None
        except Exception as e:
            print(f"An error occurred for pmid {pmid} on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                # Backoff time increases exponentially with jitter
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                return None

# Step 2: Function to fetch content using PMCID
def fetch_pmc_content(pmcid):
    try:
        handle = Entrez.efetch(db="pmc", id=pmcid, rettype="full", retmode="xml")
        record = handle.read()
        handle.close()
        return record
    except Exception as e:
        print(f"An error occurred while fetching content for PMCID {pmcid}: {e}")
        return None

# Function to process each row in the DataFrame
def process_row(row, processed_pmids, processed_data):
    time.sleep(0.4 + random.uniform(0, 0.5))  # Introduce delay to avoid throttling
    pmid = str(row['PMID'])

    if pmid in processed_pmids:
        # Use the previously processed data for duplicate PMIDs
        return pd.Series(processed_data[pmid])

    # Step 1: Get PMCID from PMID
    pmcid = get_pmcid_from_pmid(pmid)

    if pmcid:
        # Step 2: Fetch PMC content using the new fetch_pmc_content function
        xml_content = fetch_pmc_content(pmcid)

        if xml_content:
            # Step 3: Parse the XML content to extract text and title using BeautifulSoup
            soup = BeautifulSoup(xml_content, 'xml')

            # Extract the article title
            title_tag = soup.find('article-title')
            title = title_tag.get_text() if title_tag else "No Title Found"

            # Extract the full text of the article
            clean_text = soup.get_text()

            # Save processed data for this PMID
            processed_pmids.add(pmid)
            processed_data[pmid] = {
                'PMCID': pmcid,
                'Title': title,
                'Content': xml_content,
                'Content_text': clean_text,
            }
        else:
            # Save processed data for failed PMC content fetch
            processed_pmids.add(pmid)
            processed_data[pmid] = {
                'PMCID': pmcid,
                'Title': None,
                'Content': None,
                'Content_text': None,
            }
    else:
        # Save processed data for invalid PMIDs
        processed_pmids.add(pmid)
        processed_data[pmid] = {
            'PMCID': None,
            'Title': None,
            'Content': None,
            'Content_text': None,
        }

    # Return the processed data for the current row
    return pd.Series(processed_data[pmid])

# Wrapper function to handle processed PMIDs and data
def process_dataframe(df):
    processed_pmids = set()
    processed_data = {}

    tqdm.pandas(desc="Processing rows")  # Initialize tqdm for Pandas
    return df.progress_apply(lambda row: process_row(row, processed_pmids, processed_data), axis=1)

how_many = 5
testdf = df_var_drug_ann[:how_many]  
result_df = process_dataframe(testdf)

# Combine the results back with the original DataFrame
df_new = pd.concat([testdf, result_df], axis=1)
df_new.to_csv(f"first_{how_many}_var_drug.csv")

df_new.dropna(subset=['Content'], inplace=True)
df_new.reset_index(drop=True, inplace=True)
print(df_new)

len(df_new['PMID'].unique())

schema_text = '''
{
    "type": "object",
    "properties": {
        "gene": {
            "type": "string",
            "description": "The specific gene related to the drug response or phenotype (e.g., CYP3A4).",
            "examples": ["CYP2C19", "UGT1A3"]
        },
        "variant/haplotypes": {
                                    "type": "string",
                                    "description": "full star allele including gene, full rsid, or full haplotype"
                                    "example":["CYP2C19*17"]
                                },
        "drug(s)": {
            "type": "string",
            "description": "The drug(s) that are influenced by the gene variant(s).",
            "examples": ["abrocitinib", "mirabegron"]
        },
        "phenotype category": {
            "type": "string",
            "description": "Describes the type of phenotype related to the gene-drug interaction (e.g., Metabolism/PK, toxicity).",
            "enum": ["Metabolism/PK", "Efficacy", "Toxicity", "Other"],
            "examples": ["Metabolism/PK"]
        },
        "significance": {
            "type": "string",
            "description": "The level of importance or statistical significance of the gene-drug interaction (e.g., 'significant', 'not significant').",
            "enum": ["significant", "not significant", "not stated"],
            "examples": ["significant", "not stated"]
        },
        "metabolizer types": {
            "type": "string",
            "description": "Indicates the metabolizer status of the patient based on the gene variant (e.g., poor metabolizer, extensive metabolizer).",
            "enum": ["poor", "intermediate", "extensive", "ultrarapid"],
            "examples": ["poor", "extensive"]
        },
        "specialty population": {
            "type": "string",
            "description": "Refers to specific populations where this gene-drug interaction may have different effects (e.g., ethnic groups, pediatric populations).",
            "examples": ["healthy individuals", "African American", "pediatric"],
            "default": "Not specified"
        },
        "PMID": {
            "type": "integer",  # Changed from 'int' to 'integer'
            "description": "PMID from source spreadsheet",
            "example": 123345
        }
    },
    "required": ["gene","variant/haplotyptes", "drug(s)", "phenotype category", "significance", "metabolizer types", "PMID"]
}
'''

def clean_enum_list(enum_list):
    # Remove NaN
    cleaned_list = [x for x in enum_list if pd.notna(x)]
    # Split comma-separated strings and flatten the list
    split_list = [item.strip() for sublist in cleaned_list for item in sublist.split(',')]
    return list(set(split_list))  # Ensure uniqueness

# Clean phenotype_category_enum and metabolizer_types_enum
phenotype_category_enum = clean_enum_list(phenotype_category_enum)
metabolizer_types_enum = clean_enum_list(metabolizer_types_enum)


schema = {
    "type": "object",  # The root must be an object, not an array
    "properties": {
        "genes": {  # The "genes" property will contain an array of gene objects
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "gene": {
                        "type": "string"
                    },
                    "variant": {
                        "type": "string",
                        "description": "can be in the form of a star allele, rsid"
                    },
                    "drug(s)": {
                        "type": "string"
                    },

                    "phenotype category": {
                        "type": "string",
                        "enum": phenotype_category_enum
                    },
                    "significance": {
                        "type": "string",
                        "enum": ["significant", "not significant", "not stated"]
                    },
                    "metabolizer types": {
                        "type": "string",
                        "enum": metabolizer_types_enum
                    },
                    "specialty population": {
                        "type": "string"
                    }


                },
                "required": ["gene","variant","drug(s)", "phenotype category", "significance", "metabolizer types", "specialty population"],
                "additionalProperties": False
            }
        }
    },
    "required": ["genes"],  # The root object must have a "genes" array
    "additionalProperties": False
}

# Initialize a list to hold the flattened JSON results
flattened_results = []

# Loop through each row in df_new
for index, row in df_new.iterrows():
    content_text = row['Content_text']
    pmid = row['PMID']

    # Make the API call for each row
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": f"Extract multiple gene-related information from the text and return them as an array of JSON objects with example schema{schema_text}"},
            {"role": "user", "content": content_text}  # Assuming Content contains the text you're processing
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "gene_array_response",
                "schema": schema,
                "strict": True
            }
        }
    )

    # Extract and load the JSON response
    extracted_data = json.loads(response.choices[0].message.content)

    # Flatten the JSON output and attach PMID
    for gene_info in extracted_data.get('genes', []):
        gene_info['PMID'] = pmid  # Attach the PMID to each gene entry
        flattened_results.append(gene_info)  # Add to the list of flattened results

# Convert flattened results to a DataFrame
flattened_df = pd.DataFrame(flattened_results)

print(flattened_df)

# this fetches data.
def fetch_test_data(df, num_rows=10):
    """
    Fetch a subset of data for testing.
    :param df: DataFrame containing the full dataset.
    :param num_rows: Number of rows to sample for testing.
    :return: DataFrame with sampled rows.
    """
    return df.head(num_rows)

def create_messages(content_text, schema_text, custom_template=None):
    """
    Create API messages from templates.
    :param content_text: Text content to process.
    :param schema_text: Schema description for the API call.
    :param custom_template: Optional custom template string for the system message.
    :return: List of messages for the API.
    """
    if custom_template:
        system_message = custom_template.format(schema=schema_text, content=content_text)
    else:
        system_message = (
            "You are tasked with extracting information from scientific articles to assist in genetic variant annotation. "
            "Focus on identifying key details related to genetic variants, including but not limited to:\n"
            "- Variant identifiers (e.g., rsIDs, gene names, protein changes like p.Val600Glu, or DNA changes like c.1799T>A).\n"
            "- Associated genes, transcripts, and protein products.\n"
            "- Contextual information such as clinical significance, population frequency, or related diseases and drugs.\n"
            "- Methodologies or evidence supporting the findings (e.g., experimental results, population studies, computational predictions).\n\n"
            "Your output must be in the form of an array of JSON objects adhering to the following schema:\n"
            f"{schema_text}\n\n"
            "Each JSON object should include:\n"
            "1. A unique variant identifier.\n"
            "2. Relevant metadata (e.g., associated gene, protein change, clinical significance).\n"
            "3. Contextual evidence supporting the variant's importance.\n\n"
            "Ensure the extracted information is accurate and directly relevant to variant annotation. "
            "When extracting, prioritize structured data, avoiding ambiguous or irrelevant information."
        )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": content_text}
    ]

def call_api(client, messages, schema):
    """
    Make an API call using the provided messages and schema.
    :param client: API client object.
    :param messages: List of messages to send to the API.
    :param schema: JSON schema definition.
    :return: Parsed JSON response.
    """
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "gene_array_response",
                "schema": schema,
                "strict": True
            }
        }
    )
    return json.loads(response.choices[0].message.content)

def load_checkpoint(checkpoint_path):
    """
    Load checkpoint data (processed PMIDs and saved results).
    :param checkpoint_path: Path to the checkpoint file.
    :return: Tuple of processed PMIDs set and saved results list.
    """
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
            return set(checkpoint.get('processed_pmids', [])), checkpoint.get('results', [])
    return set(), []

def save_checkpoint(checkpoint_path, processed_pmids, results):
    """
    Save checkpoint data (processed PMIDs and results).
    :param checkpoint_path: Path to the checkpoint file.
    :param processed_pmids: Set of processed PMIDs.
    :param results: List of saved results.
    """
    with open(checkpoint_path, 'w') as f:
        json.dump({"processed_pmids": list(processed_pmids), "results": results}, f)

def process_responses(df, client, schema_text, schema, checkpoint_path, custom_template=None):
    """
    Process rows from the DataFrame and fetch API responses, saving dynamically.
    :param df: DataFrame containing the rows to process.
    :param client: API client object.
    :param schema_text: Schema description for the API call.
    :param schema: JSON schema definition.
    :param checkpoint_path: Path to the checkpoint file.
    :param custom_template: Optional custom template string for the system message.
    :return: List of flattened JSON objects with additional metadata.
    """
    processed_pmids, results = load_checkpoint(checkpoint_path)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing rows"):
        pmid = row['PMID']

        if pmid in processed_pmids:
            continue  # Skip already-processed PMIDs

        content_text = row['Content_text']
        try:
            messages = create_messages(content_text, schema_text, custom_template)
            extracted_data = call_api(client, messages, schema)
            for gene_info in extracted_data.get('genes', []):
                gene_info['PMID'] = pmid
                results.append(gene_info)

            processed_pmids.add(pmid)  # Mark as processed
        except Exception as e:
            print(f"Error processing PMID {pmid}: {e}")

        # Save progress after each processed row
        save_checkpoint(checkpoint_path, processed_pmids, results)

    return results

checkpoint_file = "/content/api_processing_checkpoint.json"
flattened_results = process_responses(df_new, client, schema_text, schema, checkpoint_file)

# Convert to DataFrame
flattened_df = pd.DataFrame(flattened_results)

# Print the resulting DataFrame
print(flattened_df)

def loadCSV(path="/content/first_5000_var_drug.csv"):
    return pd.read_csv(path,index_col=[0])

df_new = loadCSV()

groups = df_new.groupby("PMID")

maxV = [0,""]
lengths = set()
for i, (name, group) in enumerate(groups):
    lengths.add(len(group))
    maxV[0] = max(len(group),maxV[0])
    maxV[1] = name

print(maxV)
print(lengths)

#load the outputs from chatgpt
outputsDF = pd.read_csv("/content/outputs_per_pmid.csv")
outputGroups = outputsDF.groupby("PMID")

print(outputsDF.columns)
print(df_new.columns)

column_mapping = {
    'gene': 'Gene',
    'variant/haplotypes': 'Variant/Haplotypes',
    'drug(s)': 'Drug(s)',
    'phenotype category': 'Phenotype Category',
    'significance': 'Significance',
    'metabolizer types': 'Metabolizer types',
    'specialty population': 'Specialty Population',
    'PMID': 'PMID'  # Keep this for grouping
}

# Add a new column to flattened_df to indicate whether a match was found and to store the Variant Annotation ID
flattened_df['match'] = False
flattened_df['Variant Annotation ID'] = None

# Iterate through each row in flattened_df
for idx, row in flattened_df.iterrows():
    pmid = row['PMID']
    gene = row['gene']

    # Find all rows in df_new where PMID matches
    matching_pmid_rows = df_new[df_new['PMID'] == pmid]

    # Check if there is a gene match in the filtered df_new
    gene_match_row = matching_pmid_rows[matching_pmid_rows['Gene'] == gene]

    if not gene_match_row.empty:
        # If there's a match, attach the Variant Annotation ID to flattened_df
        flattened_df.at[idx, 'Variant Annotation ID'] = gene_match_row.iloc[0]['Variant Annotation ID']
        flattened_df.at[idx, 'match'] = True  # Mark as matched
    else:
        flattened_df.at[idx, 'match'] = False  # No match found

# Output the result
print(flattened_df)

flattened_df = pd.read_csv("/content/outputs_per_pmid_matched.csv")

# Perform a merge on 'Variant Annotation ID'
merged_df = pd.merge(flattened_df, df_new, on='Variant Annotation ID', how='inner', suffixes=('_flattened', '_df_new'))

merged_df = merged_df.rename(columns={'Variant Annotation ID_flattened': 'Variant Annotation ID'})

# Output the final DataFrame

merged_df.to_csv('/content/merged_first100.csv', index=False)

df_new.to_csv('/content/df_new.csv', index=False)

df_new_one = df_new
outputs_first100_one = flattened_df

# Align the datasets based only on PMID, which is guaranteed to match
df_aligned_pmid = pd.merge(df_new_one, outputs_first100_one, how='inner', left_on='PMID', right_on='PMID', suffixes=('_truth', '_output'))

# Compare key fields: 'Gene', 'Drug(s)', and 'Phenotype Category'
df_aligned_pmid['gene_match'] = df_aligned_pmid['Gene'] == df_aligned_pmid['gene']
df_aligned_pmid['drug_match'] = df_aligned_pmid['Drug(s)'] == df_aligned_pmid['drug(s)']
df_aligned_pmid['phenotype_match'] = df_aligned_pmid['Phenotype Category'] == df_aligned_pmid['phenotype category']

# Calculate the match statistics for each field
match_stats = {
    'gene_match_rate': df_aligned_pmid['gene_match'].mean() * 100,
    'drug_match_rate': df_aligned_pmid['drug_match'].mean() * 100,
    'phenotype_match_rate': df_aligned_pmid['phenotype_match'].mean() * 100,
    'exact_match_rate': df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match']].all(axis=1).mean() * 100,
    'partial_match_rate': df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match']].any(axis=1).mean() * 100,
    'mismatch_rate': (~df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match']].any(axis=1)).mean() * 100
}

# Display match statistics
print("Match Statistics:")
for key, value in match_stats.items():
    print(f"{key}: {value:.2f}%")

pmidGroups=df_aligned_pmid.groupby("PMID")

len(flattened_df["PMID"].unique())
len(df_new[df_new["PMID"].isin(flattened_df["PMID"].unique())])

# Simplified VariantMatcher class
class SimplifiedVariantMatcher:
    @staticmethod
    def split_variants(variant_string):
        """Split variant strings into individual components."""
        if pd.isna(variant_string):
            return set()
        return set(map(str.strip, variant_string.replace('/', ',').split(',')))

    @staticmethod
    def preprocess_variants(variant_string, gene=None):
        """Attach star alleles to gene and handle complex variant notations."""
        variants = SimplifiedVariantMatcher.split_variants(variant_string)
        processed_variants = set()

        for variant in variants:
            variant = variant.strip()
            # Handle rsIDs
            if 'rs' in variant:
                rs_match = re.findall(r'rs\d+', variant)
                processed_variants.update(rs_match)

            # Handle star alleles with additional SNP information
            if '*' in variant and '-' in variant and gene:
                star_allele, mutation = variant.split('-', 1)
                processed_variants.add(f"{gene}{star_allele.strip()}")
                processed_variants.add(mutation.strip())

            # Handle simple star alleles
            elif '*' in variant and gene:
                processed_variants.add(f"{gene}{variant.strip()}")

            # Handle SNP notations directly
            elif '>' in variant:
                processed_variants.add(variant.strip())

            # Add any remaining variants as is
            else:
                processed_variants.add(variant.strip())

        return processed_variants

    def match_row(self, row):
        """Match ground truth and predicted variants for a single row."""
        truth_variants = self.preprocess_variants(row['Variant/Haplotypes_truth'], gene=row['Gene_truth'])
        predicted_variants = self.preprocess_variants(row['variant/haplotypes_output'], gene=row['Gene_output'])

        # Perform matching
        if predicted_variants.intersection(truth_variants):
            return 'Partial Match'
        if predicted_variants == truth_variants:
            return 'Exact Match'
        return 'No Match'


# Manually add suffixes to overlapping columns
df_new_one = df_new_one.rename(columns={
    'Gene': 'Gene_truth',
    'Drug(s)': 'Drug(s)_truth',
    'Phenotype Category': 'Phenotype Category_truth',
    'Variant/Haplotypes': 'Variant/Haplotypes_truth'
})

outputs_first100_one = outputs_first100_one.rename(columns={
    'gene': 'Gene_output',
    'drug(s)': 'Drug(s)_output',
    'phenotype category': 'Phenotype Category_output',
    'variant/haplotypes': 'variant/haplotypes_output'
})

# Merge the datasets based on PMID
df_aligned_pmid = pd.merge(
    df_new_one,
    outputs_first100_one,
    how='inner',
    on='PMID'
)

# Initialize SimplifiedVariantMatcher
matcher = SimplifiedVariantMatcher()

# Add the variant_match column to the aligned dataset
df_aligned_pmid['variant_match'] = df_aligned_pmid.apply(lambda row: matcher.match_row(row), axis=1)

# Compare key fields: 'Gene', 'Drug(s)', and 'Phenotype Category'
df_aligned_pmid['gene_match'] = df_aligned_pmid['Gene_truth'] == df_aligned_pmid['Gene_output']
df_aligned_pmid['drug_match'] = df_aligned_pmid['Drug(s)_truth'] == df_aligned_pmid['Drug(s)_output']
df_aligned_pmid['phenotype_match'] = df_aligned_pmid['Phenotype Category_truth'] == df_aligned_pmid['Phenotype Category_output']
df_aligned_pmid['significance_match'] = (
    df_aligned_pmid['Significance'] ==
    df_aligned_pmid['significance'].map({
        'significant': 'yes',
        'not significant': 'no',
        'not stated': 'not stated'
    })
)
df_aligned_pmid['metabolizer_match'] = df_aligned_pmid['Metabolizer types'] == df_aligned_pmid['metabolizer types']
df_aligned_pmid['population_match'] = df_aligned_pmid['Specialty Population'] == df_aligned_pmid['specialty population']


# Calculate match statistics for each field
match_stats = {
    'gene_match_rate': df_aligned_pmid['gene_match'].mean() * 100,
    'drug_match_rate': df_aligned_pmid['drug_match'].mean() * 100,
    'phenotype_match_rate': df_aligned_pmid['phenotype_match'].mean() * 100,
    'variant_match_rate': (df_aligned_pmid['variant_match'] == 'Exact Match').mean() * 100,
    'partial_variant_match_rate': (df_aligned_pmid['variant_match'] == 'Partial Match').mean() * 100,
    'exact_match_rate': df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match']].all(axis=1).mean() * 100,
    'partial_match_rate': df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match']].any(axis=1).mean() * 100,
    'mismatch_rate': (~df_aligned_pmid[['gene_match', 'drug_match', 'phenotype_match', 'variant_match']].any(axis=1)).mean() * 100,
    'significance_match_rate': df_aligned_pmid['significance_match'].mean() * 100,
    'metabolizer_match_rate': df_aligned_pmid['metabolizer_match'].mean() * 100,
    'population_match_rate': df_aligned_pmid['population_match'].mean() * 100,
}

# Display match statistics
print("Match Statistics:")
for key, value in match_stats.items():
    print(f"{key}: {value:.2f}%")


# Assuming 'flattened_df' is your DataFrame and 'PMID' is the column name
flattened_df = flattened_df.dropna(subset=['PMID'])


# Update column names in comparisons based on the actual merged dataframe
gene_matches = []
variant_matches = []
drug_matches = []
# Grouping annotations per PMID and creating sets for genes, variants, and drugs

# Function to normalize and split values, handling missing data
def normalize_split(value):
    if pd.isna(value):
        return set()
    return set(map(str.strip, str(value).lower().replace(';', ',').split(',')))

# Group by PMID and create sets for each component
grouped_outputs = flattened_df.groupby('PMID').agg({
    'gene': lambda x: set().union(*x.apply(normalize_split)),
    'variant/haplotypes': lambda x: set().union(*x.apply(normalize_split)),
    'drug(s)': lambda x: set().union(*x.apply(normalize_split))
}).reset_index()

grouped_drug = df_new.groupby('PMID').agg({
    'Gene': lambda x: set().union(*x.apply(normalize_split)),
    'Variant/Haplotypes': lambda x: set().union(*x.apply(normalize_split)),
    'Drug(s)': lambda x: set().union(*x.apply(normalize_split))
}).reset_index()

# Merge the grouped dataframes on PMID
merged_grouped_df = pd.merge(grouped_outputs, grouped_drug, on='PMID', suffixes=('_output', '_drug'), how='inner')


# Compare sets for each PMID
for _, row in merged_grouped_df.iterrows():
    gene_matches.append(len(row['gene'].intersection(row['Gene'])) / len(row['Gene']) if len(row['Gene']) > 0 else 0)
    variant_matches.append(len(row['variant/haplotypes'].intersection(row['Variant/Haplotypes'])) / len(row['Variant/Haplotypes']) if len(row['Variant/Haplotypes']) > 0 else 0)
    drug_matches.append(len(row['drug(s)'].intersection(row['Drug(s)'])) / len(row['Drug(s)']) if len(row['Drug(s)']) > 0 else 0)

# Calculate the average match rates
average_gene_match_rate = sum(gene_matches) / len(gene_matches)
average_variant_match_rate = sum(variant_matches) / len(variant_matches)
average_drug_match_rate = sum(drug_matches) / len(drug_matches)

# Display average match rates
(average_gene_match_rate, average_variant_match_rate, average_drug_match_rate)

average_gene_match_rate, average_variant_match_rate, average_drug_match_rate

import matplotlib.pyplot as plt
# 1. Bar plot to visualize match rates for Gene, Drug, and Phenotype
match_fields = ['Gene', 'Drug', 'Phenotype','Signficance',"Variant"]

match_rates = [match_stats['gene_match_rate'], match_stats['drug_match_rate'], match_stats['phenotype_match_rate'],match_stats['significance_match_rate'],match_stats['variant_match_rate']]

plt.figure(figsize=(8, 6))
plt.bar(match_fields, match_rates, color = ['#004B8D', '#175E54', '#8C1515', '#F58025','#5D4B3C']
)
plt.title('Exact Match Rates by Category', fontweight='bold', fontsize=14)

plt.ylabel('Match Rate (%)',fontweight="bold")
plt.xlabel('Category',fontweight='bold')
plt.ylim(0, 100)  # Ensure the y-axis goes from 0 to 100
plt.tight_layout()
plt.show()


# Data for Partial Match (outer pie chart)
sizes_partial = [match_stats['partial_match_rate'], 100 - match_stats['partial_match_rate']]
colors_partial = ['#175E54', 'none']  # Stanford Green for relevant portion

# Data for Exact Match (inner pie chart)
sizes_exact = [match_stats['exact_match_rate'], 100 - match_stats['exact_match_rate']]
colors_exact = ['#8C1515', 'none']  # Cardinal Red for relevant portion

# Create the figure
plt.figure(figsize=(8, 8))

# Plot the larger pie chart (Partial Match)
plt.pie(
    sizes_partial,
    colors=colors_partial,
    startangle=90,
    radius=1.0,
    wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
    labels=None  # No direct labels, handled in legend
)

# Plot the smaller pie chart (Exact Match) on top
plt.pie(
    sizes_exact,
    colors=colors_exact,
    startangle=90,
    radius=0.7,
    wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
    labels=None  # No direct labels, handled in legend
)

# Add legend with appropriate colors
legend_labels = [
    f"Partial Match ({round(match_stats['partial_match_rate'],2)}%)",
    f"Exact Match ({round(match_stats['exact_match_rate'],3)}%)"
]
legend_colors = ['#175E54', '#8C1515']  # Match the colors used in the chart

plt.legend(
    handles=[
        plt.Line2D([0], [0], color=legend_colors[0], lw=6),  # Partial Match color
        plt.Line2D([0], [0], color=legend_colors[1], lw=6)   # Exact Match color
    ],
    labels=legend_labels,
    loc='upper right',
    fontsize=10,
    frameon=True,
    title="Match Types",
    title_fontsize=12
)

# Add a title
plt.title('Exact vs Partial Match Rates', fontweight = "bold",fontsize=14, pad=20)

# Adjust layout for better spacing
plt.tight_layout()
plt.show()

import matplotlib.pyplot as plt

# Match rates grouped by PMID (these variables should be defined in your data)
# Example: average_gene_match_rate, average_variant_match_rate, average_drug_match_rate
categories = ['Gene',  'Drug','Variant']
match_rates = [average_gene_match_rate*100,  average_drug_match_rate*100,average_variant_match_rate*100,]

# Stanford-inspired colors for bars
colors = ['#8C1515', '#175E54', '#F58025']  # Cardinal Red, Stanford Green, Stanford Orange

# Create the bar chart
plt.figure(figsize=(10, 6))
bars = plt.bar(categories, match_rates, color=colors, edgecolor='black', linewidth=1.2)

# Add values on top of bars
for bar, rate in zip(bars, match_rates):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1,  # Adjust height for the text
        f'{rate:.1f}%',  # Rounded percentage
        ha='center',
        fontweight="bold",
        fontsize=10,
        color='black'
    )

# Title and labels
plt.title('Match Rates by Category (Grouped by PMID)',fontweight="bold", fontsize=14, pad=20)
plt.ylabel('Match Rate (%)',fontweight="bold",fontsize=12)
plt.xlabel('Categories',fontweight="bold", fontsize=12)

# Adjust ticks for readability
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)

# Set y-axis limits
plt.ylim(0, 100)  # Assuming match rates are percentages

# Add grid for better readability


# Show the plot
plt.tight_layout()
plt.show()

# Load the dataset (replace the path with the correct file location in Colab)
wholecsv = pd.read_csv('/content/wholecsv.csv')

# Summarizing match statistics based on the pre-marked columns
match_columns = [
    'Match metabolizer',
    'Match significance',
    'Match all drug',
    'Match Any Drug',
    'Match gene',
    'Match phenotype',
    'Match population'
]

# Calculating the percentage of matches for each attribute
match_stats_new = wholecsv[match_columns].mean() * 100

# Adjusting the color scheme to be more neutral and less bright
plt.figure(figsize=(10, 6))
plt.bar(match_stats_new.index, match_stats_new.values, color=['#2E8B57', '#4682B4', '#6A5ACD', '#D2691E', '#556B2F', '#8B4513', '#2F4F4F'])
plt.title('Match Statistics for Different Attributes', fontsize=16)
plt.ylabel('Match Percentage (%)', fontsize=12)
plt.xlabel('Attributes', fontsize=12)
plt.xticks(rotation=45)
plt.ylim(0, 100)
plt.tight_layout()
plt.show()


# Creating the table summarizing match statistics for the poster
table_data = match_stats_new.reset_index()
table_data.columns = ['Attribute', 'Match Percentage']

# If you want to print the table to the console (optional):
print(table_data)