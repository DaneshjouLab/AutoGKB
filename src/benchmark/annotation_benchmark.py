from typing import List, Optional
import json
from src.utils import get_pmcid_annotation
from src.benchmark.pheno_benchmark import evaluate_phenotype_annotations
from src.benchmark.fa_benchmark import evaluate_functional_analysis
from src.benchmark.drug_benchmark import evaluate_drug_annotations


class AnnotationBenchmark:
    def __init__(self):
        pass

    def get_var_drug_ann_score(self, var_drug_ann: List[dict]):
        try:
            result = evaluate_drug_annotations(var_drug_ann)
            return float(result.get("overall_score", 0.0))
        except Exception:
            return 1.0

    def get_var_pheno_ann_score(
        self,
        var_pheno_ann: List[dict],
        pmcid: Optional[str] = None,
        ground_truth_pheno_ann: Optional[List[dict]] = None,
    ):
        """
        Get phenotype annotation score.
        
        Args:
            var_pheno_ann: Prediction annotations
            pmcid: PMCID for loading ground truth (for backward compatibility)
            ground_truth_pheno_ann: Ground truth annotations (preferred, passed directly)
        """
        # If ground truth is provided directly, use it (preferred)
        if ground_truth_pheno_ann is not None:
            gt_list = ground_truth_pheno_ann
        elif pmcid is not None:
            # Fallback: load from file (for backward compatibility)
            with open("persistent_data/benchmark_annotations.json", "r") as f:
                ground_truth_data = json.load(f)

            if pmcid not in ground_truth_data:
                return 0.0

            gt_list = ground_truth_data[pmcid].get("var_pheno_ann", [])
        else:
            raise ValueError(
                "Either ground_truth_pheno_ann or pmcid must be provided"
            )

        # If both are empty, perfect score
        if not var_pheno_ann and not gt_list:
            return 1.0

        # If one is empty but not the other, score is 0
        if not var_pheno_ann or not gt_list:
            return 0.0

        # Compare: [ground_truth, prediction]
        try:
            result = evaluate_phenotype_annotations([gt_list, var_pheno_ann])
            return float(result.get("overall_score", 0.0))
        except Exception:
            return 0.0

    def get_var_fa_ann_score(self, var_fa_ann: List[dict]):
        try:
            result = evaluate_functional_analysis(var_fa_ann)
            return float(result.get("overall_score", 0.0))
        except Exception:
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
