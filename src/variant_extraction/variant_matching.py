# variant_matching.py
import pandas as pd
import re

class SimplifiedVariantMatcher:
    @staticmethod
    def split_variants(variant_string):
        """Split variant strings into individual components."""
        if pd.isna(variant_string):
            return set()
        return set(map(str.strip, variant_string.replace('/', ',').split(',')))

    @staticmethod
    def preprocess_variants(variant_string, gene=None):
        """Preprocess variant strings."""
        variants = SimplifiedVariantMatcher.split_variants(variant_string)
        processed_variants = set()
        for variant in variants:
            variant = variant.strip()
            if 'rs' in variant:
                rs_match = re.findall(r'rs\d+', variant)
                processed_variants.update(rs_match)
            elif '*' in variant and '-' in variant and gene:
                star_allele, mutation = variant.split('-', 1)
                processed_variants.add(f"{gene}{star_allele.strip()}")
                processed_variants.add(mutation.strip())
            elif '*' in variant and gene:
                processed_variants.add(f"{gene}{variant.strip()}")
            elif '>' in variant:
                processed_variants.add(variant.strip())
            else:
                processed_variants.add(variant.strip())
        return processed_variants

    def match_row(self, row):
        """Match ground truth and predicted variants for a single row."""
        truth_variants = self.preprocess_variants(row['Variant/Haplotypes_truth'], gene=row['Gene_truth'])
        predicted_variants = self.preprocess_variants(row['variant/haplotypes_output'], gene=row['Gene_output'])
        if predicted_variants == truth_variants:
            return 'Exact Match'
        if predicted_variants.intersection(truth_variants):
            return 'Partial Match'
        return 'No Match'

def align_and_compare_datasets(df_new, flattened_df):
    """Align and compare datasets based on PMID."""
    df_new = df_new.rename(columns={
        'Gene': 'Gene_truth',
        'Drug(s)': 'Drug(s)_truth',
        'Phenotype Category': 'Phenotype Category_truth',
        'Variant/Haplotypes': 'Variant/Haplotypes_truth'
    })
    flattened_df = flattened_df.rename(columns={
        'gene': 'Gene_output',
        'drug(s)': 'Drug(s)_output',
        'phenotype category': 'Phenotype Category_output',
        'variant/haplotypes': 'variant/haplotypes_output'
    })
    df_aligned = pd.merge(df_new, flattened_df, how='inner', on='PMID')
    matcher = SimplifiedVariantMatcher()
    df_aligned['variant_match'] = df_aligned.apply(lambda row: matcher.match_row(row), axis=1)
    df_aligned['gene_match'] = df_aligned['Gene_truth'] == df_aligned['Gene_output']
    df_aligned['drug_match'] = df_aligned['Drug(s)_truth'] == df_aligned['Drug(s)_output']
    df_aligned['phenotype_match'] = df_aligned['Phenotype Category_truth'] == df_aligned['Phenotype Category_output']
    df_aligned['significance_match'] = df_aligned['Significance'] == df_aligned['significance'].map({
        'significant': 'yes', 'not significant': 'no', 'not stated': 'not stated'
    })
    df_aligned['metabolizer_match'] = df_aligned['Metabolizer types'] == df_aligned['metabolizer types']
    df_aligned['population_match'] = df_aligned['Specialty Population'] == df_aligned['specialty population']
    return df_aligned