import re
from termcolor import colored
from loguru import logger


def extractVariantsRegex(text):
    # Note, seems to extract a ton of variants, not just the ones that are being studied
    # Think it might only be applicable to rsIDs
    variantRegex = r"\b([A-Z]+\d+[A-Z]*\*\d+|\brs\d+)\b"
    return re.findall(variantRegex, text) or []


def save_output(prompt, output, filename):
    # save prompt and output to file
    with open(f"test_outputs/{filename}.txt", "w") as f:
        f.write("Prompt:\n")
        f.write(prompt)
        f.write("\nOutput:\n")
        f.write(output)
    logger.info(f"Saved output to {filename}.txt")
