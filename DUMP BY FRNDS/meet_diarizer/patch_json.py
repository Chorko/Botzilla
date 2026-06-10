import os
import json
import sys

JSON_FILE = sys.argv[1]
SLIDES_DIR = "extracted_slides"

slides = []
for file in sorted(os.listdir(SLIDES_DIR)):
    if file.startswith("slide_") and len(file.split('_')) == 2:
        try:
            # Assumes format slide_001.png
            idx = int(file.split('_')[1].split('.')[0]) - 1
            timestamp_sec = idx * 10
            mm = int(timestamp_sec // 60)
            ss = int(timestamp_sec % 60)
            
            # Rename file to match botzilla format
            new_name = f"slide_{mm:02d}m{ss:02d}s.png"
            old_path = os.path.join(SLIDES_DIR, file)
            new_path = os.path.join(SLIDES_DIR, new_name)
            os.rename(old_path, new_path)
            
            slides.append({
                "timestamp_sec": float(timestamp_sec),
                "timestamp_fmt": f"{mm:02d}:{ss:02d}",
                "image_path": new_path
            })
        except:
            pass

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

data["slides"] = slides
data["metadata"]["num_slides_extracted"] = len(slides)

for seg in data["transcript"]:
    seg_start = seg["start"]
    seg_end = seg["end"]
    active_slides = []
    for s in slides:
        if seg_start <= s["timestamp_sec"] <= seg_end:
            active_slides.append(s["image_path"])
    seg["slides_shown"] = active_slides

with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("✅ Patched JSON with FFmpeg extracted slides!")
