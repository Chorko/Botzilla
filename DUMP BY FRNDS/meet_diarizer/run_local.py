#!/usr/bin/env python3
"""
🎙️ Meeting Diarizer — Local Edition
WhisperX + Pyannote — runs fully offline on CPU or GPU.

Usage:
    python run_local.py <audio_file>
    python run_local.py                   # will prompt for file path
"""

import sys
import os
import json
import gc
import time

HF_TOKEN = os.getenv("HF_TOKEN", "")

# Whisper model: "tiny", "base", "small", "medium", "large-v3"
# CPU recommendation: "base" (fast) or "small" (better accuracy, ~2x slower)
# GPU recommendation: "large-v3" (best accuracy)
WHISPER_MODEL = "base"  # change to "large-v3" if you have a GPU

# Language code — set to None for auto-detect
LANGUAGE = "en"

# Speaker settings
NUM_SPEAKERS = None   # set to exact count if known (e.g. 3)
MIN_SPEAKERS = 2
MAX_SPEAKERS = 10

# Batch size (lower if OOM errors; only matters for GPU)
BATCH_SIZE = 16

SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── Main Pipeline ────────────────────────────────────────────────────────────

def main():
    import torch
    import whisperx

    # --- Get audio file path ---
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        audio_file = input("📁 Enter the path to your audio file: ").strip().strip('"')

    if not os.path.isfile(audio_file):
        print(f"❌ File not found: {audio_file}")
        sys.exit(1)

    file_ext = os.path.splitext(audio_file)[1].lower()
    file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)

    print(f"\n✅ Audio file: {audio_file}")
    print(f"   Size: {file_size_mb:.1f} MB")
    if file_ext not in SUPPORTED_FORMATS:
        print(f"⚠️  Warning: '{file_ext}' may not be supported. Best with .wav or .mp3")

    # --- Device setup ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "float32"

    print(f"\n{'='*60}")
    print(f"🖥️  Device: {device.upper()}")
    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"   Model: {WHISPER_MODEL} | Compute: {compute_type}")
    print(f"{'='*60}\n")

    # ── Step 1: Transcribe ───────────────────────────────────────────────
    t0 = time.time()
    print(f"🔄 [1/4] Loading Whisper model '{WHISPER_MODEL}'...")
    model = whisperx.load_model(
        WHISPER_MODEL,
        device,
        compute_type=compute_type,
        language=LANGUAGE,
    )

    print("🔄 [1/4] Loading audio...")
    audio = whisperx.load_audio(audio_file)
    duration_min = len(audio) / 16000 / 60
    print(f"   Duration: {duration_min:.1f} minutes")

    print("🔄 [1/4] Transcribing... (this may take a while on CPU)")
    result = model.transcribe(audio, batch_size=BATCH_SIZE)

    detected_lang = result.get("language", LANGUAGE)
    print(f"✅ [1/4] Transcription done — {len(result['segments'])} segments, lang={detected_lang}")
    print(f"   ⏱️  {time.time() - t0:.1f}s elapsed")

    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # ── Step 2: Align Timestamps ─────────────────────────────────────────
    t1 = time.time()
    print(f"\n🔄 [2/4] Loading alignment model...")
    model_a, metadata = whisperx.load_align_model(
        language_code=detected_lang,
        device=device,
    )

    print("🔄 [2/4] Aligning transcription...")
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    print(f"✅ [2/4] Alignment done — {len(result['segments'])} segments")
    print(f"   ⏱️  {time.time() - t1:.1f}s elapsed")

    del model_a
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # ── Step 3: Diarize (Speaker ID) ─────────────────────────────────────
    t2 = time.time()
    print(f"\n🔄 [3/4] Loading diarization model (Pyannote)...")
    print("   (First run downloads ~300MB of model weights)")
    diarize_model = whisperx.diarize.DiarizationPipeline(
        token=HF_TOKEN,
        device=device,
    )

    diarize_kwargs = {}
    if NUM_SPEAKERS is not None:
        diarize_kwargs["num_speakers"] = NUM_SPEAKERS
    else:
        if MIN_SPEAKERS is not None:
            diarize_kwargs["min_speakers"] = MIN_SPEAKERS
        if MAX_SPEAKERS is not None:
            diarize_kwargs["max_speakers"] = MAX_SPEAKERS

    print("🔄 [3/4] Diarizing... (identifying speakers)")
    diarize_segments = diarize_model(audio_file, **diarize_kwargs)

    result = whisperx.assign_word_speakers(diarize_segments, result)

    speakers = set()
    for seg in result["segments"]:
        if "speaker" in seg:
            speakers.add(seg["speaker"])

    print(f"✅ [3/4] Diarization done — {len(speakers)} speakers: {sorted(speakers)}")
    print(f"   ⏱️  {time.time() - t2:.1f}s elapsed")

    del diarize_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    # ── Step 4: Display + Export ──────────────────────────────────────────
    print(f"\n🔄 [4/4] Formatting and exporting results...\n")

    merged_segments = merge_consecutive_segments(result["segments"])

    # Print transcript
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

    # --- Export files ---
    base_name = os.path.splitext(audio_file)[0]

    # TXT
    txt_path = f"{base_name}_transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("MEETING TRANSCRIPT\n")
        f.write(f"File: {audio_file}\n")
        f.write(f"Speakers: {len(speakers)}\n")
        f.write("=" * 60 + "\n\n")
        for seg in merged_segments:
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            f.write(f"{seg['speaker']} [{start} → {end}]\n")
            f.write(f"{seg['text']}\n\n")
    print(f"\n✅ Saved: {txt_path}")

    # SRT
    srt_path = f"{base_name}_transcript.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(merged_segments, 1):
            start_s = seg["start"]
            end_s = seg["end"]
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

    # JSON
    json_path = f"{base_name}_transcript.json"
    export_data = {
        "audio_file": audio_file,
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

    total_time = time.time() - t0
    print(f"\n🎉 All done! Total time: {total_time:.1f}s")
    print(f"   Files saved next to your audio file.")


if __name__ == "__main__":
    main()
