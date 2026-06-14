# 🩸 Blood Test Pipeline — ISA Project

An automated pipeline that converts blood test images into structured data, visual charts, and a PowerPoint report — fully automated in one command.

## Overview
This project was built for the ISA (Information System Architecture) course. It reads a blood test image using OCR, extracts relevant markers, analyzes them against reference ranges, generates charts, and produces a PowerPoint report — all under ~5 seconds on a typical laptop.

## Quickstart

1. Install dependencies

```bash
pip install -r requirements.txt
brew install tesseract        # macOS only
brew install tesseract-lang   # language packs
```

2. Run the full pipeline

```bash
python3 pipeline.py
```

## Project Structure

```
ISA/isa/
├── pipeline.py          # Main pipeline (runs all steps in order)
├── ocr.py               # Step 1: OCR image → raw text
├── extractor.py         # Step 2: Parse raw text → JSON
├── exporter.py          # Step 3: JSON → CSV
├── analyzer.py          # Step 4: Analyze values (normal / low / high)
├── charts.py            # Step 5: Generate charts
├── report.py            # Step 6: Build PowerPoint report
├── requirements.txt     # Python dependencies
└── output/
    ├── ocr_output.txt
    ├── extracted_values.json
    ├── bloodtest_results.csv
    ├── analysis_results.csv
    ├── bar_chart.png
    ├── deviation_chart.png
    ├── status_pie.png
    └── blood_test_report.pptx
```

## Pipeline Steps

| Step | Script | Input | Output |
|---|---|---|---|
| 1 | `ocr.py` | `bloodtest.jpg` | `ocr_output.txt` |
| 2 | `extractor.py` | `ocr_output.txt` | `extracted_values.json` |
| 3 | `exporter.py` | `extracted_values.json` | `bloodtest_results.csv` |
| 4 | `analyzer.py` | `bloodtest_results.csv` | `analysis_results.csv` |
| 5 | `charts.py` | `analysis_results.csv` | `bar_chart.png`, `deviation_chart.png`, `status_pie.png` |
| 6 | `report.py` | all outputs | `blood_test_report.pptx` |

## Requirements

Install the Python dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

Packages used:

- pytesseract
- Pillow
- pandas
- matplotlib
- python-pptx
- opencv-python

## Output Example

- 10 blood markers extracted per image
- 3 charts generated automatically (bar, deviation, pie)
- 1 PowerPoint report ready to present
- Total processing time: ~4 seconds (on tested hardware)

## Known Issues & Fixes

| Problem | Fix |
|---|---|
| tesseract not found | Run `brew install tesseract` (macOS) or install Tesseract by your platform's package manager |
| OCR reads values incorrectly | Improve preprocessing (binarization, denoising), adjust Tesseract settings, or add custom parsing heuristics |
| Reference ranges not recognized | We use hardcoded trusted reference ranges to avoid OCR noise |
| CSV encoding issues with special characters | Files are written using `encoding='utf-8'` |
| Pipeline breaks on error | All steps wrapped in `try/except` and pipeline aborts with helpful messages |

## Course Info

Course: ISA — Intelligent System Automation
Project: Automated Blood Test Analysis Pipeline
Completion: June 2026

---
Created by Tuna Safak for the ISA course.
