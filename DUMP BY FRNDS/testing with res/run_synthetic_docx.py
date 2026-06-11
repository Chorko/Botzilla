import os
import json
import re
import subprocess
from PIL import Image

script_dir = r"d:\ai-meeting-summarizer\DUMP BY FRNDS\testing with res"
root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

# Inputs
grid_path = os.path.join(script_dir, "synthetic_grid.png")
vtt_path = os.path.join(script_dir, "synthetic_timeline_map.vtt")
report_path = os.path.join(script_dir, "synthetic_report.json")

# 1. Parse Report
with open(report_path, "r", encoding="utf-8") as f:
    report_data = json.load(f)

segments = report_data.get("segments", [])

# 2. Parse VTT and Crop Slides
slides_arr = []
grid_img = Image.open(grid_path)
coord_pattern = re.compile(r"#xywh=(\d+),(\d+),(\d+),(\d+)")

with open(vtt_path, "r", encoding="utf-8") as f:
    vtt_text = f.read()

blocks = vtt_text.strip().split('\n\n')
for block in blocks:
    lines = block.split('\n')
    if len(lines) < 2: continue
    
    time_line = lines[0]
    if "-->" not in time_line: continue
    
    start_str = time_line.split("-->")[0].strip()
    time_parts = start_str.split(":")
    if len(time_parts) == 3:
        s_sec = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + float(time_parts[2])
    elif len(time_parts) == 2:
        s_sec = int(time_parts[0]) * 60 + float(time_parts[1])
    else:
        s_sec = 0
        
    coord_match = coord_pattern.search(lines[1])
    saved_path = grid_path
    
    if coord_match:
        x, y, w, h = map(int, coord_match.groups())
        crop_box = (x, y, x + w, y + h)
        frame_img = grid_img.crop(crop_box)
        saved_path = os.path.join(script_dir, f"synthetic_slide_{int(s_sec)}.png")
        frame_img.save(saved_path)
        
    slides_arr.append({
        "id": f"slide_{int(s_sec)}",
        "timestamp": s_sec,
        "dataUrl": saved_path
    })

# 3. Construct 0-Hallucination Payload
def sec_to_str(secs):
    m = int(secs // 60)
    s = int(secs % 60)
    return f"00:{m:02d}:{s:02d}"

utterances = []
speakers_map = {}

for seg in segments:
    spk = seg.get("speaker", "Unknown")
    start = seg.get("start", 0)
    end = seg.get("end", 0)
    words = len(seg.get("text", "").split())
    
    if spk not in speakers_map:
        speakers_map[spk] = {"duration": 0, "words": 0}
        
    speakers_map[spk]["duration"] += (end - start)
    speakers_map[spk]["words"] += words
    
    # slide timestamp logic: closest slide before start
    slide_ts = None
    for slide in reversed(slides_arr):
        if slide["timestamp"] <= start:
            slide_ts = sec_to_str(slide["timestamp"])
            break
            
    utterances.append({
        "speaker": spk,
        "start": sec_to_str(start),
        "end": sec_to_str(end),
        "text": seg.get("text", ""),
        "slide_timestamp": sec_to_str(start)  # To map exactly, or we can use start.
    })

speakers_arr = []
for spk, stats in speakers_map.items():
    speakers_arr.append({
        "name": spk,
        "duration": f"{int(stats['duration'])}s",
        "pct": "N/A",
        "words": str(stats['words'])
    })

payload = {
  "meta": {
    "title": "Synthetic 0-Hallucination Meeting",
    "duration": "00:00:40",
    "participants": str(len(speakers_map)),
    "language": "English",
    "slides": str(len(slides_arr)),
    "mode": "UNIFIED",
    "source": "synthetic_inputs"
  },
  "exec_summary": "This is a 100% deterministic synthetic meeting summary generated directly from the audio and vision engine outputs, bypassing LLM hallucination entirely.",
  "key_topics": [
    {
      "title": "Synthetic Intro",
      "body": "Introductory remarks generated perfectly from segment timestamps."
    },
    {
      "title": "Synthetic Conclusion",
      "body": "Concluding remarks."
    }
  ],
  "speakers": speakers_arr,
  "utterances": utterances,
  "slides": slides_arr
}

payload_path = os.path.join(script_dir, "synthetic_payload.json")
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print(f"Created payload: {payload_path}")

# 4. Generate DOCX
tsx_script = f"""import fs from 'fs';
import path from 'path';
import {{ compileMeetingDocx }} from '../../docxGenerator';

async function run() {{
    const data = JSON.parse(fs.readFileSync('{payload_path.replace("\\", "\\\\")}', 'utf8'));
    const docBuffer = await compileMeetingDocx(data, []);
    fs.writeFileSync('{os.path.join(script_dir, "synthetic_final.docx").replace("\\", "\\\\")}', docBuffer);
    console.log("Successfully generated synthetic_final.docx");
}}
run();
"""

tsx_path = os.path.join(script_dir, "run_synthetic_docx.ts")
with open(tsx_path, "w", encoding="utf-8") as f:
    f.write(tsx_script)

subprocess.run(["npx.cmd", "tsx", tsx_path], cwd=root_dir, shell=True)
print("✅ Pipeline complete! Check synthetic_final.docx")
