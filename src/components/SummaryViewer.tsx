import { useState } from 'react';
import { FileText, Calendar, ChevronDown, ChevronUp, Download, Users, Target, ListChecks, MessageSquare } from 'lucide-react';
import { MeetingSummary } from '../types';

interface SummaryViewerProps {
  summary: MeetingSummary;
  onDownloadDocx: () => void;
  isGeneratingDocx: boolean;
  excludedSlideIds: Set<string>;
  onToggleExcludeSlide: (id: string) => void;
}

// Dynamic speaker color palette — cycles through 8 distinct colors
const SPEAKER_COLORS = [
  { bg: 'bg-blue-50', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-800 border-blue-200', accent: 'border-l-blue-500', dot: 'bg-blue-500' },
  { bg: 'bg-emerald-50', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-800 border-emerald-200', accent: 'border-l-emerald-500', dot: 'bg-emerald-500' },
  { bg: 'bg-violet-50', text: 'text-violet-700', badge: 'bg-violet-100 text-violet-800 border-violet-200', accent: 'border-l-violet-500', dot: 'bg-violet-500' },
  { bg: 'bg-amber-50', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800 border-amber-200', accent: 'border-l-amber-500', dot: 'bg-amber-500' },
  { bg: 'bg-rose-50', text: 'text-rose-700', badge: 'bg-rose-100 text-rose-800 border-rose-200', accent: 'border-l-rose-500', dot: 'bg-rose-500' },
  { bg: 'bg-cyan-50', text: 'text-cyan-700', badge: 'bg-cyan-100 text-cyan-800 border-cyan-200', accent: 'border-l-cyan-500', dot: 'bg-cyan-500' },
  { bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-800 border-orange-200', accent: 'border-l-orange-500', dot: 'bg-orange-500' },
  { bg: 'bg-indigo-50', text: 'text-indigo-700', badge: 'bg-indigo-100 text-indigo-800 border-indigo-200', accent: 'border-l-indigo-500', dot: 'bg-indigo-500' },
];

function getSpeakerColor(speakerId: string, speakerKeys: string[]) {
  const idx = speakerKeys.indexOf(speakerId);
  return SPEAKER_COLORS[(idx >= 0 ? idx : 0) % SPEAKER_COLORS.length];
}

export default function SummaryViewer({
  summary,
  onDownloadDocx,
  isGeneratingDocx,
  excludedSlideIds,
  onToggleExcludeSlide,
}: SummaryViewerProps) {
  const [showTranscript, setShowTranscript] = useState(false);
  const [showSlides, setShowSlides] = useState(false);

  const speakerKeys = Object.keys(summary.speakerMapping);
  const activeSlides = (summary.slides || []).filter(s => !excludedSlideIds.has(s.id));

  return (
    <div id="summary-viewer" className="space-y-0">
      {/* Header banner */}
      <div className="bg-indigo-600 rounded-t-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            {summary.title || "Meeting Summary Report"}
          </h2>
          <p className="text-indigo-200 text-xs mt-1 flex items-center gap-2 flex-wrap">
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" /> {summary.date}
            </span>
            <span>•</span>
            <span>{Object.keys(summary.speakerMapping).length} Participants</span>
            <span>•</span>
            <span>{summary.segments?.length || 0} Segments</span>
          </p>
        </div>
        <button
          onClick={onDownloadDocx}
          disabled={isGeneratingDocx}
          className="flex items-center gap-2 bg-white text-indigo-700 font-bold text-xs py-2 px-5 rounded-lg hover:bg-indigo-50 disabled:opacity-60 cursor-pointer transition-colors shadow-sm shrink-0"
        >
          {isGeneratingDocx ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin" />
              Compiling...
            </>
          ) : (
            <>
              <Download className="w-3.5 h-3.5" />
              Download .docx
            </>
          )}
        </button>
      </div>

      <div className="bg-white border border-t-0 border-slate-200 rounded-b-xl shadow-sm">
        {/* Metrics grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-slate-200 border-b border-slate-200">
          {[
            { label: 'Participants', value: Object.keys(summary.speakerMapping).length, icon: Users, color: 'text-blue-600' },
            { label: 'Segments', value: summary.segments?.length || 0, icon: MessageSquare, color: 'text-emerald-600' },
            { label: 'Decisions', value: summary.decisions?.length || 0, icon: Target, color: 'text-violet-600' },
            { label: 'Action Items', value: summary.actionItems?.length || 0, icon: ListChecks, color: 'text-amber-600' },
          ].map((m) => (
            <div key={m.label} className="bg-white p-4 text-center">
              <m.icon className={`w-4 h-4 mx-auto mb-1.5 ${m.color}`} />
              <p className="text-2xl font-extrabold text-slate-800">{m.value}</p>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-0.5">{m.label}</p>
            </div>
          ))}
        </div>

        <div className="p-6 sm:p-8 space-y-8">
          {/* Participants */}
          <div>
            <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-500" />
              Identified Speakers
            </h3>
            <div className="flex flex-wrap gap-2">
              {speakerKeys.map((key) => {
                const color = getSpeakerColor(key, speakerKeys);
                return (
                  <div key={key} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${color.badge}`}>
                    <span className={`w-2 h-2 rounded-full ${color.dot}`} />
                    <span className="font-mono text-[10px] opacity-60">{key}</span>
                    <span className="mx-0.5">→</span>
                    <span className="font-bold">{summary.speakerMapping[key]}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Executive Summary */}
          <div>
            <h3 className="text-sm font-bold text-slate-800 mb-2">Executive Summary</h3>
            <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
              {summary.executiveSummary}
            </p>
          </div>

          {/* Key Decisions + Discussion Points — side by side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-3">Key Decisions</h3>
              {summary.decisions.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No explicit decisions recorded.</p>
              ) : (
                <ul className="space-y-2">
                  {summary.decisions.map((d, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm">
                      <span className="w-5 h-5 rounded-full bg-emerald-500 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                      <div>
                        <p className="text-slate-700 font-medium">{d.decision}</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Owner: <strong className="text-slate-600">{d.owner}</strong>
                          {d.context && <> — <span className="italic">{d.context}</span></>}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-3">Discussion Points</h3>
              {(!summary.keyPoints || summary.keyPoints.length === 0) ? (
                <p className="text-xs text-slate-400 italic">No discussion points categorized.</p>
              ) : (
                <ul className="space-y-2">
                  {summary.keyPoints.map((kp, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-indigo-500 font-bold mt-0.5">•</span>
                      <div>
                        <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{kp.category}</span>
                        <p className="text-slate-600 mt-1">{kp.point}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Action Items Table */}
          <div>
            <h3 className="text-sm font-bold text-slate-800 mb-3">Action Items</h3>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="p-3 text-xs font-semibold text-slate-500">Task</th>
                    <th className="p-3 text-xs font-semibold text-slate-500 w-1/5">Owner</th>
                    <th className="p-3 text-xs font-semibold text-slate-500 w-[90px] text-center">Priority</th>
                    <th className="p-3 text-xs font-semibold text-slate-500 w-[100px] text-center">Deadline</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.actionItems.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="p-3 text-slate-700">{item.task}</td>
                      <td className="p-3 text-slate-600 font-medium">{item.owner}</td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          item.priority === 'High' ? 'bg-red-50 text-red-700 border border-red-200' :
                          item.priority === 'Medium' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                          'bg-green-50 text-green-700 border border-green-200'
                        }`}>
                          {item.priority}
                        </span>
                      </td>
                      <td className="p-3 text-center text-slate-500 text-xs font-medium">{item.deadline}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Slide Gallery — collapsible */}
          {summary.slides && summary.slides.length > 0 && (
            <div>
              <button
                onClick={() => setShowSlides(!showSlides)}
                className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 text-left transition-colors cursor-pointer"
              >
                <span className="text-sm font-bold text-slate-800">
                  Extracted Slides ({summary.slides.length})
                </span>
                {showSlides ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>

              {showSlides && (
                <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {summary.slides.map((s) => {
                    const isExcluded = excludedSlideIds.has(s.id);
                    return (
                      <div key={s.id} className={`relative group rounded-lg border overflow-hidden ${isExcluded ? 'border-red-200 opacity-50' : 'border-slate-200'}`}>
                        <div className="aspect-video bg-slate-900">
                          <img src={s.dataUrl} alt={s.caption} className="w-full h-full object-contain" />
                        </div>
                        <div className="absolute top-1.5 left-1.5 bg-black/70 text-white text-[9px] font-mono px-1.5 py-0.5 rounded">
                          {Math.floor(s.timestamp / 60)}:{(s.timestamp % 60).toString().padStart(2, '0')}
                        </div>
                        <div className="p-2 bg-white">
                          <p className="text-[10px] text-slate-600 truncate">{s.caption}</p>
                          <button
                            onClick={() => onToggleExcludeSlide(s.id)}
                            className={`mt-1 text-[9px] font-bold cursor-pointer ${isExcluded ? 'text-emerald-600 hover:text-emerald-700' : 'text-red-500 hover:text-red-600'}`}
                          >
                            {isExcluded ? '+ Include in report' : '× Exclude from report'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Transcript — collapsible accordion */}
          {summary.segments && summary.segments.length > 0 && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 text-left transition-colors cursor-pointer"
              >
                <span className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-indigo-500" />
                  Full Transcript ({summary.segments.length} segments)
                </span>
                {showTranscript ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>

              {showTranscript && (
                <div className="p-4 space-y-3 max-h-[450px] overflow-y-auto border-t border-slate-200 bg-white">
                  {/* Legend */}
                  <div className="flex flex-wrap gap-1.5 pb-3 border-b border-slate-100">
                    {speakerKeys.map((key) => {
                      const color = getSpeakerColor(key, speakerKeys);
                      return (
                        <span key={key} className={`text-[10px] font-bold px-2 py-0.5 rounded border ${color.badge}`}>
                          {summary.speakerMapping[key]}
                        </span>
                      );
                    })}
                  </div>

                  {summary.segments.map((seg) => {
                    const color = getSpeakerColor(seg.originalSpeaker, speakerKeys);
                    return (
                      <div key={seg.id} className="flex items-start gap-2.5">
                        <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded whitespace-nowrap mt-1 shrink-0">
                          {Math.floor(seg.startTime / 60)}:{(seg.startTime % 60).toString().padStart(2, '0')}
                        </span>
                        <div className="flex-1 min-w-0">
                          <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded border mb-1 ${color.badge}`}>
                            {seg.speaker || seg.originalSpeaker}
                          </span>
                          <p className={`text-sm text-slate-600 leading-relaxed border-l-4 pl-3 py-1 ${color.accent}`}>
                            {seg.text}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
