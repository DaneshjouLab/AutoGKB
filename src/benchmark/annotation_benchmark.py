from typing import List
import json
from src.utils import get_pmcid_annotation
from src.benchmark.pheno_benchmark import evaluate_phenotype_annotations


class AnnotationBenchmark:
    def __init__(self):
        pass

    def get_var_drug_ann_score(self, var_drug_ann: List[dict]):
        return 1.0

    def get_var_pheno_ann_score(self, var_pheno_ann: List[dict], pmcid: str):
        # Load ground truth annotations
        with open("persistent_data/benchmark_annotations.json", "r") as f:
            ground_truth_data = json.load(f)

        # Get ground truth for this PMCID
        if pmcid not in ground_truth_data:
            return 0.0

        ground_truth_pheno_ann = ground_truth_data[pmcid].get("var_pheno_ann", [])

        # If both are empty, perfect score
        if not var_pheno_ann and not ground_truth_pheno_ann:
            return 1.0

        # If one is empty but not the other, score is 0
        if not var_pheno_ann or not ground_truth_pheno_ann:
            return 0.0

        # Compare: [ground_truth, prediction]
        try:
            score = evaluate_phenotype_annotations([ground_truth_pheno_ann, var_pheno_ann])
            return score / 100.0
        except Exception:
            return 0.0

    def get_var_fa_ann_score(self, var_fa_ann: List[dict]):
        return 1.0

    def get_study_parameters_score(self, study_parameters: List[dict]):
        return 1.0

    def calculate_total_score(
        self,
        var_drug_ann: List[dict],
        var_pheno_ann: List[dict],
        var_fa_ann: List[dict],
        study_parameters: List[dict],
        pmcid: str,
    ):
        # Return average of all scores
        scores = [
            self.get_var_drug_ann_score(var_drug_ann),
            self.get_var_pheno_ann_score(var_pheno_ann, pmcid),
            self.get_var_fa_ann_score(var_fa_ann),
            self.get_study_parameters_score(study_parameters),
        ]
        return sum(scores) / len(scores)

    def run(self, pmcid: str):
        pmcid_annotation = get_pmcid_annotation(pmcid)

        var_drug_ann = pmcid_annotation.get("varDrugAnn", [])
        var_pheno_ann = pmcid_annotation.get("varPhenoAnn", [])
        var_fa_ann = pmcid_annotation.get("varFaAnn", [])
        study_parameters = pmcid_annotation.get("studyParameters", [])

        total_score = self.calculate_total_score(
            var_drug_ann, var_pheno_ann, var_fa_ann, study_parameters, pmcid
        )
        print(f"Score for pmcid {pmcid}: {total_score}")
        return total_score

    def run_all(self):
        benchmark_pmcids = []
        with open("persistent_data/benchmark_pmcids.txt", "r") as f:
            benchmark_pmcids = f.read().splitlines()
        scores = []
        for pmcid in benchmark_pmcids:
            scores.append(self.run(pmcid))

        overall_score = sum(scores) / len(scores)
        print(f"Average score: {overall_score}")
        return overall_score


if __name__ == "__main__":
    benchmark = AnnotationBenchmark()
    benchmark.run_all()
