# 🎙️ Meeting Diarizer — WhisperX + Pyannote on Google Colab

Transcribe meeting audio and label each speaker (Speaker 1, Speaker 2, etc.) using **fully open-source** models.

**Stack:** WhisperX (OpenAI Whisper + forced alignment + Pyannote diarization)

---

## Prerequisites

Before you start, you need **one thing**: a free HuggingFace account with a token.

### Get Your HuggingFace Token (2 minutes)

1. **Create account** → [huggingface.co/join](https://huggingface.co/join)
2. **Create token** → [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Click "New token"
   - Name: anything (e.g., `diarizer`)
   - Type: `Read`
   - Click "Generate"
   - **Copy the token** (starts with `hf_...`)
3. **Accept model licenses** (click "Agree" on each page):
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

> ⚠️ **You MUST accept both model licenses**, or diarization will fail with a 401 error.

---

## Step-by-Step: Running in Google Colab

### Step 1: Open Google Colab

Go to [colab.research.google.com](https://colab.research.google.com) → **New Notebook**

### Step 2: Enable GPU

1. Click **Runtime** → **Change runtime type**
2. Set **Hardware accelerator** to **T4 GPU**
3. Click **Save**

### Step 3: Create the cells

Copy each section from `diarizer_colab.py` into **separate Colab cells** (each section starts with `# %%`). You will have **9 cells total**.

Alternatively, you can upload the whole `.py` file and run it, but **cells are recommended** so you can fix issues one step at a time.

### Step 4: Run Cell 1 — Install Dependencies

**Before running**, uncomment the pip install lines (remove the `# ` before each `!pip` line):

```python
# Don't install torch — Colab already has it with CUDA!
!pip install -q "numpy==2.0.2" "pandas==2.2.3" git+https://github.com/m-bain/whisperX.git
```

> ⚠️ **Important:** Do NOT install torch/torchaudio manually. Colab's pre-installed version works. Installing a different version will break CUDA.

Run the cell. Wait ~2-3 minutes for installation. You should see:

```
✅ PyTorch version: 2.x.x+cu121
✅ CUDA available: True
✅ GPU: Tesla T4
✅ VRAM: 15.8 GB
```

> If you see `❌ No GPU detected`, go back to Step 2.

### Step 5: Run Cell 2 — Configuration

1. **Paste your HuggingFace token** in the `HF_TOKEN` variable:
   ```python
   HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxx"
   ```

2. **Adjust settings** (optional):
   - `WHISPER_MODEL` — Use `"large-v3"` for best accuracy, `"medium"` if you get memory errors
   - `LANGUAGE` — Set to `"en"` for English, or `None` for auto-detect
   - `NUM_SPEAKERS` — Set to exact count if known (e.g., `3`), or leave `None`

3. Run the cell.

### Step 6: Run Cell 3 — Upload Audio

- Run the cell → a file picker appears
- Select your meeting recording (.wav, .mp3, .m4a, etc.)
- Wait for upload to complete

> 💡 **Tip:** .wav files give best results. If your file is .mp4 video, that works too — audio will be extracted automatically.

### Step 7: Run Cell 4 — Transcribe

- This runs Whisper on your audio
- Takes **~1-5 minutes** depending on audio length
- You'll see progress as it processes

> ⚠️ **Out of Memory?** Change `BATCH_SIZE = 8` or use `WHISPER_MODEL = "medium"` in Cell 2, then restart from Cell 4.

### Step 8: Run Cell 5 — Align Timestamps

- Improves timestamp accuracy with forced alignment
- Takes ~30 seconds
- Quick step, just run it

### Step 9: Run Cell 6 — Diarize (Speaker Identification)

- This is where the magic happens — Pyannote identifies who is speaking
- First run downloads model weights (~300MB)
- Takes ~1-3 minutes

You should see:
```
✅ Diarization complete!
   Speakers found: 3 → ['SPEAKER_00', 'SPEAKER_01', 'SPEAKER_02']
```

### Step 10: Run Cell 7 — View Results

Displays the formatted transcript:

```
======================================================================
📝 MEETING TRANSCRIPT WITH SPEAKER LABELS
======================================================================

🎤 SPEAKER_00 [00:00 → 00:15]
   Good morning everyone, let's start with the project update.

🎤 SPEAKER_01 [00:16 → 00:32]
   Sure. We completed the API integration last week and...

🎤 SPEAKER_02 [00:33 → 00:45]
   I have a question about the timeline for phase two.
```

### Step 11: Run Cell 8 — Export & Download

Automatically exports and downloads 3 files:

| File | Format | Use Case |
|------|--------|----------|
| `*_transcript.txt` | Plain text | Human reading |
| `*_transcript.srt` | SRT subtitles | Video subtitling |
| `*_transcript.json` | JSON | Feed into your pipeline / LLM summarizer |

### Step 12 (Optional): Run Cell 9 — Debug Inspector

Shows a table of all raw segments with speaker distribution stats. Useful for debugging.

---

## JSON Output Format

The JSON export is structured for easy pipeline integration:

```json
{
  "audio_file": "meeting.wav",
  "language": "en",
  "num_speakers": 3,
  "speakers": ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"],
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 15.23,
      "text": "Good morning everyone, let's start with the project update."
    },
    {
      "speaker": "SPEAKER_01",
      "start": 16.01,
      "end": 32.45,
      "text": "Sure. We completed the API integration last week..."
    }
  ]
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `❌ No GPU detected` | Runtime → Change runtime type → GPU (T4) |
| `CUDA out of memory` | Use `WHISPER_MODEL = "medium"` and `BATCH_SIZE = 8` |
| `401 Unauthorized` | Your HF token is wrong OR you didn't accept the Pyannote model licenses |
| `FileNotFoundError` | Re-run Cell 3 to re-upload your audio file |
| `ModuleNotFoundError` | Re-run Cell 1 (installs may have failed) |
| Speakers are wrong | Try setting `NUM_SPEAKERS` to the exact count in Cell 2 |
| Audio not supported | Convert to .wav first: `ffmpeg -i input.mp4 output.wav` |
| Colab disconnected | Re-run all cells from Cell 1 (Colab loses state on disconnect) |

---

## Tips for Better Results

1. **Clean audio = better results.** Reduce background noise if possible.
2. **Set speaker count** if you know it — `NUM_SPEAKERS = 4` is more accurate than auto-detect.
3. **Use `large-v3`** for production quality. Only drop to `medium` if you hit memory limits.
4. **Short files (<1 min)** may have poor diarization — Pyannote needs enough audio to distinguish speakers.
5. **Multiple languages** in one meeting? Set `LANGUAGE = None` for auto-detection.

---

## What Next?

Once you have the JSON output, you can feed it into an LLM (GPT-4, Gemini, etc.) to:
- Generate meeting summaries
- Extract action items
- Create meeting minutes
- Identify key decisions

Example prompt for your summarizer:
```
Given this meeting transcript with speaker labels, generate:
1. A brief summary (3-5 sentences)
2. Key decisions made
3. Action items with assigned speakers
4. Follow-up topics

Transcript:
{paste JSON segments here}
```
