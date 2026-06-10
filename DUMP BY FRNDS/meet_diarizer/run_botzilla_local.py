import os
import sys
import time
import subprocess
import gc
import json
import cv2
import argparse
import requests
import io

# Force UTF-8 encoding on Windows consoles to prevent UnicodeEncodeError
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import whisperx
import torch
from pydantic import BaseModel
from typing import List, Optional

# ── Load Environment Variables from .env ──────────────────────────────────
def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        os.environ[key] = val

load_env()

# Default Configurations
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DEFAULT_WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
DEFAULT_LANGUAGE = os.environ.get("LANGUAGE", "en")

INITIAL_PROMPT = "The following is a corporate meeting with speakers using both English and Hindi (Hinglish). Technical terms are in English."

# ── Pydantic Output Schemas ──────────────────────────────────────────────
class SlideSnapshot(BaseModel):
    timestamp_sec: float
    timestamp_fmt: str
    image_path: str

class TranscriptSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str
    slides_shown: List[str]

class ActionItem(BaseModel):
    task: str
    assignee: str
    priority: str

class TopicDiscussion(BaseModel):
    name: str
    summary: str

class BotzillaSummary(BaseModel):
    title: str
    executive_summary: str
    key_decisions: List[str]
    action_items: List[ActionItem]
    topics: List[TopicDiscussion]

class BotzillaMetadata(BaseModel):
    pipeline_mode: str
    audio_file: str
    video_file: Optional[str] = None
    video_offset_seconds: float
    language: str
    num_slides_extracted: int

class BotzillaReport(BaseModel):
    metadata: BotzillaMetadata
    slides: List[SlideSnapshot]
    transcript: List[TranscriptSegment]
    speaker_mapping: dict
    summary: BotzillaSummary

# ── Smart Slide Extraction ───────────────────────────────────────────────
def extract_slides_smart(video_path: str, output_dir: str, sample_interval_sec: float = 2.0, offset_sec: float = 0.0) -> List[dict]:
    os.makedirs(output_dir, exist_ok=True)
    print(f"🔄 Smart extracting visual slides from: {video_path}")
    print(f"   Sample interval: {sample_interval_sec}s | Video Offset: {offset_sec}s")
    
    slides = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"⚠️ Error: Could not open video file {video_path}")
        return slides
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps != fps:
        fps = 30.0
        
    frame_interval = int(fps * sample_interval_sec)
    
    prev_gray = None
    frame_idx = 0
    
    # Stability tracking parameters
    stable_frames_count = 0
    STABILITY_THRESHOLD = 2  # Screen must be stable for 2 samples (e.g. 4 seconds at 2s interval)
    candidate_frame = None
    candidate_timestamp = 0.0
    in_motion = False
    
    # Smart filters
    MIN_CHANGE_PCT = 0.015  # Minimum screen change (1.5% pixels) to detect slide transitions (ignores cursor/mouse movement)
    MIN_EDGE_DENSITY = 0.005  # Slide check: slides contain text/shapes; webcam feeds/blank screens have low edge density
    MIN_LAPLACIAN_VAR = 80.0  # Blur check: ignore blurry transitions
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % frame_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Resize for faster structural comparison
            resized_gray = cv2.resize(gray, (640, 360))
            timestamp_sec = frame_idx / fps
            
            if prev_gray is not None:
                # Absolute difference
                diff = cv2.absdiff(prev_gray, resized_gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                changed_pixels = cv2.countNonZero(thresh)
                change_pct = changed_pixels / (640 * 360)
                
                significant_change = change_pct >= MIN_CHANGE_PCT
                
                if significant_change:
                    in_motion = True
                    stable_frames_count = 0
                    candidate_frame = None
                elif in_motion:
                    stable_frames_count += 1
                    if stable_frames_count >= STABILITY_THRESHOLD:
                        candidate_frame = frame.copy()
                        candidate_timestamp = timestamp_sec
                        in_motion = False
                        stable_frames_count = 0
                        
                        # Validate candidate frame quality
                        cand_gray = cv2.cvtColor(candidate_frame, cv2.COLOR_BGR2GRAY)
                        
                        # Blurriness check
                        lap_var = cv2.Laplacian(cand_gray, cv2.CV_64F).var()
                        
                        # Edge density check
                        edges = cv2.Canny(cand_gray, 50, 150)
                        edge_density = cv2.countNonZero(edges) / (edges.shape[0] * edges.shape[1])
                        
                        if lap_var >= MIN_LAPLACIAN_VAR and edge_density >= MIN_EDGE_DENSITY:
                            # Verify if it differs significantly from the last saved slide (deduplication)
                            is_duplicate = False
                            if slides:
                                last_slide_path = slides[-1]["image_path"]
                                if os.path.exists(last_slide_path):
                                    last_img = cv2.imread(last_slide_path, cv2.IMREAD_GRAYSCALE)
                                    if last_img is not None:
                                        last_resized = cv2.resize(last_img, (640, 360))
                                        slide_diff = cv2.absdiff(last_resized, resized_gray)
                                        _, slide_thresh = cv2.threshold(slide_diff, 25, 255, cv2.THRESH_BINARY)
                                        slide_change = cv2.countNonZero(slide_thresh) / (640 * 360)
                                        if slide_change < 0.05:  # Less than 5% difference is duplicate
                                            is_duplicate = True
                                            
                            if not is_duplicate:
                                aligned_sec = candidate_timestamp + offset_sec
                                if aligned_sec < 0:
                                    aligned_sec = 0.0
                                    
                                mm = int(aligned_sec // 60)
                                ss = int(aligned_sec % 60)
                                img_name = f"slide_{mm:02d}m{ss:02d}s.png"
                                img_path = os.path.join(output_dir, img_name)
                                cv2.imwrite(img_path, candidate_frame)
                                
                                slides.append({
                                    "timestamp_sec": round(aligned_sec, 2),
                                    "timestamp_fmt": f"{mm:02d}:{ss:02d}",
                                    "image_path": img_path
                                })
                                print(f"  📸 Extracted: {img_name} (time: {mm:02d}:{ss:02d}, edges: {edge_density:.4f}, variance: {lap_var:.1f})")
            else:
                # Capture the very first frame as initial slide if it meets quality filters
                lap_var = cv2.Laplacian(resized_gray, cv2.CV_64F).var()
                edges = cv2.Canny(resized_gray, 50, 150)
                edge_density = cv2.countNonZero(edges) / (resized_gray.shape[0] * resized_gray.shape[1])
                
                if lap_var >= MIN_LAPLACIAN_VAR and edge_density >= MIN_EDGE_DENSITY:
                    aligned_sec = 0.0 + offset_sec
                    if aligned_sec < 0:
                        aligned_sec = 0.0
                    mm = int(aligned_sec // 60)
                    ss = int(aligned_sec % 60)
                    img_name = f"slide_initial_{mm:02d}m{ss:02d}s.png"
                    img_path = os.path.join(output_dir, img_name)
                    cv2.imwrite(img_path, frame)
                    
                    slides.append({
                        "timestamp_sec": round(aligned_sec, 2),
                        "timestamp_fmt": f"{mm:02d}:{ss:02d}",
                        "image_path": img_path
                    })
                    print(f"  📸 Extracted Initial: {img_name}")
                    
            prev_gray = resized_gray
        frame_idx += 1
        
    cap.release()
    print(f"✅ Finished extracting slides. Total saved: {len(slides)}")
    return slides

# ── Gemini API Calls ───────────────────────────────────────────────────────
def call_gemini(api_key: str, prompt: str, system_instruction: str = None, response_schema: dict = None) -> Optional[str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    contents = [{"parts": [{"text": prompt}]}]
    payload = {
        "contents": contents,
        "generationConfig": {}
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if response_schema:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        payload["generationConfig"]["responseSchema"] = response_schema
        
    max_retries = 3
    backoff = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
            elif response.status_code in [429, 503, 504]:
                print(f"⚠️ Gemini API returned status {response.status_code}. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
            else:
                print(f"⚠️ Gemini API error ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            print(f"⚠️ Gemini API call attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2
            else:
                return None
    return None

def resolve_speaker_names(api_key: str, segments: List[dict]) -> dict:
    if not api_key:
        print("⚠️ No Gemini API key provided. Skipping speaker name resolution.")
        return {}
        
    print("🔄 Analyzing transcript to identify speaker names...")
    
    # Build transcript text for the prompt
    transcript_lines = []
    for seg in segments[:200]:  # Use up to first 200 segments to avoid exceeding token limits and keep it fast
        speaker = seg.get("speaker", "UNKNOWN")
        start = seg.get("start", 0.0)
        minutes = int(start // 60)
        seconds = int(start % 60)
        text = seg.get("text", "")
        transcript_lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
        
    transcript_text = "\n".join(transcript_lines)
    
    prompt = f"""You are an expert meeting analyst. You are given a transcript where speakers are labeled with temporary IDs like SPEAKER_00, SPEAKER_01, etc.
Your task is to analyze the text and find their real names.
Look closely for:
1. Self-introductions: "Hi, I am Amit", "Amit here", "This is Rahul".
2. Greetings/conversations: "Hey Suresh, how is the project?" followed by SPEAKER_02 answering "It is going well". This implies SPEAKER_02 is Suresh.
3. Code-switching: Hinglish (Hindi + English) references where they introduce themselves.

Return a JSON object containing a "speaker_mapping" array that maps the temporary speaker label to their identified real name (formatted cleanly, e.g. "Rahul Sharma" or "Rahul").
If a speaker's name cannot be found, map it to a friendly fallback like "Speaker 1" (based on their order/label) or keep the original.

Transcript:
{transcript_text}"""

    system_instruction = "You are a professional meeting analysis system. Identify the speaker names and return only a JSON mapping."
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "speaker_mapping": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "speaker_label": {"type": "STRING", "description": "The speaker label, e.g. SPEAKER_00"},
                        "real_name": {"type": "STRING", "description": "The resolved real name of the speaker"}
                    },
                    "required": ["speaker_label", "real_name"]
                },
                "description": "List of speaker mapping entries."
            },
            "reasoning": {
                "type": "STRING",
                "description": "Short reasoning of how you resolved the names."
            }
        },
        "required": ["speaker_mapping"]
    }
    
    res = call_gemini(api_key, prompt, system_instruction, schema)
    if res:
        try:
            data = json.loads(res)
            mapping = {}
            for item in data.get("speaker_mapping", []):
                label = item.get("speaker_label")
                name = item.get("real_name")
                if label and name:
                    mapping[label] = name
            print(f"✅ Speaker Mapping Resolved: {mapping}")
            return mapping
        except Exception as e:
            print(f"⚠️ Failed to parse speaker mapping JSON: {e}")
            
    return {}

def generate_ai_summary(api_key: str, segments: List[dict]) -> Optional[dict]:
    if not api_key:
        print("⚠️ No Gemini API key provided. Skipping AI summarization.")
        return None
        
    print("🔄 Generating AI-powered meeting summary...")
    
    # Build transcript text for the prompt
    transcript_lines = []
    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        start = seg.get("start", 0.0)
        minutes = int(start // 60)
        seconds = int(start % 60)
        text = seg.get("text", "")
        transcript_lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
        
    transcript_text = "\n".join(transcript_lines)
    
    prompt = f"""You are a professional corporate secretary. Generate a comprehensive meeting report from this transcript.
The meeting is in Hinglish (mixed English and Hindi). Please write the summary, action items, and topic explanations in clear, professional English.

Generate a JSON object with:
1. "title": A professional, descriptive title for the meeting.
2. "executive_summary": A high-level 1-2 paragraph summary capturing the purpose, context, and key outcomes.
3. "key_decisions": A list of key agreements or decisions made.
4. "action_items": An array of objects, where each object has:
   - "task": The action description.
   - "assignee": The person assigned to it.
   - "priority": High, Medium, or Low.
5. "topics": An array of objects detailing the agenda or discussion topics, where each has:
   - "name": Topic title.
   - "summary": Summary of what was discussed.

Transcript:
{transcript_text}"""

    system_instruction = "You are an AI meeting summarization system. Synthesize the transcript and return only a JSON summary conforming to the requested schema."
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "executive_summary": {"type": "STRING"},
            "key_decisions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "action_items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "task": {"type": "STRING"},
                        "assignee": {"type": "STRING"},
                        "priority": {"type": "STRING"}
                    },
                    "required": ["task", "assignee", "priority"]
                }
            },
            "topics": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "summary": {"type": "STRING"}
                    },
                    "required": ["name", "summary"]
                }
            }
        },
        "required": ["title", "executive_summary", "key_decisions", "action_items", "topics"]
    }
    
    res = call_gemini(api_key, prompt, system_instruction, schema)
    if res:
        try:
            return json.loads(res)
        except Exception as e:
            print(f"⚠️ Failed to parse summary JSON: {e}")
            
    return None

# ── Main Pipeline ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="🎙️ Botzilla: Offline Meeting Diarizer & AI Summarizer")
    parser.add_argument("input_file", nargs="?", help="Input video or audio file path")
    parser.add_argument("--mode", "-m", choices=["UNIFIED", "AUDIO_ONLY", "SPLIT_STREAMS"], help="Pipeline mode")
    parser.add_argument("--video", "-v", help="Independent screen recording video path (for SPLIT_STREAMS)")
    parser.add_argument("--audio", "-a", help="Audio file path (for SPLIT_STREAMS or AUDIO_ONLY)")
    parser.add_argument("--offset", "-s", type=float, default=0.0, help="Video offset in seconds (for SPLIT_STREAMS)")
    parser.add_argument("--model", "-w", default=DEFAULT_WHISPER_MODEL, help="Whisper model size (tiny, base, small, medium, large-v3)")
    parser.add_argument("--lang", "-l", default=DEFAULT_LANGUAGE, help="Whisper language code ('en', 'hi', or None for auto-detect)")
    parser.add_argument("--hf-token", "-t", default=HF_TOKEN, help="Hugging Face API Token")
    parser.add_argument("--gemini-key", "-g", default=GEMINI_API_KEY, help="Gemini API Key")
    parser.add_argument("--num-speakers", "-n", type=int, help="Exact number of speakers if known")
    parser.add_argument("--min-speakers", type=int, default=2, help="Minimum speakers for diarization")
    parser.add_argument("--max-speakers", type=int, default=10, help="Maximum speakers for diarization")
    
    args = parser.parse_args()
    
    # ── Auto-Detect Inputs and Modes ──
    mode = args.mode
    video_file = args.video
    audio_file = args.audio
    input_file = args.input_file
    
    if input_file:
        ext = os.path.splitext(input_file)[1].lower()
        if ext in {".mp4", ".webm", ".avi", ".mov", ".mkv"}:
            if not video_file:
                video_file = input_file
        else:
            if not audio_file:
                audio_file = input_file
                
    if not mode:
        if video_file and audio_file:
            mode = "SPLIT_STREAMS"
        elif video_file:
            mode = "UNIFIED"
        elif audio_file:
            mode = "AUDIO_ONLY"
        else:
            print("❌ Error: No inputs provided. Please supply an input file or use --audio/--video.")
            parser.print_help()
            sys.exit(1)
            
    print(f"🤖 Botzilla Run Configuration:")
    print(f"   Mode: {mode}")
    print(f"   Video File: {video_file}")
    print(f"   Audio File: {audio_file}")
    
    # ── Input Validation & Extraction ──
    if mode == "UNIFIED":
        if not video_file or not os.path.isfile(video_file):
            print(f"❌ Error: Video file not found: {video_file}")
            sys.exit(1)
        audio_file = "extracted_audio.wav"
        print("🎵 Extracting audio from unified video file using FFmpeg...")
        subprocess.run(["ffmpeg.exe", "-i", video_file, "-q:a", "0", "-map", "a", audio_file, "-y", "-loglevel", "error"])
        print("✅ Audio extracted!")
        
    elif mode == "AUDIO_ONLY":
        if not audio_file or not os.path.isfile(audio_file):
            print(f"❌ Error: Audio file not found: {audio_file}")
            sys.exit(1)
            
    elif mode == "SPLIT_STREAMS":
        if not video_file or not os.path.isfile(video_file):
            print(f"❌ Error: Screen recording video file not found: {video_file}")
            sys.exit(1)
        if not audio_file or not os.path.isfile(audio_file):
            print(f"❌ Error: Full meeting audio file not found: {audio_file}")
            sys.exit(1)
            
    # Setup paths
    base_output_name = os.path.splitext(video_file if video_file else audio_file)[0]
    json_output_path = f"{base_output_name}_botzilla.json"
    slides_dir = f"{base_output_name}_slides"
    
    # ── Step 1: Slide Extraction ──
    slides = []
    if mode in ["UNIFIED", "SPLIT_STREAMS"] and video_file:
        slides = extract_slides_smart(video_file, slides_dir, sample_interval_sec=2.0, offset_sec=args.offset)
        
    # ── Step 2: Transcription with WhisperX ──
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "float32"
    
    print(f"\n🔄 Loading Whisper model '{args.model}' on {device.upper()}...")
    asr_options = {
        "temperatures": [0.0],
        "condition_on_previous_text": False,
        "initial_prompt": INITIAL_PROMPT,
        "no_speech_threshold": 0.6,
        "log_prob_threshold": -1.0
    }
    
    model = whisperx.load_model(
        args.model,
        device,
        compute_type=compute_type,
        language=args.lang if args.lang != "None" else None,
        asr_options=asr_options
    )
    
    print("🔄 Loading audio file...")
    audio = whisperx.load_audio(audio_file)
    print("🔄 Transcribing meet audio...")
    result = model.transcribe(audio, batch_size=16, print_progress=True)
    detected_lang = result.get("language", args.lang)
    print(f"✅ Transcription done! Language: {detected_lang} | Segments: {len(result['segments'])}")
    
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    # ── Step 3: Align Timestamps ──
    print("\n🔄 Aligning timestamps (word-level accuracy)...")
    model_a, alignment_metadata = whisperx.load_align_model(language_code=detected_lang, device=device)
    result = whisperx.align(result["segments"], model_a, alignment_metadata, audio, device, return_char_alignments=False)
    print("✅ Alignment complete!")
    
    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    # ── Step 4: Speaker Diarization with Pyannote ──
    print("\n🔄 Running Pyannote diarization...")
    if not args.hf_token:
        print("❌ Error: Hugging Face Token required for diarization. Set it in .env or pass --hf-token.")
        sys.exit(1)
        
    diarize_model = whisperx.diarize.DiarizationPipeline(token=args.hf_token, device=device)
    
    diarize_kwargs = {}
    if args.num_speakers is not None:
        diarize_kwargs["num_speakers"] = args.num_speakers
    else:
        diarize_kwargs["min_speakers"] = args.min_speakers
        diarize_kwargs["max_speakers"] = args.max_speakers
        
    diarize_segments = diarize_model(audio_file, **diarize_kwargs)
    result = whisperx.assign_word_speakers(diarize_segments, result)
    print("✅ Diarization complete!")
    
    del diarize_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
        
    # ── Step 5: Merge Consecutive Speaker Segments ──
    print("\n🔄 Formatting and merging consecutive segments...")
    merged_segments = []
    for seg in result["segments"]:
        spk = seg.get("speaker", "UNKNOWN")
        # Merge segments if the speaker is the same and gap is less than 2.0s
        if merged_segments and merged_segments[-1]["speaker"] == spk and (seg["start"] - merged_segments[-1]["end"]) < 2.0:
            merged_segments[-1]["end"] = seg["end"]
            merged_segments[-1]["text"] += " " + seg["text"].strip()
        else:
            merged_segments.append({
                "speaker": spk,
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip()
            })
            
    # ── Step 6: Gemini Speaker Name Resolution & AI Summary ──
    # Resolve speaker name mapping
    speaker_mapping = resolve_speaker_names(args.gemini_key, merged_segments)
    
    # Fill defaults for remaining speakers: Map SPEAKER_00 -> "Speaker 1" or keep resolved name
    unique_speakers = sorted(list({seg["speaker"] for seg in merged_segments}))
    idx = 1
    final_speaker_mapping = {}
    for spk in unique_speakers:
        if spk in speaker_mapping:
            final_speaker_mapping[spk] = speaker_mapping[spk]
        else:
            final_speaker_mapping[spk] = f"Speaker {idx}"
            idx += 1
            
    # Rename speakers in transcript segments directly
    for seg in merged_segments:
        seg["speaker"] = final_speaker_mapping.get(seg["speaker"], seg["speaker"])
        
    # Generate meeting summary using Gemini
    ai_summary = generate_ai_summary(args.gemini_key, merged_segments)
    
    # Fallback heuristic summary (if Gemini failed or was skipped)
    if not ai_summary:
        print("💡 Falling back to rule-based summary heuristic...")
        # Simple summary values
        ai_summary = {
            "title": f"Meeting Report ({os.path.basename(video_file if video_file else audio_file)})",
            "executive_summary": f"This meeting lasted {len(audio)/16000/60:.1f} minutes. "
                                 f"Diarization identified {len(final_speaker_mapping)} participants. "
                                 f"Below is the full transcript with speaker identification.",
            "key_decisions": [],
            "action_items": [],
            "topics": [
                {
                    "name": "General Discussion",
                    "summary": "The participants discussed various items throughout the duration of the meeting."
                }
            ]
        }
        
    # ── Step 7: Populate Pydantic Schema and Export ──
    pydantic_slides = [SlideSnapshot(**s) for s in slides]
    pydantic_transcript = []
    
    for seg in merged_segments:
        # Improved slide matching: Find all slides shown *during* this segment.
        active_slides = [s.image_path for s in pydantic_slides if seg["start"] <= s.timestamp_sec <= seg["end"]]
        
        # If no slides were shown during this segment, find the most recent slide shown before it.
        if not active_slides and pydantic_slides:
            most_recent = None
            for s in pydantic_slides:
                if s.timestamp_sec <= seg["start"]:
                    most_recent = s.image_path
                else:
                    break
            if most_recent:
                active_slides.append(most_recent)
                
        pydantic_transcript.append(TranscriptSegment(
            speaker=seg["speaker"],
            start=seg["start"],
            end=seg["end"],
            text=seg["text"],
            slides_shown=active_slides
        ))
        
    summary_model = BotzillaSummary(
        title=ai_summary["title"],
        executive_summary=ai_summary["executive_summary"],
        key_decisions=ai_summary["key_decisions"],
        action_items=[ActionItem(**item) for item in ai_summary["action_items"]],
        topics=[TopicDiscussion(**top) for top in ai_summary["topics"]]
    )
    
    final_report = BotzillaReport(
        metadata=BotzillaMetadata(
            pipeline_mode=mode,
            audio_file=audio_file,
            video_file=video_file,
            video_offset_seconds=args.offset if mode == "SPLIT_STREAMS" else 0.0,
            language=detected_lang,
            num_slides_extracted=len(pydantic_slides)
        ),
        slides=pydantic_slides,
        transcript=pydantic_transcript,
        speaker_mapping=final_speaker_mapping,
        summary=summary_model
    )
    
    # Save Report JSON
    with open(json_output_path, "w", encoding="utf-8") as f:
        f.write(final_report.model_dump_json(indent=2))
        
    print(f"\n🎉 Pipeline Complete! Exported JSON report to: {json_output_path}")
    print(f"   Next step: Run 'python generate_docx.py {json_output_path}' to create the Word document summary.")

if __name__ == "__main__":
    main()
