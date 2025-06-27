# Annotation Extraction


## Examples
```
model = Generator()
article_text = MarkdownParser(pmcid="PMC11730665").get_article_text()
prompt_generator = GeneratorPrompt(<Prompt>, {"article_text": article_text})
prompt = prompt_generator.get_prompt()
output = model.generate(prompt, response_format=<Pydantic Class>)
```