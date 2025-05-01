import requests
import zipfile
import io
import pandas as pd
from Bio import Entrez
import time
import random
from tqdm import tqdm
import os
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import seaborn as sns

class PharmGKBProcessor:
    def __init__(self, output_dir: str = "pharmgkb_data"):
        """
        Initialize the PharmGKB processor.
        
        Args:
            output_dir (str): Directory to save downloaded data
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def download_pharmgkb_data(self):
        """
        Download and extract PharmGKB data files.
        """
        urls = {
            "clinicalVariants": "https://api.pharmgkb.org/v1/download/file/data/clinicalVariants.zip",
            "variantAnnotations": "https://api.pharmgkb.org/v1/download/file/data/variantAnnotations.zip"
        }
        
        for name, url in urls.items():
            try:
                print(f"Downloading {name}...")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall(os.path.join(self.output_dir, name))
                    print(f"Successfully downloaded and unpacked {name}")
                
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {name}: {e}")
            except zipfile.BadZipFile as e:
                print(f"Error unpacking {name}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred with {name}: {e}")
    
    def load_variant_annotations(self) -> pd.DataFrame:
        """
        Load the variant annotations data.
        
        Returns:
            pd.DataFrame: Variant annotations dataframe
        """
        var_drug_ann_path = os.path.join(self.output_dir, "variantAnnotations", "var_drug_ann.tsv")
        return pd.read_csv(var_drug_ann_path, sep='\t')
    
    def plot_variant_distributions(self, df: pd.DataFrame):
        """
        Create various plots to visualize the variant annotation data.
        
        Args:
            df (pd.DataFrame): Variant annotations dataframe
        """
        # Create plots directory
        plots_dir = os.path.join(self.output_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        
        # Set style
        plt.style.use('seaborn')
        
        # 1. Distribution of Phenotype Categories
        plt.figure(figsize=(12, 6))
        phenotype_counts = df['Phenotype Category'].value_counts()
        sns.barplot(x=phenotype_counts.values, y=phenotype_counts.index)
        plt.title('Distribution of Phenotype Categories')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'phenotype_categories.png'))
        plt.close()
        
        # 2. Distribution of Significance
        plt.figure(figsize=(10, 6))
        significance_counts = df['Significance'].value_counts()
        sns.barplot(x=significance_counts.values, y=significance_counts.index)
        plt.title('Distribution of Significance Levels')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'significance_levels.png'))
        plt.close()
        
        # 3. Distribution of Metabolizer Types
        plt.figure(figsize=(12, 6))
        metabolizer_counts = df['Metabolizer types'].value_counts()
        sns.barplot(x=metabolizer_counts.values, y=metabolizer_counts.index)
        plt.title('Distribution of Metabolizer Types')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'metabolizer_types.png'))
        plt.close()
        
        # 4. Top 20 Drugs
        plt.figure(figsize=(12, 6))
        drug_counts = df['Drug(s)'].value_counts().head(20)
        sns.barplot(x=drug_counts.values, y=drug_counts.index)
        plt.title('Top 20 Drugs with Variant Annotations')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'top_20_drugs.png'))
        plt.close()
        
        # 5. Distribution of Evidence Levels
        plt.figure(figsize=(10, 6))
        evidence_counts = df['Evidence Level'].value_counts()
        sns.barplot(x=evidence_counts.values, y=evidence_counts.index)
        plt.title('Distribution of Evidence Levels')
        plt.xlabel('Count')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'evidence_levels.png'))
        plt.close()
        
        print(f"Plots saved to {plots_dir}")

class PubMedDownloader:
    def __init__(self, email: str):
        """
        Initialize the PubMed downloader.
        
        Args:
            email (str): Email address for NCBI API
        """
        Entrez.email = email
        
    def get_pmcid_from_pmid(self, pmid: str) -> Optional[str]:
        """
        Get PMCID from PMID.
        
        Args:
            pmid (str): PubMed ID
            
        Returns:
            Optional[str]: PMCID if found, None otherwise
        """
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
            print(f"An error occurred for pmid {pmid}: {e}")
            return None
    
    def fetch_article_content(self, pmcid: str) -> Optional[str]:
        """
        Fetch article content using PMCID.
        
        Args:
            pmcid (str): PubMed Central ID
            
        Returns:
            Optional[str]: Article content if successful, None otherwise
        """
        try:
            handle = Entrez.efetch(db="pmc", id=pmcid, retmode="xml")
            content = handle.read()
            handle.close()
            return content
        except Exception as e:
            print(f"Error fetching content for PMCID {pmcid}: {e}")
            return None

def main():
    # Initialize processors
    pharmgkb = PharmGKBProcessor()
    pubmed = PubMedDownloader(email="your.email@example.com")  # Replace with your email
    
    # Download PharmGKB data
    pharmgkb.download_pharmgkb_data()
    
    # Load variant annotations
    df = pharmgkb.load_variant_annotations()
    
    # Create visualizations
    pharmgkb.plot_variant_distributions(df)
    
    # Example: Process PMIDs from the dataframe
    pmids = df['PMID'].dropna().unique().tolist()[:10]  # Process first 10 PMIDs as example
    
    for pmid in tqdm(pmids, desc="Processing PMIDs"):
        pmcid = pubmed.get_pmcid_from_pmid(pmid)
        if pmcid:
            content = pubmed.fetch_article_content(pmcid)
            if content:
                # Save content to file
                with open(os.path.join(pharmgkb.output_dir, f"{pmid}.xml"), "w") as f:
                    f.write(content)
        
        # Add delay to avoid rate limiting
        time.sleep(random.uniform(0.1, 0.3))

if __name__ == "__main__":
    main() 