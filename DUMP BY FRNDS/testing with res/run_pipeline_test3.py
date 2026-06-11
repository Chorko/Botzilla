import os
import sys
import json
import subprocess
import imageio_ffmpeg
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.insert(0, root_dir)

# Add ffmpeg to PATH for whisperx
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_exe)

load_dotenv(os.path.join(root_dir, ".env"))

video_path = os.path.join(script_dir, "test3.mp4")
audio_path = os.path.join(script_dir, "test3.wav")
output_dir = script_dir

# print("1. Extracting audio...")
# subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path, "-loglevel", "error"])

# print("2. Extracting slides with ApplicationCodeFile/vedio_processor.py...")
app_code_dir = os.path.join(root_dir, "ApplicationCodeFile")
sys.path.insert(0, app_code_dir)
os.chdir(output_dir) # work from output dir since grid is here
# from vedio_processor import process_video_in_chunks
# process_video_in_chunks(video_path)

vtt_path = os.path.join(output_dir, "test3_timeline_map.vtt")
slides_log = ""
if os.path.exists(vtt_path):
    with open(vtt_path, 'r') as f:
        slides_log = f.read()

print("3. Skipping audio_engine.py because it already completed... using transcript from previous run.")
transcript = ""
with open(os.path.join(output_dir, "report.json"), "r") as f:
    report_data = json.load(f)
    for seg in report_data.get("segments", []):
        transcript += seg.get("speaker", "Unknown") + ": " + seg.get("text", "") + "\n"

print("4. Generating structured JSON using Gemini...")
prompt = f"""You are a professional meeting report generator. Your job is to produce 
a structured JSON payload that will be used to render a Word document 
(.docx) meeting summary report. Follow every instruction exactly.

─────────────────────────────────────────────────────────────
OUTPUT FORMAT
─────────────────────────────────────────────────────────────
Return ONLY a single valid JSON object. No markdown fences, no 
explanation, no preamble. The JSON must match this exact schema:

{{
  "meta": {{
    "title": "string",
    "duration": "string",
    "participants": "string",
    "language": "string",
    "slides": "string",
    "mode": "UNIFIED",
    "source": "test3.mp4"
  }},
  "exec_summary": "string",
  "key_topics": [
    {{
      "title": "string",
      "body": "string"
    }}
  ],
  "speakers": [
    {{
      "name": "string",
      "duration": "string",
      "pct": "string",
      "words": "string"
    }}
  ],
  "utterances": [
    {{
      "speaker": "string",
      "start": "string",
      "end": "string",
      "text": "string",
      "slide_timestamp": "string or null",
      "slide_frame_path": null
    }}
  ]
}}

─────────────────────────────────────────────────────────────
SPEAKER NAMING RULES
─────────────────────────────────────────────────────────────
1. Default labels are "Speaker 1", "Speaker 2", etc. in order of first appearance.
2. If the speaker introduces themselves anywhere in the transcript — in English OR Hinglish — replace their label with their real first name (capitalised) for ALL their utterances and in speakers[].
3. If the same speaker is addressed by name by another speaker ("Thanks Rahul", "Good point Reina"), use that name too.
4. Never guess names. Only use names explicitly spoken in the audio.
5. Once a name is resolved, apply it consistently everywhere.

─────────────────────────────────────────────────────────────
TRANSCRIPT CLEANING RULES
─────────────────────────────────────────────────────────────
1. Remove filler words: "um", "uh", "like", "you know", "basically".
2. Fix obvious STT errors using context.
3. Do NOT paraphrase or summarise utterances. Keep the speaker's actual words, just cleaned.
4. Preserve Hinglish words exactly as spoken (e.g. "yaar", "bhai", "toh", "matlab"). Do not translate them.
5. Merge consecutive utterances from the same speaker only if they are under 3 seconds apart with no other speaker in between.

─────────────────────────────────────────────────────────────
SLIDE TIMESTAMP RULES
─────────────────────────────────────────────────────────────
1. slide_timestamp should be set on the utterance that begins AFTER a visible slide change in the video.
2. If no screen share or slides are present, all slide_timestamp values must be null.

─────────────────────────────────────────────────────────────
EXEC SUMMARY RULES
─────────────────────────────────────────────────────────────
1. Written in third person.
2. Must cover: what was shown/discussed, the core problem being solved, the key solution features, and outcomes.
3. No bullet points. One flowing paragraph.
4. Hinglish meetings: write the summary in English.

─────────────────────────────────────────────────────────────
KEY TOPICS RULES
─────────────────────────────────────────────────────────────
1. Topics must be in chronological order.
2. Each title is a noun phrase describing the topic, sentence case.
3. Body is 2–3 sentences of synthesis — not a quote, not a transcript fragment.
4. Minimum 4 topics, maximum 8.

Transcript:
{transcript}
"""

system_instruction = "You are a professional meeting report generator. Follow all rules and output exactly the requested JSON schema."

from groq import Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

print("Calling Groq to generate structured JSON...")
response = groq_client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ],
    temperature=0.1,
    response_format={"type": "json_object"}
)

json_data = json.loads(response.choices[0].message.content)

# We need to construct the slides array for docxGenerator.ts
# VTT file is parsed in docxGenerator via slide_timestamp, but we need to pass slides in the JSON.
from PIL import Image

slides_arr = []
import re

grid_path = os.path.join(output_dir, "test3_grid.png")
grid_img = None
if os.path.exists(grid_path):
    Image.MAX_IMAGE_PIXELS = None
    grid_img = Image.open(grid_path)

coord_pattern = re.compile(r"#xywh=(\d+),(\d+),(\d+),(\d+)")

blocks = slides_log.strip().split('\n\n')
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
    
    if coord_match and grid_img:
        x, y, w, h = map(int, coord_match.groups())
        crop_box = (x, y, x + w, y + h)
        frame_img = grid_img.crop(crop_box)
        saved_path = os.path.join(output_dir, f"test3_slide_{int(s_sec)}.png")
        frame_img.save(saved_path)
        
    slides_arr.append({
        "id": f"slide_{int(s_sec)}",
        "timestamp": s_sec,
        "dataUrl": saved_path
    })

json_data["slides"] = slides_arr

output_json = os.path.join(output_dir, "test3_payload.json")
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=2)

print(f"5. Wrote payload to {output_json}. Now compiling docx...")

# Call the docx script
tsx_script = f"""import fs from 'fs';
import path from 'path';
import {{ compileMeetingDocx }} from '../../docxGenerator';

async function run() {{
    const data = JSON.parse(fs.readFileSync('{output_json.replace("\\", "\\\\")}', 'utf8'));
    const docBuffer = await compileMeetingDocx(data, []);
    fs.writeFileSync('{os.path.join(output_dir, "test3_final.docx").replace("\\", "\\\\")}', docBuffer);
    console.log("Successfully generated test3_final.docx");
}}
run();
"""

tsx_path = os.path.join(output_dir, "run_docx.ts")
with open(tsx_path, "w", encoding="utf-8") as f:
    f.write(tsx_script)

subprocess.run(["npx", "tsx", tsx_path], cwd=root_dir)
print("✅ Pipeline complete!")
