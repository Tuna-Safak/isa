"""
Read OCR text from a .txt file, extract likely blood test rows, and save them
as a clean CSV at output/bloodtest_results.csv.
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


UNIT_PATTERN = r"(?:mg/dl|g/dl|g/l|mmol/l|mmol/mol|nmol/l|µmol/l|umol/l|ng/ml|µg/l|ug/l|u/l|iu/l|u?iu/ml|u?iu/l|miu/l|miu/ml|pg|fl|%|t/l|mio\.?/ul|/ul)"

MARKER_PATTERNS = [
    r"\b(gpt|alat|alt)\b",
    r"\b(got|ast)\b",
    r"\bgamma[-\s]?gt\b",
    r"\b(ldh|laktatdehydrogenase)\b",
    r"\bcholesterin\b",
    r"\bhdl[-\s]?cholesterin\b",
    r"\blldl[-\s]?cholesterin\b",
    r"\bldl[-\s]?cholesterin\b",
    r"\bgesamt[-\s]?cholesterin\b",
    r"\btriglyceride\b",
    r"\bkreatinin\b",
    r"\begfr\b",
    r"\bharnstoff\b",
    r"\bharnsäure\b",
    r"\bkalium\b",
    r"\bnatrium\b",
    r"\bchlorid\b",
    r"\bcalcium\b",
    r"\bmagnesium\b",
    r"\banionen[-\s]?lücke\b",
    r"\bglukose\b",
    r"\bglucose\b",
    r"\bhba1c\b",
    r"\binsulin\b",
    r"\bcrp\b",
    r"\bhs[-\s]?crp\b",
    r"\bferritin\b",
    r"\beisen\b",
    r"\btransferrin\b",
    r"\bvitamin\s*b12\b",
    r"\bfolsäure\b",
    r"\btsh\b",
    r"\bfT4\b",
    r"\bfT3\b",
    r"\bleukozyten\b",
    r"\berythrozyten\b",
    r"\bhaemoglobin\b",
    r"\bhemoglobin\b",
    r"\bhb\b",
    r"\bthrombozyten\b",
    r"\balbumin\b",
    r"\bgesamtprotein\b",
    r"\bprotein\b",
    r"\bbilirubin\b",
    r"\balkalische\s+phosphatase\b",
]
MARKER_REGEX = re.compile("|".join(MARKER_PATTERNS), re.IGNORECASE)


def ensure_output_dir(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"ERROR: Could not create output directory: {exc}")
        raise


def read_ocr_text(txt_path: Path) -> str:
    try:
        return txt_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return txt_path.read_text(encoding="latin-1")


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("mg/dAl", "mg/dl")
    text = text.replace("mg/dAI", "mg/dl")
    text = re.sub(r"[“”„‟´`'’]", "", text)
    text = re.sub(r"[|§]", " ", text)
    text = re.sub(r"[\[\]{}()]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_marker(marker: str) -> str:
    marker = clean_text(marker)
    marker = re.sub(r"\s+", " ", marker).strip(" -:")
    marker = re.sub(r"\bgamma\s+gt\b", "Gamma-GT", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\bhdl\s+cholesterin\b", "HDL-Cholesterin", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\bldl\s+cholesterin\b", "LDL-Cholesterin", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\bgpt\b", "GPT", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\balat\b", "ALAT", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\bgot\b", "GOT", marker, flags=re.IGNORECASE)
    marker = re.sub(r"\bast\b", "AST", marker, flags=re.IGNORECASE)
    return marker


def is_valid_lab_line(line: str) -> bool:
    line = clean_text(line)
    if len(line) < 6:
        return False
    marker_match = MARKER_REGEX.search(line)
    has_value = bool(re.search(r"\d+(?:[.,]\d+)?", line))
    has_unit = bool(re.search(UNIT_PATTERN, line, flags=re.IGNORECASE))
    has_reference = bool(re.search(r"(?:<|>|-|–)\s*\d|\d\s*-\s*\d", line))
    return bool(marker_match) and has_value and (has_unit or has_reference)


def filter_valid_lab_lines(raw_text: str) -> list[str]:
    lines = []
    for raw_line in raw_text.splitlines():
        line = clean_text(raw_line)
        if not line:
            continue
        if is_valid_lab_line(line):
            lines.append(line)
    return lines


def extract_row(line: str) -> Optional[Dict[str, str]]:
    line = clean_text(line)

    marker_match = MARKER_REGEX.search(line)
    if not marker_match:
        return None

    match = re.match(
        rf"^(?P<marker>.*?{MARKER_REGEX.pattern}.*?)\s+(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>{UNIT_PATTERN})?\s*(?P<reference>.*)$",
        line,
        flags=re.IGNORECASE,
    )

    if not match:
        value_match = re.search(r"(?P<value>-?\d+(?:[.,]\d+)?)", line)
        if not value_match:
            return None
        value_start = value_match.start("value")
        marker = line[:value_start]
        remainder = line[value_start:]
        unit_match = re.match(
            rf"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<unit>{UNIT_PATTERN})?\s*(?P<reference>.*)$",
            remainder,
            flags=re.IGNORECASE,
        )
        if not unit_match:
            return None
        value = unit_match.group("value").replace(",", ".")
        unit = unit_match.group("unit") or ""
        reference = clean_text(unit_match.group("reference"))
    else:
        marker = clean_text(match.group("marker"))
        value = match.group("value").replace(",", ".")
        unit = match.group("unit") or ""
        reference = clean_text(match.group("reference"))

    marker = normalize_marker(marker)

    if not marker:
        return None

    marker = re.sub(r"^[^A-Za-zÄÖÜäöüß0-9]+", "", marker)
    marker = re.sub(r"\s+", " ", marker).strip(" -:")

    if not marker:
        return None

    if unit:
        unit = unit.replace("Mio./ul", "Mio./ul").replace("mio./ul", "Mio./ul")
        unit = unit.replace("mg/dAI", "mg/dl").replace("mg/dAl", "mg/dl")
        unit = unit.replace("IU/L", "u/l")
        unit = unit.replace("iu/l", "u/l")

    if not reference:
        reference = ""

    return {
        "marker": marker,
        "value": value,
        "unit": unit,
        "reference": reference,
    }


def parse_ocr_text(raw_text: str) -> list[dict]:
    rows = []
    for line in filter_valid_lab_lines(raw_text):
        try:
            row = extract_row(line)
            if row:
                rows.append(row)
        except Exception as exc:
            print(f"Skipping line due to parse error: {line}")
            print(f"Reason: {exc}")
    deduped = []
    seen = set()
    for row in rows:
        key = (row["marker"].lower(), row["value"], row["unit"].lower(), row["reference"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def write_csv(records: list[dict], csv_path: Path) -> None:
    fieldnames = ["marker", "value", "unit", "reference"]
    try:
        with csv_path.open("w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    except Exception as exc:
        print(f"ERROR: Could not write CSV: {exc}")
        raise


def print_rows(records: list[dict]) -> None:
    if not records:
        print("No blood test rows found.")
        return

    print("\nExtracted rows:\n")
    for record in records:
        print(
            f"{record['marker']} | {record['value']} | {record['unit']} | {record['reference']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract blood test rows from OCR text and save CSV.")
    parser.add_argument("input_txt", help="Path to OCR .txt file")
    parser.add_argument(
        "-o",
        "--output",
        default="output/bloodtest_results.csv",
        help="Output CSV path",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_txt)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    if input_path.suffix.lower() != ".txt":
        print("Please provide a .txt OCR file.")
        sys.exit(1)

    try:
        raw_text = read_ocr_text(input_path)
        records = parse_ocr_text(raw_text)

        ensure_output_dir(output_path.parent)
        write_csv(records, output_path)

        print_rows(records)
        print(f"\nSaved CSV: {output_path}")
    except Exception as exc:
        print(f"Extractor failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
