import cv2
import os
import sys
import json
import shutil

if len(sys.argv) < 2:
    print("Usage: python fast_slide_patcher.py <video_file> [report.json]")
    sys.exit(1)

VIDEO_FILE = sys.argv[1]
JSON_FILE = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(os.path.dirname(VIDEO_FILE), 'report.json')
SLIDES_DIR = os.path.join(os.path.dirname(JSON_FILE), "slides")

# Check if task ID is in directory path
# e.g., output/task_12345/
task_id = os.path.basename(os.path.dirname(JSON_FILE))

if os.path.exists(SLIDES_DIR):
    shutil.rmtree(SLIDES_DIR)
os.makedirs(SLIDES_DIR, exist_ok=True)

print(f"🔄 Fast extracting visual timeline (1 frame every 10 seconds) for Task: {task_id}...")
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
        gray = cv2.resize(gray, (640, 360))  # Resize for faster comparison
        
        extract = True
        if prev_gray is not None:
            # Check if exactly identical (e.g., static slide)
            diff = cv2.absdiff(prev_gray, gray)
            non_zero = cv2.countNonZero(diff)
            if non_zero < 1000:  # Less than 1000 pixels changed out of 230k
                extract = False
                
        if extract:
            timestamp_sec = frame_idx / fps
            mm = int(timestamp_sec // 60)
            ss = int(timestamp_sec % 60)
            img_name = f"slide_{mm:02d}m{ss:02d}s.png"
            img_path = os.path.join(SLIDES_DIR, img_name)
            cv2.imwrite(img_path, frame)
            
            # Canny edge density & Laplacian blur score for quality logging
            edges = cv2.Canny(gray, 50, 150)
            edge_density = cv2.countNonZero(edges) / (gray.shape[0] * gray.shape[1])
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            slides.append({
                "id": f"slide_{len(slides) + 1}",
                "timestamp": round(timestamp_sec, 2),
                "dataUrl": f"/output/{task_id}/slides/{img_name}",
                "edgeDensity": round(float(edge_density), 4),
                "blurScore": round(float(lap_var), 1),
                "caption": f"Extracted Slide Frame at {mm:02d}:{ss:02d}",
                "isScreenShare": True
            })
            prev_gray = gray
            print(f"  📸 Extracted: {img_name} (time: {mm:02d}:{ss:02d}, edges: {edge_density*100:.1f}%)")
            
    frame_idx += 1

cap.release()
print(f"✅ Extracted {len(slides)} timeline images!")

if os.path.exists(JSON_FILE):
    print(f"🔄 Updating existing JSON file: {JSON_FILE}...")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["slides"] = slides

    # Re-map slides to segments in transcript
    for seg in data.get("segments", []):
        seg_start = seg["startTime"]
        seg_end = seg["endTime"]
        
        active_slides = []
        for s in slides:
            if seg_start <= s["timestamp"] <= seg_end:
                active_slides.append(s["id"])
        
        if active_slides:
            seg["slideId"] = active_slides[0]

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ JSON file successfully updated with new slides and transcript mappings!")
else:
    print(f"⚠️ Warning: JSON report file not found at {JSON_FILE}. Skipping patching.")
