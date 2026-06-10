import cv2
import os
import sys
import json
import shutil

VIDEO_FILE = sys.argv[1]
JSON_FILE = VIDEO_FILE.replace('.mp4', '_botzilla.json')
SLIDES_DIR = "extracted_slides"

if os.path.exists(SLIDES_DIR):
    shutil.rmtree(SLIDES_DIR)
os.makedirs(SLIDES_DIR, exist_ok=True)

print("🔄 Fast extracting visual timeline (1 frame every 10 seconds)...")
cap = cv2.VideoCapture(VIDEO_FILE)
fps = cap.get(cv2.CAP_PROP_FPS)
if not fps or fps != fps: fps = 30.0

slides = []
interval_sec = 10  # Extract every 10 seconds
frame_interval = int(fps * interval_sec)

frame_idx = 0
prev_gray = None

while True:
    ret, frame = cap.read()
    if not ret: break
    
    if frame_idx % frame_interval == 0:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (640, 360)) # Resize for faster comparison
        
        extract = True
        if prev_gray is not None:
            # Check if exactly identical (e.g., static slide)
            diff = cv2.absdiff(prev_gray, gray)
            non_zero = cv2.countNonZero(diff)
            if non_zero < 1000: # Less than 1000 pixels changed out of 230k
                extract = False
                
        if extract:
            timestamp_sec = frame_idx / fps
            mm = int(timestamp_sec // 60)
            ss = int(timestamp_sec % 60)
            img_name = f"slide_{mm:02d}m{ss:02d}s.png"
            img_path = os.path.join(SLIDES_DIR, img_name)
            cv2.imwrite(img_path, frame)
            
            slides.append({
                "timestamp_sec": round(timestamp_sec, 2),
                "timestamp_fmt": f"{mm:02d}:{ss:02d}",
                "image_path": img_path
            })
            prev_gray = gray
            print(f"  📸 Extracted: {img_name}")
            
    frame_idx += 1

cap.release()
print(f"✅ Extracted {len(slides)} timeline images!")

print("\n🔄 Updating existing Botzilla JSON...")
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

data["slides"] = slides
data["metadata"]["num_slides_extracted"] = len(slides)

for seg in data["transcript"]:
    # Map new slides to transcript segments
    seg_start = seg["start"]
    seg_end = seg["end"]
    
    active_slides = []
    for s in slides:
        if seg_start <= s["timestamp_sec"] <= seg_end:
            active_slides.append(s["image_path"])
    seg["slides_shown"] = active_slides

with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("✅ Botzilla JSON updated with new slides!")
