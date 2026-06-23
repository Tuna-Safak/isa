from pathlib import Path

p = Path('ocr.py')
s = p.read_text(encoding='utf-8')
old = 'if __name__ == "__main__":\n    main()'
new = ('def process_image_file(input_path: str, lang: str = \'deu\') -> str:\n'
       '    if not os.path.exists(input_path):\n'
       '        raise FileNotFoundError(f"Input image not found: {input_path}")\n'
       '    return extract_text_from_image(input_path)\n\n'
       'if __name__ == "__main__":\n'
       '    main()')

if old not in s:
    raise SystemExit('Old string not found in ocr.py')

p.write_text(s.replace(old, new), encoding='utf-8')
print('patched')
