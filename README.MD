<!-- SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md) -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

![Build and Test](https://github.com/DaneshjouLab/AutoGKB/actions/workflows/build-and-test.yml/badge.svg)


# AutoGKB

Goals:
1. Fetch annotated articles from variantAnnotations stored in PharmGKB API
2. Create a general benchmark for an extraction system that can output a score for an extraction system
Given: Article, Ground Truth Variants (Manually extracted and recorded in var_drug_ann.tsv:)
Input: Extraction System or Extracted Variants
Output: Score 
3. System for extracting drug related variants annotations from an article. Associations in which the variant affects a drug dose, response, metabolism, etc.
4. Continously fetch new pharmacogenomic articles

## Description

This repository contains Python scripts for running and building a Pharmacogenomic Agentic system to annotate and label genetic variants based on their phenotypical associations from journal articles. 


## Progress Tracker
| Task | Status |
| --- | --- |
| Download the zip of variants from pharmgkb | ✅  |
| Get a PMID list from the variants tsv (column PMID) | ✅ |
| Convert the PMID to PMCID | ✅ |
| Update to use non-official pmid to pmcid | |
| Fetch the content from the PMCID | ✅ |
| Create pairing of annotations to article | |