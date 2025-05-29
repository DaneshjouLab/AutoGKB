# Variant Extraction Module

This is organized into the following Python modules, each handling a specific aspect of the workflow:

- **config.py**: Stores configuration variables, such as URLs, file paths, and API settings.
- **ncbi_fetch.py**: Manages fetching PMCID and content from NCBI using the Entrez API.
- **processing.py**: Loads and processes the variant annotation dataset, including enumeration cleaning and DataFrame processing. Also interacts with the OpenAI API to extract structured genetic variant data from publication content.
- **variant_matching.py**: Compares extracted data with ground truth for accuracy evaluation.
- **visualization.py**: Generates visualizations to summarize match rates and analysis results.
- **run_variant_extraction.py**: Orchestrates the entire workflow, integrating all modules.

## config.py
This module centralizes configuration settings to avoid hardcoding values in the codebase.

**Variables**:
- URLs for downloading PharmGKB data (CLINICAL_VARIANTS_URL, VARIANT_ANNOTATIONS_URL).
- File paths for input and output data (VAR_DRUG_ANN_PATH, CHECKPOINT_PATH, OUTPUT_CSV_PATH, DF_NEW_CSV_PATH, WHOLE_CSV_PATH).
- NCBI Entrez email (ENTREZ_EMAIL) for API compliance.
- OpenAI model name (OPENAI_MODEL) and JSON schema (SCHEMA_TEXT) for structured API responses.
- System message template (SYSTEM_MESSAGE_TEMPLATE) for API prompts.

## processing.py
This module handles interactions with the OpenAI API to extract structured genetic variant data.

`clean_enum_list(enum_list)`:

Cleans and normalizes enumeration lists by removing NaN values, splitting comma-separated strings, and ensuring uniqueness.
Used to prepare valid enumeration values for the JSON schema.


`load_and_prepare_data(file_path)`:

Loads the variant annotation TSV file into a pandas DataFrame.
Extracts unique values for Phenotype Category, Significance, Metabolizer types, and Population types to create enumeration lists.
Returns the DataFrame and a dictionary of cleaned enumeration values.


`create_schema(enum_values)`:

Creates a JSON schema for API responses based on the provided enumeration values.
Defines a structure for an array of gene objects with fields like gene, variant, drug(s), and others, enforcing strict validation.


`create_messages(content_text, schema_text, custom_template=None)`:

Generates API messages with a system prompt (using SYSTEM_MESSAGE_TEMPLATE or a custom template) and user content.
The system prompt instructs the API to extract genetic variant information in the specified schema format.


`call_api(client, messages, schema)`:

Makes an API call to the OpenAI model (gpt-4o-2024-08-06) with the provided messages and schema.
Returns the parsed JSON response containing extracted gene data.


`load_checkpoint(checkpoint_path)`:

Loads previously processed PMIDs and results from a checkpoint file to avoid redundant API calls.
Returns a set of processed PMIDs and a list of results.


`save_checkpoint(checkpoint_path, processed_pmids, results)`:

Saves processed PMIDs and results to a checkpoint file for persistence.
Ensures progress is saved after each processed row to handle interruptions.


`process_responses(df, client, schema_text, schema, checkpoint_path, custom_template=None)`:

Iterates through the DataFrame to process each row’s Content_text using the OpenAI API.
Skips previously processed PMIDs based on checkpoint data.
Saves results and updates the checkpoint after each row to ensure progress is not lost.
Returns a list of flattened JSON objects with extracted gene data and associated PMIDs.



## variant_matching.py
This module compares extracted data with ground truth to evaluate accuracy.

`SimplifiedVariantMatcher`:

`split_variants(variant_string)`:
Splits variant strings into individual components, handling delimiters like commas and slashes.


`preprocess_variants(variant_string, gene=None)`:
Preprocesses variant strings to handle rsIDs, star alleles, and SNP notations.
Attaches gene names to star alleles and processes complex notations (e.g., CYP2C19*2-1234G>A).


`match_row(row)`:
Compares ground truth and predicted variants for a single row.
Returns Exact Match, Partial Match, or No Match based on set intersections.


`align_and_compare_datasets(df_new, flattened_df)`:

Renames columns in input DataFrames to distinguish ground truth (_truth) and predicted (_output) data.
Merges DataFrames on PMID using an inner join.
Applies variant matching using SimplifiedVariantMatcher and compares other fields (gene, drug(s), phenotype category, significance, metabolizer types, specialty population).
Returns a DataFrame with match indicators for each field.



## visualization.py
This module generates visualizations to summarize match rates and analysis results.

`plot_match_rates(match_stats)`:

Creates a bar plot of exact match rates for Gene, Drug, Phenotype, Significance, and Variant categories.
Uses a professional color scheme and ensures readability with appropriate labels and limits.


`plot_pie_charts(match_stats)`:

Generates nested pie charts showing partial_match_rate (outer) and exact_match_rate (inner).
Includes a legend with percentage values for clarity.


`plot_grouped_match_rates(average_gene_match_rate, average_drug_match_rate, average_variant_match_rate)`:

Plots a bar chart of match rates for Gene, Drug, and Variant categories, calculated by grouping data by PMID.
Adds percentage labels above bars for clarity.


`plot_attribute_match_rates(wholecsv)`:

Creates a bar plot of match percentages for attributes like Match metabolizer, Match significance, etc., from the wholecsv dataset.
Returns a DataFrame summarizing the match statistics for inclusion in reports or posters.



## run_variant_extraction.py
This module orchestrates the entire workflow.

`main()`:
- Initializes the OpenAI client with the API key from the environment.
- Downloads and extracts PharmGKB data using data_download.download_and_extract_zip.
- Loads and prepares the variant annotation dataset using data_processing.load_and_prepare_data.
- Processes a subset of the DataFrame (e.g., 5 rows) to fetch NCBI data using data_processing.process_dataframe.
- Creates a JSON schema using processing.create_schema.
- Processes API responses to extract gene data using processing.process_responses.
- Aligns and compares datasets using variant_matching.align_and_compare_datasets.
- Calculates match statistics for various fields and grouped match rates by PMID.
- Saves output DataFrames to CSV files (DF_NEW_CSV_PATH, OUTPUT_CSV_PATH).
- Generates visualizations using visualization module functions.
- Prints match statistics and attribute match table to the console.

## Run the variant extraction:
`python -m src.variant_extraction.run_variant_extraction`