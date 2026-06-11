import os
import re
import json
import numpy as np
from PIL import Image
import easyocr
from rapidfuzz import fuzz

def extract_grid_text(video_base_name: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 🌟 FIX 1: Auto-detect whether the file is a .png or a .jpg grid
    grid_path = os.path.join(base_dir, f"{video_base_name}_grid.png")
    if not os.path.exists(grid_path):
        grid_path = os.path.join(base_dir, f"{video_base_name}_grid.jpg")
        
    vtt_path = os.path.join(base_dir, f"{video_base_name}_timeline_map.vtt")
    output_json = os.path.join(base_dir, f"{video_base_name}_text_manifest.json")
    output_md = os.path.join(base_dir, f"{video_base_name}_ocr_transcript.md")

    # Verify files exist
    if not os.path.exists(grid_path):
        print(f"❌ Error: Grid image not found (checked for both .png and .jpg) at: {grid_path}")
        return
    if not os.path.exists(vtt_path):
        print(f"❌ Error: VTT file not found at {vtt_path}")
        return

    print("🧠 Initializing EasyOCR (CPU mode)...")
    reader = easyocr.Reader(['en'], gpu=False)

    print(f"🖼️ Opening master grid layout: {grid_path}")
    Image.MAX_IMAGE_PIXELS = None  # Disable decompression limits
    grid_img = Image.open(grid_path)

    print(f"📖 Parsing VTT timeline map: {vtt_path}")
    with open(vtt_path, "r", encoding="utf-8") as f:
        vtt_content = f.read()

    # Normalize line breaks and segment structural cue blocks
    vtt_content = vtt_content.replace("\r\n", "\n")
    blocks = [b.strip() for b in vtt_content.strip().split('\n\n') if b.strip()]
    
    # Skip standard WebVTT header block if present
    if blocks and blocks[0].startswith("WEBVTT"):
        blocks.pop(0)

    manifest = {}
    last_text = ""
    time_window_pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})")
    coord_pattern = re.compile(r"#xywh=(\d+),(\d+),(\d+),(\d+)")

    # 🌟 FIX 2: Safely choose the correct Pillow Lanczos interpolation token dynamically
    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:
        resample_filter = Image.LANCZOS

    print(f"⚡ Extracting text from {len(blocks)} frames entirely in RAM...")
    for index, block in enumerate(blocks, start=1):
        lines = block.split('\n')
        if len(lines) < 2:
            continue
            
        print(f"   ↳ [Frame {index}/{len(blocks)}] Analyzing image matrix...")
        
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
        
        # 1. Spatial slice out of master image matrix in memory
        crop_box = (x, y, x + w, y + h)
        frame_img = grid_img.crop(crop_box)

        # 2. Magnify frame scale factor 2x to clarify sub-pixel texts
        new_size = (w * 2, h * 2)
        frame_img = frame_img.resize(new_size, resample_filter)
        
        # 3. Drop channels to grayscale matrix for high black/white separation contrast
        gray_img = frame_img.convert('L')
        np_img = np.array(gray_img)
        
        # 4. Extract characters cleanly grouping fragments as natural text blocks
        ocr_result = reader.readtext(np_img, detail=0, paragraph=True)
        extracted_text = "\n".join([text.strip() for text in ocr_result if text.strip()])
        
        # 5. Fuzzy string matching comparison 
        is_duplicate = False
        if last_text and extracted_text:
            similarity = fuzz.ratio(extracted_text, last_text)
            if similarity > 90.0:
                is_duplicate = True
                
        if not is_duplicate and extracted_text:
            last_text = extracted_text
            
        manifest[start_time] = {
            "time_window": time_window,
            "extracted_text": extracted_text,
            "is_duplicate": is_duplicate
        }
        
    print(f"💾 Saving structured index data to: {output_json}")
    with open(output_json, "w", encoding="utf-8") as out_file:
        json.dump(manifest, out_file, indent=4, ensure_ascii=False)

    print(f"📝 Saving clean markdown transcript markdown to: {output_md}")
    with open(output_md, "w", encoding="utf-8") as md_file:
        md_file.write(f"# OCR Transcript: {video_base_name}\n\n")
        for ts, data in manifest.items():
            if not data.get("is_duplicate") and data.get("extracted_text"):
                md_file.write(f"### {data['time_window']}\n```text\n{data['extracted_text']}\n```\n\n")

    print(f"✨ Success! OCR tracking operations completed for '{video_base_name}'!")

if __name__ == "__main__":
    # Test fallback call targeting test5 assets directly
    extract_grid_text("test5")