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


# def format_vtt_time(seconds):
#     """Converts seconds float into WebVTT timestamp format (HH:MM:SS.000)"""
#     td = datetime.timedelta(seconds=seconds)
#     hours, remainder = divmod(td.seconds, 3600)
#     minutes, secs = divmod(remainder, 60)
#     milliseconds = int((seconds - int(seconds)) * 1000)
#     return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

# def process_video_in_chunks(video_filename):
#     video_basename = os.path.basename(video_filename)
#     video_name, _ = os.path.splitext(video_basename)
    
#     chunk_size = 30  # Process in 30-second chunks
#     width, height = 320, 180
#     columns = 10
    
#     temp_dir = f"temp_frames_{video_name}"
#     log_file = f"ffmpeg_log_{video_name}.txt"
#     output_image = f"{video_name}_grid.jpg"
#     output_vtt = f"{video_name}_timeline_map.vtt"
    
#     # Create a clean folder to hold frames temporarily
#     if os.path.exists(temp_dir):
#         shutil.rmtree(temp_dir)
#     os.makedirs(temp_dir)

#     # 1. Get the total duration of the original video
#     duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_filename]
#     duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
#     total_duration = float(duration_result.stdout.strip())
    
#     print(f"Total Video Duration: {total_duration} seconds.")
    
#     frame_counter = 0
#     timeline_entries = []

#     # 2. Loop through the video in 30-second windows
#     for start_time in range(0, int(total_duration), chunk_size):
#         print(f"\n--- Processing Chunk: {start_time}s to {start_time + chunk_size}s ---")
        
#         chunk_name = f"temp_chunk_{video_name}_{start_time}.mp4"
        
#         # Step A: Slice a 30-second clip out of the main video
#         slice_cmd = [
#             "ffmpeg", "-y", "-ss", str(start_time), "-i", video_filename, 
#             "-t", str(chunk_size), "-c", "copy", chunk_name
#         ]
#         subprocess.run(slice_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
#         # Step B: Run the Smart Scene Detection on the 30-second chunk
#         # Filter details: 
#         # - gte(t-prev_selected_t,5): ensures a heartbeat frame every 5 seconds
#         # - gt(scene,0.02): catches any visual changes greater than 2% instantly
#         smart_filter = "select='isnan(prev_selected_t)+gte(t-prev_selected_t,5)+gt(scene,0.02)',scale=320:180:flags=lanczos,showinfo"
        
#         extract_cmd = [
#             "ffmpeg", "-y", "-i", chunk_name, 
#             "-vf", smart_filter, "-vsync", "vfr", 
#             os.path.join(temp_dir, "frame_%04d.png")
#         ]
        
#         # We capture the text output (stderr) because 'showinfo' prints frame times there
#         result = subprocess.run(extract_cmd, capture_output=True, text=True)
        
#         # Step C: Parse the logs to find the exact sub-second timestamps of changes
#         chunk_frame_times = []
#         for line in result.stderr.split('\n'):
#             if "pts_time:" in line:
#                 # Extract the timestamp value using regular expressions
#                 match = re.search(r"pts_time:([\d.]+)", line)
#                 if match:
#                     chunk_frame_times.append(float(match.group(1)))
                    
#         # Step D: Match the extracted images to their global timestamps
#         # Files are extracted as frame_0001.png, frame_0002.png etc. 
#         # We need to rename them globally so they don't overwrite the next chunk's files
#         extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_")])
        
#         for idx, filename in enumerate(extracted_files):
#             old_path = os.path.join(temp_dir, filename)
#             new_filename = f"global_{frame_counter:04d}.png"
#             new_path = os.path.join(temp_dir, new_filename)
#             os.rename(old_path, new_path)
            
#             # Global time = start of the 30s chunk + precise time inside the chunk
#             global_time = start_time + chunk_frame_times[idx]
#             timeline_entries.append(global_time)
#             frame_counter += 1

#         # Step E: AUTO-CLEANUP! Delete the 30-second video chunk file immediately
#         if os.path.exists(chunk_name):
#             os.remove(chunk_name)
#             print(f"🗑️ Deleted temporary chunk file: {chunk_name}")

#     if frame_counter == 0:
#         print("No frames were captured. Adjust scene sensitivity thresholds.")
#         return

#     print(f"\nProcessing complete. Captured {frame_counter} total distinct visual states.")
    
#     # 3. Stitch all accumulated frame images into a single master Sprite sheet
#     print("📸 Stitching all snapshots into a final image grid layout...")
#     stitch_cmd = [
#         "ffmpeg", "-y", "-i", os.path.join(temp_dir, "global_%04d.png"), 
#         "-vf", f"tile={columns}x{math.ceil(frame_counter/columns)}", 
#         "-qscale:v", "2", 
#         output_image
#     ]
#     subprocess.run(stitch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
#     # 4. Generate the precise WebVTT Map text file using variable timestamps
#     print("🗺️ Creating the final WebVTT coordinate map file...")
#     with open(output_vtt, "w") as vtt_file:
#         vtt_file.write("WEBVTT\n\n")
        
#         for i in range(frame_counter):
#             start_ts = format_vtt_time(timeline_entries[i])
#             # The frame lasts until the next frame begins, or for 5 seconds if it's the final frame
#             end_time_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 5.0
#             end_ts = format_vtt_time(end_time_val)
            
#             row = i // columns
#             col = i % columns
#             x = col * width
#             y = row * height
            
#             vtt_file.write(f"{start_ts} --> {end_ts}\n")
#             vtt_file.write(f"{output_image}#xywh={x},{y},{width},{height}\n\n")

#     # Final Directory Cleanup
#     shutil.rmtree(temp_dir)
#     print("✨ Process entirely finished! Check output_grid.jpg and timeline_map.vtt")

# # Run it on your file
# process_video_in_chunks("test3.mp4")

import subprocess
import math
import datetime
import os
import shutil
import re
from ocr_processor import extract_grid_text


# Add CoreExecutionBinary to system PATH dynamically so ffmpeg/ffprobe can be run by subprocess
binary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CoreExecutionBinary"))
if binary_path not in os.environ["PATH"]:
    os.environ["PATH"] = binary_path + os.pathsep + os.environ["PATH"]


def format_vtt_time(seconds):
    """Converts seconds float into WebVTT timestamp format (HH:MM:SS.000)"""
    td = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def process_video_in_chunks(video_filename):
    video_basename = os.path.basename(video_filename)
    video_name, _ = os.path.splitext(video_basename)
    
    chunk_size = 30  # Process in 30-second chunks
    # 🌟 CHANGE 1: Bump standalone script tracking bounds to 640x360
    width, height = 640, 360
    columns = 10
    
    temp_dir = f"temp_frames_{video_name}"
    log_file = f"ffmpeg_log_{video_name}.txt"
    output_image = f"{video_name}_grid.png" # 🌟 CHANGE 2: Output file is now lossless PNG
    output_vtt = f"{video_name}_timeline_map.vtt"
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # 1. Get the total duration of the original video
    duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_filename]
    duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
    total_duration = float(duration_result.stdout.strip())
    
    print(f"Total Video Duration: {total_duration} seconds.")
    
    frame_counter = 0
    timeline_entries = []

    # 2. Loop through the video in 30-second windows
    for start_time in range(0, int(total_duration), chunk_size):
        print(f"\n--- Processing Chunk: {start_time}s to {start_time + chunk_size}s ---")
        
        chunk_name = f"temp_chunk_{video_name}_{start_time}.mp4"
        
        # Step A: Slice a 30-second clip out of the main video
        slice_cmd = [
            "ffmpeg", "-y", "-ss", str(start_time), "-i", video_filename, 
            "-t", str(chunk_size), "-c", "copy", chunk_name
        ]
        subprocess.run(slice_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Step B: Run the Smart Scene Detection on the 30-second chunk
        # 🌟 CHANGE 3: Update extraction command filter to target 640x360 resolution profiles
        smart_filter = "select='isnan(prev_selected_t)+gte(t-prev_selected_t,7)+gt(scene,0.02)',scale=640:360:flags=lanczos,showinfo"
        
        extract_cmd = [
            "ffmpeg", "-y", "-i", chunk_name, 
            "-vf", smart_filter, "-vsync", "vfr", 
            os.path.join(temp_dir, "frame_%04d.png")
        ]
        
        result = subprocess.run(extract_cmd, capture_output=True, text=True)
        
        # Step C: Parse logs for timestamps
        chunk_frame_times = []
        for line in result.stderr.split('\n'):
            if "pts_time:" in line:
                match = re.search(r"pts_time:([\d.]+)", line)
                if match:
                    chunk_frame_times.append(float(match.group(1)))
                    
        # Step D: Match the extracted images to their global timestamps
        extracted_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("frame_")])
        
        for idx, filename in enumerate(extracted_files):
            old_path = os.path.join(temp_dir, filename)
            new_filename = f"global_{frame_counter:04d}.png"
            new_path = os.path.join(temp_dir, new_filename)
            os.rename(old_path, new_path)
            
            global_time = start_time + chunk_frame_times[idx]
            timeline_entries.append(global_time)
            frame_counter += 1

        # Step E: Delete the temporary video chunk
        if os.path.exists(chunk_name):
            os.remove(chunk_name)
            print(f"🗑️ Deleted temporary chunk file: {chunk_name}")

    if frame_counter == 0:
        print("No frames were captured. Adjust scene sensitivity thresholds.")
        return

    print(f"\nProcessing complete. Captured {frame_counter} total distinct visual states.")
    
    # Dynamically calculate columns to prevent ffmpeg dimension limits (32767 pixels)
    max_rows = 32000 // height
    columns = max(10, math.ceil(frame_counter / max_rows))
    
    # 3. Stitch all accumulated frame images into a single master Sprite sheet
    print("📸 Stitching all snapshots into a final image grid layout...")
    # 🌟 CHANGE 4: Output as clean PNG instead of compressed JPEG (-qscale is removed)
    stitch_cmd = [
        "ffmpeg", "-y", "-i", os.path.join(temp_dir, "global_%04d.png"), 
        "-vf", f"tile={columns}x{math.ceil(frame_counter/columns)}", 
        output_image
    ]
    try:
        subprocess.run(stitch_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: ffmpeg stitching failed:\n{e.stderr}")
        return
    
    # 4. Generate the precise WebVTT Map text file using variable timestamps
    print("🗺️ Creating the final WebVTT coordinate map file...")
    with open(output_vtt, "w") as vtt_file:
        vtt_file.write("WEBVTT\n\n")
        
        for i in range(frame_counter):
            start_ts = format_vtt_time(timeline_entries[i])
            end_time_val = timeline_entries[i+1] if (i + 1) < frame_counter else timeline_entries[i] + 7.0
            end_ts = format_vtt_time(end_time_val)
            
            row = i // columns
            col = i % columns
            x = col * width
            y = row * height
            
            vtt_file.write(f"{start_ts} --> {end_ts}\n")
            vtt_file.write(f"{output_image}#xywh={x},{y},{width},{height}\n\n")

    # Trigger offline OCR ingestion layer
    print("🔍 Extracting text via local OCR pipeline...")
    extract_grid_text(video_name)

    # Final Directory Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"✨ Process entirely finished! Check {output_image} and {output_vtt}")

# Run it on your file
import os
video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SourceVedio", "test5.mp4"))
process_video_in_chunks(video_path)