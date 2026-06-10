import cv2
import os
import sys
import shutil

VIDEO_FILE = sys.argv[1]
SLIDES_DIR = "test_slides"

if os.path.exists(SLIDES_DIR):
    shutil.rmtree(SLIDES_DIR)
os.makedirs(SLIDES_DIR, exist_ok=True)

cap = cv2.VideoCapture(VIDEO_FILE)
fps = cap.get(cv2.CAP_PROP_FPS)
if not fps or fps != fps: fps = 30.0

sample_rate = int(fps) # 1 frame per second
print(f"Sampling 1 frame per second. FPS is {fps}")

slides = []
prev_hist = None
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret: break
    
    if frame_idx % sample_rate == 0:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Using Hue and Saturation for histogram
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        timestamp_sec = frame_idx / fps
        extract = False
        
        if prev_hist is None:
            extract = True
            similarity = 0
        else:
            similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            # 0.85 means 15% difference in overall color palette
            if similarity < 0.85:
                extract = True
                
        if extract:
            mm = int(timestamp_sec // 60)
            ss = int(timestamp_sec % 60)
            img_path = os.path.join(SLIDES_DIR, f"slide_{mm:02d}m{ss:02d}s.png")
            cv2.imwrite(img_path, frame)
            slides.append((timestamp_sec, img_path))
            print(f"Extracted at {mm:02d}:{ss:02d} | Similarity to previous: {similarity:.2f}")
            prev_hist = hist
            
    frame_idx += 1

cap.release()
print(f"Total extracted: {len(slides)}")
