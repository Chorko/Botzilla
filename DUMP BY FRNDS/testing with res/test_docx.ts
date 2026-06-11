import * as fs from 'fs';
import * as path from 'path';

// Import the function we just rewrote
import { compileMeetingDocx } from '../../docxGenerator';

async function runTest() {
  // Mock summary object representing Gemini's output + slide metadata
  const mockSummary = {
    meta: {
      title: "Terra Truce - Property Analysis System Demo",
      duration: "2m 9s",
      participants: "2",
      language: "English",
      slides: "7 captured",
      mode: "UNIFIED",
      source: "Terra-Truce_Demo.mp4"
    },
    exec_summary: "The meeting demonstrated the Terra Truce Property Analysis System. The presenters showcased the dashboard, map layers, and predictive models to evaluate real estate properties.",
    key_topics: [
      {
        title: "Dashboard Overview",
        body: "Walkthrough of the main analytics dashboard and key KPIs."
      },
      {
        title: "Map Integration",
        body: "Demonstration of GIS overlays for property valuation."
      }
    ],
    speakers: [
      { name: "Speaker 1", duration: "1m 10s", pct: "54%", words: 210 },
      { name: "Speaker 2", duration: "0m 59s", pct: "46%", words: 180 }
    ],
    timeline_summaries: [
      {
        time_range: "00:00 - 00:45",
        speakers: "Speaker 1",
        summary: "Introduced the Terra Truce project and opened the main dashboard.",
        slide_timestamp: "00:15"
      },
      {
        time_range: "00:45 - 01:30",
        speakers: "Speaker 2",
        summary: "Discussed the predictive modeling features using the map interface.",
        slide_timestamp: "01:05"
      }
    ],
    slides: [
      {
        id: "slide_1",
        timestamp: 15,
        // We need a real image for the test, let's just use any png we have or a dummy base64
        dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", 
        extractedText: "DASHBOARD\nTOTAL PROPERTIES 1,200\nREVENUE $4.5M"
      },
      {
        id: "slide_2",
        timestamp: 65,
        dataUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=",
        extractedText: "MAP VIEW\nPREDICTIVE ZONING MODEL\nCONFIDENCE: 92%"
      }
    ]
  };

  try {
    const docBuffer = await compileMeetingDocx(mockSummary, []);
    const outputPath = path.join(process.cwd(), 'DUMP BY FRNDS', 'testing with res', 'test_output.docx');
    fs.writeFileSync(outputPath, docBuffer);
    console.log(`Successfully generated DOCX at: ${outputPath}`);
  } catch (error) {
    console.error("Error generating DOCX:", error);
  }
}

runTest();
