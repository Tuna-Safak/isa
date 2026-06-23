## OCR usage

Single file:

```bash
python ocr.py /path/to/image.jpg --lang deu+eng
```

Folder batch:

```bash
python ocr.py /path/to/folder --lang deu+eng --recursive
```

Outputs:
- Single file: `*_ocr_output.txt`
- Folder batch: `folder/ocr_output/` with one text file per input plus a combined file
