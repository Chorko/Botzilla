import sys
import re
import json
import os

def parse_vtt_time(ts):
    # format HH:MM:SS.mmm
    parts = ts.split(":")
    if len(parts) != 3:
        return 0.0
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    return h*3600 + m*60 + s

def parse_vtt(vtt_path):
    timeline = []
    if not os.path.exists(vtt_path):
        raise FileNotFoundError(vtt_path)

    with open(vtt_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    i = 0
    idx = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", line):
            start_s, _, end_s = line.partition(" --> ")
            start = parse_vtt_time(start_s)
            end = parse_vtt_time(end_s)
            # next line contains image#xywh
            if i+1 < len(lines):
                imgline = lines[i+1]
                m = re.search(r"([^#]+)#xywh=(\d+),(\d+),(\d+),(\d+)", imgline)
                if m:
                    image = os.path.basename(m.group(1))
                    x = int(m.group(2))
                    y = int(m.group(3))
                    w = int(m.group(4))
                    h = int(m.group(5))
                else:
                    image = imgline
                    x = y = w = h = None
                timeline.append({
                    "index": idx,
                    "start": float(start),
                    "end": float(end),
                    "image": image,
                    "xywh": [x, y, w, h]
                })
                idx += 1
                i += 2
                continue
        i += 1
    return {"timeline": timeline}

def main():
    vtt = sys.argv[1] if len(sys.argv) > 1 else "test3_timeline_map.vtt"
    out = os.path.splitext(vtt)[0] + ".json"
    data = parse_vtt(vtt)
    with open(out, "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2)
    print(f"Wrote {out} with {len(data['timeline'])} entries")

if __name__ == '__main__':
    main()
