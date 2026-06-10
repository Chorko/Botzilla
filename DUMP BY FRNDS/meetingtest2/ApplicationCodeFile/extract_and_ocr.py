import sys
import os
import json
from PIL import Image

def load_timeline(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_timeline(data, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def crop_and_ocr(sprite_path, timeline_json, out_json):
    try:
        import pytesseract
    except Exception as e:
        print('pytesseract not installed or not importable:', e)
        print('Please run: pip install pytesseract pillow and ensure Tesseract OCR is installed.')
        return 1

    img = Image.open(sprite_path)
    entries = timeline_json.get('timeline', [])

    for entry in entries:
        xywh = entry.get('xywh')
        if not xywh or len(xywh) != 4:
            entry['ocr_text'] = None
            continue
        x, y, w, h = xywh
        try:
            crop = img.crop((x, y, x + w, y + h))
            # Preprocess: convert to grayscale and increase contrast lightly
            gray = crop.convert('L')
            entry_text = pytesseract.image_to_string(gray, config='--psm 6')
            entry['ocr_text'] = entry_text.strip()
        except Exception as e:
            entry['ocr_text'] = None
            print('Error processing entry', entry.get('index'), e)

    save_timeline(timeline_json, out_json)
    print(f'Wrote enriched JSON to {out_json} (entries: {len(entries)})')
    return 0

def main():
    sprite = sys.argv[1] if len(sys.argv) > 1 else 'Terra-Truce_Demo - Made with Clipchamp_grid.png'
    timeline = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(sprite)[0] + '_timeline.json'
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(timeline)[0] + '_enriched.json'

    if not os.path.exists(sprite):
        print('Sprite not found:', sprite)
        return
    if not os.path.exists(timeline):
        print('Timeline JSON not found:', timeline)
        return

    tl = load_timeline(timeline)
    rc = crop_and_ocr(sprite, tl, out)
    return rc

if __name__ == '__main__':
    sys.exit(main())
