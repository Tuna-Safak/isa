"""
filename: exporter.py
purpose: Read extracted blood marker JSON and export to CSV for reporting/analysis.
author: Tuna Safak
date: 2026-06-14
decision_rationale: CSV is a widely supported tabular format suitable for
  spreadsheets, data analysis, and import into downstream systems. We use
  UTF-8 encoding and explicit column ordering to ensure consistency.

This script follows the same documentation and error-handling style as the
other pipeline scripts (`ocr.py`, `extractor.py`). It creates the `output/`
folder if missing, reads `output/extracted_values.json`, writes
`output/bloodtest_results.csv`, and prints confirmations.
"""

import os
import sys
import json
import csv
from typing import List, Dict


def ensure_output_dir(output_dir: str):
    """Create the output directory if it does not exist.

    This prevents write errors when saving CSV and mirrors behavior used
    across other pipeline scripts.
    """
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Could not create output directory: {e}")
            raise


def read_json(path: str) -> List[Dict]:
    """Read JSON file and return a list of records.

    We use UTF-8 to correctly handle German umlauts and ensure predictable
    parsing by expecting a list-of-objects layout created by `extractor.py`.
    """
    try:
        print(f"Reading extracted data from: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError('Expected JSON to be a list of marker objects')
        return data
    except Exception as e:
        print(f"ERROR: Failed to read JSON file: {e}")
        raise


def write_csv(records: List[Dict], csv_path: str):
    """Write records to CSV with fixed column order.

    Column order: marker, value, unit, reference, status
    We write numeric values as-is and ensure consistent quoting for text.
    """
    fieldnames = ['marker', 'value', 'unit', 'reference', 'status']
    try:
        print(f"Writing CSV to: {csv_path}")
        with open(csv_path, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for rec in records:
                # Ensure we only write the expected fields. Missing keys are
                # written as empty strings to avoid exceptions.
                row = {k: rec.get(k, '') for k in fieldnames}
                writer.writerow(row)
        print(f"Saved CSV: {csv_path}")
    except Exception as e:
        print(f"ERROR: Failed to write CSV: {e}")
        raise


def main():
    # File paths relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    json_path = os.path.join(output_dir, 'extracted_values.json')
    csv_path = os.path.join(output_dir, 'bloodtest_results.csv')

    print('Exporter started.')

    # Ensure output directory exists
    try:
        ensure_output_dir(output_dir)
    except Exception:
        sys.exit(1)

    # Read extracted JSON
    try:
        records = read_json(json_path)
    except Exception:
        sys.exit(1)

    # Write CSV
    try:
        write_csv(records, csv_path)
    except Exception:
        sys.exit(1)

    # Print confirmation for created files
    print(f"Confirmed: JSON input read: {json_path}")
    print(f"Confirmed: CSV output saved: {csv_path}")


if __name__ == '__main__':
    main()
