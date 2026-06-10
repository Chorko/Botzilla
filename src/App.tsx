import React, { useState, useEffect } from 'react';
import {
  FileText,
  UploadCloud,
  Play,
  Zap,
  RefreshCw,
  Video,
  Database,
  AlertTriangle,
  Loader2,
  Layers,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  MeetingMode,
  TranscriptSegment,
  SlideFrame,
  MeetingSummary,
  ProcessingState
} from './types';
import SummaryViewer from './components/SummaryViewer';
import { createClient } from '@supabase/supabase-js';

export default function App() {
  const [mode, setMode] = useState<MeetingMode>('UNIFIED');
  const [uploadedAudioFile, setUploadedAudioFile] = useState<File | null>(null);
  const [uploadedVideoFile, setUploadedVideoFile] = useState<File | null>(null);

  const [processingState, setProcessingState] = useState<ProcessingState>({
    stage: 'idle',
    progress: 0,
    message: '',
  });

  const [activeTab, setActiveTab] = useState<'results' | 'supabase'>('results');
  const [meetingSummary, setMeetingSummary] = useState<MeetingSummary | null>(null);
  const [excludedSlideIds, setExcludedSlideIds] = useState<Set<string>>(new Set());
  const [isGeneratingDocx, setIsGeneratingDocx] = useState(false);

  // Supabase config
  const [supabaseUrl, setSupabaseUrl] = useState<string>(() => localStorage.getItem('sb_url') || 'https://aeogbakoskqjrftaqnd.supabase.co');
  const [supabaseAnonKey, setSupabaseAnonKey] = useState<string>(() => localStorage.getItem('sb_key') || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlb2diYWtvc2tmcWpyZnRhcW5kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwMjAzNzUsImV4cCI6MjA5NjU5NjM3NX0.SEheeBRXy3iPzeOi7gsm6yqH0zY2x7uQkG-HrFHR5KI');
  const [isSyncingSupabase, setIsSyncingSupabase] = useState<boolean>(false);
  const [supabaseSyncLogs, setSupabaseSyncLogs] = useState<string[]>([]);
  const [syncedMeetings, setSyncedMeetings] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  useEffect(() => {
    localStorage.setItem('sb_url', supabaseUrl);
    localStorage.setItem('sb_key', supabaseAnonKey);
  }, [supabaseUrl, supabaseAnonKey]);

  const fetchSyncedMeetings = async () => {
    if (!supabaseUrl || !supabaseAnonKey) return;
    setIsLoadingHistory(true);
    try {
      const supabase = createClient(supabaseUrl, supabaseAnonKey);
      const { data, error } = await supabase
        .from('meetings')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setSyncedMeetings(data || []);
    } catch (err: any) {
      console.error("Failed to fetch history:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'supabase') {
      fetchSyncedMeetings();
    }
  }, [activeTab, supabaseUrl, supabaseAnonKey]);

  // Handle file uploads
  const handleAudioDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) setUploadedAudioFile(e.dataTransfer.files[0]);
  };
  const handleVideoDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) setUploadedVideoFile(e.dataTransfer.files[0]);
  };

  const handleToggleExcludeSlide = (id: string) => {
    setExcludedSlideIds(prev => {
      const copy = new Set(prev);
      if (copy.has(id)) copy.delete(id);
      else copy.add(id);
      return copy;
    });
  };

  const trackProgress = (taskId: string) => {
    localStorage.setItem('active_task_id', taskId);
    setProcessingState({ stage: 'uploading', progress: 15, message: `Pipeline started (${taskId})` });

    const eventSource = new EventSource(`/api/progress/${taskId}`);

    eventSource.onmessage = (event) => {
      const update = JSON.parse(event.data);

      if (update.stage === 'completed') {
        eventSource.close();
        localStorage.removeItem('active_task_id');
        setMeetingSummary(update.data);
        setProcessingState({ stage: 'completed', progress: 100, message: 'Analysis complete!' });
        setActiveTab('results'); // Auto-switch
      } else if (update.stage === 'error') {
        eventSource.close();
        localStorage.removeItem('active_task_id');
        setProcessingState({ stage: 'error', progress: 100, message: update.message || 'Processing failed.' });
      } else {
        setProcessingState({
          stage: update.stage as any,
          progress: update.progress,
          message: update.message
        });
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setProcessingState({ stage: 'error', progress: 100, message: 'Lost connection to pipeline.' });
    };
  };

  // Reconnect to active task on mount
  useEffect(() => {
    const savedTaskId = localStorage.getItem('active_task_id');
    if (savedTaskId) {
      trackProgress(savedTaskId);
    }
  }, []);

  // Real pipeline — upload files, spawn Python, track via SSE
  const handleStartAnalysis = async () => {
    setProcessingState({ stage: 'uploading', progress: 5, message: 'Preparing upload...' });
    setMeetingSummary(null);

    try {
      const formData = new FormData();
      formData.append('mode', mode);
      formData.append('offset', '0.0');
      formData.append('language', 'en');
      formData.append('whisperModel', 'base');

      if (mode === 'AUDIO_ONLY') {
        if (!uploadedAudioFile) throw new Error("Audio file is required.");
        formData.append('audio', uploadedAudioFile);
      } else if (mode === 'UNIFIED') {
        if (!uploadedVideoFile) throw new Error("Unified video file is required.");
        formData.append('video', uploadedVideoFile);
      } else if (mode === 'SPLIT_STREAMS') {
        if (!uploadedAudioFile || !uploadedVideoFile) throw new Error("Both audio and video files are required.");
        formData.append('audio', uploadedAudioFile);
        formData.append('video', uploadedVideoFile);
      }

      setProcessingState({ stage: 'uploading', progress: 10, message: 'Uploading files...' });

      const response = await fetch('/api/process', { method: 'POST', body: formData });
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.error || 'Pipeline initiation failed.');
      }

      const { taskId } = await response.json();
      trackProgress(taskId);

    } catch (err: any) {
      setProcessingState({ stage: 'error', progress: 100, message: err.message || 'Failed to start analysis.' });
    }
  };

  // Load demo data via the server summarize endpoint
  const handlePreloadDemo = async () => {
    setProcessingState({ stage: 'uploading', progress: 30, message: 'Loading demo data...' });

    const demoSegments: TranscriptSegment[] = [
      { id: "tx-1", originalSpeaker: "SPEAKER_00", speaker: "Aarav", text: "Hello everyone, let's start the sync call. Hum presentation slide setup kar lete hain humare smart visual summarizer ka. Can you check screen-share Rahul?", startTime: 2, endTime: 12 },
      { id: "tx-2", originalSpeaker: "SPEAKER_01", speaker: "Rahul", text: "Haan Aarav, perfect screen visible hai na? Today product delivery targets discuss karenge aur backend API optimization specifications solve karenge path resolution flow ke liye.", startTime: 14, endTime: 25 },
      { id: "tx-3", originalSpeaker: "SPEAKER_00", speaker: "Aarav", text: "Perfect screen share visible hai. Speaker mapping list prepare karenge. Please resolve our SQLite database connections in our code before Friday deadline. This is a high priority task for you, Rahul.", startTime: 28, endTime: 40 },
      { id: "tx-4", originalSpeaker: "SPEAKER_02", speaker: "Surbhi", text: "Correct, I will join as QA lead. Surbhi here. Main verify karungi deployment pipelines. Wednesday tak test suites resolve kar dungi standard test containers pe.", startTime: 42, endTime: 55 },
      { id: "tx-5", originalSpeaker: "SPEAKER_01", speaker: "Rahul", text: "Excellent, security audit updates bhi handle kar lenge environment secrets key safeguard lock use karke. Meeting summaries local build package format document create target wrapup karenge right now.", startTime: 58, endTime: 75 },
    ];

    try {
      setProcessingState({ stage: 'resolving_names', progress: 60, message: 'Sending to Gemini for summary...' });

      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segments: demoSegments, meetingMode: 'UNIFIED' })
      });

      if (!res.ok) throw new Error("Summarize request failed.");
      const aiResult = await res.json();

      // Apply resolved names to segments
      const resolvedSegments = demoSegments.map(seg => ({
        ...seg,
        speaker: aiResult.speakerMapping?.[seg.originalSpeaker] || seg.speaker
      }));

      const summary: MeetingSummary = {
        title: "Project Sync & Database Lock Mitigation",
        date: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }),
        executiveSummary: aiResult.executiveSummary,
        keyPoints: aiResult.keyPoints || [],
        decisions: aiResult.decisions || [],
        actionItems: aiResult.actionItems || [],
        speakerMapping: aiResult.speakerMapping || {},
        segments: resolvedSegments,
        slides: [],
        isFallback: aiResult.isFallback || false,
      };

      setMeetingSummary(summary);
      setProcessingState({ stage: 'completed', progress: 100, message: 'Demo loaded!' });
      setActiveTab('results'); // Auto-switch
    } catch (err: any) {
      setProcessingState({ stage: 'error', progress: 100, message: err.message || 'Demo loading failed.' });
    }
  };

  // Download Word doc
  const handleDownloadDocx = async () => {
    if (!meetingSummary) return;
    setIsGeneratingDocx(true);
    try {
      const response = await fetch('/api/generate-docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: meetingSummary, excludedSlideIds: Array.from(excludedSlideIds) })
      });
      if (!response.ok) throw new Error("Failed to generate .docx");
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${(meetingSummary.title || 'Meeting').replace(/\s+/g, '_')}_Summary.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    } catch (err) {
      alert("Word document generation failed.");
    } finally {
      setIsGeneratingDocx(false);
    }
  };

  // Supabase sync
  const handleSyncToSupabase = async () => {
    if (!meetingSummary) return alert("No summary to sync. Run analysis first.");
    if (!supabaseUrl || !supabaseAnonKey) {
      setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Error: Missing Supabase credentials.`]);
      return;
    }

    setIsSyncingSupabase(true);
    setSupabaseSyncLogs([`[${new Date().toLocaleTimeString()}] Connecting to Supabase...`]);

    try {
      const supabase = createClient(supabaseUrl, supabaseAnonKey);

      setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Inserting meeting record...`]);
      const { data, error } = await supabase.from('meetings').insert([{
        title: meetingSummary.title,
        session_date: meetingSummary.date,
        executive_summary: meetingSummary.executiveSummary,
        decisions: meetingSummary.decisions,
        action_items: meetingSummary.actionItems,
        key_points: meetingSummary.keyPoints || [],
        speaker_mapping: meetingSummary.speakerMapping || {},
        segments: meetingSummary.segments || [],
        slides_count: meetingSummary.slides?.length || 0,
        slides: meetingSummary.slides || [],
        created_at: new Date().toISOString()
      }]).select();

      if (error) throw new Error(`Insert failed: ${error.message}`);
      const recordId = data?.[0]?.id;
      setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] ✓ Record created (ID: ${recordId || 'ok'})`]);

      setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Generating .docx for upload...`]);
      const res = await fetch('/api/generate-docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: meetingSummary, excludedSlideIds: Array.from(excludedSlideIds) })
      });
      if (!res.ok) throw new Error("Failed to generate docx for upload.");
      const blob = await res.blob();
      const file = new File([blob], `${meetingSummary.title.replace(/\s+/g, '_')}_Summary.docx`);

      setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Uploading to storage bucket...`]);
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('meeting-summaries')
        .upload(`summaries/${Date.now()}_report.docx`, file, { cacheControl: '3600', upsert: false });

      if (uploadError) throw new Error(`Storage upload failed: ${uploadError.message}`);

      let publicUrl = '';
      if (recordId && uploadData?.path) {
        setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Fetching public URL for report...`]);
        const { data: publicUrlData } = supabase.storage
          .from('meeting-summaries')
          .getPublicUrl(uploadData.path);
        
        publicUrl = publicUrlData?.publicUrl || '';
        
        if (publicUrl) {
          setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] Updating record with report URL...`]);
          const { error: updateError } = await supabase
            .from('meetings')
            .update({ report_path: publicUrl })
            .eq('id', recordId);
            
          if (updateError) {
            setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] ⚠️ Database update for report_path failed: ${updateError.message}`]);
          } else {
            setSupabaseSyncLogs(p => [...p, `[${new Date().toLocaleTimeString()}] ✓ Database updated with report path.`]);
          }
        }
      }

      setSupabaseSyncLogs(p => [
        ...p,
        `[${new Date().toLocaleTimeString()}] ✓ File stored at: ${uploadData?.path}`,
        `[${new Date().toLocaleTimeString()}] 🚀 Sync complete!`
      ]);

      // Automatically refresh history listing
      fetchSyncedMeetings();
    } catch (err: any) {
      setSupabaseSyncLogs(p => [
        ...p,
        `[${new Date().toLocaleTimeString()}] ✗ Error: ${err.message}`,
        `[${new Date().toLocaleTimeString()}] Make sure you've run the SQL migration in your Supabase dashboard.`
      ]);
    } finally {
      setIsSyncingSupabase(false);
    }
  };

  const resetAll = () => {
    localStorage.removeItem('active_task_id');
    setUploadedAudioFile(null);
    setUploadedVideoFile(null);
    setMeetingSummary(null);
    setExcludedSlideIds(new Set());
    setProcessingState({ stage: 'idle', progress: 0, message: '' });
  };

  const isProcessing = ['uploading', 'vad', 'transcribing_diarizing', 'resolving_names', 'summarizing'].includes(processingState.stage);

  const canStart =
    (mode === 'AUDIO_ONLY' && !!uploadedAudioFile) ||
    (mode === 'UNIFIED' && !!uploadedVideoFile) ||
    (mode === 'SPLIT_STREAMS' && !!uploadedAudioFile && !!uploadedVideoFile);

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-700 antialiased">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shrink-0">
              <FileText className="w-4.5 h-4.5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-800 tracking-tight">AI Meeting Summarizer</h1>
              <p className="text-[9px] text-slate-400 font-medium uppercase tracking-wider">WhisperX · Pyannote · Gemini AI</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={handlePreloadDemo} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer transition-all border border-slate-200 flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-amber-500" />
              Demo
            </button>
            {meetingSummary && (
              <button onClick={resetAll} className="px-3 py-1.5 text-slate-400 hover:text-slate-700 text-xs font-medium cursor-pointer transition-colors flex items-center gap-1">
                <X className="w-3 h-3" />
                Clear
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left Panel — Upload & Controls */}
        <div className="lg:col-span-4 space-y-5">

          {/* Mode Selector */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5 mb-3">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              Input Mode
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'AUDIO_ONLY', label: 'Audio Only', desc: 'WAV / MP3' },
                { id: 'UNIFIED', label: 'Unified Video', desc: 'Video + Audio' },
                { id: 'SPLIT_STREAMS', label: 'Split Streams', desc: 'Separate files' }
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m.id as MeetingMode)}
                  className={`flex flex-col items-center p-2.5 rounded-lg border text-center cursor-pointer transition-all ${
                    mode === m.id
                      ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm'
                      : 'bg-white border-slate-200 hover:border-slate-300 text-slate-600'
                  }`}
                >
                  <span className="text-[11px] font-bold">{m.label}</span>
                  <span className={`text-[8px] mt-0.5 ${mode === m.id ? 'text-indigo-200' : 'text-slate-400'}`}>{m.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Upload Zone */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
              <UploadCloud className="w-3.5 h-3.5 text-indigo-600" />
              Upload Files
            </h3>

            {/* Video upload (UNIFIED or SPLIT_STREAMS) */}
            {mode !== 'AUDIO_ONLY' && (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleVideoDrop}
                className={`border-2 border-dashed rounded-lg p-5 text-center transition-all flex flex-col items-center ${
                  uploadedVideoFile ? 'border-indigo-200 bg-indigo-50/30' : 'border-slate-200 hover:border-indigo-300 bg-slate-50'
                }`}
              >
                <Video className={`w-6 h-6 mb-2 ${uploadedVideoFile ? 'text-indigo-600' : 'text-slate-400'}`} />
                {uploadedVideoFile ? (
                  <div>
                    <p className="text-xs font-bold text-slate-800 truncate max-w-[200px]">{uploadedVideoFile.name}</p>
                    <p className="text-[10px] text-emerald-600 font-medium mt-1">✓ Video loaded</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-medium text-slate-600">Drop video file here</p>
                    <label className="mt-2 inline-block text-[10px] font-bold text-indigo-600 cursor-pointer bg-white border border-indigo-200 px-3 py-1 rounded hover:bg-indigo-50">
                      Browse
                      <input type="file" accept="video/*" className="hidden" onChange={(e) => { if (e.target.files?.[0]) { setUploadedVideoFile(e.target.files[0]); if (mode === 'UNIFIED') setUploadedAudioFile(null); } }} />
                    </label>
                  </div>
                )}
              </div>
            )}

            {/* Audio upload (AUDIO_ONLY or SPLIT_STREAMS) */}
            {mode !== 'UNIFIED' && (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleAudioDrop}
                className={`border-2 border-dashed rounded-lg p-5 text-center transition-all flex flex-col items-center ${
                  uploadedAudioFile ? 'border-indigo-200 bg-indigo-50/30' : 'border-slate-200 hover:border-indigo-300 bg-slate-50'
                }`}
              >
                <Zap className={`w-6 h-6 mb-2 ${uploadedAudioFile ? 'text-indigo-600' : 'text-slate-400'}`} />
                {uploadedAudioFile ? (
                  <div>
                    <p className="text-xs font-bold text-slate-800 truncate max-w-[200px]">{uploadedAudioFile.name}</p>
                    <p className="text-[10px] text-emerald-600 font-medium mt-1">✓ Audio loaded</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-medium text-slate-600">Drop audio file here</p>
                    <label className="mt-2 inline-block text-[10px] font-bold text-indigo-600 cursor-pointer bg-white border border-indigo-200 px-3 py-1 rounded hover:bg-indigo-50">
                      Browse
                      <input type="file" accept="audio/*" className="hidden" onChange={(e) => { if (e.target.files?.[0]) setUploadedAudioFile(e.target.files[0]); }} />
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Analyze Button */}
          <button
            onClick={handleStartAnalysis}
            disabled={!canStart || isProcessing}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold text-xs py-3 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Analyze Meeting
              </>
            )}
          </button>

          {/* Progress */}
          {processingState.stage !== 'idle' && processingState.stage !== 'completed' && processingState.stage !== 'error' && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium text-slate-700 truncate max-w-[220px]">{processingState.message}</span>
                <span className="text-xs font-bold text-indigo-600 font-mono">{processingState.progress}%</span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  style={{ width: `${processingState.progress}%` }}
                  className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                />
              </div>
              <div className="grid grid-cols-5 gap-1 text-[8px] text-center font-bold text-slate-300 uppercase">
                <span className={processingState.progress >= 10 ? 'text-indigo-600' : ''}>Upload</span>
                <span className={processingState.progress >= 30 ? 'text-indigo-600' : ''}>VAD</span>
                <span className={processingState.progress >= 50 ? 'text-indigo-600' : ''}>Transcribe</span>
                <span className={processingState.progress >= 75 ? 'text-indigo-600' : ''}>Resolve</span>
                <span className={processingState.progress >= 95 ? 'text-indigo-600' : ''}>Summary</span>
              </div>
            </div>
          )}

          {/* Error */}
          {processingState.stage === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-red-800">Pipeline Error</p>
                <p className="text-xs text-red-600 mt-0.5">{processingState.message}</p>
                <button onClick={resetAll} className="text-[10px] text-red-700 underline mt-2 cursor-pointer">Reset</button>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel — Results */}
        <div className="lg:col-span-8 space-y-5">

          {/* Tabs */}
          <div className="flex items-center gap-1 border-b border-slate-200">
            {[
              { id: 'results', label: 'Results', icon: FileText },
              { id: 'supabase', label: 'Supabase Sync', icon: Database },
            ].map((t) => {
              const Icon = t.icon;
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id as any)}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold cursor-pointer border-b-2 transition-all ${
                    isActive ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {t.label}
                </button>
              );
            })}
          </div>

          <AnimatePresence mode="wait">
            {activeTab === 'results' && (
              <motion.div key="results" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}>
                {meetingSummary ? (
                  <SummaryViewer
                    summary={meetingSummary}
                    onDownloadDocx={handleDownloadDocx}
                    isGeneratingDocx={isGeneratingDocx}
                    excludedSlideIds={excludedSlideIds}
                    onToggleExcludeSlide={handleToggleExcludeSlide}
                  />
                ) : (
                  <div className="h-80 flex flex-col items-center justify-center border border-dashed border-slate-300 rounded-xl bg-white p-6 text-center">
                    <FileText className="w-10 h-10 text-slate-200 mb-3" />
                    <p className="text-sm font-semibold text-slate-500">No results yet</p>
                    <p className="text-xs text-slate-400 max-w-xs mt-1">
                      Upload a meeting file and click "Analyze Meeting", or try the Demo button to see sample output.
                    </p>
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'supabase' && (
              <motion.div key="supabase" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}>
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                      <Database className="w-4 h-4 text-indigo-600" />
                      Supabase Sync & Archive
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Store meeting records and .docx files in your Supabase database and storage bucket.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-slate-600 block mb-1">Project URL</label>
                      <input
                        type="text"
                        value={supabaseUrl}
                        onChange={(e) => setSupabaseUrl(e.target.value)}
                        className="w-full text-xs p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                        placeholder="https://xxx.supabase.co"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-600 block mb-1">Anon Key</label>
                      <input
                        type="password"
                        value={supabaseAnonKey}
                        onChange={(e) => setSupabaseAnonKey(e.target.value)}
                        className="w-full text-xs p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                        placeholder="eyJhb..."
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleSyncToSupabase}
                    disabled={isSyncingSupabase || !meetingSummary}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold text-xs py-3 rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {isSyncingSupabase ? (
                      <><RefreshCw className="w-4 h-4 animate-spin" /> Syncing...</>
                    ) : (
                      <><Database className="w-4 h-4" /> Sync to Supabase</>
                    )}
                  </button>

                  {supabaseSyncLogs.length > 0 && (
                    <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 font-mono text-[10px] text-slate-300 space-y-1 max-h-48 overflow-y-auto">
                      {supabaseSyncLogs.map((log, i) => (
                        <div key={i} className={
                          log.includes('Error') || log.includes('✗') ? 'text-red-400 font-bold' :
                          log.includes('✓') || log.includes('🚀') ? 'text-emerald-400 font-bold' : ''
                        }>
                          {log}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Synced History Dashboard */}
                  <div className="pt-6 border-t border-slate-200 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">Synced Meeting Archive</h4>
                        <p className="text-[10px] text-slate-400 font-medium">History of meetings synced to Supabase database</p>
                      </div>
                      <button
                        onClick={fetchSyncedMeetings}
                        disabled={isLoadingHistory}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-600 rounded-md text-[10px] font-bold border border-slate-200 flex items-center gap-1 transition-all cursor-pointer"
                      >
                        <RefreshCw className={`w-3 h-3 ${isLoadingHistory ? 'animate-spin' : ''}`} />
                        Refresh
                      </button>
                    </div>

                    {isLoadingHistory ? (
                      <div className="h-32 flex flex-col items-center justify-center border border-slate-100 rounded-xl bg-slate-50/50">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin mb-1.5" />
                        <p className="text-xs font-semibold text-slate-500">Loading history archive...</p>
                      </div>
                    ) : syncedMeetings.length === 0 ? (
                      <div className="h-32 flex flex-col items-center justify-center border border-dashed border-slate-200 rounded-xl bg-slate-50/50 p-4 text-center">
                        <Database className="w-6 h-6 text-slate-300 mb-1.5" />
                        <p className="text-xs font-semibold text-slate-500">No synced meetings found</p>
                        <p className="text-[10px] text-slate-400 max-w-xs mt-0.5">
                          Configure your credentials and click "Sync to Supabase" above to save your first report.
                        </p>
                      </div>
                    ) : (
                      <div className="border border-slate-200 rounded-lg overflow-hidden max-h-80 overflow-y-auto">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 sticky top-0">
                              <th className="p-2.5 font-semibold text-slate-500">Meeting Details</th>
                              <th className="p-2.5 font-semibold text-slate-500 text-center w-[120px]">Stats</th>
                              <th className="p-2.5 font-semibold text-slate-500 text-right w-[150px]">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {syncedMeetings.map((mtg) => (
                              <tr key={mtg.id} className="hover:bg-slate-50/60 transition-colors">
                                <td className="p-2.5">
                                  <p className="font-bold text-slate-800 truncate max-w-[200px]" title={mtg.title}>{mtg.title}</p>
                                  <p className="text-[9px] text-slate-400 font-medium mt-0.5">{mtg.session_date}</p>
                                </td>
                                <td className="p-2.5 text-center">
                                  <div className="flex items-center justify-center gap-1.5 text-[9px] font-bold text-slate-500">
                                    <span className="bg-blue-50 text-blue-700 px-1 py-0.5 rounded border border-blue-100" title="Decisions count">
                                      {mtg.decisions?.length || 0} D
                                    </span>
                                    <span className="bg-amber-50 text-amber-700 px-1 py-0.5 rounded border border-amber-100" title="Action Items count">
                                      {mtg.action_items?.length || 0} A
                                    </span>
                                    {mtg.slides_count > 0 && (
                                      <span className="bg-purple-50 text-purple-700 px-1 py-0.5 rounded border border-purple-100" title="Slides count">
                                        {mtg.slides_count} S
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="p-2.5 text-right space-x-1.5">
                                  <button
                                    onClick={() => {
                                      setMeetingSummary({
                                        title: mtg.title,
                                        date: mtg.session_date,
                                        executiveSummary: mtg.executive_summary,
                                        decisions: mtg.decisions || [],
                                        actionItems: mtg.action_items || [],
                                        keyPoints: mtg.key_points || [],
                                        speakerMapping: mtg.speaker_mapping || {},
                                        segments: mtg.segments || [],
                                        slides: mtg.slides || [],
                                      });
                                      setActiveTab('results');
                                    }}
                                    className="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold cursor-pointer transition-colors animate-none"
                                  >
                                    Load
                                  </button>
                                  {mtg.report_path ? (
                                    <a
                                      href={mtg.report_path}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-block px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded text-[10px] font-bold transition-colors"
                                    >
                                      Report
                                    </a>
                                  ) : (
                                    <span className="text-[10px] text-slate-300 italic">No Doc</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
