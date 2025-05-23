# visualization.py
import matplotlib.pyplot as plt

def plot_match_rates(match_stats):
    """Plot match rates for different categories."""
    match_fields = ['Gene', 'Drug', 'Phenotype', 'Significance', 'Variant']
    match_rates = [
        match_stats['gene_match_rate'],
        match_stats['drug_match_rate'],
        match_stats['phenotype_match_rate'],
        match_stats['significance_match_rate'],
        match_stats['variant_match_rate']
    ]
    plt.figure(figsize=(8, 6))
    plt.bar(match_fields, match_rates, color=['#004B8D', '#175E54', '#8C1515', '#F58025', '#5D4B3C'])
    plt.title('Exact Match Rates by Category', fontweight='bold', fontsize=14)
    plt.ylabel('Match Rate (%)', fontweight="bold")
    plt.xlabel('Category', fontweight='bold')
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()

def plot_pie_charts(match_stats):
    """Plot pie charts for exact and partial match rates."""
    sizes_partial = [match_stats['partial_match_rate'], 100 - match_stats['partial_match_rate']]
    colors_partial = ['#175E54', 'none']
    sizes_exact = [match_stats['exact_match_rate'], 100 - match_stats['exact_match_rate']]
    colors_exact = ['#8C1515', 'none']
    plt.figure(figsize=(8, 8))
    plt.pie(sizes_partial, colors=colors_partial, startangle=90, radius=1.0, wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
    plt.pie(sizes_exact, colors=colors_exact, startangle=90, radius=0.7, wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
    legend_labels = [f"Partial Match ({round(match_stats['partial_match_rate'], 2)}%)", f"Exact Match ({round(match_stats['exact_match_rate'], 3)}%)"]
    legend_colors = ['#175E54', '#8C1515']
    plt.legend(handles=[plt.Line2D([0], [0], color=c, lw=6) for c in legend_colors], labels=legend_labels, loc='upper right', fontsize=10, frameon=True, title="Match Types", title_fontsize=12)
    plt.title('Exact vs Partial Match Rates', fontweight="bold", fontsize=14, pad=20)
    plt.tight_layout()
    plt.show()

def plot_grouped_match_rates(average_gene_match_rate, average_drug_match_rate, average_variant_match_rate):
    """Plot match rates grouped by PMID."""
    categories = ['Gene', 'Drug', 'Variant']
    match_rates = [average_gene_match_rate * 100, average_drug_match_rate * 100, average_variant_match_rate * 100]
    colors = ['#8C1515', '#175E54', '#F58025']
    plt.figure(figsize=(10, 6))
    bars = plt.bar(categories, match_rates, color=colors, edgecolor='black', linewidth=1.2)
    for bar, rate in zip(bars, match_rates):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f'{rate:.1f}%', ha='center', fontweight="bold", fontsize=10, color='black')
    plt.title('Match Rates by Category (Grouped by PMID)', fontweight="bold", fontsize=14, pad=20)
    plt.ylabel('Match Rate (%)', fontweight="bold", fontsize=12)
    plt.xlabel('Categories', fontweight="bold", fontsize=12)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()

def plot_attribute_match_rates(wholecsv):
    """Plot match statistics for different attributes."""
    match_columns = ['Match metabolizer', 'Match significance', 'Match all drug', 'Match Any Drug', 'Match gene', 'Match phenotype', 'Match population']
    match_stats_new = wholecsv[match_columns].mean() * 100
    plt.figure(figsize=(10, 6))
    plt.bar(match_stats_new.index, match_stats_new.values, color=['#2E8B57', '#4682B4', '#6A5ACD', '#D2691E', '#556B2F', '#8B4513', '#2F4F4F'])
    plt.title('Match Statistics for Different Attributes', fontsize=16)
    plt.ylabel('Match Percentage (%)', fontsize=12)
    plt.xlabel('Attributes', fontsize=12)
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()
    return match_stats_new.reset_index().rename(columns={'index': 'Attribute', 0: 'Match Percentage'})