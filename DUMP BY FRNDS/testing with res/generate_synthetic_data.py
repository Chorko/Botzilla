import os
import json
from PIL import Image, ImageDraw, ImageFont

script_dir = r"d:\ai-meeting-summarizer\DUMP BY FRNDS\testing with res"

# 1. Create a synthetic grid image (4 slides in a 2x2 grid)
grid_size = (1000, 1000)
img = Image.new('RGB', grid_size, color='white')
draw = ImageDraw.Draw(img)

# Slide 1: Red (top-left) - xywh=0,0,500,500
draw.rectangle([0, 0, 500, 500], fill='red')
draw.text((200, 250), "Slide 1: Intro", fill='white')

# Slide 2: Green (top-right) - xywh=500,0,500,500
draw.rectangle([500, 0, 1000, 500], fill='green')
draw.text((700, 250), "Slide 2: Architecture", fill='white')

# Slide 3: Blue (bottom-left) - xywh=0,500,500,500
draw.rectangle([0, 500, 500, 1000], fill='blue')
draw.text((200, 750), "Slide 3: Implementation", fill='white')

# Slide 4: Purple (bottom-right) - xywh=500,500,500,500
draw.rectangle([500, 500, 1000, 1000], fill='purple')
draw.text((700, 750), "Slide 4: Conclusion", fill='white')

grid_path = os.path.join(script_dir, "synthetic_grid.png")
img.save(grid_path)
print(f"Created synthetic grid image: {grid_path}")

# 2. Create a synthetic VTT file
vtt_content = """WEBVTT

00:00:00.000 --> 00:00:10.000
#xywh=0,0,500,500
Title: Slide 1 Intro
Text: Welcome to the synthetic meeting.

00:00:10.000 --> 00:00:20.000
#xywh=500,0,500,500
Title: Slide 2 Architecture
Text: This is the architecture slide.

00:00:20.000 --> 00:00:30.000
#xywh=0,500,500,500
Title: Slide 3 Implementation
Text: Here we implement the code.

00:00:30.000 --> 00:00:40.000
#xywh=500,500,500,500
Title: Slide 4 Conclusion
Text: Thank you for attending.
"""
vtt_path = os.path.join(script_dir, "synthetic_timeline_map.vtt")
with open(vtt_path, "w", encoding="utf-8") as f:
    f.write(vtt_content)
print(f"Created synthetic VTT: {vtt_path}")

# 3. Create synthetic audio_engine.py output (report.json)
report_content = {
    "segments": [
        {
            "start": 0.5,
            "end": 8.0,
            "speaker": "Speaker 1",
            "text": "Hello everyone. Welcome to our synthetic meeting. Today we're going to cover four main topics, starting with the introduction."
        },
        {
            "start": 10.5,
            "end": 18.0,
            "speaker": "Speaker 2",
            "text": "Thanks Speaker 1. If we look at the architecture here, you can see it's quite robust and scalable."
        },
        {
            "start": 21.0,
            "end": 28.0,
            "speaker": "Speaker 1",
            "text": "Exactly. And for the implementation, we'll be using Python and Node.js to glue everything together."
        },
        {
            "start": 31.0,
            "end": 39.0,
            "speaker": "Speaker 2",
            "text": "That concludes our presentation. Let me know if there are any questions."
        }
    ]
}
report_path = os.path.join(script_dir, "synthetic_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report_content, f, indent=2)
print(f"Created synthetic report JSON: {report_path}")
