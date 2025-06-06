"""
Reporting and visualization utilities for benchmark results.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from .evaluator import EvaluationResult


class BenchmarkReporter:
    """Generate reports and visualizations for benchmark results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comparative_report(
        self, 
        results: Dict[str, EvaluationResult], 
        split: str
    ) -> Path:
        """Generate a comparative report across multiple models."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.output_dir / f"comparative_report_{split}_{timestamp}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate summary report
        summary_path = self._generate_summary_report(results, report_dir, split)
        
        # Generate detailed reports for each model
        for model_name, result in results.items():
            self._generate_model_report(result, report_dir / f"{model_name}_detailed.html")
        
        # Generate performance comparison
        self._generate_performance_comparison(results, report_dir / "performance_comparison.html")
        
        # Export raw data
        self._export_raw_results(results, report_dir)
        
        logger.info(f"Comparative report generated at {report_dir}")
        return report_dir
    
    def _generate_summary_report(
        self, 
        results: Dict[str, EvaluationResult],
        report_dir: Path,
        split: str
    ) -> Path:
        """Generate HTML summary report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Summary Report - {split.upper()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .metrics-table th, .metrics-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .metrics-table th {{ background-color: #f2f2f2; }}
        .field-stats {{ margin: 20px 0; }}
        .model-section {{ margin: 30px 0; border: 1px solid #ccc; padding: 20px; border-radius: 5px; }}
        .score {{ font-weight: bold; }}
        .high-score {{ color: green; }}
        .medium-score {{ color: orange; }}
        .low-score {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Pharmacogenomic Benchmark Results</h1>
        <p><strong>Split:</strong> {split.upper()}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Models Evaluated:</strong> {len(results)}</p>
    </div>
    
    <h2>Overall Performance Comparison</h2>
    <table class="metrics-table">
        <thead>
            <tr>
                <th>Model</th>
                <th>Overall Score</th>
                <th>Weighted Score</th>
                <th>Successful Predictions</th>
                <th>Failed Predictions</th>
                <th>Success Rate</th>
            </tr>
        </thead>
        <tbody>
"""
        
        # Sort models by weighted score
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].aggregate_metrics.get("mean_weighted_score", 0),
            reverse=True
        )
        
        for model_name, result in sorted_results:
            metrics = result.aggregate_metrics
            overall_score = metrics.get("mean_overall_score", 0)
            weighted_score = metrics.get("mean_weighted_score", 0)
            success_rate = result.successful_predictions / result.total_samples * 100
            
            score_class = self._get_score_class(weighted_score)
            
            html_content += f"""
            <tr>
                <td><strong>{model_name}</strong></td>
                <td class="score {score_class}">{overall_score:.3f}</td>
                <td class="score {score_class}">{weighted_score:.3f}</td>
                <td>{result.successful_predictions}</td>
                <td>{len(result.failed_predictions)}</td>
                <td>{success_rate:.1f}%</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
    
    <h2>Field-Level Performance</h2>
"""
        
        # Field-level comparison
        if results:
            # Get all fields from first result
            first_result = next(iter(results.values()))
            field_stats = first_result.aggregate_metrics.get("field_statistics", {})
            
            html_content += """
    <table class="metrics-table">
        <thead>
            <tr>
                <th>Field</th>
"""
            for model_name in results.keys():
                html_content += f"<th>{model_name} (Score)</th>"
                html_content += f"<th>{model_name} (Exact Match %)</th>"
            
            html_content += """
            </tr>
        </thead>
        <tbody>
"""
            
            for field_name in sorted(field_stats.keys()):
                html_content += f"<tr><td><strong>{field_name}</strong></td>"
                
                for model_name, result in results.items():
                    field_data = result.aggregate_metrics.get("field_statistics", {}).get(field_name, {})
                    mean_score = field_data.get("mean_score", 0)
                    exact_match_rate = field_data.get("exact_match_rate", 0) * 100
                    
                    score_class = self._get_score_class(mean_score)
                    html_content += f'<td class="score {score_class}">{mean_score:.3f}</td>'
                    html_content += f'<td>{exact_match_rate:.1f}%</td>'
                
                html_content += "</tr>"
            
            html_content += """
        </tbody>
    </table>
"""
        
        # Model-specific sections
        for model_name, result in sorted_results:
            html_content += self._generate_model_section_html(model_name, result)
        
        html_content += """
</body>
</html>
"""
        
        summary_path = report_dir / "summary.html"
        with open(summary_path, 'w') as f:
            f.write(html_content)
        
        return summary_path
    
    def _generate_model_section_html(self, model_name: str, result: EvaluationResult) -> str:
        """Generate HTML section for a single model."""
        metrics = result.aggregate_metrics
        
        html = f"""
    <div class="model-section">
        <h3>{model_name}</h3>
        <p><strong>Total Samples:</strong> {result.total_samples}</p>
        <p><strong>Successful Predictions:</strong> {result.successful_predictions}</p>
        <p><strong>Mean Overall Score:</strong> <span class="score">{metrics.get('mean_overall_score', 0):.3f}</span></p>
        <p><strong>Mean Weighted Score:</strong> <span class="score">{metrics.get('mean_weighted_score', 0):.3f}</span></p>
        
        <h4>Score Distribution</h4>
        <ul>
"""
        
        score_dist = metrics.get("score_distribution", {})
        for category, count in score_dist.items():
            percentage = count / result.successful_predictions * 100 if result.successful_predictions > 0 else 0
            html += f"<li><strong>{category.title()}:</strong> {count} ({percentage:.1f}%)</li>"
        
        html += """
        </ul>
        
        <h4>Top Field Issues</h4>
        <ul>
"""
        
        # Show fields with lowest scores
        field_stats = metrics.get("field_statistics", {})
        sorted_fields = sorted(field_stats.items(), key=lambda x: x[1].get("mean_score", 0))
        
        for field_name, stats in sorted_fields[:5]:  # Top 5 problematic fields
            mean_score = stats.get("mean_score", 0)
            exact_match = stats.get("exact_match_rate", 0) * 100
            html += f"<li><strong>{field_name}:</strong> Score {mean_score:.3f}, Exact Match {exact_match:.1f}%</li>"
        
        html += """
        </ul>
    </div>
"""
        
        return html
    
    def _get_score_class(self, score: float) -> str:
        """Get CSS class for score styling."""
        if score >= 0.8:
            return "high-score"
        elif score >= 0.5:
            return "medium-score"
        else:
            return "low-score"
    
    def _generate_model_report(self, result: EvaluationResult, output_path: Path) -> None:
        """Generate detailed report for a single model."""
        # For now, create a simple JSON report
        # In a full implementation, this would be a rich HTML report
        
        report_data = {
            "model_name": result.model_name,
            "summary": {
                "total_samples": result.total_samples,
                "successful_predictions": result.successful_predictions,
                "success_rate": result.successful_predictions / result.total_samples,
                "aggregate_metrics": result.aggregate_metrics
            },
            "error_analysis": result.error_analysis,
            "failed_predictions": result.failed_predictions
        }
        
        with open(output_path.with_suffix('.json'), 'w') as f:
            json.dump(report_data, f, indent=2)
    
    def _generate_performance_comparison(
        self, 
        results: Dict[str, EvaluationResult],
        output_path: Path
    ) -> None:
        """Generate performance comparison visualization."""
        # Create a simple comparison table
        # In a full implementation, this would include charts and graphs
        
        comparison_data = {}
        for model_name, result in results.items():
            comparison_data[model_name] = {
                "overall_score": result.aggregate_metrics.get("mean_overall_score", 0),
                "weighted_score": result.aggregate_metrics.get("mean_weighted_score", 0),
                "success_rate": result.successful_predictions / result.total_samples,
                "field_performance": result.aggregate_metrics.get("field_statistics", {})
            }
        
        with open(output_path.with_suffix('.json'), 'w') as f:
            json.dump(comparison_data, f, indent=2)
    
    def _export_raw_results(self, results: Dict[str, EvaluationResult], output_dir: Path) -> None:
        """Export raw results in various formats."""
        raw_dir = output_dir / "raw_data"
        raw_dir.mkdir(exist_ok=True)
        
        # Export as JSON
        for model_name, result in results.items():
            # Sample-level scores
            sample_scores_data = []
            for sample_score in result.sample_scores:
                sample_data = {
                    "pmcid": sample_score.pmcid,
                    "overall_score": sample_score.overall_score,
                    "weighted_score": sample_score.weighted_score,
                    "field_scores": [
                        {
                            "field": fs.field_name,
                            "score": fs.score,
                            "exact_match": fs.exact_match,
                            "predicted": fs.predicted,
                            "expected": fs.expected,
                            "error_type": fs.error_type
                        }
                        for fs in sample_score.field_scores
                    ]
                }
                sample_scores_data.append(sample_data)
            
            with open(raw_dir / f"{model_name}_sample_scores.json", 'w') as f:
                json.dump(sample_scores_data, f, indent=2)
    
    def export_predictions(
        self, 
        result: EvaluationResult, 
        split: str,
        format: str = "jsonl"
    ) -> Path:
        """Export model predictions for external analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.model_name}_{split}_predictions_{timestamp}"
        
        if format == "jsonl":
            output_path = self.output_dir / f"{filename}.jsonl"
            with open(output_path, 'w') as f:
                for sample_score in result.sample_scores:
                    prediction_data = {
                        "pmcid": sample_score.pmcid,
                        "overall_score": sample_score.overall_score,
                        "predictions": {
                            fs.field_name: fs.predicted for fs in sample_score.field_scores
                        },
                        "ground_truth": {
                            fs.field_name: fs.expected for fs in sample_score.field_scores
                        }
                    }
                    f.write(json.dumps(prediction_data) + '\n')
        
        elif format == "csv":
            output_path = self.output_dir / f"{filename}.csv"
            
            if result.sample_scores:
                # Get all field names
                field_names = list(set(
                    fs.field_name for sample_score in result.sample_scores 
                    for fs in sample_score.field_scores
                ))
                field_names.sort()
                
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    header = ['pmcid', 'overall_score', 'weighted_score']
                    for field in field_names:
                        header.extend([f"{field}_predicted", f"{field}_expected", f"{field}_score"])
                    writer.writerow(header)
                    
                    # Data rows
                    for sample_score in result.sample_scores:
                        row = [sample_score.pmcid, sample_score.overall_score, sample_score.weighted_score]
                        
                        # Create field lookup
                        field_lookup = {fs.field_name: fs for fs in sample_score.field_scores}
                        
                        for field in field_names:
                            if field in field_lookup:
                                fs = field_lookup[field]
                                row.extend([fs.predicted, fs.expected, fs.score])
                            else:
                                row.extend([None, None, 0.0])
                        
                        writer.writerow(row)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Predictions exported to {output_path}")
        return output_path
    
    def save_sample_analysis(self, analysis: Dict[str, Any]) -> Path:
        """Save detailed analysis of a single sample."""
        pmcid = analysis["pmcid"]
        model = analysis["model"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"sample_analysis_{pmcid}_{model}_{timestamp}.json"
        output_path = self.output_dir / "sample_analyses" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Sample analysis saved to {output_path}")
        return output_path