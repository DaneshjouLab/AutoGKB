<!-- SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md) -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

![Build and Test](https://github.com/DaneshjouLab/AutoGKB/actions/workflows/build-and-test.yml/badge.svg)


# AutoGKB

Goals:
1. Fetch annotated articles from variantAnnotations stored in PharmGKB API
2. Create a general benchmark for an extraction system that can output a score for an extraction system
Given: Article, Ground Truth Variants (Manually extracted and recorded in var_drug_ann.tsv:)
Input: Extracted Variants
Output: Score 
3. System for extracting drug related variants annotations from an article. Associations in which the variant affects a drug dose, response, metabolism, etc.
4. Continously fetch new pharmacogenomic articles

## Setup
To get started, you need two sources of data locally:
1. The annotations for the articles (data/variantAnnotations/var_drug_ann.tsv)
2. the articles themselves (data/articles)
These can be populated using the following commands:
```
pixi run download-variants
pixi run update-download-map
pixi run download-articles
```
The download-articles step takes the longest and can be skipped by unzipping data/articles.zip, creating a list of XMLs at the directory data/articles.

## Description

This repository contains Python scripts for running and building a Pharmacogenomic Agentic system to annotate and label genetic variants based on their phenotypical associations from journal articles. 


## Progress Tracker
| Category | Task | Status |
| --- | --- | --- |
| Initial Download | Download the zip of variants from pharmgkb | ✅  |
|                  | Get a PMID list from the variants tsv (column PMID) | ✅ |
|                  | Convert the PMID to PMCID | ✅ |
|                  | Update to use non-official pmid to pmcid (aaron's method) | |
|                  | Fetch the content from the PMCID | ✅ |
| Benchmark        | Create pairings of annotations to articles | |
|                  | Create a niave score of number of matches | |
|                  | Create group wise score | |
|                  | Look into advanced scoring based on distance from truth per term | |
| Workflows        | Integrate Aaron's current approach | |
|                  | Document on individual annotation meanings | |
|                  | Delegate annotation groupings to team members | |
| New Article Fetching | Replicate PharGKB current workflow | |

## System Overview
![Annotations Diagram](assets/annotations_diagram.svg)

