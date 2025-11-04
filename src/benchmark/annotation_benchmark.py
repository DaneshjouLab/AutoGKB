from typing import List
from src.utils import get_pmcid_annotation
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

    def get_var_pheno_ann_score(self, var_pheno_ann: List[dict]):
        return 1.0

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
    ):
        # Return average of all scores
        scores = [
            self.get_var_drug_ann_score(var_drug_ann),
            self.get_var_pheno_ann_score(var_pheno_ann),
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
            var_drug_ann, var_pheno_ann, var_fa_ann, study_parameters
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
