# SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md)
#
# SPDX-License-Identifier: Apache-2.0

"""
AutoGKB Full End-to-End DSPy Pipeline

Steps:
1. Load ground truth TSV and group entries by conceptual PGx associations per PMID.
2. Scrape or load full-text articles per PMID.
3. Extract mentions of variants and drugs using modular DSPy signatures.
4. Predict candidate variant-drug pairs using DSPy reasoning.
5. For each candidate pair, assemble a structured PGx association using DSPy.
6. Evaluate predictions against TSV gold data using field-level logic-aware matching.
"""

import os
import dspy
import pandas as pd
import requests
import browser_cookie3
import time
import random
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from dspy import Signature, InputField, OutputField, Module, Predict, ChainOfThought

# DSPy configuration
lm = dspy.LM("ollama_chat/llama3.3", api_base="http://localhost:11434", api_key="")
dspy.configure(lm=lm)

# --- DSPy Signatures ---
class ExtractVariants(Signature):
    """Extract all variant mentions from the text."""
    text: str = InputField()
    variants: str = OutputField(desc='Genetic variants including haplotypes and snps')

class ExtractDrugs(Signature):
    """Extract all drug mentions from the text."""
    text: str = InputField()
    drugs: str = OutputField()

class CandidatePairingSignature(Signature):
    """Select relevant variant-drug pairs to investigate."""
    text: str = InputField()
    variants: str = InputField()
    drugs: str = InputField()
    pairs: str = OutputField(desc="Variant-drug pairs (one per line): e.g. 'CYP2C9*11 - Warfarin'")

class AssociationBuildSignature(Signature):
    """
    Build a structured pharmacogenomic (PGx) association entry.
    """
    text: str = InputField(
        desc="Full article text to analyze for PGx associations."
    )
    variant: str = InputField(
        desc="Genetic variant mention from the text "
             "(e.g., “CYP2C9*3”, “rs1799853”, or “A123T”)."
    )
    drug: str = InputField(
        desc="Drug mention from the text "
             "(e.g., “warfarin”, “ketoconazole”, “clopidogrel”)."
    )
    gene: str = OutputField(
        desc="Gene name corresponding to the variant "
             "(e.g., “CYP2C9”, “CYP2D6”)."
    )
    alleles: str = OutputField(
        desc="Specific alleles involved in the association "
             "(e.g., “*1/*3”, “rs1799853/rs1057910”)."
    )
    association: str = OutputField(
        desc="Binary association result: “associated” or “not associated”."
    )
    direction: str = OutputField(
        desc="Direction or type of effect "
             "(e.g., “increased exposure”, “decreased clearance”, “inhibition”)."
    )
    term: str = OutputField(
        desc="Pharmacodynamic or pharmacokinetic term describing the interaction "
             "(e.g., “pharmacokinetic interaction”, “QT prolongation”)."
    )
    population: str = OutputField(
        desc="Population context for the association "
             "(e.g., “Caucasian adults”, “elderly patients”, “healthy volunteers”)."
    )

# --- DSPy Modules ---
class VariantMentionExtractor(Module):
    def __init__(self):
        super().__init__()
        self.model = ChainOfThought(ExtractVariants)
    def forward(self, text):
        return self.model(text=text)

class DrugMentionExtractor(Module):
    def __init__(self):
        super().__init__()
        self.model = ChainOfThought(ExtractDrugs)
    def forward(self, text):
        return self.model(text=text)

class CandidatePairSelector(Module):
    def __init__(self):
        super().__init__()
        self.model = ChainOfThought(CandidatePairingSignature)
    def forward(self, text, variants, drugs):
        return self.model(text=text, variants=variants, drugs=drugs)

class AssociationBuilder(Module):
    def __init__(self):
        super().__init__()
        self.model = ChainOfThought(AssociationBuildSignature)
    def forward(self, text, variant, drug):
        return self.model(text=text, variant=variant, drug=drug)

# --- Utilities ---
class PMCTextScraper:
    def __init__(self, output_dir="pmc_fulltexts"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.session.cookies.update(browser_cookie3.chrome())
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_and_save(self, pmid_list):
        for pmid in pmid_list:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/"
            try:
                r = self.session.get(url)
                r.raise_for_status()
                text = BeautifulSoup(r.text, "html.parser").get_text(separator="\n")
                with open(os.path.join(self.output_dir, f"{pmid}.txt"), "w") as f:
                    f.write(text)
                print(f"[PMC] Saved {pmid}")
            except Exception as e:
                print(f"[PMC] Failed {pmid}: {e}")

def load_full_texts(text_dir):
    pmid_to_text = {}
    for fname in os.listdir(text_dir):
        if fname.endswith(".txt"):
            pmid = fname.replace(".txt", "")
            with open(os.path.join(text_dir, fname), "r") as f:
                pmid_to_text[pmid] = f.read()
    return pmid_to_text

class GroundTruthManager:
    def __init__(self, df):
        self.grouped = {}
        for _, row in df.iterrows():
            pmid = str(row["PMID"]).strip()
            entry = {
                "gene": str(row["Gene"]).strip(),
                "alleles": str(row["Alleles"]).strip(),
                "drug": str(row["Drug(s)"]).strip(),
                "association": str(row["Is/Is Not associated"]).strip(),
                "direction": str(row["Direction of effect"]).strip(),
                "term": str(row["PD/PK terms"]).strip(),
                "population": str(row["Population"]).strip() if "Population" in row else None
            }
            self.grouped.setdefault(pmid, []).append(entry)

    def get(self, pmid):
        return self.grouped.get(pmid, [])

def pmid_to_pmcid_batch(pmids, email="aron7628@gmail.com"):
    """Convert a list of PMIDs to a dictionary of PMID → PMCID using Entrez eLink."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    out_map = {}
    for pmid in pmids:
        try:
            jitter = random.uniform(0.4, 1.0)
            time.sleep(jitter)
            params = {
                "dbfrom": "pubmed",
                "linkname": "pubmed_pmc",
                "id": pmid,
                "email": email,
                "tool": "AutoGKB"
            }
            r = requests.get(base_url, params=params, timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            for link in root.findall(".//LinkSetDb/Link/Id"):
                pmcid = link.text.strip()
                if pmcid:
                    out_map[pmid] = pmcid
                    break
        except Exception as e:
            print(f"[eLink] Failed to fetch PMCID for PMID {pmid}: {e}")
    return out_map

# --- Pipeline ---
def run_pipeline(pmid, full_text, gt_entries):
    print(f"[INFO] Processing PMID {pmid}")

    variants = VariantMentionExtractor().forward(text=full_text).variants
    drugs = DrugMentionExtractor().forward(text=full_text).drugs
    pairs = CandidatePairSelector().forward(text=full_text, variants=variants, drugs=drugs).pairs

    variant_drug_pairs = [
        line.strip().split(" - ") for line in pairs.splitlines() if " - " in line
    ]

    results = []
    builder = AssociationBuilder()
    for variant, drug in variant_drug_pairs:
        
        out = builder.forward(text=full_text, variant=variant, drug=drug)
        print(out)
        result = {
            "pmid": pmid,
            "variant": variant,
            "drug": drug,
            "gene": out.gene,
            "alleles": out.alleles,
            "association": out.association,
            "direction": out.direction,
            "term": out.term,
            "population": out.population
        }
        results.append(result)

    return results

# --- Main ---
if __name__ == "__main__":
    tsv_path = "src/data/var_drug_ann.tsv"
    text_dir = "pmc_fulltexts"
    df = pd.read_csv(tsv_path, sep="\t")
    gt_manager = GroundTruthManager(df)

    pmids = sorted(list(set(df["PMID"].astype(str).str.strip())))[:10]
    pmid_to_pmcid = pmid_to_pmcid_batch(pmids)
    pmcids = list(pmid_to_pmcid.values())

    scraper = PMCTextScraper(output_dir=text_dir)
    scraper.fetch_and_save(pmcids)

    full_texts = load_full_texts(text_dir)
    all_results = []

    for pmid in pmids:
        if pmid not in pmid_to_pmcid:
            print(f"[WARN] No PMCID for PMID {pmid}, skipping.")
            continue
        pmcid = pmid_to_pmcid[pmid]
        gt_entries = gt_manager.get(pmid)
        full_text = full_texts.get(pmcid)
        if not full_text:
            print(f"[WARN] No full text for PMCID {pmcid}, skipping.")
            continue
        predictions = run_pipeline(pmid, full_text, gt_entries)
        all_results.extend(predictions)

    print("[DONE] Results:")
    for r in all_results:
        print(r)