# ncbi_fetch.py
from Bio import Entrez
import time
import random
from bs4 import BeautifulSoup
from config import ENTREZ_EMAIL

def setup_entrez():
    """Configure Entrez with email."""
    Entrez.email = ENTREZ_EMAIL

def get_pmcid_from_pmid(pmid, retries=3):
    """Get PMCID from PMID with retry mechanism."""
    for attempt in range(retries):
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc")
            record = Entrez.read(handle)
            handle.close()
            if record and 'LinkSetDb' in record[0] and record[0]['LinkSetDb']:
                return record[0]['LinkSetDb'][0]['Link'][0]['Id']
            print(f"No PMCID found for PMID {pmid}.")
            return None
        except Exception as e:
            print(f"Error for PMID {pmid} on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                return None

def fetch_pmc_content(pmcid):
    """Fetch PMC content using PMCID."""
    try:
        handle = Entrez.efetch(db="pmc", id=pmcid, rettype="full", retmode="xml")
        record = handle.read()
        handle.close()
        return record
    except Exception as e:
        print(f"Error fetching content for PMCID {pmcid}: {e}")
        return None

def process_row(row, processed_pmids, processed_data):
    """Process a single DataFrame row to fetch PMCID and content."""
    time.sleep(0.4 + random.uniform(0, 0.5))
    pmid = str(row['PMID'])

    if pmid in processed_pmids:
        return pd.Series(processed_data[pmid])

    pmcid = get_pmcid_from_pmid(pmid)
    result = {'PMCID': None, 'Title': None, 'Content': None, 'Content_text': None}

    if pmcid:
        xml_content = fetch_pmc_content(pmcid)
        if xml_content:
            soup = BeautifulSoup(xml_content, 'xml')
            title_tag = soup.find('article-title')
            title = title_tag.get_text() if title_tag else "No Title Found"
            clean_text = soup.get_text()
            result = {'PMCID': pmcid, 'Title': title, 'Content': xml_content, 'Content_text': clean_text}

    processed_pmids.add(pmid)
    processed_data[pmid] = result
    return pd.Series(result)