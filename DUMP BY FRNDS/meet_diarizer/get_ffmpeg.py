import urllib.request
import zipfile
import os
import shutil

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
print("Downloading ffmpeg...")
urllib.request.urlretrieve(url, "ffmpeg.zip")
print("Extracting...")
with zipfile.ZipFile("ffmpeg.zip", 'r') as zip_ref:
    zip_ref.extractall("ffmpeg_ext")

for root, dirs, files in os.walk("ffmpeg_ext"):
    if "ffmpeg.exe" in files:
        shutil.copy(os.path.join(root, "ffmpeg.exe"), ".")
    if "ffprobe.exe" in files:
        shutil.copy(os.path.join(root, "ffprobe.exe"), ".")

print("Cleaning up...")
os.remove("ffmpeg.zip")
shutil.rmtree("ffmpeg_ext")
print("Done!")
