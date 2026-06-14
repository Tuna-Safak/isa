"""
filename: extractor.py
purpose: Read OCR text produced by `ocr.py`, extract blood marker values using
         regular expressions, determine units and reference ranges, compute
         status (normal/high/low), print results and save as JSON.
author: Tuna Safak
date: 2026-06-14
approach: Use conservative, documented regular expressions to find markers and
          nearby numeric tokens. This keeps the extractor simple and robust
          against OCR noise while producing structured data for downstream
          processing (e.g., analytics or reporting).

This file includes detailed comments, status prints, and try/except blocks
so the pipeline is transparent and failures are easy to diagnose.
"""

import os
import sys
import re
import json
from typing import Optional, Tuple


def ensure_output_dir(output_dir: str):
    """Create the output directory if missing.

    This mirrors the behavior in `ocr.py` so output files are always stored
    inside the project workspace.
    """
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Could not create output directory: {e}")
            raise


def parse_number(token: str) -> Optional[float]:
    """Extract a floating number from a token-like string.

    Accepts comma or dot as decimal separator and returns a float, or None
    if parsing fails. We look for the first numeric pattern to be robust
    against surrounding garbage introduced by OCR.
    """
    if not token:
        return None
    m = re.search(r"-?\d+[.,]?\d*", token)
    if not m:
        return None
    num_str = m.group(0).replace(',', '.')
    try:
        return float(num_str)
    except ValueError:
        return None


def find_reference_range(text: str) -> Optional[Tuple[float, float, str]]:
    """Find a reference range like '74 - 100' in a text snippet.

    Returns (low, high, raw_range_string) or None if not found.
    """
    m = re.search(r"(\d+(?:[.,]\d*)?)\s*[-–]\s*(\d+(?:[.,]\d*)?)", text)
    if not m:
        return None
    low = parse_number(m.group(1))
    high = parse_number(m.group(2))
    if low is None or high is None:
        return None
    raw = f"{m.group(1).replace(',', '.')} - {m.group(2).replace(',', '.')}"
    return (low, high, raw)


def extract_marker_from_lines(lines, start_idx, marker_name):
    """Attempt to extract value/unit/range for a marker searching nearby lines.

    We examine the line where the marker appears and the next two lines to
    increase robustness against OCR splitting relevant tokens across lines.
    """
    # Look up to 2 lines after the found line for value/unit/range
    window = " ".join(lines[start_idx:start_idx + 3])

    # 1) Try to find an explicit reference range in the window
    ref = find_reference_range(window)

    # 2) Try to find numbers in the window
    numbers = re.findall(r"-?\d+[.,]?\d*", window)
    value = None
    unit = None
    ref_str = None

    if numbers:
        # Heuristic: the first numeric token is usually the value
        value = parse_number(numbers[0])
        # If a range was found earlier, use it
        if ref:
            ref_str = ref[2]
        else:
            # If there are two numbers right after marker and no dash,
            # they might represent a range (min max) or value + upper bound;
            # try to interpret two adjacent numbers as a range if no explicit dash
            if len(numbers) >= 2:
                # If both numbers look like plausible ints and the second > first,
                # treat them as range and keep the first as value (best-effort).
                n1 = parse_number(numbers[0])
                n2 = parse_number(numbers[1])
                if n1 is not None and n2 is not None and n2 > n1:
                    ref_str = f"{numbers[0].replace(',', '.')} - {numbers[1].replace(',', '.')}"

    # 3) Try to find a unit token near the first numeric token
    # Common units in blood tests
    unit_match = re.search(r"(mg/dl|g/dl|g/l|%|Mio\.?/?ul|Mio\.?/ul|/ul|pg|fl|mmol/mol|mmol/L|mmol/l)", window, re.IGNORECASE)
    if unit_match:
        unit = unit_match.group(1)

    return value, unit, ref_str


def determine_status(value: Optional[float], low: Optional[float], high: Optional[float]) -> str:
    """Determine 'low', 'normal', or 'high' based on numeric low/high bounds.

    This version uses trusted numeric bounds (hardcoded) instead of parsing
    OCR-captured reference strings.
    """
    if value is None or low is None or high is None:
        return 'unknown'
    try:
        if value < low:
            return 'low'
        if value > high:
            return 'high'
        return 'normal'
    except Exception:
        return 'unknown'


def normalize_marker_key(key: str) -> str:
    """Normalize marker keys for consistent JSON output."""
    return key.strip()


def main():
    # Paths (project-root relative)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ocr_path = os.path.join(script_dir, 'output', 'ocr_output.txt')
    output_dir = os.path.join(script_dir, 'output')
    output_json = os.path.join(output_dir, 'extracted_values.json')

    print('Extractor started.')

    # Ensure output dir exists
    ensure_output_dir(output_dir)

    # Read OCR output
    try:
        print(f"Reading OCR text from: {ocr_path}")
        with open(ocr_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except Exception as e:
        print(f"ERROR: Could not read OCR output: {e}")
        sys.exit(1)

    # Split into lines for localized searching
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    # Markers to extract; include possible OCR variants for each name.
    markers = {
        'Leukozyten': r'Leukozyten',
        'Erythrozyten': r'Erythrozyten',
        'Haemoglobin': r'Haemoglobin|H[ae]moglobin|Hemoglobin',
        'Haematokrit': r'Haematokrit|Hematokrit|Hk',
        'MCV': r'\bMCV\b',
        'MCH': r'\bMCH\b',
        'MCHC': r'\bMCHC\b',
        'Thrombozyten': r'Thrombozyten',
        'HbA1c': r'HbA1[cl]|HbA1c|HbAlc|HbAl ce',
        'Blutzucker': r'Blutzucker|Blutzucker im Serum|Blutzucker im Serum'
    }

    # Hardcoded reference ranges (trusted values) and preferred units.
    # Using hardcoded ranges avoids relying on OCR-captured ranges which are noisy.
    reference_ranges = {
        'Leukozyten': {'low': 3.0, 'high': 10.0, 'unit': '/ul', 'ref': '3.0-10.0 /ul'},
        'Erythrozyten': {'low': 4.4, 'high': 5.9, 'unit': 'Mio./ul', 'ref': '4.4-5.9 Mio./ul'},
        'Haemoglobin': {'low': 11.8, 'high': 16.9, 'unit': 'g/dl', 'ref': '11.8-16.9 g/dl'},
        'Haematokrit': {'low': 35.0, 'high': 52.0, 'unit': '%', 'ref': '35-52 %'},
        'MCV': {'low': 80.0, 'high': 100.0, 'unit': 'fl', 'ref': '80-100 fl'},
        'MCH': {'low': 27.0, 'high': 34.0, 'unit': 'pg', 'ref': '27-34 pg'},
        'MCHC': {'low': 32.0, 'high': 36.0, 'unit': 'g/dl', 'ref': '32-36 g/dl'},
        'Thrombozyten': {'low': 130.0, 'high': 400.0, 'unit': 'Tsd/ul', 'ref': '130-400 Tsd/ul'},
        'HbA1c': {'low': 4.5, 'high': 5.6, 'unit': '%', 'ref': '4.5-5.6 %'},
        'Blutzucker': {'low': 74.0, 'high': 100.0, 'unit': 'mg/dl', 'ref': '74-100 mg/dl'}
    }

    results = []

    # Iterate over markers and search the text
    for key, pattern in markers.items():
        print(f"Searching for marker: {key}")
        compiled = re.compile(pattern, re.IGNORECASE)
        found = False

        for idx, line in enumerate(lines):
            if compiled.search(line):
                found = True
                try:
                    # Extract tentative value and unit from nearby text
                    value, detected_unit, _ = extract_marker_from_lines(lines, idx, key)

                    # Choose the reference range for this marker
                    ref = reference_ranges.get(key)

                    # Prefer the trusted, hardcoded unit from the reference ranges
                    # because OCR often misreads unit symbols (e.g. '%' instead of 'g/dl').
                    unit = ref.get('unit') if ref else (detected_unit if detected_unit else None)

                    # If multiple numeric candidates exist, `extract_marker_from_lines`
                    # returns the first. Improve selection by checking closeness to
                    # the expected reference range center when available.
                    if ref and value is not None:
                        # If value is wildly outside a plausible extended window,
                        # try to find a better candidate in the window.
                        low = ref['low']
                        high = ref['high']
                        window = " ".join(lines[idx:idx+3])
                        candidates = re.findall(r"-?\d+[.,]?\d*", window)
                        best = value
                        best_score = float('inf')
                        mid = (low + high) / 2.0
                        for c in candidates:
                            cv = parse_number(c)
                            if cv is None:
                                continue
                            # scale factor: accommodate units like "Mio./ul" vs plain numbers
                            # but here we assume numbers are comparable to reference ranges
                            score = abs(cv - mid)
                            if score < best_score:
                                best_score = score
                                best = cv
                        value = best

                    # Determine status using hardcoded references if available
                    if ref and value is not None:
                        status = determine_status(value, ref['low'], ref['high'])
                        ref_str = ref['ref']
                    else:
                        status = 'unknown'
                        ref_str = None

                    record = {
                        'marker': normalize_marker_key(key),
                        'value': value,
                        'unit': unit,
                        'reference': ref_str,
                        'status': status
                    }

                    results.append(record)

                    # Print found marker
                    print(f"Found: {record}")
                except Exception as e:
                    print(f"Warning: error extracting {key}: {e}")
                # Only consider the first occurrence per marker
                break

        if not found:
            print(f"Marker not found in text: {key}")

    # Save results to JSON
    try:
        print(f"Saving extracted values to: {output_json}")
        with open(output_json, 'w', encoding='utf-8') as out:
            json.dump(results, out, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to save JSON: {e}")
        sys.exit(1)

    print('Extraction complete.')


if __name__ == '__main__':
    main()
