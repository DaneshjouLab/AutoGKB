"""
Entry point for the full end to end pipeline


"""
from dotenv import load_dotenv
import os
import pandas as pd
from google import genai
from typing import List
from src.dataset.pydantic_types.models_variants import *
from openai import OpenAI



load_dotenv("./config/.env")

def generate_message(instructions, query_content):
  return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": query_content },
    ]


def call_model(instructions, query_content, response_schema,model="gemini-2.0-flash"):
  gemini_key=os.environ["GEMINI_KEY"] = os.getenv("GEMINI_KEY")
  client = OpenAI(
    api_key=gemini_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
  completion=client.beta.chat.completions.parse(
    model=model,
    messages=generate_message(
        instructions,
        query_content),
    response_format=response_schema
)
  return completion
  


def parse_md(markdown,sentences=4) -> List[str]:
    """parse_md parses the md and into blocks"""

    
    return [markdown]



def process_variants(block,prompt_dict) :
    # 

    completion = call_model(prompt_dict["Variant_Instructions"],block,response_schema=Variants )
    print(completion)
    variants=completion.choices[0].message.parsed

    return variants

# the following should be done in 



def load_key_value_dict(path: str, key_col: str, value_col: str) -> dict:
    """Load a key-value dict from a CSV using pandas."""
    df = pd.read_csv(path)
    return dict(zip(df[key_col], df[value_col]))


def run(input_MD: str,**kwargs ):
    """run is the end to end pipeline that is used by autogkb. 

    Args:
        input_MD (MDInput): _description_
    """
    #load prompt dict
    prompt_dict=load_key_value_dict(kwargs["csv_path"],"Task", "Prompt")
    
    compiled_information=parse_md(input_MD,) # list[str], 
    
    
    for block in compiled_information:
        # read the blcok for each thing and then move onto the enxt part and then move o
        variants= process_variants(block, prompt_dict)
        print(variants)
    return
    






if __name__ =="__main__":
    markdown_folder_path=os.environ.get("MARKDOWN_FOLDER_PATH")
    all_entries = os.listdir(markdown_folder_path)
    first_md_file=all_entries[0]

    with open(os.path.join(markdown_folder_path, first_md_file), "r") as f:
        markdown = f.read()
    prompt_path=os.environ.get("PROMPT_CSV_PATH")
    result = run(markdown, csv_path=prompt_path)
    
    