"""
filename: pipeline.py
purpose: Run the full OCR -> extraction -> export -> analysis -> charts -> report
         pipeline in sequence. Prints clear status messages before and after
         each step, measures total duration, and aborts on errors.
author: Tuna Safak
date: 2026-06-14
approach: Import each module and call its `main()` function. Each step is
          wrapped in try/except so failures are reported immediately and the
          pipeline stops with a helpful message. We measure total runtime and
          print a completion message when successful.
"""

import time
import sys
import traceback


def run_step(step_no: int, name: str, func):
    """Run a single pipeline step and handle errors.

    Prints a start message, executes `func()` and prints success. On
    exception, prints the traceback and exits the process with non-zero code.
    """
    print(f">>> STEP {step_no}: {name} — Starting...")
    try:
        func()
        print(f"✓ STEP {step_no} complete")
    except Exception as e:
        print(f"✗ STEP {step_no} FAILED: {e}")
        print(traceback.format_exc())
        print("Pipeline aborted due to error in step", step_no)
        sys.exit(1)


def main():
    start_time = time.time()

    # STEP 1: OCR
    run_step(1, 'OCR', lambda: __import__('ocr').main())

    # STEP 2: Extractor
    run_step(2, 'Extractor', lambda: __import__('extractor').main())

    # STEP 3: Exporter
    run_step(3, 'Exporter', lambda: __import__('exporter').main())

    # STEP 4: Analyzer
    run_step(4, 'Analyzer', lambda: __import__('analyzer').main())

    # STEP 5: Charts
    run_step(5, 'Charts', lambda: __import__('charts').main())

    # STEP 6: Report
    run_step(6, 'Report', lambda: __import__('report').main())

    total = time.time() - start_time
    print(f"Total pipeline duration: {total:.2f} seconds")
    print("PIPELINE COMPLETE — all files saved to output/")


if __name__ == '__main__':
    main()
