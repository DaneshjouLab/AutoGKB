"""Run benchmark examples comparing LLM predictions to ground truth."""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.benchmark.pheno_benchmark import evaluate_phenotype_annotations
from src.benchmark.drug_benchmark import evaluate_drug_annotations
from src.benchmark.fa_benchmark import evaluate_functional_analysis
from src.benchmark.study_parameters_benchmark import evaluate_study_parameters


def load_data_files():
    """Load LLM predictions and ground truth annotations."""
    base_path = Path(__file__).parent.parent.parent / "persistent_data"
    
    llm_file = base_path / "combined_output_11_02_25.json"
    gt_file = base_path / "benchmark_annotations.json"
    
    print(f"Loading LLM predictions from: {llm_file}")
    with open(llm_file, "r") as f:
        llm_data = json.load(f)
    
    print(f"Loading ground truth from: {gt_file}")
    with open(gt_file, "r") as f:
        gt_data = json.load(f)
    
    return llm_data, gt_data


def find_common_pmcids(llm_data: Dict, gt_data: Dict, num_examples: int = 5) -> List[str]:
    """Find common PMCIDs between LLM and ground truth data."""
    llm_pmcids = set(llm_data.keys())
    gt_pmcids = set(gt_data.keys())
    common = sorted(list(llm_pmcids & gt_pmcids))
    
    print(f"\nFound {len(common)} common PMCIDs")
    print(f"Selecting first {min(num_examples, len(common))} examples")
    
    return common[:num_examples]


def run_benchmark(
    benchmark_func,
    gt_list: List[Dict[str, Any]],
    pred_list: List[Dict[str, Any]],
    benchmark_name: str,
    accepts_lists: bool = False,
) -> Optional[Dict[str, Any]]:
    """Run a single benchmark and return results."""
    if not gt_list and not pred_list:
        return {
            "overall_score": 1.0,
            "total_samples": 0,
            "status": "both_empty",
        }
    
    if not gt_list or not pred_list:
        return {
            "overall_score": 0.0,
            "total_samples": 0,
            "status": "one_empty",
        }
    
    try:
        if accepts_lists:
            # Pheno benchmark can handle lists directly
            result = benchmark_func([gt_list, pred_list])
        else:
            # Drug, FA, Study Parameters expect single dicts
            if len(gt_list) == 0 or len(pred_list) == 0:
                return {
                    "overall_score": 0.0,
                    "total_samples": 0,
                    "status": "empty_list",
                }
            
            # Compare first annotations (can be extended to compare all pairs)
            result = benchmark_func([gt_list[0], pred_list[0]])
        
        return result
    except Exception as e:
        print(f"  Error in {benchmark_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "overall_score": 0.0,
            "total_samples": 0,
            "status": "error",
            "error": str(e),
        }


def evaluate_pmcid(
    pmcid: str, llm_data: Dict, gt_data: Dict
) -> Dict[str, Any]:
    """Evaluate all benchmark types for a single PMCID."""
    llm_entry = llm_data.get(pmcid, {})
    gt_entry = gt_data.get(pmcid, {})
    
    results = {
        "pmcid": pmcid,
        "title": gt_entry.get("title", llm_entry.get("title", "Unknown")),
        "benchmarks": {},
    }
    
    # Pheno benchmark (accepts lists)
    gt_pheno = gt_entry.get("var_pheno_ann", [])
    pred_pheno = llm_entry.get("var_pheno_ann", [])
    pheno_result = run_benchmark(
        evaluate_phenotype_annotations, gt_pheno, pred_pheno, "Pheno", accepts_lists=True
    )
    results["benchmarks"]["pheno"] = pheno_result
    
    # Drug benchmark (expects single dicts)
    gt_drug = gt_entry.get("var_drug_ann", [])
    pred_drug = llm_entry.get("var_drug_ann", [])
    drug_result = run_benchmark(
        evaluate_drug_annotations, gt_drug, pred_drug, "Drug", accepts_lists=False
    )
    results["benchmarks"]["drug"] = drug_result
    
    # FA benchmark (expects single dicts)
    gt_fa = gt_entry.get("var_fa_ann", [])
    pred_fa = llm_entry.get("var_fa_ann", [])
    fa_result = run_benchmark(
        evaluate_functional_analysis, gt_fa, pred_fa, "FA", accepts_lists=False
    )
    results["benchmarks"]["fa"] = fa_result
    
    # Study Parameters benchmark (expects single dicts)
    gt_study = gt_entry.get("study_parameters", [])
    pred_study = llm_entry.get("study_parameters", [])
    study_result = run_benchmark(
        evaluate_study_parameters, gt_study, pred_study, "Study Parameters", accepts_lists=False
    )
    results["benchmarks"]["study_parameters"] = study_result
    
    return results


def print_summary(results: Dict[str, Any]):
    """Print a summary of results to console."""
    pmcid = results["pmcid"]
    title = results["title"]
    
    print(f"\n{'='*60}")
    print(f"=== {pmcid} ===")
    print(f"Title: {title}")
    print(f"{'='*60}")
    
    for bench_name, bench_result in results["benchmarks"].items():
        if bench_result is None:
            continue
        
        overall = bench_result.get("overall_score", 0.0)
        total_samples = bench_result.get("total_samples", 0)
        status = bench_result.get("status")
        
        print(f"\n{bench_name.upper()} Benchmark:")
        print(f"  Overall Score: {overall:.3f}")
        print(f"  Aligned Samples: {total_samples}")
        
        if status:
            print(f"  Status: {status}")
        
        # Print top field scores if available
        field_scores = bench_result.get("field_scores", {})
        if field_scores:
            # Sort by mean_score and get top 3
            sorted_fields = sorted(
                field_scores.items(),
                key=lambda x: x[1].get("mean_score", 0.0),
                reverse=True,
            )[:3]
            
            if sorted_fields:
                top_fields = ", ".join(
                    [
                        f"{field} ({score['mean_score']:.2f})"
                        for field, score in sorted_fields
                    ]
                )
                print(f"  Top Fields: {top_fields}")
        
        # Print dependency issues if present
        detailed_results = bench_result.get("detailed_results", [])
        all_issues = []
        for dr in detailed_results:
            issues = dr.get("dependency_issues", [])
            all_issues.extend(issues)
        
        if all_issues:
            unique_issues = list(set(all_issues))[:3]  # Show first 3 unique issues
            print(f"  Dependency Issues: {len(all_issues)} total")
            for issue in unique_issues:
                print(f"    - {issue}")


def main(num_examples: int = 5):
    """Main function to run benchmark examples."""
    print("=" * 60)
    print("Benchmark Evaluation Script")
    print("=" * 60)
    
    # Load data
    llm_data, gt_data = load_data_files()
    
    # Find common PMCIDs
    common_pmcids = find_common_pmcids(llm_data, gt_data, num_examples)
    
    if not common_pmcids:
        print("No common PMCIDs found!")
        return
    
    # Evaluate each PMCID
    all_results = []
    for pmcid in common_pmcids:
        print(f"\nEvaluating {pmcid}...")
        results = evaluate_pmcid(pmcid, llm_data, gt_data)
        all_results.append(results)
        print_summary(results)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # From src/benchmark/, go up 3 levels to project root, then to persistent_data
    output_file = Path(__file__).parent.parent.parent / "persistent_data" / f"benchmark_results_{timestamp}.json"
    
    output_data = {
        "timestamp": timestamp,
        "num_examples": len(all_results),
        "results": all_results,
    }
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}")
    
    # Print overall summary
    print("\nOverall Summary:")
    for bench_name in ["pheno", "drug", "fa", "study_parameters"]:
        scores = [
            r["benchmarks"][bench_name].get("overall_score", 0.0)
            for r in all_results
            if r["benchmarks"].get(bench_name)
        ]
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"  {bench_name.upper()}: {avg_score:.3f} (avg across {len(scores)} examples)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run benchmark examples")
    parser.add_argument(
        "-n",
        "--num-examples",
        type=int,
        default=5,
        help="Number of examples to evaluate (default: 5)",
    )
    
    args = parser.parse_args()
    main(num_examples=args.num_examples)

