import sys
import os
import whisperx
import torch
import json
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def get_chunks(segments, max_words= 1500):
    arr= []
    new_= ""
    res= 0
    for sg in segments:
        if "speaker" in sg:
            line= f"{sg[ 'start' ]:.3f} {sg[ 'speaker' ]} {sg[ 'text' ]}\n"
            count= len(line.split())
            if res+ count > max_words:
                arr.append(new_)
                new_= line
                res= count
            else:
                new_+= line
                res+= count
    if new_:
        arr.append(new_)
    return arr

def process_chunk(client, chunk_text):
    sys_= """
    You are an AI meeting agent processing a segment of a transcript.
    
    Tasks:
    1. Keep the exact speaker labels (e.g., SPEAKER_00). Do NOT change them to real names.
    2. Fix broken pauses by the SAME speaker into one paragraph.
    3. CRITICAL: Every single time a DIFFERENT speaker talks, you MUST start a new line. NEVER merge two different speakers into the same block of text.
    4. Extract action items.

    Output ONLY valid JSON matching this schema:
    {
      "clean_transcript": "String",
      "action_items": [
        {"task": "String", "owner": "String", "due_date": "String"}
      ]
    }
    """
    new_= client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_},
            {"role": "user", "content": chunk_text}
        ],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    return json.loads(new_.choices[ 0 ].message.content)

def gen_master(client, text):
    sys_= """
    You are an executive analyzer. 
    
    Tasks:
    1. Read the full transcript and figure out the real names for SPEAKER_00, SPEAKER_01, etc.
    2. Generate a formal architecture sync summary. 
    3. CRITICAL: Append exact spoken quotes in brackets for all key points.

    Output ONLY valid JSON matching this schema:
    {
      "speaker_mapping": {"SPEAKER_00": "Real Name", "SPEAKER_01": "Real Name"},
      "meeting_title": "String",
      "date": "YYYY-MM-DD",
      "attendees": ["String"],
      "metrics": {
        "duration_hours": "Number",
        "attendees_count": "Number",
        "decisions_count": "Number",
        "actions_count": "Number"
      },
      "executive_summary": "String",
      "key_decisions": ["Point 1. [\\"Exact quote\\"]"],
      "key_discussion_points": ["Point 1. [\\"Exact quote\\"]"],
      "pending_issues": ["Point 1. [\\"Exact quote\\"]"]
    }
    """
    new_= client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_},
            {"role": "user", "content": text}
        ],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    return json.loads(new_.choices[ 0 ].message.content)

def process_full_audio(fp, hf_token, groq_key, task_dir):
    print("[STATUS] transcribing_diarizing 10 Loading WhisperX models...", flush=True)
    dev= "cuda" if torch.cuda.is_available() else "cpu"
    mdl= whisperx.load_model("tiny", dev)
    aud= whisperx.load_audio(fp)
    
    print("[STATUS] transcribing_diarizing 30 Transcribing vocal segments...", flush=True)
    res= mdl.transcribe(aud, batch_size=16)
    
    print("[STATUS] transcribing_diarizing 50 Aligning phonetic timings...", flush=True)
    aln, mtd= whisperx.load_align_model(language_code=res[ "language" ], device=dev)
    res= whisperx.align(res[ "segments" ], aln, mtd, aud, dev, return_char_alignments=False)
    
    print("[STATUS] transcribing_diarizing 70 Running Pyannote diarization...", flush=True)
    dz_mdl= whisperx.diarize.DiarizationPipeline(token=hf_token, device=dev)
    dz_df= dz_mdl(aud)
    out= whisperx.assign_word_speakers(dz_df, res)
    arr= get_chunks(out[ "segments" ])
    
    client= Groq(api_key=groq_key)
    new_= ""
    final_actions= []
    
    print("[STATUS] resolving_names 80 Generating AI meeting summary...", flush=True)
    for c in arr:
        data= process_chunk(client, c)
        new_+= data.get("clean_transcript", "") + "\n\n"
        final_actions.extend(data.get("action_items", []))
            
    master= gen_master(client, new_)
    map_= master.get("speaker_mapping", {})
    for key, val in map_.items():
        new_= new_.replace(key, val)
        
    print("[STATUS] finalizing 95 Compiling UI visual report...", flush=True)
    ui_seg= []
    for sg in out[ "segments" ]:
        ui_seg.append({
            "speaker": map_.get(sg.get("speaker", ""), sg.get("speaker", "SPEAKER_00")),
            "text": sg.get("text", ""),
            "startTime": sg.get("start", 0.0),
            "endTime": sg.get("end", 0.0)
        })
        
    ui_dec= []
    for d in master.get("key_decisions", []):
        ui_dec.append({ "decision": d, "owner": "Team" })
        
    ui_act= []
    for a in final_actions:
        ui_act.append({
            "task": a.get("task", "Task"),
            "owner": a.get("owner", "Unassigned"),
            "priority": "High",
            "deadline": a.get("due_date", "TBD")
        })
        
    ui_kp= []
    for p in master.get("key_discussion_points", []):
        ui_kp.append({ "category": "Discussion", "point": p })

    ui_json= {
        "title": master.get("meeting_title", "SAKSHI LEDGER Sync"),
        "date": master.get("date", "Today"),
        "executiveSummary": master.get("executive_summary", ""),
        "speakerMapping": map_,
        "segments": ui_seg,
        "decisions": ui_dec,
        "actionItems": ui_act,
        "keyPoints": ui_kp,
        "metrics": master.get("metrics", {})
    }
    
    with open(os.path.join(task_dir, "report.json"), "w") as f:
        json.dump(ui_json, f)
        
    return {
        "summary": master,
        "clean_transcript": new_.strip(),
        "action_items": final_actions
    }

def gen_pdf(data, task_dir):
    out= os.path.join(task_dir, "Final_Report.pdf")
    new_= SimpleDocTemplate(out, pagesize=letter)
    styles= getSampleStyleSheet()
    
    head= ParagraphStyle('ColoredHeading1', parent=styles[ 'Heading1' ], alignment=1, textColor=colors.HexColor("#1E3A8A"))
    sub= ParagraphStyle('ColoredHeading2', parent=styles[ 'Heading2' ], textColor=colors.HexColor("#2563EB"), spaceBottom=6)
    norm= styles[ 'Normal' ]
    
    arr= []
    arr.append(Paragraph("Meeting Summary", head))
    arr.append(Spacer(1, 12))
    
    title= data.get("summary", {}).get("meeting_title", "Architecture Sync")
    arr.append(Paragraph(f"<b>{title}</b>", sub))
    
    date= data.get("summary", {}).get("date", "N/A")
    arr.append(Paragraph(f"<b>Date:</b> {date}", norm))
    
    att= ", ".join(data.get("summary", {}).get("attendees", []))
    arr.append(Paragraph(f"<b>Attendees:</b> {att}", norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Key Metrics", sub))
    m= data.get("summary", {}).get("metrics", {})
    met= f"Duration: {m.get('duration_hours', 0)} Hours | Attendees: {m.get('attendees_count', 0)} | Decisions: {m.get('decisions_count', 0)} | Actions: {m.get('actions_count', 0)}"
    arr.append(Paragraph(met, norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Executive Summary", sub))
    exec_summary= data.get("summary", {}).get("executive_summary", "N/A")
    arr.append(Paragraph(exec_summary, norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Key Decisions", sub))
    for d in data.get("summary", {}).get("key_decisions", []):
        arr.append(Paragraph(f"• {d}", norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Action Items", sub))
    for act in data.get("action_items", []):
        t= act.get("task", "N/A")
        o= act.get("owner", "N/A")
        d= act.get("due_date", "N/A")
        arr.append(Paragraph(f"<b>Task:</b> {t} | <b>Owner:</b> {o} | <b>Due:</b> {d}", norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Key Discussion Points", sub))
    for p in data.get("summary", {}).get("key_discussion_points", []):
        arr.append(Paragraph(f"• {p}", norm))
    arr.append(Spacer(1, 12))
    
    arr.append(Paragraph("Pending Issues", sub))
    for p in data.get("summary", {}).get("pending_issues", []):
        arr.append(Paragraph(f"• {p}", norm))
    arr.append(Spacer(1, 24))
    
    foot= ParagraphStyle('Footer', parent=styles[ 'Normal' ], alignment=1, fontSize=8, textColor=colors.grey)
    arr.append(Paragraph("Generated by SAKSHI LEDGER | Confidential", foot))
    
    new_.build(arr)
    return out

if __name__ == "__main__":
    audio_path= sys.argv[ 1 ]
    hf_token= sys.argv[ 2 ]
    groq_key= sys.argv[ 3 ]
    task_dir= sys.argv[ 4 ]
    
    new_= process_full_audio(audio_path, hf_token, groq_key, task_dir)
    output_pdf= gen_pdf(new_, task_dir)
    print(f"[SUCCESS] {output_pdf}", flush=True)