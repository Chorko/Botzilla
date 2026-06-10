# from fastapi import FastAPI, BackgroundTasks
# from fastapi.responses import FileResponse, JSONResponse
# from fastapi.staticfiles import StaticFiles
# import subprocess
# import math
# import datetime
# import os
# import shutil
# import re

# # Add CoreExecutionBinary to system PATH dynamically so ffmpeg/ffprobe can be run by subprocess
# binary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CoreExecutionBinary"))
# if binary_path not in os.environ["PATH"]:
#     os.environ["PATH"] = binary_path + os.pathsep + os.environ["PATH"]

# app = FastAPI()

# # Global state tracker and file scan for multiple videos
# video_statuses = {}
# current_processing_video = None

# def scan_existing_outputs():
#     video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio"))
#     if os.path.exists(video_dir):
#         for filename in os.listdir(video_dir):
#             if filename.endswith(".mp4"):
#                 video_name, _ = os.path.splitext(filename)
#                 grid_path = f"{video_name}_grid.jpg"
#                 vtt_path = f"{video_name}_timeline_map.vtt"
#                 if os.path.exists(grid_path) and os.path.exists(vtt_path):
#                     video_statuses[filename] = "complete"
#                 else:
#                     video_statuses[filename] = "idle"

# scan_existing_outputs()

# def format_vtt_time(seconds):
#     td = datetime.timedelta(seconds=seconds)
#     hours, remainder = divmod(td.seconds, 3600)
#     minutes, secs = divmod(remainder, 60)
#     milliseconds = int((seconds - int(seconds)) * 1000)
#     return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

# def advanced_chunk_processor(video_filename):
#     global current_processing_video
#     video_basename = os.path.basename(video_filename)
#     video_name, _ = os.path.splitext(video_basename)
    
#     video_statuses[video_basename] = "processing"
#     current_processing_video = video_basename
    
#     chunk_size = 30
#     width, height, columns = 320, 180, 10
#     temp_dir = f"temp_frames_{video_name}"
#     output_image = f"{video_name}_grid.jpg"
#     output_vtt = f"{video_name}_timeline_map.vtt"
    
#     if os.path.exists(temp_dir):
#         shutil.rmtree(temp_dir)
#     os.makedirs(temp_dir)

#     try:
#         # Get video length
#         duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_filename]
#         duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
#         total_duration = float(duration_result.stdout.strip())
        
#         frame_counter = 0
#         timeline_entries = []

#         for start_time in range(0, int(total_duration), chunk_size):
#             chunk_name = f"temp_chunk_{video_name}_{start_time}.mp4"
            
#             # 1. Slice a 30s chunk
#             slice_cmd = ["ffmpeg", "-y", "-ss", str(start_time), "-i", video_filename, "-t", str(chunk_size), "-c", "copy", chunk_name]
#             subprocess.run(slice_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
#             # 2. Extract with 5s heartbeat + 2% scene change filter
#             smart_filter = "select='isnan(prev_selected_t)+gte(t-prev_selected_t,5)+gt(scene,0.02)',scale=320:180:flags=lanczos,showinfo"
#             extract_cmd = ["ffmpeg", "-y", "-i", chunk_name, "-vf", smart_filter, "-vsync", "vfr", os.path.join(temp_dir, "frame_%04d.png")]
#             result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
#             # 3. Parse precise logs
#             chunk_frame_times = []
#             for line in result.stderr.split('\n'):
#                 if "pts_time:" in line:
#                     match = re.search(r"pts_time:([\d.]+)", line)
#                     if match:
#                         chunk_frame_times.append(float(match.group(1)))
            
#             # 4. Global map translation
#             extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_")])
#             for idx, filename in enumerate(extracted_files):
#                 os.rename(os.path.join(temp_dir, filename), os.path.join(temp_dir, f"global_{frame_counter:04d}.png"))
#                 timeline_entries.append(start_time + chunk_frame_times[idx])
#                 frame_counter += 1

#             # 5. Volumetric Cleanup
#             if os.path.exists(chunk_name):
#                 os.remove(chunk_name)

#         if frame_counter > 0:
#             # 6. Stitch Sprite Sheet
#             stitch_cmd = ["ffmpeg", "-y", "-i", os.path.join(temp_dir, "global_%04d.png"), "-vf", f"tile={columns}x{math.ceil(frame_counter/columns)}", "-qscale:v", "2", output_image]
#             subprocess.run(stitch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
#             # 7. Write Dynamic VTT Map
#             with open(output_vtt, "w") as vtt_file:
#                 vtt_file.write("WEBVTT\n\n")
#                 for i in range(frame_counter):
#                     start_ts = format_vtt_time(timeline_entries[i])
#                     end_time_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 5.0
#                     end_ts = format_vtt_time(end_time_val)
#                     x, y = (i % columns) * width, (i // columns) * height
#                     vtt_file.write(f"{start_ts} --> {end_ts}\n{output_image}#xywh={x},{y},{width},{height}\n\n")
        
#         shutil.rmtree(temp_dir)
#         video_statuses[video_basename] = "complete"
#         print(f"✨ Backend processing completely finished for {video_basename}!")
#     except Exception as e:
#         video_statuses[video_basename] = f"failed: {str(e)}"

# # --- WEB ENDPOINTS ---

# @app.get("/")
# def serve_homepage():
#     # Serves the HTML frontend page directly when visiting http://localhost:8000/
#     return FileResponse("index.html")

# @app.get("/videos")
# def list_videos():
#     video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio"))
#     if not os.path.exists(video_dir):
#         return []
#     return sorted([f for f in os.listdir(video_dir) if f.endswith(".mp4")])

# @app.get("/videos/{filename}")
# def serve_video(filename: str):
#     video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", filename))
#     if os.path.exists(video_path):
#         return FileResponse(video_path)
#     return JSONResponse(status_code=404, content={"message": "Video not found"})

# @app.post("/process-video/{filename}")
# def trigger_pipeline(filename: str, background_tasks: BackgroundTasks):
#     global current_processing_video
#     video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", filename))
#     if not os.path.exists(video_path):
#         return JSONResponse(status_code=404, content={"status": "Video file not found"})
        
#     status = video_statuses.get(filename, "idle")
#     if status == "processing":
#         return {"status": "Already processing"}
    
#     video_statuses[filename] = "processing"
#     current_processing_video = filename
#     background_tasks.add_task(advanced_chunk_processor, video_path)
#     return {"status": "started"}

# @app.get("/status/{filename}")
# def get_status(filename: str):
#     video_name, _ = os.path.splitext(filename)
#     grid_path = f"{video_name}_grid.jpg"
#     vtt_path = f"{video_name}_timeline_map.vtt"
    
#     status = video_statuses.get(filename, "idle")
    
#     # Double check actual file existence to auto-correct status
#     if status == "complete" and (not os.path.exists(grid_path) or not os.path.exists(vtt_path)):
#         status = "idle"
#         video_statuses[filename] = "idle"
#     elif status == "idle" and os.path.exists(grid_path) and os.path.exists(vtt_path):
#         status = "complete"
#         video_statuses[filename] = "complete"
        
#     return {"status": status}

# # Expose the current directory so the browser can read video, sprite, and VTT files natively
# app.mount("/", StaticFiles(directory="."), name="static")
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import math
import datetime
import os
import shutil
import re
import json

# Add CoreExecutionBinary to system PATH dynamically so ffmpeg/ffprobe can be run by subprocess
binary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CoreExecutionBinary"))
if binary_path not in os.environ["PATH"]:
    os.environ["PATH"] = binary_path + os.pathsep + os.environ["PATH"]

app = FastAPI()

# Global state tracker and file scan for multiple videos
video_statuses = {}
current_processing_video = None

def scan_existing_outputs():
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio"))
    if os.path.exists(video_dir):
        for filename in os.listdir(video_dir):
            if filename.endswith(".mp4"):
                video_name, _ = os.path.splitext(filename)
                # 🌟 CHANGE 1: Look for .png grids instead of lossy .jpg files
                grid_path = f"{video_name}_grid.png"
                vtt_path = f"{video_name}_timeline_map.vtt"
                if os.path.exists(grid_path) and os.path.exists(vtt_path):
                    video_statuses[filename] = "complete"
                else:
                    video_statuses[filename] = "idle"

scan_existing_outputs()

def format_vtt_time(seconds):
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def advanced_chunk_processor(video_filename):
    global current_processing_video
    video_basename = os.path.basename(video_filename)
    video_name, _ = os.path.splitext(video_basename)
    
    video_statuses[video_basename] = "processing"
    current_processing_video = video_basename
    
    chunk_size = 30
    # 🌟 CHANGE 2: Quadruple canvas scale coordinates to 640x360 for crisp letter reading
    width, height, columns = 640, 360, 10
    temp_dir = f"temp_frames_{video_name}"
    output_image = f"{video_name}_grid.png" # 🌟 CHANGE 3: Swap string extension target to PNG
    output_vtt = f"{video_name}_timeline_map.vtt"
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        # Get video length
        duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_filename]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
        total_duration = float(duration_result.stdout.strip())
        
        frame_counter = 0
        timeline_entries = []

        for start_time in range(0, int(total_duration), chunk_size):
            chunk_name = f"temp_chunk_{video_name}_{start_time}.mp4"
            
            # 1. Slice a 30s chunk
            slice_cmd = ["ffmpeg", "-y", "-ss", str(start_time), "-i", video_filename, "-t", str(chunk_size), "-c", "copy", chunk_name]
            subprocess.run(slice_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Extract with 5s heartbeat + 2% scene change filter
            # 🌟 CHANGE 4: Upgrade image dimensions in extraction filter to 640:360
            smart_filter = "select='isnan(prev_selected_t)+gte(t-prev_selected_t,5)+gt(scene,0.02)',scale=640:360:flags=lanczos,showinfo"
            extract_cmd = ["ffmpeg", "-y", "-i", chunk_name, "-vf", smart_filter, "-vsync", "vfr", os.path.join(temp_dir, "frame_%04d.png")]
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            # 3. Parse precise logs
            chunk_frame_times = []
            for line in result.stderr.split('\n'):
                if "pts_time:" in line:
                    match = re.search(r"pts_time:([\d.]+)", line)
                    if match:
                        chunk_frame_times.append(float(match.group(1)))
            
            # 4. Global map translation
            extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_")])
            for idx, filename in enumerate(extracted_files):
                os.rename(os.path.join(temp_dir, filename), os.path.join(temp_dir, f"global_{frame_counter:04d}.png"))
                timeline_entries.append(start_time + chunk_frame_times[idx])
                frame_counter += 1

            # 5. Volumetric Cleanup
            if os.path.exists(chunk_name):
                os.remove(chunk_name)

        if frame_counter > 0:
            # 6. Stitch Sprite Sheet (Lossless mosaic grid export)
            # 🌟 CHANGE 5: Removed JPEG quality flag (-qscale:v 2) as PNG handles compression losslessly
            stitch_cmd = [
                "ffmpeg", "-y", "-i", os.path.join(temp_dir, "global_%04d.png"), 
                "-vf", f"tile={columns}x{math.ceil(frame_counter/columns)}", 
                output_image
            ]
            subprocess.run(stitch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 7. Write Dynamic VTT Map
            with open(output_vtt, "w") as vtt_file:
                vtt_file.write("WEBVTT\n\n")
                for i in range(frame_counter):
                    start_ts = format_vtt_time(timeline_entries[i])
                    end_time_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 5.0
                    end_ts = format_vtt_time(end_time_val)
                    x, y = (i % columns) * width, (i // columns) * height
                    vtt_file.write(f"{start_ts} --> {end_ts}\n{output_image}#xywh={x},{y},{width},{height}\n\n")
            # Create a machine-readable JSON summary for the sprite grid
            output_json = f"{video_name}_timeline.json"
            timeline_json = []
            for i in range(frame_counter):
                start_val = timeline_entries[i]
                end_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 5.0
                x, y = (i % columns) * width, (i // columns) * height
                timeline_json.append({
                    "index": i,
                    "start": float(start_val),
                    "end": float(end_val),
                    "image": output_image,
                    "xywh": [x, y, width, height]
                })
            with open(output_json, "w", encoding="utf-8") as jf:
                json.dump({"timeline": timeline_json}, jf, ensure_ascii=False, indent=2)
        
        shutil.rmtree(temp_dir)
        video_statuses[video_basename] = "complete"
        print(f"✨ Backend processing completely finished for {video_basename}!")
    except Exception as e:
        video_statuses[video_basename] = f"failed: {str(e)}"

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

@app.post("/process-video/{filename}")
def trigger_pipeline(filename: str, background_tasks: BackgroundTasks):
    global current_processing_video
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", filename))
    if not os.path.exists(video_path):
        return JSONResponse(status_code=404, content={"status": "Video file not found"})
        
    status = video_statuses.get(filename, "idle")
    if status == "processing":
        return {"status": "Already processing"}
    
    video_statuses[filename] = "processing"
    current_processing_video = filename
    background_tasks.add_task(advanced_chunk_processor, video_path)
    return {"status": "started"}

@app.get("/status/{filename}")
def get_status(filename: str):
    video_name, _ = os.path.splitext(filename)
    # 🌟 CHANGE 6: Direct status validation to target .png assets
    grid_path = f"{video_name}_grid.png"
    vtt_path = f"{video_name}_timeline_map.vtt"
    
    status = video_statuses.get(filename, "idle")
    
    if status == "complete" and (not os.path.exists(grid_path) or not os.path.exists(vtt_path)):
        status = "idle"
        video_statuses[filename] = "idle"
    elif status == "idle" and os.path.exists(grid_path) and os.path.exists(vtt_path):
        status = "complete"
        video_statuses[filename] = "complete"
        
    return {"status": status}

app.mount("/", StaticFiles(directory="."), name="static")