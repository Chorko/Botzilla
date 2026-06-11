import * as fs from 'fs';
import * as path from 'path';
import { compileMeetingDocx } from '../../docxGenerator';

async function runTests() {
  const dummyBase64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

  const test1: any = {
    meta: {
      title: "Backend Architecture Sync",
      duration: "15m 30s",
      participants: "2",
      language: "English",
      slides: "1 captured",
      mode: "UNIFIED",
      source: "synth.txt"
    },
    exec_summary: "The presentation covered the new backend architecture migration and API rotation strategy. The core problem being solved was the frequent database locks occurring during high-load periods on the legacy SQLite deployment. The team discussed the key solution features, including WAL journal mode integration and connection limits, which should resolve the locking issues. Outcomes include an action plan to deploy these mitigations in staging by Friday and monitor the metrics over the weekend.",
    key_topics: [
      {
        title: "Database Infrastructure Locks",
        body: "The team analyzed the recurrent database locks in the current SQLite environment. High read/write concurrency during peak hours was identified as the primary culprit."
      },
      {
        title: "WAL Mode Integration",
        body: "Implementing Write-Ahead Logging (WAL) was proposed as the definitive solution. This change is expected to drastically improve concurrent read operations."
      },
      {
        title: "Deployment Timelines",
        body: "A strict deadline was established for Friday EOD to roll out these changes to the staging environment. Testing will commence immediately after."
      }
    ],
    speakers: [
      { name: "Speaker 1", duration: "1m 43s", pct: "98.7%", words: "271" },
      { name: "Speaker 2", duration: "0m 01s", pct: "1.3%", words: "4" }
    ],
    utterances: [
      {
        speaker: "Speaker 1",
        start: "00:00",
        end: "00:26",
        text: "Introduced the core problem: getting stuck chasing documents, missing emails, and guessing on financials. Highlighted how this leads to lost deals and introduced the 'respo engine' as an instant data-matching solution.",
        slide_timestamp: "00:00",
        slide_frame_path: null
      },
      {
        speaker: "Speaker 2",
        start: "00:27",
        end: "00:28",
        text: "Agreed on the approach.",
        slide_timestamp: null,
        slide_frame_path: null
      }
    ],
    slides: [
      { id: "slide_1", timestamp: 0, dataUrl: dummyBase64, extractedText: "DATABASE LOCKS" }
    ]
  };

  const test2: any = {
    meta: {
      title: "Property Analysis System Demo",
      duration: "2m 9s",
      participants: "2",
      language: "English",
      slides: "7 captured",
      mode: "UNIFIED",
      source: "template2_dump.txt"
    },
    exec_summary: "This presentation introduced an innovative property analysis and management system designed to improve the efficiency and security of property acquisition. The system addresses common challenges by providing instant data matching, comprehensive risk analysis, and an interactive financial dashboard. The presentation demonstrated how users can identify and secure profitable property deals quickly, backed by a smart API rotation system and robust backend ensuring continuous data availability.",
    key_topics: [
      {
        title: "Addressing Inefficiencies in Property Acquisition",
        body: "Highlighted common pitfalls like document chasing and financial ambiguities that cause deals to be lost. A 'respo engine' was introduced to provide instant answers and data matching."
      },
      {
        title: "Interactive Financial Dashboard",
        body: "Showcased a dashboard giving a holistic view of all properties at once, including virtual cash performance and operating margins."
      }
    ],
    speakers: [
      { name: "Rahul", duration: "1m 43s", pct: "98.7%", words: "271" },
      { name: "Reina", duration: "0m 01s", pct: "1.3%", words: "4" }
    ],
    utterances: [
      {
        speaker: "Rahul",
        start: "00:00",
        end: "00:26",
        text: "In Chara, she found a perfect property but got stuck in a trap — chasing documents, missing emails, and guessing on financials. By the time she was ready, she lost the deal to a faster firm. Now imagine instead she gets answers in seconds.",
        slide_timestamp: "00:00",
        slide_frame_path: null
      },
      {
        speaker: "Rahul",
        start: "00:29",
        end: "00:41",
        text: "We also have an interactive financial dashboard where she can look over all her properties at once and review virtual cash performance and operating margins.",
        slide_timestamp: "00:29",
        slide_frame_path: null
      },
      {
        speaker: "Reina",
        start: "01:07",
        end: "01:08",
        text: "Thanks Rahul. Let's consider this example.",
        slide_timestamp: "01:02",
        slide_frame_path: null
      }
    ],
    slides: [
      { id: "slide_1", timestamp: 0, dataUrl: dummyBase64, extractedText: "CHARA PROPERTY SYSTEM" },
      { id: "slide_2", timestamp: 29, dataUrl: dummyBase64, extractedText: "FINANCIAL DASHBOARD" },
      { id: "slide_3", timestamp: 62, dataUrl: dummyBase64, extractedText: "EXAMPLE ANALYSIS" }
    ]
  };

  const test3: any = {
    meta: {
      title: "Hinglish Standup Sync",
      duration: "5m 12s",
      participants: "3",
      language: "Hinglish",
      slides: "None",
      mode: "UNIFIED",
      source: "mock3.txt"
    },
    exec_summary: "The team discussed the upcoming frontend changes and verified the deployment issues from the previous night. It was agreed that the new React components need further optimization before merging into main.",
    key_topics: [
      {
        title: "Frontend Optimization",
        body: "React components are causing unnecessary re-renders. A memoization strategy was proposed."
      }
    ],
    speakers: [
      { name: "Amit", duration: "2m", pct: "40%", words: "150" },
      { name: "Priya", duration: "2m", pct: "40%", words: "160" },
      { name: "Speaker 3", duration: "1m 12s", pct: "20%", words: "80" }
    ],
    utterances: [
      {
        speaker: "Amit",
        start: "00:00",
        end: "00:15",
        text: "Mera naam Amit hai. Toh kal raat deployment mein issue aaya tha yaar. Matlab pipeline fail ho gayi thi.",
        slide_timestamp: null,
        slide_frame_path: null
      },
      {
        speaker: "Priya",
        start: "00:16",
        end: "00:30",
        text: "Haan bhai, react components kafi re-render ho rahe hain. We need to optimize them before the next release.",
        slide_timestamp: null,
        slide_frame_path: null
      },
      {
        speaker: "Speaker 3",
        start: "00:31",
        end: "00:45",
        text: "I will check the CI/CD logs to see what exactly broke the build.",
        slide_timestamp: null,
        slide_frame_path: null
      }
    ],
    slides: []
  };

  const runs = [
    { name: "test1.docx", payload: test1 },
    { name: "test2.docx", payload: test2 },
    { name: "test3.docx", payload: test3 }
  ];

  for (const run of runs) {
    try {
      const docBuffer = await compileMeetingDocx(run.payload, []);
      const outputPath = path.join(process.cwd(), 'DUMP BY FRNDS', 'testing with res', run.name);
      fs.writeFileSync(outputPath, docBuffer);
      console.log(`Successfully generated DOCX at: ${outputPath}`);
    } catch (error) {
      console.error(`Error generating ${run.name}:`, error);
    }
  }
}

runTests();
