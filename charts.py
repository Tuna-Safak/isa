"""
filename: charts.py
purpose: Create visualizations from `output/analysis_results.csv` and save
         three charts to the `output/` folder: a bar chart, a deviation chart,
         and a status pie chart.
author: Tuna Safak
date: 2026-06-14
decision_rationale: Matplotlib provides flexible control for publication-quality
  PNG charts. We color-code risk levels and deviations to make results easy
  to interpret at a glance. Charts are sized to 10x6 inches for consistency.

This script uses pandas to load the enriched analysis CSV produced by
`analyzer.py`, generates the three requested charts, and writes them to
`output/` with clear status messages and error handling.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def ensure_output_dir(output_dir: str):
    """Create the output directory if it does not exist."""
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Could not create output directory: {e}")
            raise


def bar_chart(df, out_path):
    """Create bar chart of marker values colored by risk_level.

    Each bar is colored by the `risk_level` column. A small horizontal line
    segment is drawn above each bar to indicate the reference maximum value
    for that marker (ref_max).
    """
    print(f"Creating bar chart: {out_path}")
    try:
        plt.figure(figsize=(10, 6))
        markers = df['marker'].tolist()
        values = df['value'].astype(float).tolist()
        ref_max = pd.to_numeric(df['ref_max'], errors='coerce').tolist()

        # Color mapping for risk levels
        color_map = {'normal': 'green', 'borderline': 'orange', 'high': 'red', 'critical': 'darkred', 'unknown': 'gray'}
        colors = [color_map.get(r, 'gray') for r in df['risk_level'].fillna('unknown')]

        x = np.arange(len(markers))
        bars = plt.bar(x, values, color=colors, edgecolor='black')

        # Draw small horizontal line segments showing ref_max for each marker
        for i, rm in enumerate(ref_max):
            if rm is not None and not np.isnan(rm):
                plt.hlines(rm, i - 0.4, i + 0.4, colors='blue', linestyles='dashed', linewidth=1)

        plt.xticks(x, markers, rotation=45, ha='right')
        plt.ylabel('Value')
        plt.title('Blood Test Results — April 2021')
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        print(f"Saved: {out_path}")
    except Exception as e:
        print(f"ERROR creating bar chart: {e}")
        raise


def deviation_chart(df, out_path):
    """Create horizontal bar chart of percent deviations from center.

    Bars are colored by absolute deviation thresholds:
    - <30%: green
    - 30-50%: orange
    - >50%: red
    A vertical line at x=0 marks the center of the reference range.
    """
    print(f"Creating deviation chart: {out_path}")
    try:
        plt.figure(figsize=(10, 6))
        df_sorted = df.sort_values('pct_deviation_from_center')
        markers = df_sorted['marker']
        deviations = df_sorted['pct_deviation_from_center'].astype(float)

        abs_dev = deviations.abs()
        colors = []
        for a in abs_dev:
            if a < 30:
                colors.append('green')
            elif 30 <= a <= 50:
                colors.append('orange')
            else:
                colors.append('red')

        y_positions = np.arange(len(markers))
        plt.barh(y_positions, deviations, color=colors, edgecolor='black')
        plt.yticks(y_positions, markers)
        plt.xlabel('% Deviation from Center')
        plt.title('Deviation from Reference Range Center')
        plt.axvline(0, color='black', linewidth=1)
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        print(f"Saved: {out_path}")
    except Exception as e:
        print(f"ERROR creating deviation chart: {e}")
        raise


def status_pie_chart(df, out_path):
    """Create a pie chart showing counts per risk_level/status."""
    print(f"Creating status pie chart: {out_path}")
    try:
        plt.figure(figsize=(10, 6))
        # Count risk levels
        counts = df['risk_level'].fillna('unknown').value_counts()
        labels = counts.index.tolist()
        sizes = counts.values.tolist()

        # Define colors for known labels; unknowns get gray
        color_map = {'normal': 'green', 'borderline': 'orange', 'high': 'red', 'critical': 'darkred', 'unknown': 'gray'}
        colors = [color_map.get(lbl, 'gray') for lbl in labels]

        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90)
        plt.title('Overall Risk Distribution')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        print(f"Saved: {out_path}")
    except Exception as e:
        print(f"ERROR creating status pie chart: {e}")
        raise


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, 'output', 'analysis_results.csv')
    output_dir = os.path.join(script_dir, 'output')

    # Paths for output images
    bar_path = os.path.join(output_dir, 'bar_chart.png')
    deviation_path = os.path.join(output_dir, 'deviation_chart.png')
    pie_path = os.path.join(output_dir, 'status_pie.png')

    print('Charts generator started.')

    # Ensure output dir exists
    try:
        ensure_output_dir(output_dir)
    except Exception:
        sys.exit(1)

    # Read analysis CSV
    try:
        print(f"Reading analysis CSV: {input_csv}")
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"ERROR: Could not read analysis CSV: {e}")
        sys.exit(1)

    # Generate charts
    try:
        bar_chart(df, bar_path)
        deviation_chart(df, deviation_path)
        status_pie_chart(df, pie_path)
    except Exception:
        print('ERROR: One or more charts failed to generate.')
        sys.exit(1)

    print('Charts generated successfully.')


if __name__ == '__main__':
    main()
