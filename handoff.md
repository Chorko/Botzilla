# Project Handoff: Botzilla Meeting Summarizer

This document details all implemented features, engineering decisions, and verification steps taken so far.

---

## 1. Core Features & Implementation Details

### 1.1 Vite Hot Module Replacement (HMR) Watcher Bypass
- **Problem**: When the Python pipeline generated slide frame images or exported `report.json` to the output folders, the Vite watcher detected these file modifications, triggered a full page reload in the browser, and reset the React frontend state and progress bars.
- **Solution**: Updated [vite.config.ts](file:///d:/ai-meeting-summarizer/vite.config.ts) to ignore HMR watchers on the `output/`, `DUMP BY FRNDS/`, and `tmp/` directories.
- **Why we chose this**: Rather than moving the outputs outside of the public server folder, configuring `watch.ignored` keeps the workspace clean and cohesive while preventing browser resets.

### 1.2 SSE Progress Persistence & Connection Recovery
- **Problem**: A page refresh or momentary drop in connection severed the Server-Sent Events (SSE) progress stream, leaving the user with an idle loading bar even when the backend process was still running.
- **Solution**: Extracted the progress tracking code in [App.tsx](file:///d:/ai-meeting-summarizer/src/App.tsx) into a reusable `trackProgress(taskId)` function. When the task starts, the `taskId` is written to `localStorage`. On component mount, the app automatically reads the key and attempts to reconnect.
- **Why we chose this**: It provides client-side resilience against network drops and reloads without needing complex session management on the backend.

### 1.3 Automatic Word (.docx) Compilation on Disk
- **Problem**: The Python script only generated `report.json`, requiring a manual step to generate the Word document.
- **Solution**: Modified [run_botzilla_local.py](file:///d:/ai-meeting-summarizer/run_botzilla_local.py) to import the `generate_docx` function from [generate_docx.py](file:///d:/ai-meeting-summarizer/generate_docx.py) and compile the Word document (`report.docx`) automatically inside the task output directory upon completion.
- **Why we chose this**: This guarantees that the Word report is generated directly on the server file system for archiving and syncing, rather than relying on browser-triggered requests.

### 1.4 Dynamic Rules-Based Heuristic Fallback Summarizer
- **Problem**: When the Gemini API key was throttled (HTTP 429) or offline (HTTP 503), the python script fallback was completely static, returning a hardcoded mock sync meeting transcript (discussing Aarav, Rahul, and database locks) regardless of the user's uploaded video.
- **Solution**: Implemented a dynamic rules-based parser in Python that scans the actual transcribed text segments. It dynamically maps speakers and filters out decisions (looking for consensus keywords) and action items (using task/deadline keywords) from the **actual audio transcript** of the video.
- **Why we chose this**: It ensures that even when the AI API is rate-limited, the generated report reflects the actual content of the user's meeting instead of showing static placeholder texts.

### 1.5 System Library and Environment Fixes
- **Problem**: Package mismatches on the Windows host caused execution crashes:
  - `python-docx` was missing.
  - Protobuf version mismatch between TensorFlow and transformers caused `AttributeError: 'MessageFactory' object has no attribute 'GetPrototype'`.
  - NumPy version mismatch caused `ImportError` on loading C-extensions.
- **Solution**: Installed `python-docx`, downgraded `numpy` to `<2` (specifically `1.26.4`), and downgraded `protobuf` to `<5` (specifically `4.25.9`). We also made the stream wrapper initialization in [generate_docx.py](file:///d:/ai-meeting-summarizer/generate_docx.py) conditional.
- **KeyError Fix**: Fixed a `KeyError: 'end'` in the WhisperX segment merger where it tried to read `seg["end"]` but the key was stored as `endTime`.

---

## 2. File Directory structure Changes

- [requirements.txt](file:///d:/ai-meeting-summarizer/requirements.txt): Lists all required Python dependencies including `numpy<2`, `python-docx`, `torch`, `opencv-python`, and `whisperx` from its source repository.
- [run_botzilla_local.py](file:///d:/ai-meeting-summarizer/run_botzilla_local.py): Upgraded with dynamic fallback, automatic directory creation, and automatic DOCX compilation.
- [generate_docx.py](file:///d:/ai-meeting-summarizer/generate_docx.py): Stream wrapping was made conditional to avoid stream closure issues on import.

### 1.6 Environment Configuration (Why there are two `.env` files)
- **Root `.env`**: Used by the main Node/TypeScript backend (`server.ts`) and the orchestration script (`run_botzilla_local.py`). It contains credentials for Supabase integration (`SUPABASE_URL`, `SUPABASE_ANON_KEY`), Hugging Face (`HF_TOKEN` for PyAnnote diarization), and Gemini API (`GEMINI_API_KEY` for summary generation).
- **Nested `DUMP BY FRNDS/meet_diarizer/.env`**: Used by the standalone, modular scripts in that sub-folder (e.g. `diarizer_colab.py`). It contains the Hugging Face and Gemini API keys required to execute the standalone diarization scripts directly.
- **Why they are identical/both exist**: The standalone reference code runs from its own context inside the `DUMP BY FRNDS` sub-folder, while the main fullstack app runs from the root context. Both require access to the same Gemini and Hugging Face keys.
- **Git Safety**: Both files match the `.env*` pattern in [.gitignore](file:///d:/ai-meeting-summarizer/.gitignore) and are safely ignored from version control.

### 1.7 Known Issue: Supabase Sync Failure (Implementation Plan)
- **Symptom**: Ingested meetings are not populating the Supabase dashboard `meetings` table, despite the UI indicating success.
- **Diagnosis & Fix Strategy** (from [implementation_plan.md](file:///C:/Users/chork/.gemini/antigravity-ide/brain/956c4f67-5f68-41d7-8db3-3648cd160919/implementation_plan.md)):
  1. Inspect browser console/network tab to log exact response payloads from Supabase API requests.
  2. Verify Row-Level Security (RLS) policies on the `meetings` table.
  3. Ensure the `meeting-summaries` storage bucket is set up, public, and allows public anonymous inserts.
  4. Ensure anon key in credentials matches the active key in Supabase settings.
  5. Add rollback safety inside `App.tsx` so database inserts do not persist if file storage upload fails.

