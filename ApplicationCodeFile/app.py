from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import math
import datetime
import os
import shutil
import re
from ocr_processor import extract_grid_text
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Add CoreExecutionBinary to system PATH dynamically so ffmpeg/ffprobe can be run by subprocess
binary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CoreExecutionBinary"))
if binary_path not in os.environ["PATH"]:
    os.environ["PATH"] = binary_path + os.pathsep + os.environ["PATH"]

app = FastAPI()

def get_db_status(filename):
    if not supabase: return "idle", None
    try:
        response = supabase.table("video_outputs").select("*").eq("video_name", filename).execute()
        if response.data:
            return response.data[0].get("status", "idle"), response.data[0]
    except Exception as e:
        print(f"Supabase GET error: {e}")
    return "idle", None

def set_db_status(filename, status, urls=None):
    if not supabase: return
    try:
        data = {"video_name": filename, "status": status}
        if urls:
            data.update(urls)
        existing = supabase.table("video_outputs").select("id").eq("video_name", filename).execute()
        if existing.data:
            supabase.table("video_outputs").update(data).eq("video_name", filename).execute()
        else:
            supabase.table("video_outputs").insert(data).execute()
    except Exception as e:
        print(f"Supabase SET error: {e}")

def format_vtt_time(seconds):
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def advanced_chunk_processor(video_filename):
    video_basename = os.path.basename(video_filename)
    video_name, _ = os.path.splitext(video_basename)
    
    chunk_size = 30
    width, height, columns = 640, 360, 10
    
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", f"{video_name}_output"))
    os.makedirs(output_dir, exist_ok=True)
    
    temp_dir = f"temp_frames_{video_name}"
    output_image = os.path.join(output_dir, f"{video_name}_grid.png")
    output_vtt = os.path.join(output_dir, f"{video_name}_timeline_map.vtt")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_filename]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
        total_duration = float(duration_result.stdout.strip())
        
        frame_counter = 0
        timeline_entries = []

        for start_time in range(0, int(total_duration), chunk_size):
            chunk_name = f"temp_chunk_{video_name}_{start_time}.mp4"
            slice_cmd = ["ffmpeg", "-y", "-ss", str(start_time), "-i", video_filename, "-t", str(chunk_size), "-c", "copy", chunk_name]
            subprocess.run(slice_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            smart_filter = "select='isnan(prev_selected_t)+gte(t-prev_selected_t,7)+gt(scene,0.02)',scale=640:360:flags=lanczos,showinfo"
            extract_cmd = ["ffmpeg", "-y", "-i", chunk_name, "-vf", smart_filter, "-vsync", "vfr", os.path.join(temp_dir, "frame_%04d.png")]
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            chunk_frame_times = []
            for line in result.stderr.split('\n'):
                if "pts_time:" in line:
                    match = re.search(r"pts_time:([\d.]+)", line)
                    if match:
                        chunk_frame_times.append(float(match.group(1)))
            
            extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_")])
            for idx, filename in enumerate(extracted_files):
                os.rename(os.path.join(temp_dir, filename), os.path.join(temp_dir, f"global_{frame_counter:04d}.png"))
                timeline_entries.append(start_time + chunk_frame_times[idx])
                frame_counter += 1

            if os.path.exists(chunk_name):
                os.remove(chunk_name)

        if frame_counter > 0:
            max_rows = 32000 // height
            columns = max(10, math.ceil(frame_counter / max_rows))
            
            stitch_cmd = [
                "ffmpeg", "-y", "-i", os.path.join(temp_dir, "global_%04d.png"), 
                "-vf", f"tile={columns}x{math.ceil(frame_counter/columns)}", 
                output_image
            ]
            try:
                subprocess.run(stitch_cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"ffmpeg stitching failed: {e.stderr}")
            
            with open(output_vtt, "w") as vtt_file:
                vtt_file.write("WEBVTT\n\n")
                for i in range(frame_counter):
                    start_ts = format_vtt_time(timeline_entries[i])
                    end_time_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 7.0
                    end_ts = format_vtt_time(end_time_val)
                    x, y = (i % columns) * width, (i // columns) * height
                    vtt_file.write(f"{start_ts} --> {end_ts}\n{os.path.basename(output_image)}#xywh={x},{y},{width},{height}\n\n")
        
        # Trigger offline OCR ingestion layer
        print("🔍 Extracting text via local OCR pipeline...")
        extract_grid_text(video_name)

        urls = {}
        if supabase:
            print("☁️ Uploading assets to Supabase Storage...")
            bucket_name = "video-assets"
            files_to_upload = [
                f"{video_name}_grid.png",
                f"{video_name}_timeline_map.vtt",
                f"{video_name}_text_manifest.json",
                f"{video_name}_ocr_transcript.md"
            ]
            for fname in files_to_upload:
                fpath = os.path.join(output_dir, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        # Upload directly to the bucket root or under a folder
                        supabase.storage.from_(bucket_name).upload(f"{video_name}/{fname}", f, file_options={"upsert": "true", "content-type": "text/vtt" if fname.endswith(".vtt") else "image/png" if fname.endswith(".png") else "application/json" if fname.endswith(".json") else "text/markdown"})
                    
                    # Generate public URL
                    public_url = supabase.storage.from_(bucket_name).get_public_url(f"{video_name}/{fname}")
                    if "grid" in fname: urls["grid_url"] = public_url
                    elif "timeline" in fname: urls["vtt_url"] = public_url
                    elif "manifest" in fname: urls["json_url"] = public_url
                    elif "transcript" in fname: urls["md_url"] = public_url

        set_db_status(video_basename, "complete", urls)

        # Cleanup local outputs
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        print(f"✨ Backend processing completely finished for {video_basename}!")
    except Exception as e:
        set_db_status(video_basename, f"failed: {str(e)}")

# --- WEB ENDPOINTS ---

@app.get("/")
def serve_homepage():
    return FileResponse("index.html")

@app.get("/videos")
def list_videos():
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio"))
    if not os.path.exists(video_dir):
        return []
    return sorted([f for f in os.listdir(video_dir) if f.endswith(".mp4")])

@app.get("/videos/{filename}")
def serve_video(filename: str):
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", filename))
    if os.path.exists(video_path):
        return FileResponse(video_path)
    return JSONResponse(status_code=404, content={"message": "Video not found"})

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio"))
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)
    
    file_path = os.path.join(video_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"status": "success", "filename": file.filename}

@app.post("/process-video/{filename}")
def trigger_pipeline(filename: str, background_tasks: BackgroundTasks):
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", filename))
    if not os.path.exists(video_path):
        return JSONResponse(status_code=404, content={"status": "Video file not found"})
        
    status, _ = get_db_status(filename)
    if status == "processing":
        return {"status": "Already processing"}
    
    set_db_status(filename, "processing")
    background_tasks.add_task(advanced_chunk_processor, video_path)
    return {"status": "started"}

@app.get("/status/{filename}")
def get_status(filename: str):
    status, db_data = get_db_status(filename)
    
    if status == "complete" and db_data:
        return {
            "status": status,
            "grid_url": db_data.get("grid_url"),
            "vtt_url": db_data.get("vtt_url")
        }
        
    return {"status": status}

output_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
os.makedirs(output_base_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=output_base_dir), name="outputs")
app.mount("/", StaticFiles(directory="."), name="static")