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
            # Pheno and Study Parameters benchmarks can handle lists directly
            result = benchmark_func([gt_list, pred_list])
        else:
            # Drug, FA expect single dicts
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


def create_aggregated_summary(bench_result: Dict[str, Any], bench_name: str) -> Dict[str, Any]:
    """Create aggregated summary from benchmark results, excluding detailed per-sample data."""
    aggregated = {
        "overall_score": bench_result.get("overall_score", 0.0),
        "total_samples": bench_result.get("total_samples", 0),
    }
    
    status = bench_result.get("status")
    if status:
        aggregated["status"] = status
    
    # Aggregate field scores
    field_scores = bench_result.get("field_scores", {})
    if field_scores:
        aggregated["field_scores"] = {}
        for field, score_data in field_scores.items():
            aggregated["field_scores"][field] = {
                "mean_score": score_data.get("mean_score", 0.0),
                "scores": score_data.get("scores", [])
            }
    
    # Aggregate low-scoring fields with values
    detailed_results = bench_result.get("detailed_results", [])
    if detailed_results and field_scores:
        # Exclude ID fields from display for study_parameters
        excluded_from_display = set()
        if bench_name == "study_parameters":
            excluded_from_display = {'Study Parameters ID', 'Variant Annotation ID'}
        
        # Find low-scoring fields
        sorted_fields = sorted(
            field_scores.items(),
            key=lambda x: x[1].get("mean_score", 0.0),
            reverse=True,
        )
        low_scoring_fields = [
            f for f in sorted_fields 
            if f[1].get("mean_score", 1.0) < 1.0 
            and f[0] not in excluded_from_display
        ]
        
        if low_scoring_fields:
            aggregated["low_scoring_fields"] = {}
            for field, score_data in low_scoring_fields:
                field_info = {
                    "mean_score": score_data.get("mean_score", 0.0),
                    "scores": score_data.get("scores", [])
                }
                
                # Collect values from all samples
                field_values_list = []
                for dr in detailed_results:
                    field_values = dr.get("field_values", {})
                    if field in field_values:
                        field_values_list.append(field_values[field])
                
                if field_values_list:
                    # Store all sample values
                    field_info["sample_values"] = field_values_list
                
                aggregated["low_scoring_fields"][field] = field_info
    
    # Aggregate dependency issues
    all_issues = []
    all_penalties = []
    for dr in detailed_results:
        issues = dr.get("dependency_issues", [])
        all_issues.extend(issues)
        
        penalty_info = dr.get("penalty_info", {})
        if penalty_info and penalty_info.get("total_penalty", 0) > 0:
            all_penalties.append(penalty_info)
    
    if all_issues:
        aggregated["dependency_issues"] = list(set(all_issues))  # Unique issues
    
    if all_penalties:
        aggregated["penalties"] = []
        for penalty_info in all_penalties:
            aggregated["penalties"].append({
                "total_penalty": penalty_info.get("total_penalty", 0.0),
                "penalized_fields": list(penalty_info.get("penalized_fields", {}).keys()),
                "issues_count": len(penalty_info.get("issues_by_field", {}))
            })
    
    return aggregated


def create_aggregated_summary(bench_result: Dict[str, Any], bench_name: str) -> Dict[str, Any]:
    """Create aggregated summary from benchmark results, excluding detailed per-sample data."""
    aggregated = {
        "overall_score": bench_result.get("overall_score", 0.0),
        "total_samples": bench_result.get("total_samples", 0),
    }
    
    status = bench_result.get("status")
    if status:
        aggregated["status"] = status
    
    # Aggregate field scores
    field_scores = bench_result.get("field_scores", {})
    if field_scores:
        aggregated["field_scores"] = {}
        for field, score_data in field_scores.items():
            aggregated["field_scores"][field] = {
                "mean_score": score_data.get("mean_score", 0.0),
                "scores": score_data.get("scores", [])
            }
    
    # Aggregate low-scoring fields with values
    detailed_results = bench_result.get("detailed_results", [])
    if detailed_results and field_scores:
        # Exclude ID fields from display for study_parameters
        excluded_from_display = set()
        if bench_name == "study_parameters":
            excluded_from_display = {'Study Parameters ID', 'Variant Annotation ID'}
        
        # Find low-scoring fields
        sorted_fields = sorted(
            field_scores.items(),
            key=lambda x: x[1].get("mean_score", 0.0),
            reverse=True,
        )
        low_scoring_fields = [
            f for f in sorted_fields 
            if f[1].get("mean_score", 1.0) < 1.0 
            and f[0] not in excluded_from_display
        ]
        
        if low_scoring_fields:
            aggregated["low_scoring_fields"] = {}
            for field, score_data in low_scoring_fields:
                field_info = {
                    "mean_score": score_data.get("mean_score", 0.0),
                    "scores": score_data.get("scores", [])
                }
                
                # Collect values from all samples
                field_values_list = []
                for dr in detailed_results:
                    field_values = dr.get("field_values", {})
                    if field in field_values:
                        field_values_list.append(field_values[field])
                
                if field_values_list:
                    # Store all sample values
                    field_info["sample_values"] = field_values_list
                
                aggregated["low_scoring_fields"][field] = field_info
    
    # Aggregate dependency issues
    all_issues = []
    all_penalties = []
    for dr in detailed_results:
        issues = dr.get("dependency_issues", [])
        all_issues.extend(issues)
        
        penalty_info = dr.get("penalty_info", {})
        if penalty_info and penalty_info.get("total_penalty", 0) > 0:
            all_penalties.append(penalty_info)
    
    if all_issues:
        aggregated["dependency_issues"] = list(set(all_issues))  # Unique issues
    
    if all_penalties:
        aggregated["penalties"] = []
        for penalty_info in all_penalties:
            aggregated["penalties"].append({
                "total_penalty": penalty_info.get("total_penalty", 0.0),
                "penalized_fields": list(penalty_info.get("penalized_fields", {}).keys()),
                "issues_count": len(penalty_info.get("issues_by_field", {}))
            })
    
    return aggregated


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
    
    # Study Parameters benchmark (now handles lists directly with similarity-based alignment)
    gt_study = gt_entry.get("study_parameters", [])
    pred_study = llm_entry.get("study_parameters", [])
    study_result = run_benchmark(
        evaluate_study_parameters, gt_study, pred_study, "Study Parameters", accepts_lists=True
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
        
        # Get detailed results early for value display
        detailed_results = bench_result.get("detailed_results", [])
        
        # Print field score analysis
        field_scores = bench_result.get("field_scores", {})
        if field_scores:
            # Sort by mean_score
            sorted_fields = sorted(
                field_scores.items(),
                key=lambda x: x[1].get("mean_score", 0.0),
                reverse=True,
            )
            
            # Show top 3 performing fields
            top_fields = sorted_fields[:3]
            if top_fields:
                top_fields_str = ", ".join(
                    [
                        f"{field} ({score['mean_score']:.2f})"
                        for field, score in top_fields
                    ]
                )
                print(f"  Top Performing Fields: {top_fields_str}")
            
            # Show bottom performing fields (causing score reduction)
            # For study_parameters, exclude ID fields from display
            excluded_from_display = set()
            if bench_name == "study_parameters":
                excluded_from_display = {'Study Parameters ID', 'Variant Annotation ID'}
            
            bottom_fields = [
                f for f in sorted_fields 
                if f[1].get("mean_score", 1.0) < 1.0 
                and f[0] not in excluded_from_display
            ]
            
            if bottom_fields:
                print(f"  Low Scoring Fields (reducing overall score):")
                for field, score_data in bottom_fields:
                    mean_score = score_data.get("mean_score", 0.0)
                    scores = score_data.get("scores", [])
                    # Show range if multiple samples
                    if len(scores) > 1:
                        min_score = min(scores)
                        max_score = max(scores)
                        print(f"    • {field}: {mean_score:.3f} (range: {min_score:.3f}-{max_score:.3f})")
                    else:
                        print(f"    • {field}: {mean_score:.3f}")
                    
                    # Show actual values for misaligned fields
                    if detailed_results:
                        # Get values from first sample (or aggregate if multiple)
                        field_values_list = []
                        for dr in detailed_results:
                            field_values = dr.get("field_values", {})
                            if field in field_values:
                                field_values_list.append(field_values[field])
                        
                        if field_values_list:
                            # Show values from first sample, or aggregate if multiple
                            if len(field_values_list) == 1:
                                vals = field_values_list[0]
                                gt_val = vals.get("ground_truth")
                                pred_val = vals.get("prediction")
                                gt_str = str(gt_val) if gt_val is not None else "None"
                                pred_str = str(pred_val) if pred_val is not None else "None"
                                # Truncate long values
                                if len(gt_str) > 60:
                                    gt_str = gt_str[:57] + "..."
                                if len(pred_str) > 60:
                                    pred_str = pred_str[:57] + "..."
                                print(f"      GT: {gt_str}")
                                print(f"      Pred: {pred_str}")
                            else:
                                # Show values per sample when multiple samples exist
                                print(f"      ({len(field_values_list)} samples)")
                                for sample_idx, vals in enumerate(field_values_list[:3]):  # Show first 3 samples
                                    gt_val = vals.get("ground_truth")
                                    pred_val = vals.get("prediction")
                                    gt_str = str(gt_val) if gt_val is not None else "None"
                                    pred_str = str(pred_val) if pred_val is not None else "None"
                                    # Truncate long values
                                    if len(gt_str) > 50:
                                        gt_str = gt_str[:47] + "..."
                                    if len(pred_str) > 50:
                                        pred_str = pred_str[:47] + "..."
                                    print(f"        Sample {sample_idx}: GT={gt_str}, Pred={pred_str}")
                                if len(field_values_list) > 3:
                                    print(f"        ... ({len(field_values_list) - 3} more samples)")
        
        # Print dependency issues and penalty information if present
        all_issues = []
        all_penalties = []
        
        for dr in detailed_results:
            issues = dr.get("dependency_issues", [])
            all_issues.extend(issues)
            
            penalty_info = dr.get("penalty_info", {})
            if penalty_info and penalty_info.get("total_penalty", 0) > 0:
                all_penalties.append(penalty_info)
        
        if all_issues:
            unique_issues = list(set(all_issues))[:5]  # Show first 5 unique issues
            print(f"  Dependency Issues: {len(all_issues)} total")
            for issue in unique_issues:
                print(f"    - {issue}")
        
        # Print detailed penalty information
        if all_penalties:
            print(f"  Penalties Applied: {len(all_penalties)} sample(s) penalized")
            for i, penalty_info in enumerate(all_penalties[:2]):  # Show first 2 samples
                total_penalty = penalty_info.get("total_penalty", 0)
                penalized_fields = penalty_info.get("penalized_fields", {})
                issues_by_field = penalty_info.get("issues_by_field", {})
                
                if penalized_fields:
                    print(f"    Sample {i+1}: {total_penalty*100:.1f}% penalty applied")
                    for field, penalty_data in list(penalized_fields.items())[:3]:  # Show top 3 penalized fields
                        orig = penalty_data.get("original_score", 0)
                        penal = penalty_data.get("penalized_score", 0)
                        pct = penalty_data.get("penalty_percentage", 0)
                        field_issues = issues_by_field.get(field, [])
                        
                        print(f"      • {field}:")
                        print(f"        Score: {orig:.3f} → {penal:.3f} ({pct:.1f}% reduction)")
                        if field_issues:
                            for issue in field_issues[:1]:  # Show first issue for this field
                                print(f"        Reason: {issue}")
        
        # Show field-level score breakdown for better understanding
        if field_scores and total_samples > 0:
            # Calculate which fields contribute most to score reduction
            perfect_fields = sum(1 for f, s in field_scores.items() if abs(s.get("mean_score", 0) - 1.0) < 0.001)
            total_fields = len(field_scores)
            if perfect_fields < total_fields:
                imperfect_count = total_fields - perfect_fields
                print(f"  Field Performance: {perfect_fields}/{total_fields} fields perfect, {imperfect_count} fields with mismatches")


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
        scores = []
        for r in all_results:
            bench_result = r["benchmarks"].get(bench_name)
            if bench_result:
                # Exclude entries with "one_empty" status from average
                status = bench_result.get("status")
                if status != "one_empty":
                    scores.append(bench_result.get("overall_score", 0.0))
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"  {bench_name.upper()}: {avg_score:.3f} (avg across {len(scores)} examples, excluding 'one_empty')")
        else:
            print(f"  {bench_name.upper()}: No valid scores (all had 'one_empty' status)")


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

