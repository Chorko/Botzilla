# =============================================================================
# 🎙️ Meeting Diarizer — WhisperX + Pyannote (Google Colab)
# =============================================================================
# Copy each section into a separate Colab cell and run them in order.
# Make sure your Colab runtime is set to GPU (T4 is fine).
#
# Runtime → Change runtime type → GPU (T4)
# =============================================================================


# %%  ========== CELL 1: Install Dependencies ==========
# Run this cell first. It takes ~2-3 minutes.
# ⚠️ UNCOMMENT the lines below (remove the leading #) before running!

# NOTE: Do NOT install torch — Colab already has a compatible version with CUDA.
# Installing whisperX from GitHub (the PyPI version is yanked/unofficial).
# This automatically pulls the correct pyannote.audio version.

# !pip install -q "numpy==2.0.2" "pandas==2.2.3" git+https://github.com/m-bain/whisperX.git

# Verify GPU is available
import torch
print(f"✅ PyTorch version: {torch.__version__}")
print(f"✅ CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✅ VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
else:
    raise RuntimeError("❌ No GPU detected! Go to Runtime → Change runtime type → GPU")


# %%  ========== CELL 2: Configuration ==========
# ⚠️ EDIT THESE VALUES BEFORE RUNNING

import os

# ----------------------------------------------------------------------
# REQUIRED: Your HuggingFace token (free)
# 1. Go to https://huggingface.co/settings/tokens
# 2. Create a token (read access is enough)
# 3. Accept the model licenses:
#    - https://huggingface.co/pyannote/speaker-diarization-3.1
#    - https://huggingface.co/pyannote/segmentation-3.0
# 4. Paste your token below
# ----------------------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Whisper model size: "tiny", "base", "small", "medium", "large-v3"
# Bigger = more accurate but slower. "large-v3" recommended for meetings.
WHISPER_MODEL = "large-v3"

# Language code (e.g., "en", "hi", "es", "fr", "de")
# Set to None for auto-detection
LANGUAGE = "en"

# Expected number of speakers (set to None for auto-detect)
# Setting this improves accuracy if you know the count
NUM_SPEAKERS = None  # e.g., 3 for a 3-person meeting

# Min/Max speakers (used only if NUM_SPEAKERS is None)
MIN_SPEAKERS = 2
MAX_SPEAKERS = 10

# Batch size for transcription (lower if you get OOM errors)
BATCH_SIZE = 16

# Compute type: "float16" for GPU, "int8" for less VRAM, "float32" for CPU
COMPUTE_TYPE = "float16"

# Validate token
if HF_TOKEN == "YOUR_HF_TOKEN_HERE" or not HF_TOKEN:
    raise ValueError(
        "❌ You must set your HuggingFace token!\n"
        "   1. Go to https://huggingface.co/settings/tokens\n"
        "   2. Create a token and paste it in the HF_TOKEN variable above.\n"
        "   3. Accept the pyannote model licenses (links in comments above)."
    )

print("✅ Configuration set!")
print(f"   Model: {WHISPER_MODEL}")
print(f"   Language: {LANGUAGE or 'auto-detect'}")
print(f"   Speakers: {NUM_SPEAKERS or f'auto-detect ({MIN_SPEAKERS}-{MAX_SPEAKERS})'}")


# %%  ========== CELL 3: Upload Audio File ==========
# This cell lets you upload your meeting audio file.
# Supported formats: .wav, .mp3, .m4a, .flac, .ogg, .webm, .mp4

from google.colab import files
import os

print("📁 Upload your meeting audio file...")
print("   Supported: .wav, .mp3, .m4a, .flac, .ogg, .webm, .mp4\n")

uploaded = files.upload()

if not uploaded:
    raise ValueError("❌ No file uploaded! Run this cell again and select a file.")

AUDIO_FILE = list(uploaded.keys())[0]
file_size_mb = os.path.getsize(AUDIO_FILE) / (1024 * 1024)

print(f"\n✅ Uploaded: {AUDIO_FILE}")
print(f"   Size: {file_size_mb:.1f} MB")

SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}
file_ext = os.path.splitext(AUDIO_FILE)[1].lower()
if file_ext not in SUPPORTED_FORMATS:
    print(f"⚠️  Warning: '{file_ext}' may not be supported. Best results with .wav or .mp3")


# %%  ========== CELL 4: Transcribe with Whisper ==========
# This transcribes the audio into text with timestamps.
# Takes ~1-5 minutes depending on audio length and model size.

import whisperx
import torch
import gc

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🔄 Loading Whisper model '{WHISPER_MODEL}'...")
print(f"   Device: {device} | Compute: {COMPUTE_TYPE} | Batch: {BATCH_SIZE}\n")

# Load model
model = whisperx.load_model(
    WHISPER_MODEL,
    device,
    compute_type=COMPUTE_TYPE,
    language=LANGUAGE,
)

# Load audio
print("🔄 Loading audio...")
audio = whisperx.load_audio(AUDIO_FILE)
duration_min = len(audio) / 16000 / 60
print(f"   Duration: {duration_min:.1f} minutes\n")

# Transcribe
print("🔄 Transcribing... (this may take a few minutes)")
result = model.transcribe(audio, batch_size=BATCH_SIZE)

detected_lang = result.get("language", LANGUAGE)
num_segments = len(result["segments"])
print(f"\n✅ Transcription complete!")
print(f"   Language detected: {detected_lang}")
print(f"   Segments: {num_segments}")

# Free GPU memory — we don't need the Whisper model anymore
del model
gc.collect()
torch.cuda.empty_cache()
print("   (Whisper model unloaded to free VRAM)")


# %%  ========== CELL 5: Align Timestamps ==========
# Improves word-level timestamp accuracy using forced alignment.

import whisperx

print("🔄 Loading alignment model...")
model_a, metadata = whisperx.load_align_model(
    language_code=detected_lang,
    device=device,
)

print("🔄 Aligning transcription...")
result = whisperx.align(
    result["segments"],
    model_a,
    metadata,
    audio,
    device,
    return_char_alignments=False,
)

print(f"✅ Alignment complete! Segments: {len(result['segments'])}")

# Free alignment model
del model_a
gc.collect()
torch.cuda.empty_cache()
print("   (Alignment model unloaded to free VRAM)")


# %%  ========== CELL 6: Diarize (Identify Speakers) ==========
# This identifies WHO is speaking WHEN using Pyannote.

import whisperx

print("🔄 Loading diarization model (Pyannote)...")
print("   (First run downloads ~300MB of model weights)\n")

diarize_model = whisperx.diarize.DiarizationPipeline(
    token=HF_TOKEN,
    device=device,
)

# Build diarization kwargs
diarize_kwargs = {}
if NUM_SPEAKERS is not None:
    diarize_kwargs["num_speakers"] = NUM_SPEAKERS
else:
    if MIN_SPEAKERS is not None:
        diarize_kwargs["min_speakers"] = MIN_SPEAKERS
    if MAX_SPEAKERS is not None:
        diarize_kwargs["max_speakers"] = MAX_SPEAKERS

print("🔄 Diarizing... (identifying speakers)")
diarize_segments = diarize_model(AUDIO_FILE, **diarize_kwargs)

# Assign speakers to transcript segments
result = whisperx.assign_word_speakers(diarize_segments, result)

# Count unique speakers
speakers = set()
for seg in result["segments"]:
    if "speaker" in seg:
        speakers.add(seg["speaker"])

print(f"\n✅ Diarization complete!")
print(f"   Speakers found: {len(speakers)} → {sorted(speakers)}")

# Free diarization model
del diarize_model
gc.collect()
torch.cuda.empty_cache()


# %%  ========== CELL 7: Display Results ==========
# Pretty-prints the speaker-labeled transcript.

def format_timestamp(seconds):
    """Convert seconds to MM:SS or HH:MM:SS format."""
    if seconds is None:
        return "??:??"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def merge_consecutive_segments(segments, max_gap=1.5):
    """
    Merge consecutive segments from the same speaker
    if the gap between them is less than max_gap seconds.
    This makes the output much cleaner and more readable.
    """
    if not segments:
        return []

    merged = []
    current = {
        "speaker": segments[0].get("speaker", "UNKNOWN"),
        "start": segments[0].get("start", 0),
        "end": segments[0].get("end", 0),
        "text": segments[0].get("text", "").strip(),
    }

    for seg in segments[1:]:
        speaker = seg.get("speaker", "UNKNOWN")
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()

        # Same speaker and small gap → merge
        if speaker == current["speaker"] and (start - current["end"]) < max_gap:
            current["end"] = end
            current["text"] += " " + text
        else:
            merged.append(current)
            current = {
                "speaker": speaker,
                "start": start,
                "end": end,
                "text": text,
            }

    merged.append(current)
    return merged


# Merge and display
merged_segments = merge_consecutive_segments(result["segments"])

print("=" * 70)
print("📝 MEETING TRANSCRIPT WITH SPEAKER LABELS")
print("=" * 70)
print()

for seg in merged_segments:
    speaker = seg["speaker"]
    start = format_timestamp(seg["start"])
    end = format_timestamp(seg["end"])
    text = seg["text"]
    print(f"🎤 {speaker} [{start} → {end}]")
    print(f"   {text}\n")

print("=" * 70)
print(f"Total segments: {len(merged_segments)} | Speakers: {len(speakers)}")
print("=" * 70)


# %%  ========== CELL 8: Export Results ==========
# Exports the transcript in multiple formats: TXT, SRT, JSON

import json
import os

base_name = os.path.splitext(AUDIO_FILE)[0]

# --- Export as plain text ---
txt_path = f"{base_name}_transcript.txt"
with open(txt_path, "w", encoding="utf-8") as f:
    f.write("MEETING TRANSCRIPT\n")
    f.write(f"File: {AUDIO_FILE}\n")
    f.write(f"Speakers: {len(speakers)}\n")
    f.write("=" * 60 + "\n\n")
    for seg in merged_segments:
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        f.write(f"{seg['speaker']} [{start} → {end}]\n")
        f.write(f"{seg['text']}\n\n")

print(f"✅ Saved: {txt_path}")

# --- Export as SRT (subtitle format) ---
srt_path = f"{base_name}_transcript.srt"
with open(srt_path, "w", encoding="utf-8") as f:
    for i, seg in enumerate(merged_segments, 1):
        start_s = seg["start"]
        end_s = seg["end"]
        # SRT timestamp format: HH:MM:SS,mmm
        start_srt = (
            f"{int(start_s//3600):02d}:{int((start_s%3600)//60):02d}"
            f":{int(start_s%60):02d},{int((start_s%1)*1000):03d}"
        )
        end_srt = (
            f"{int(end_s//3600):02d}:{int((end_s%3600)//60):02d}"
            f":{int(end_s%60):02d},{int((end_s%1)*1000):03d}"
        )
        f.write(f"{i}\n")
        f.write(f"{start_srt} --> {end_srt}\n")
        f.write(f"[{seg['speaker']}] {seg['text']}\n\n")

print(f"✅ Saved: {srt_path}")

# --- Export as JSON (for your pipeline) ---
json_path = f"{base_name}_transcript.json"
export_data = {
    "audio_file": AUDIO_FILE,
    "language": detected_lang,
    "num_speakers": len(speakers),
    "speakers": sorted(list(speakers)),
    "segments": [
        {
            "speaker": seg["speaker"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"],
        }
        for seg in merged_segments
    ],
}

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(export_data, f, indent=2, ensure_ascii=False)

print(f"✅ Saved: {json_path}")

# --- Download all files ---
print("\n📥 Downloading files...")
from google.colab import files

files.download(txt_path)
files.download(srt_path)
files.download(json_path)

print("\n🎉 Done! Check your downloads folder.")


# %%  ========== CELL 9 (OPTIONAL): Raw Segment Inspector ==========
# Use this to inspect the raw (un-merged) segments for debugging.

import pandas as pd

rows = []
for seg in result["segments"]:
    rows.append({
        "Speaker": seg.get("speaker", "UNKNOWN"),
        "Start": round(seg.get("start", 0), 2),
        "End": round(seg.get("end", 0), 2),
        "Duration": round(seg.get("end", 0) - seg.get("start", 0), 2),
        "Text": seg.get("text", "").strip(),
    })

df = pd.DataFrame(rows)
print(f"Raw segments: {len(df)}")
print(f"Speaker distribution:\n{df['Speaker'].value_counts()}\n")
df.head(20)
