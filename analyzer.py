"""
filename: analyzer.py
purpose: Analyze blood test CSV, compute % deviation from reference center,
         assign risk levels, and save enriched results to CSV.
author: Tuna Safak
date: 2026-06-14
decision_rationale: Using pandas simplifies tabular analysis and enables
  concise computations. We parse trusted hardcoded references written by the
  extractor/exporter pipeline, compute percent deviations and risk levels,
  and produce a CSV for downstream reporting.

This script includes clear status prints, comments for each step, and
try/except error handling to make the pipeline robust and transparent.
"""

import os
import sys
import re
import pandas as pd
from typing import Tuple, Optional


def ensure_output_dir(output_dir: str):
    """Ensure the output directory exists; create it if necessary."""
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Could not create output directory: {e}")
            raise


def parse_reference(ref: str) -> Optional[Tuple[float, float]]:
    """Parse a reference string like '74-100 mg/dl' and return (low, high).

    Handles comma or dot decimals and ignores trailing units.
    Returns None on failure.
    """
    if not isinstance(ref, str):
        return None
    m = re.search(r"(\d+[\.,]?\d*)\s*[-–]\s*(\d+[\.,]?\d*)", ref)
    if not m:
        return None
    try:
        low = float(m.group(1).replace(',', '.'))
        high = float(m.group(2).replace(',', '.'))
        return low, high
    except Exception:
        return None


def infer_default_reference(marker: str) -> Optional[Tuple[float, float]]:
    marker_key = (marker or "").strip().lower()

    if "hdl" in marker_key:
        return 40.0, None
    if "ldl" in marker_key:
        return None, 130.0
    if "cholesterin" in marker_key:
        return None, 200.0
    if "triglycerid" in marker_key:
        return None, 150.0
    if "kreatinin" in marker_key:
        return None, 1.2
    if "calcium" in marker_key:
        return 2.1, 2.55
    if "glukose" in marker_key or "glucose" in marker_key:
        return 70.0, 100.0
    if "hba1c" in marker_key:
        return None, 5.7
    if "gpt" in marker_key or "alat" in marker_key or "alt" in marker_key:
        return None, 50.0
    if "gamma" in marker_key or "gt" in marker_key:
        return None, 50.0
    if "kalium" in marker_key:
        return 3.5, 5.1
    if "natrium" in marker_key:
        return 136.0, 145.0

    return None


def compute_deviation_and_risk(value: float, low: Optional[float], high: Optional[float]) -> Tuple[float, str]:
    """Compute % deviation and assign a risk level from optional low/high bounds."""
    if low is None and high is None:
        return 0.0, 'unknown'

    if low is not None and high is not None:
        center = (low + high) / 2.0
        pct_dev = (value - center) / center * 100.0 if center != 0 else 0.0

        if value > 1.5 * high:
            return pct_dev, 'critical'
        if value < 0.5 * low:
            return pct_dev, 'critical'
        if value > high:
            return pct_dev, 'high'
        if value < low:
            return pct_dev, 'low'
        if abs(value - low) / max(low, 1e-9) <= 0.10 or abs(high - value) / max(high, 1e-9) <= 0.10:
            return pct_dev, 'borderline'
        return pct_dev, 'normal'

    if high is not None:
        pct_dev = ((value - high) / high) * 100.0 if high else 0.0
        if value > high:
            return pct_dev, 'high'
        if abs(high - value) / max(high, 1e-9) <= 0.10:
            return pct_dev, 'borderline'
        return pct_dev, 'normal'

    if low is not None:
        pct_dev = ((value - low) / low) * 100.0 if low else 0.0
        if value < low:
            return pct_dev, 'low'
        if abs(value - low) / max(low, 1e-9) <= 0.10:
            return pct_dev, 'borderline'
        return pct_dev, 'normal'

    return 0.0, 'unknown'


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, 'output', 'bloodtest_results.csv')
    output_csv = os.path.join(script_dir, 'output', 'analysis_results.csv')
    output_dir = os.path.join(script_dir, 'output')

    print('Analyzer started.')

    # Ensure output directory exists
    try:
        ensure_output_dir(output_dir)
    except Exception:
        sys.exit(1)

    # Read CSV
    try:
        print(f"Reading CSV: {input_csv}")
        df = pd.read_csv(input_csv, dtype={'marker': str, 'value': float, 'unit': str, 'reference': str, 'status': str})
    except Exception as e:
        print(f"ERROR: Failed to read CSV: {e}")
        sys.exit(1)

    # Parse references and compute metrics
    lows = []
    highs = []
    pct_devs = []
    risk_levels = []

    for idx, row in df.iterrows():
        ref = row.get('reference', '')
        val = row.get('value', None)

        parsed = parse_reference(ref)
        if parsed is None and val is not None:
            parsed = infer_default_reference(row.get('marker', ''))

        if parsed and val is not None:
            low, high = parsed
            pct_dev, risk = compute_deviation_and_risk(float(val), low, high)
        else:
            # If parsing failed, mark unknowns
            low, high = None, None
            pct_dev, risk = 0.0, 'unknown'

        lows.append(low)
        highs.append(high)
        pct_devs.append(round(pct_dev, 2))
        risk_levels.append(risk)

    # Attach computed columns
    df['ref_min'] = lows
    df['ref_max'] = highs
    df['pct_deviation_from_center'] = pct_devs
    df['risk_level'] = risk_levels

    # Save enriched CSV
    try:
        print(f"Saving analysis CSV: {output_csv}")
        df.to_csv(output_csv, index=False, encoding='utf-8')
    except Exception as e:
        print(f"ERROR: Failed to write analysis CSV: {e}")
        sys.exit(1)

    # Print summary table
    try:
        display_cols = ['marker', 'value', 'reference', 'pct_deviation_from_center', 'risk_level']
        print('\nAnalysis Summary:')
        print(df[display_cols].to_string(index=False))
    except Exception as e:
        print(f"Warning: Could not print summary table: {e}")

    print('Analyzer finished successfully.')


if __name__ == '__main__':
    main()
