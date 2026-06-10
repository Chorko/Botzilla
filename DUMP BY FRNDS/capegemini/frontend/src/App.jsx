import React, { useState } from 'react';

export default function BotzillaInterface() {
    const [new_, setNew] = useState(null);
    const [res_, setRes] = useState(false);
    const [arr_, setArr] = useState(null);
    const [showText_, setShowText] = useState(false);
    
    const handleUpload = async (e) => {
        e.preventDefault();
        if (!new_) return;
        
        setRes(true);
        const form_ = new FormData();
        form_.append("file", new_); 
        
        try {
            const req_ = await fetch("http://localhost:8000/botzilla/process", {
                method: "POST",
                body: form_
            });
            const data_ = await req_.json();
            setArr(data_);
        } catch (error) {
            console.error("Botzilla Error:", error);
            alert("Error processing the audio. Check your backend terminal.");
        }
        
        setRes(false);
    };
    
    return (
        <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10 font-sans">
            {/* Header */}
            <div className="w-full max-w-5xl text-center mb-8">
                <h1 className="text-5xl font-extrabold tracking-widest text-[#0070AD]">BOTZILLA</h1>
                <p className="text-gray-500 mt-2 font-medium tracking-wide">Enterprise Audio Intelligence</p>
            </div>

            {/* Upload Section */}
            <div className="bg-white rounded-xl shadow-lg w-full max-w-5xl overflow-hidden border-t-8 border-[#0070AD] mb-8">
                <form onSubmit={handleUpload} className="p-8">
                    <div className="flex flex-col items-center justify-center w-full h-40 border-2 border-[#0070AD] border-dashed rounded-lg bg-blue-50 hover:bg-blue-100 transition-all cursor-pointer relative">
                        <input type="file" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onChange={(e) => setNew(e.target.files[0])} />
                        <svg className="w-10 h-10 text-[#0070AD] mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                        </svg>
                        <p className="text-lg text-[#0070AD] font-bold">
                            {new_ ? new_.name : "Click to upload or drag and drop"}
                        </p>
                    </div>
                    
                    <button 
                        type="submit" 
                        disabled={res_ || !new_} 
                        className="mt-6 w-full bg-[#0070AD] text-white font-bold py-4 px-4 rounded-lg hover:bg-blue-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md text-lg"
                    >
                        {res_ ? "Botzilla is Processing (This may take a few minutes)..." : "Generate Intelligence Report"}
                    </button>
                </form>
            </div>

            {/* Dynamic Results Section */}
            {arr_ && arr_.data && (
                <div className="bg-white rounded-xl shadow-lg w-full max-w-5xl overflow-hidden mb-12">
                    {/* Title & Download Bar */}
                    <div className="bg-[#0070AD] p-6 text-white flex justify-between items-center">
                        <div>
                            <h2 className="text-2xl font-bold">{arr_.data.summary.meeting_title}</h2>
                            <p className="text-blue-100 text-sm mt-1">{arr_.data.summary.date} | Attendees: {arr_.data.summary.attendees.join(", ")}</p>
                        </div>
                        <a 
    href={`http://localhost:8000/botzilla/download/${arr_.data.pdf_file || "Final_Report.pdf"}`} 
    target="_blank" 
    rel="noreferrer" 
    className="bg-white text-[#0070AD] font-bold py-2 px-6 rounded hover:bg-gray-100 transition-colors shadow"
>
    Download PDF
</a>
                    </div>

                    <div className="p-8 space-y-8">
                        {/* Metrics Grid */}
                        <div className="grid grid-cols-4 gap-4">
                            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
                                <p className="text-gray-500 text-sm font-bold uppercase">Duration</p>
                                <p className="text-2xl font-black text-[#0070AD]">{arr_.data.summary.metrics.duration_hours}h</p>
                            </div>
                            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
                                <p className="text-gray-500 text-sm font-bold uppercase">Attendees</p>
                                <p className="text-2xl font-black text-[#0070AD]">{arr_.data.summary.metrics.attendees_count}</p>
                            </div>
                            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
                                <p className="text-gray-500 text-sm font-bold uppercase">Decisions</p>
                                <p className="text-2xl font-black text-[#0070AD]">{arr_.data.summary.metrics.decisions_count}</p>
                            </div>
                            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
                                <p className="text-gray-500 text-sm font-bold uppercase">Actions</p>
                                <p className="text-2xl font-black text-[#0070AD]">{arr_.data.summary.metrics.actions_count}</p>
                            </div>
                        </div>

                        {/* Executive Summary */}
                        <div>
                            <h3 className="text-xl font-bold text-gray-800 border-b-2 border-gray-100 pb-2 mb-3">Executive Summary</h3>
                            <p className="text-gray-700 leading-relaxed">{arr_.data.summary.executive_summary}</p>
                        </div>

                        {/* Layout Split: Decisions & Discussion Points */}
                        <div className="grid grid-cols-2 gap-8">
                            <div>
                                <h3 className="text-xl font-bold text-gray-800 border-b-2 border-gray-100 pb-2 mb-3">Key Decisions</h3>
                                <ul className="space-y-2">
                                    {arr_.data.summary.key_decisions.map((item, idx) => (
                                        <li key={idx} className="text-gray-700 flex items-start">
                                            <span className="text-[#0070AD] mr-2">•</span> {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-800 border-b-2 border-gray-100 pb-2 mb-3">Discussion Points</h3>
                                <ul className="space-y-2">
                                    {arr_.data.summary.key_discussion_points.map((item, idx) => (
                                        <li key={idx} className="text-gray-700 flex items-start">
                                            <span className="text-[#0070AD] mr-2">•</span> {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Action Items Table */}
                        <div>
                            <h3 className="text-xl font-bold text-gray-800 border-b-2 border-gray-100 pb-2 mb-3">Action Items</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="bg-gray-50 text-gray-600 border-b">
                                            <th className="p-3 font-semibold">Task</th>
                                            <th className="p-3 font-semibold w-1/4">Owner</th>
                                            <th className="p-3 font-semibold w-1/4">Deadline</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {arr_.data.action_items.map((act, idx) => (
                                            <tr key={idx} className="border-b hover:bg-gray-50">
                                                <td className="p-3 text-gray-800">{act.task}</td>
                                                <td className="p-3 text-gray-600 font-medium">{act.owner}</td>
                                                <td className="p-3 text-red-600 font-medium">{act.due_date}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Raw Transcript Accordion */}
                        <div className="mt-8 border rounded-lg overflow-hidden">
                            <button 
                                onClick={() => setShowText(!showText_)} 
                                className="w-full bg-gray-50 p-4 flex justify-between items-center text-left hover:bg-gray-100 transition-colors focus:outline-none"
                            >
                                <span className="font-bold text-gray-800">View Full Transcript</span>
                                <svg className={`w-6 h-6 text-gray-500 transform transition-transform duration-200 ${showText_ ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                                </svg>
                            </button>
                            
                            {showText_ && (
                                <div className="p-6 bg-white border-t max-h-96 overflow-y-auto">
                                    <p className="text-gray-700 whitespace-pre-wrap leading-relaxed font-mono text-sm">
                                        {arr_.data.clean_transcript}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}