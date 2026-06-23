"""
Extract structured blood test rows from OCR text and save them as CSV and JSON.

Input:
    python3 extractor.py <ocr_text_file.txt>

Output:
    output/bloodtest_results.csv
    output/bloodtest_results.json
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


OUTPUT_DIR = Path("output")
CSV_PATH = OUTPUT_DIR / "bloodtest_results.csv"
JSON_PATH = OUTPUT_DIR / "bloodtest_results.json"

UNIT_PATTERN = r"(?:mg/dl|g/dl|g/l|mmol/l|mmol/mol|nmol/l|µmol/l|umol/l|ng/ml|µg/l|ug/l|u/l|iu/l|u?iu/ml|u?iu/l|miu/l|miu/ml|pg|fl|%|t/l|mio\.?/ul|/ul)"

MARKER_PATTERNS = [
    r"\b(gpt|alat|alt)\b",
    r"\b(got|ast)\b",
    r"\bgamma[-\s]?gt\b",
    r"\b(ldh|laktatdehydrogenase)\b",
    r"\bcholesterin\b",
    r"\bhdl[-\s]?cholesterin\b",
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
    r"\bft4\b",
    r"\bft3\b",
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


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("mg/dAl", "mg/dl")
    text = text.replace("mg/dAI", "mg/dl")
    text = re.sub(r"[“”„‟´`'’]", "", text)
    text = re.sub(r"[|§]", " ", text)
    text = re.sub(r"[\[\]{}()]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_numeric_token(token: str) -> str:
    token = token.strip().replace(",", ".")
    token = re.sub(r"^[aA](\d)", r"4\1", token)
    token = re.sub(r"^[oO](\d)", r"0\1", token)
    token = re.sub(r"^[lI](\d)", r"1\1", token)
    return token


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
    has_marker = bool(MARKER_REGEX.search(line))
    has_value = bool(re.search(r"[aAoOlI]?\d+(?:[.,]\d+)?", line))
    has_unit = bool(re.search(UNIT_PATTERN, line, flags=re.IGNORECASE))
    has_reference = bool(re.search(r"(?:<|>|-|–)\s*\d|\d\s*-\s*\d", line))
    return has_marker and has_value and (has_unit or has_reference)


def filter_valid_lab_lines(raw_text: str) -> List[str]:
    lines: List[str] = []
    for raw_line in raw_text.splitlines():
        line = clean_text(raw_line)
        if line and is_valid_lab_line(line):
            lines.append(line)
    return lines


def parse_line(line: str) -> Optional[Dict[str, str]]:
    line = clean_text(line)
    marker_match = MARKER_REGEX.search(line)
    if not marker_match:
        return None

    value_match = re.search(r"(?P<value>-?[aAoOlI]?\d+(?:[.,]\d+)?)", line)
    if not value_match:
        return None

    value = normalize_numeric_token(value_match.group("value"))
    marker = normalize_marker(line[: value_match.start("value")])
    marker = re.sub(r"^[^A-Za-zÄÖÜäöüß0-9]+", "", marker).strip(" -:")
    if not marker:
        return None

    tail = clean_text(line[value_match.end("value") :])
    unit_match = re.match(
        rf"^(?P<unit>{UNIT_PATTERN})?\s*(?P<reference>.*)$",
        tail,
        flags=re.IGNORECASE,
    )
    unit = ""
    reference = ""
    if unit_match:
        unit = unit_match.group("unit") or ""
        reference = clean_text(unit_match.group("reference") or "")

    if unit:
        unit = unit.replace("mio./ul", "Mio./ul").replace("Mio./ul", "Mio./ul")
        unit = unit.replace("mg/dAI", "mg/dl").replace("mg/dAl", "mg/dl")
        unit = unit.replace("IU/L", "u/l").replace("iu/l", "u/l")

    if not reference:
        reference = ""

    return {
        "marker": marker,
        "value": value,
        "unit": unit,
        "reference": reference,
    }


def parse_ocr_text(raw_text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for line in filter_valid_lab_lines(raw_text):
        try:
            row = parse_line(line)
            if row:
                rows.append(row)
        except Exception as exc:
            print(f"Skipping line due to parse error: {line}")
            print(f"Reason: {exc}")

    deduped: List[Dict[str, str]] = []
    seen = set()
    for row in rows:
        key = (
            row["marker"].lower(),
            row["value"],
            row["unit"].lower(),
            row["reference"].lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def write_csv(records: List[Dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["marker", "value", "unit", "reference"])
        writer.writeheader()
        writer.writerows(records)


def write_json(records: List[Dict[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as jsonfile:
        json.dump(records, jsonfile, ensure_ascii=False, indent=2)


def print_summary(records: List[Dict[str, str]]) -> None:
    if not records:
        print("No blood test rows found.")
        return

    print("\nExtracted rows:\n")
    for row in records:
        print(f"{row['marker']} | {row['value']} | {row['unit']} | {row['reference']}")

    print(f"\nSummary: {len(records)} rows extracted.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract blood test rows from OCR text and save CSV/JSON.")
    parser.add_argument("input_txt", help="Path to OCR .txt file")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input_txt)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() != ".txt":
        print("Please provide a .txt OCR file.")
        sys.exit(1)

    try:
        ensure_output_dir(OUTPUT_DIR)
        raw_text = read_text_file(input_path)
        records = parse_ocr_text(raw_text)
        write_csv(records, CSV_PATH)
        write_json(records, JSON_PATH)
        print_summary(records)
        print(f"\nSaved CSV: {CSV_PATH}")
        print(f"Saved JSON: {JSON_PATH}")
    except Exception as exc:
        print(f"Extractor failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
