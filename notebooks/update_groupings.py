"""
## Goals
1. Create new_all_pmids.txt
2. Create new_annotations_by_pmcid.json

Use the existing all_pmids.txt and annotations_by_pmcid.json in data/variantAnnotations for reference
Roughly, we should use the data in study_parameters.tsv, var_drug_ann.tsv, var_pheno_ann.tsv, and var_fa_ann.tsv to construct these (all under data/variantAnnotations/) 
The reference files were created using old copies of these files.
"""

import pandas as pd
import json
import requests
from collections import defaultdict
import time
import os
from dotenv import load_dotenv


def get_article_title_from_pmid(pmid, email):
    """Get article title from PMID using NCBI E-utilities API"""
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&rettype=xml&email={email}"
        response = requests.get(url)
        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Look for article title
            title_elem = root.find(".//ArticleTitle")
            if title_elem is not None:
                return title_elem.text
        return None
    except Exception as e:
        print(f"Error fetching title for PMID {pmid}: {e}")
        return None

# Provided list
provided_pmcids = [
    "PMC11430164",
    "PMC10786722",
    "PMC10993165",
    "PMC12331468",
    "PMC12319246",
    "PMC12260932",
    "PMC10275785",
    "PMC12320098",
    "PMC5508045",
    "PMC4706412",
    "PMC11603346",
    "PMC2859392",
    "PMC10399933",
    "PMC12038368",
    "PMC4916189",
    "PMC6714829",
    "PMC10946077",
    "PMC11062152",
    "PMC6465603",
    "PMC8973308",
    "PMC12035587",
    "PMC5561238",
    "PMC3839910",
    "PMC384715",
    "PMC3113609",
    "PMC554812",
    "PMC3387531",   
    "PMC8790808",
    "PMC3548984",
    "PMC3584248",
    "PMC6435416",
    "PMC11971672",
    "PMC12036300",
    "PMC10880264",
]

provided_pmids = [
    39346054,
    38216550,
    38568509,
    40786508,
    40761554,
    40672687,
    37332933,
    40762011,
    28550460,
    26745506,
    39604537,
    20338069,
    37490620,
    40297930,
    26715213,
    30336686,
    38497131,
    38707740,
    31024313,
    35431360,
    40099566,
    28819312,
    23588310,
    15024131,
    21428769,
    15743917,
    21505298,
    33768542,
    23213055,
    23476897,
    30661084,
    40184070,
    40295977,
    38377518
]

def load_pmcid_cache(cache_file):
    """Load existing PMCID cache"""
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return {}

def save_pmcid_cache(cache_file, cache):
    """Save PMCID cache"""
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)


def main():
    # Load environment variables
    load_dotenv()
    ncbi_email = os.getenv('NCBI_EMAIL')
    if not ncbi_email:
        raise ValueError("NCBI_EMAIL not found in .env file")
    
    # Base directory
    data_dir = "/Users/shloknatarajan/stanford/research/daneshjou/AutoGKB/data/variantAnnotations"
    cache_file = f"{data_dir}/pmcid_cache.json"
    
    print("Loading TSV files...")
    
    # Load all TSV files
    study_params = pd.read_csv(f"{data_dir}/study_parameters.tsv", sep='\t', low_memory=False)
    var_drug_ann = pd.read_csv(f"{data_dir}/var_drug_ann.tsv", sep='\t', low_memory=False)
    var_pheno_ann = pd.read_csv(f"{data_dir}/var_pheno_ann.tsv", sep='\t', low_memory=False)
    var_fa_ann = pd.read_csv(f"{data_dir}/var_fa_ann.tsv", sep='\t', low_memory=False)
    
    # Combine all variant annotation dataframes
    all_var_ann = pd.concat([var_drug_ann, var_pheno_ann, var_fa_ann], ignore_index=True)
    
    # Create mapping from provided aligned lists
    print("Creating PMCID to PMID mapping from provided aligned lists...")
    pmcid_to_pmid_map = {}
    target_pmids = set()
    
    for pmcid, pmid in zip(provided_pmcids, provided_pmids):
        pmcid_to_pmid_map[pmcid] = pmid
        target_pmids.add(pmid)
    
    print(f"Created mapping for {len(pmcid_to_pmid_map)} PMCID/PMID pairs")
    
    # Extract all unique PMIDs from variant annotations
    all_pmids_from_data = set(all_var_ann['PMID'].dropna().astype(int))
    
    # Filter to only include PMIDs that correspond to provided PMCIDs
    all_pmids = target_pmids.intersection(all_pmids_from_data)
    
    print(f"Found {len(all_pmids_from_data)} unique PMIDs in data")
    print(f"Found {len(target_pmids)} PMIDs from provided PMCIDs")
    print(f"Using {len(all_pmids)} PMIDs that match both")
    
    # Create the annotations structure organized by PMCID
    pmcid_to_data = {}
    
    # Initialize data for each provided PMCID
    for pmcid in provided_pmcids:
        pmcid_to_data[pmcid] = {
            'pmid': pmcid_to_pmid_map.get(pmcid),
            'pmcid': pmcid,
            'title': None,
            'study_parameters': {},
            'variant_annotations': []
        }
    
    print("Processing variant annotations...")
    
    # Group variant annotations by PMID (only for target PMIDs)
    for _, row in all_var_ann.iterrows():
        pmid = int(row['PMID']) if pd.notna(row['PMID']) else None
        if pmid and pmid in all_pmids:  # Only process PMIDs in our target set
            # Find the corresponding PMCID
            corresponding_pmcid = None
            for pmcid in provided_pmcids:
                if pmcid_to_pmid_map.get(pmcid) == pmid:
                    corresponding_pmcid = pmcid
                    break
            
            if corresponding_pmcid:
                # Create variant annotation entry
                var_ann_entry = {}
                for col in row.index:
                    if pd.notna(row[col]):
                        var_ann_entry[col] = row[col]
                
                pmcid_to_data[corresponding_pmcid]['variant_annotations'].append(var_ann_entry)
    
    print("Processing study parameters...")
    
    # Add study parameters using Variant Annotation ID as the link
    study_params_dict = {}
    for _, row in study_params.iterrows():
        var_ann_id = row['Variant Annotation ID'] if pd.notna(row['Variant Annotation ID']) else None
        if var_ann_id:
            study_params_entry = {}
            for col in row.index:
                if pd.notna(row[col]):
                    study_params_entry[col] = row[col]
            study_params_dict[var_ann_id] = study_params_entry
    
    # Link study parameters to PMCIDs through variant annotation IDs
    for pmcid, data in pmcid_to_data.items():
        for var_ann in data['variant_annotations']:
            var_ann_id = var_ann.get('Variant Annotation ID')
            if var_ann_id in study_params_dict:
                data['study_parameters'] = study_params_dict[var_ann_id]
                break  # Use the first matching study parameter
    
    print("Loading PMCID cache...")
    pmcid_cache = load_pmcid_cache(cache_file)
    print(f"Loaded {len(pmcid_cache)} cached PMCIDs")
    
    print("Fetching titles from NCBI for PMCIDs...")
    
    # Fetch titles for each PMCID (with rate limiting)
    processed_count = 0
    cache_updated = False
    
    for pmcid in provided_pmcids:
        if processed_count % 10 == 0:
            print(f"Processed {processed_count}/{len(provided_pmcids)} PMCIDs")
            # Save cache periodically
            if cache_updated:
                save_pmcid_cache(cache_file, pmcid_cache)
                cache_updated = False
        
        pmid = pmcid_to_data[pmcid]['pmid']
        if pmid:
            pmid_str = str(pmid)
            
            # Check cache first
            if pmid_str in pmcid_cache:
                pmcid_to_data[pmcid]['title'] = pmcid_cache[pmid_str].get('title')
            else:
                # Get title from NCBI using PMID
                title = get_article_title_from_pmid(pmid, ncbi_email)
                pmcid_to_data[pmcid]['title'] = title
                
                # Cache the results
                pmcid_cache[pmid_str] = {
                    'pmcid': pmcid,
                    'title': title
                }
                cache_updated = True
                
                # Rate limiting to be respectful to NCBI (with email, can be faster)
                time.sleep(0.34)  # ~3 requests per second (NCBI allows up to 10/sec with email)
        
        processed_count += 1
    
    # Save final cache
    save_pmcid_cache(cache_file, pmcid_cache)
    print(f"Saved PMCID cache with {len(pmcid_cache)} entries")
    
    print("Creating final annotations structure...")
    
    # Convert to dictionary format indexed by PMCID
    annotations_by_pmcid = {}
    entries_with_data = 0
    entries_without_data = 0
    
    for pmcid in provided_pmcids:
        data = pmcid_to_data[pmcid]
        annotations_by_pmcid[pmcid] = data  # Use PMCID as key
        if data['variant_annotations']:
            entries_with_data += 1
        else:
            entries_without_data += 1
    
    print(f"Entries with variant annotations: {entries_with_data}")
    print(f"Entries without variant annotations (included): {entries_without_data}")
    
    # Save new_annotations_by_pmcid.json
    with open(f"{data_dir}/new_annotations_by_pmcid.json", 'w') as f:
        json.dump(annotations_by_pmcid, f, indent=2)
    
    print(f"Created new_annotations_by_pmcid.json with {len(annotations_by_pmcid)} entries")
    print("Done!")

if __name__ == "__main__":
    main()
