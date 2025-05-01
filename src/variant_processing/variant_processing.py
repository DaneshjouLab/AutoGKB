from loguru import logger
import pandas as pd
from src.load_data import load_clinical_variants_tsv


def unique_variants(df: pd.DataFrame):
    """
    Generates a dictionary with unique values for each column of a Pandas DataFrame.

    Args:
        df: The input Pandas DataFrame.

    Returns:
        A dictionary where keys are column names and values are lists of unique values
        for that column. Returns an empty dictionary if the input is invalid.
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("Input is not a Pandas DataFrame")
        return {}

    return {col: df[col].unique().tolist() for col in df.columns}

if __name__ == "__main__":
    df = load_clinical_variants_tsv()
    unique_values_per_column = unique_variants(df)
    for col, values in unique_values_per_column.items():
        print(f"Column: {col} \n")
        print(f"Unique Values: {values}\n")
        print("-" * 20)
        

