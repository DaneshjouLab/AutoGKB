# main.py
import pandas as pd
from openai import OpenAI
import os
import sys

from src.variant_extraction.config import (
    VAR_DRUG_ANN_PATH, CHECKPOINT_PATH, OUTPUT_CSV_PATH, 
    DF_NEW_CSV_PATH, WHOLE_CSV_PATH, SCHEMA_TEXT
)

from src.variant_extraction.processing import load_and_prepare_data, create_schema, process_responses
from src.variant_extraction.variant_matching import align_and_compare_datasets
from src.variant_extraction.visualization import plot_match_rates, plot_pie_charts, plot_grouped_match_rates, plot_attribute_match_rates

def main():
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Load and prepare data
    df_var_drug_ann, enum_values = load_and_prepare_data(VAR_DRUG_ANN_PATH)

    # Create schema
    schema = create_schema(enum_values)

    # Process API responses
    flattened_results = process_responses(df_var_drug_ann, client, SCHEMA_TEXT, schema, CHECKPOINT_PATH)
    flattened_df = pd.DataFrame(flattened_results)

    # Align and compare datasets
    df_aligned = align_and_compare_datasets(df_var_drug_ann, flattened_df)

    # Calculate match statistics
    match_stats = {
        'gene_match_rate': df_aligned['gene_match'].mean() * 100,
        'drug_match_rate': df_aligned['drug_match'].mean() * 100,
        'phenotype_match_rate': df_aligned['phenotype_match'].mean() * 100,
        'variant_match_rate': (df_aligned['variant_match'] == 'Exact Match').mean() * 100,
        'partial_variant_match_rate': (df_aligned['variant_match'] == 'Partial Match').mean() * 100,
        'exact_match_rate': df_aligned[['gene_match', 'drug_match', 'phenotype_match']].all(axis=1).mean() * 100,
        'partial_match_rate': df_aligned[['gene_match', 'drug_match', 'phenotype_match']].any(axis=1).mean() * 100,
        'mismatch_rate': (~df_aligned[['gene_match', 'drug_match', 'phenotype_match', 'variant_match']].any(axis=1)).mean() * 100,
        'significance_match_rate': df_aligned['significance_match'].mean() * 100,
        'metabolizer_match_rate': df_aligned['metabolizer_match'].mean() * 100,
        'population_match_rate': df_aligned['population_match'].mean() * 100,
    }

    # Grouped match rates
    def normalize_split(value):
        if pd.isna(value):
            return set()
        return set(map(str.strip, str(value).lower().replace(';', ',').split(',')))

    grouped_outputs = flattened_df.groupby('PMID').agg({
        'gene': lambda x: set().union(*x.apply(normalize_split)),
        'variant/haplotypes': lambda x: set().union(*x.apply(normalize_split)),
        'drug(s)': lambda x: set().union(*x.apply(normalize_split))
    }).reset_index()

    grouped_drug = df_var_drug_ann.groupby('PMID').agg({
        'Gene': lambda x: set().union(*x.apply(normalize_split)),
        'Variant/Haplotypes': lambda x: set().union(*x.apply(normalize_split)),
        'Drug(s)': lambda x: set().union(*x.apply(normalize_split))
    }).reset_index()

    merged_grouped_df = pd.merge(grouped_outputs, grouped_drug, on='PMID', suffixes=('_output', '_drug'), how='inner')
    gene_matches = []
    variant_matches = []
    drug_matches = []
    for _, row in merged_grouped_df.iterrows():
        gene_matches.append(len(row['gene'].intersection(row['Gene'])) / len(row['Gene']) if len(row['Gene']) > 0 else 0)
        variant_matches.append(len(row['variant/haplotypes'].intersection(row['Variant/Haplotypes'])) / len(row['Variant/Haplotypes']) if len(row['Variant/Haplotypes']) > 0 else 0)
        drug_matches.append(len(row['drug(s)'].intersection(row['Drug(s)'])) / len(row['Drug(s)']) if len(row['Drug(s']) > 0 else 0)

    average_gene_match_rate = sum(gene_matches) / len(gene_matches)
    average_variant_match_rate = sum(variant_matches) / len(variant_matches)
    average_drug_match_rate = sum(drug_matches) / len(drug_matches)

    # Save outputs
    df_var_drug_ann.to_csv(DF_NEW_CSV_PATH, index=False)
    flattened_df.to_csv(OUTPUT_CSV_PATH, index=False)

    # Visualizations
    plot_match_rates(match_stats)
    plot_pie_charts(match_stats)
    plot_grouped_match_rates(average_gene_match_rate, average_drug_match_rate, average_variant_match_rate)

    table_data = plot_attribute_match_rates(wholecsv)

    # Print results
    print("Match Statistics:")
    for key, value in match_stats.items():
        print(f"{key}: {value:.2f}%")
    print("\nGrouped Match Rates:")
    print(f"Average Gene Match Rate: {average_gene_match_rate*100:.2f}%")
    print(f"Average Variant Match Rate: {average_variant_match_rate*100:.2f}%")
    print(f"Average Drug Match Rate: {average_drug_match_rate*100:.2f}%")
    print("\nAttribute Match Table:")
    print(table_data)

if __name__ == "__main__":
    main()