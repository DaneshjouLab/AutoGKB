import re

# Example usage
def extractVariants(text):
    # Note, seems to extract a ton of variants, not just the ones that are being studied
    variantRegex = r'\b([A-Z]+\d+[A-Z]*\*\d+|\brs\d+)\b'
    return re.findall(variantRegex, text) or []