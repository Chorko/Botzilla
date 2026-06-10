export type MeetingMode = 'AUDIO_ONLY' | 'UNIFIED' | 'SPLIT_STREAMS';

export interface SpeakerMap {
  [key: string]: string; // "SPEAKER_01" -> "Rahul Verma"
}

export interface TranscriptSegment {
  id: string;
  originalSpeaker: string; // e.g. "SPEAKER_01"
  speaker: string; // e.g. "Aarav" or "Speaker 1"
  text: string; // Hinglish / English transcript
  startTime: number; // in seconds
  endTime: number; // in seconds
  slideId?: string; // matched slide frame Id
}

export interface SlideFrame {
  id: string;
  timestamp: number; // in seconds
  dataUrl: string; // image presentation
  edgeDensity: number; // Canny edge check score
  blurScore: number; // Laplacian variance check score
  caption: string; // Dynamic slide caption
  isScreenShare: boolean;
}

export interface ActionItem {
  task: string;
  owner: string;
  priority: 'High' | 'Medium' | 'Low';
  deadline: string;
}

export interface DecisionItem {
  decision: string;
  owner: string;
  context: string;
}

export interface KeyPoint {
  category: string;
  point: string;
}

export interface MeetingSummary {
  title: string;
  date: string;
  executiveSummary: string;
  keyPoints: KeyPoint[];
  decisions: DecisionItem[];
  actionItems: ActionItem[];
  speakerMapping: SpeakerMap;
  segments: TranscriptSegment[];
  slides: SlideFrame[];
  isFallback?: boolean;
}

export interface ProcessingState {
  stage: 'idle' | 'uploading' | 'vad' | 'transcribing_diarizing' | 'resolving_names' | 'summarizing' | 'completed' | 'error';
  progress: number; // 0 to 100
  message: string;
}
