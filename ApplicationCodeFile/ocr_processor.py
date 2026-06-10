import os
import re
import json
import numpy as np
from PIL import Image
import easyocr
from rapidfuzz import fuzz

def extract_grid_text(video_base_name: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    grid_path = os.path.join(base_dir, f"{video_base_name}_grid.png")
    vtt_path = os.path.join(base_dir, f"{video_base_name}_timeline_map.vtt")
    output_json = os.path.join(base_dir, f"{video_base_name}_text_manifest.json")
    output_md = os.path.join(base_dir, f"{video_base_name}_ocr_transcript.md")

    # Verify files exist
    if not os.path.exists(grid_path):
        print(f"Error: Grid image not found at {grid_path}")
        return
    if not os.path.exists(vtt_path):
        print(f"Error: VTT file not found at {vtt_path}")
        return

    print("Initializing EasyOCR (CPU mode)...")
    reader = easyocr.Reader(['en'], gpu=False)

    print(f"Opening master grid: {grid_path}")
    # Disable decompression bomb warning for large images
    Image.MAX_IMAGE_PIXELS = None
    grid_img = Image.open(grid_path)

    print(f"Parsing VTT timeline map: {vtt_path}")
    with open(vtt_path, "r", encoding="utf-8") as f:
        vtt_content = f.read()

    # VTT blocks usually consist of a timestamp line followed by coordinate reference
    blocks = vtt_content.strip().split('\n\n')
    
    manifest = {}
    last_text = ""
    time_window_pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})")
    coord_pattern = re.compile(r"#xywh=(\d+),(\d+),(\d+),(\d+)")

    print(f"Extracting text from {len(blocks)} individual frames in memory...")
    for index, block in enumerate(blocks, start=1):
        lines = block.split('\n')
        
        # We need at least the timestamp and the reference line
        if len(lines) < 2:
            continue
            
        print(f"⏳ Processing frame {index}/{len(blocks)}...")
        
        # Parse timestamp window
        time_match = time_window_pattern.search(lines[0])
        if not time_match:
            continue
            
        start_time = time_match.group(1)
        time_window = lines[0].strip()
        
        # Parse coordinates
        coord_match = coord_pattern.search(lines[1])
        if not coord_match:
            continue
            
        x, y, w, h = map(int, coord_match.groups())
        
        # 1. Crop sub-frame in memory
        crop_box = (x, y, x + w, y + h)
        frame_img = grid_img.crop(crop_box)

        # 1.5. Upscale the frame 2x to help OCR read small/pixelated text
        new_size = (w * 2, h * 2)
        frame_img = frame_img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 2. Convert to grayscale for better text contrast
        gray_img = frame_img.convert('L')
        
        # 3. EasyOCR expects numpy array
        np_img = np.array(gray_img)
        
        # 4. Extract clean string text (paragraph=True keeps words in natural sentences)
        ocr_result = reader.readtext(np_img, detail=0, paragraph=True)
        extracted_text = "\n".join([text.strip() for text in ocr_result if text.strip()])
        
        # 5. RapidFuzz Deduplication (>90% similarity)
        is_duplicate = False
        if last_text and extracted_text:
            similarity = fuzz.ratio(extracted_text, last_text)
            if similarity > 90:
                is_duplicate = True
                
        if not is_duplicate and extracted_text:
            last_text = extracted_text
            
        manifest[start_time] = {
            "time_window": time_window,
            "extracted_text": extracted_text,
            "is_duplicate": is_duplicate
        }
        
    print(f"Exporting compiled manifest to: {output_json}")
    with open(output_json, "w", encoding="utf-8") as out_file:
        json.dump(manifest, out_file, indent=4, ensure_ascii=False)

    print(f"Exporting markdown transcript to: {output_md}")
    with open(output_md, "w", encoding="utf-8") as md_file:
        md_file.write(f"# OCR Transcript: {video_base_name}\n\n")
        for ts, data in manifest.items():
            if not data.get("is_duplicate") and data.get("extracted_text"):
                md_file.write(f"### {data['time_window']}\n```text\n{data['extracted_text']}\n```\n\n")

    print(f"✅ OCR text extraction complete for {video_base_name}!")
