class PromptTemplates:
    """Simple prompts for the LLM annotation pipeline."""
    
    SUMMARIZE_PROMPT = """
You are a pharmacogenomics expert reviewing biomedical literature. Analyze this article and determine if it contains information about genetic variants and their associations with drug response, metabolism, toxicity, or disease phenotypes.

Article Title: {title}
Article Text: {article_text}
"""
