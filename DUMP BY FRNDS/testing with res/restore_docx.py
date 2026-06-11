import re

replacement = """export async function compileMeetingDocx(summary: any, excludedSlideIds: string[] = []): Promise<Buffer> {
  const excludedSet = new Set(excludedSlideIds);
  const docChildren: any[] = [];
  const now = new Date();

  // We check for the new schema properties like "utterances"
  const isNewSchema = !!summary.meta || !!summary.exec_summary;

  const getImageBuffer = (s: any) => {
    if (s && s.dataUrl) {
      if (s.dataUrl.startsWith("data:image/") && s.dataUrl.includes("base64,")) {
        try {
          return Buffer.from(s.dataUrl.split("base64,")[1], "base64");
        } catch (e) { console.error("Image buffer error", e); }
      } else {
        try {
          const fs = require("fs");
          const path = require("path");
          let absPath = s.dataUrl;
          if (!path.isAbsolute(absPath)) {
            let p = s.dataUrl.startsWith("/") ? s.dataUrl.substring(1) : s.dataUrl;
            absPath = path.join(process.cwd(), p);
          }
          if (fs.existsSync(absPath)) return fs.readFileSync(absPath);
        } catch (e) { console.error("Disk image error:", e); }
      }
    }
    return null;
  };

  const FONT_FAMILY = "Arial";

  const noBorders = {
    top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    insideHorizontal: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  };

  if (isNewSchema) {
    const meta = summary.meta || {};
    const titleStr = meta.title || "MEETING SUMMARY REPORT";

    // 1. HERO HEADER
    const heroTable = new Table({
      rows: [
        new TableRow({
          children: [new TableCell({
            children: [
              new Paragraph({
                children: [new TextRun({ text: titleStr.toUpperCase(), bold: true, size: 44, color: "FFFFFF", font: FONT_FAMILY })],
                alignment: AlignmentType.LEFT, spacing: { after: 80 },
              }),
              new Paragraph({
                children: [new TextRun({ text: "AI Meeting Summary  —  Botzilla", size: 20, color: "94A3B8", font: FONT_FAMILY })],
                alignment: AlignmentType.LEFT,
              })
            ],
            shading: { fill: "0F1117" },
            margins: { top: 400, bottom: 400, left: 300, right: 300 },
          })]
        })
      ],
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: noBorders,
    });
    docChildren.push(heroTable);
    docChildren.push(new Paragraph({ text: "", spacing: { after: 200 } }));

    // 2. METRICS TABLE
    const metricsRow = new Table({
      rows: [
        new TableRow({
          children: ["Duration", "Participants", "Language", "Slides"].map(h => new TableCell({
            children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, size: 17, color: "94A3B8", font: FONT_FAMILY })], alignment: AlignmentType.LEFT })],
            shading: { fill: "0F1117" },
            margins: { top: 120, bottom: 120, left: 150, right: 150 },
          })),
        }),
        new TableRow({
          children: [meta.duration || "N/A", meta.participants || "0", meta.language || "English", meta.slides || "None"].map(d => new TableCell({
            children: [new Paragraph({ children: [new TextRun({ text: String(d), size: 17, color: "0F172A", font: FONT_FAMILY })], alignment: AlignmentType.LEFT })],
            shading: { fill: "E0F2FE" },
            margins: { top: 150, bottom: 150, left: 150, right: 150 },
          })),
        }),
      ],
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: noBorders,
    });
    docChildren.push(metricsRow);
    docChildren.push(new Paragraph({ text: "", spacing: { after: 300 } }));

    // 3. EXECUTIVE SUMMARY
    docChildren.push(new Paragraph({
      children: [new TextRun({ text: "Executive Summary", size: 24, color: "0F172A", font: FONT_FAMILY })],
      spacing: { after: 120 },
    }));
    docChildren.push(new Paragraph({
      children: [new TextRun({ text: summary.exec_summary || "No summary available.", size: 22, color: "0F172A", font: FONT_FAMILY })],
      spacing: { line: 320, after: 300 },
    }));

    // 4. KEY TOPICS
    if (summary.key_topics && summary.key_topics.length > 0) {
      docChildren.push(new Paragraph({
        children: [new TextRun({ text: "Key Discussion Topics", size: 24, color: "0F172A", font: FONT_FAMILY })],
        spacing: { after: 120 },
      }));

      summary.key_topics.forEach((kt: any, i: number) => {
        const topicTable = new Table({
          rows: [
            new TableRow({
              children: [new TableCell({
                children: [new Paragraph({ children: [new TextRun({ text: `${i + 1}`, bold: true, size: 20, color: "0F172A", font: FONT_FAMILY })] })],
                shading: { fill: "F8FAFC" },
                margins: { top: 120, bottom: 120, left: 200, right: 200 },
              })],
            }),
            new TableRow({
              children: [new TableCell({
                children: [
                  new Paragraph({ children: [new TextRun({ text: kt.title, bold: true, size: 22, color: "FFFFFF", font: FONT_FAMILY })], spacing: { after: 80 } }),
                  new Paragraph({ children: [new TextRun({ text: kt.body || "", size: 20, color: "94A3B8", font: FONT_FAMILY })], spacing: { line: 280 } })
                ],
                shading: { fill: "1E2130" },
                margins: { top: 200, bottom: 200, left: 200, right: 200 },
              })],
            }),
          ],
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: noBorders,
        });
        docChildren.push(topicTable);
        docChildren.push(new Paragraph({ text: "", spacing: { after: 150 } }));
      });
      docChildren.push(new Paragraph({ text: "", spacing: { after: 150 } }));
    }

    // 5. SPEAKER ANALYSIS
    if (summary.speakers && summary.speakers.length > 0) {
      docChildren.push(new Paragraph({
        children: [new TextRun({ text: "Speaker Participation", size: 24, color: "0F172A", font: FONT_FAMILY })],
        spacing: { after: 120 },
      }));

      const speakerRows: TableRow[] = [
        new TableRow({
          children: [
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "Speaker", bold: true, color: "FFFFFF", size: 19, font: FONT_FAMILY })] })], shading: { fill: "6366F1" }, margins: { top: 120, bottom: 120, left: 150, right: 150 }, width: { size: 40, type: WidthType.PERCENTAGE } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "Talk Duration", bold: true, color: "FFFFFF", size: 19, font: FONT_FAMILY })], alignment: AlignmentType.LEFT })], shading: { fill: "6366F1" }, margins: { top: 120, bottom: 120, left: 150, right: 150 }, width: { size: 20, type: WidthType.PERCENTAGE } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "Participation %", bold: true, color: "FFFFFF", size: 19, font: FONT_FAMILY })], alignment: AlignmentType.LEFT })], shading: { fill: "6366F1" }, margins: { top: 120, bottom: 120, left: 150, right: 150 }, width: { size: 20, type: WidthType.PERCENTAGE } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: "Words Spoken", bold: true, color: "FFFFFF", size: 19, font: FONT_FAMILY })], alignment: AlignmentType.LEFT })], shading: { fill: "6366F1" }, margins: { top: 120, bottom: 120, left: 150, right: 150 }, width: { size: 20, type: WidthType.PERCENTAGE } }),
          ],
        }),
      ];
      summary.speakers.forEach((spk: any, idx: number) => {
        const bg = idx % 2 ? "F8FAFC" : "FFFFFF";
        speakerRows.push(new TableRow({
          children: [
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: spk.name || "Unknown", size: 20, bold: true, font: FONT_FAMILY, color: "0F172A" })] })], shading: { fill: bg }, margins: { top: 120, bottom: 120, left: 150, right: 150 } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: String(spk.duration), size: 20, font: FONT_FAMILY, color: "374151" })], alignment: AlignmentType.LEFT })], shading: { fill: bg }, margins: { top: 120, bottom: 120, left: 150, right: 150 } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: String(spk.pct), size: 20, font: FONT_FAMILY, color: "374151" })], alignment: AlignmentType.LEFT })], shading: { fill: bg }, margins: { top: 120, bottom: 120, left: 150, right: 150 } }),
            new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: String(spk.words), size: 20, font: FONT_FAMILY, color: "374151" })], alignment: AlignmentType.LEFT })], shading: { fill: bg }, margins: { top: 120, bottom: 120, left: 150, right: 150 } }),
          ],
        }));
      });
      docChildren.push(new Table({
        rows: speakerRows,
        width: { size: 100, type: WidthType.PERCENTAGE },
        borders: noBorders,
      }));
      docChildren.push(new Paragraph({ text: "", spacing: { after: 300 } }));
    }

    // 6. FULL MEETING TRANSCRIPT
    docChildren.push(new Paragraph({
      children: [new TextRun({ text: "Chronological Discussion Summary", size: 24, color: "0F172A", font: FONT_FAMILY })],
      spacing: { after: 200 },
    }));

    let activeSlides = summary.slides || [];
    
    const blockStyles = [
      { accent: "0EA5E9", bg: "E0F2FE", textAccent: "0EA5E9" }, // Blue
      { accent: "10B981", bg: "D1FAE5", textAccent: "10B981" }, // Green
      { accent: "F59E0B", bg: "FEF3C7", textAccent: "F59E0B" }, // Amber
      { accent: "EF4444", bg: "FEE2E2", textAccent: "EF4444" }, // Red
      { accent: "8B5CF6", bg: "EDE9FE", textAccent: "8B5CF6" }, // Purple
    ];
    const speakerStyleMap: Record<string, any> = {};
    const uniqueSpeakers = Array.from(new Set((summary.speakers || []).map((s: any) => s.name).filter(Boolean) as string[])).sort();
    uniqueSpeakers.forEach((spk, idx) => { speakerStyleMap[spk] = blockStyles[idx % blockStyles.length]; });

    const legendRuns = [
      new TextRun({ text: "Speaker Legend:   ", bold: true, size: 19, color: "6B7280", font: FONT_FAMILY })
    ];
    uniqueSpeakers.forEach(spk => {
      legendRuns.push(new TextRun({ text: "● ", bold: true, size: 19, color: speakerStyleMap[spk]?.accent || "0EA5E9", font: FONT_FAMILY }));
      legendRuns.push(new TextRun({ text: `${spk}   `, size: 19, color: "0F172A", font: FONT_FAMILY }));
    });
    docChildren.push(new Paragraph({ children: legendRuns, spacing: { after: 240 } }));

    if (summary.utterances && summary.utterances.length > 0) {
      for (const utt of summary.utterances) {
        const style = speakerStyleMap[utt.speaker] || blockStyles[0];

        // Process slide if present
        if (utt.slide_timestamp && activeSlides.length > 0) {
          const tsParts = utt.slide_timestamp.split(":");
          let tsSeconds = 0;
          if (tsParts.length >= 2) {
            tsSeconds = parseInt(tsParts[0]) * 60 + parseInt(tsParts[1]);
          }

          let closestSlide: any = null;
          let minDiff = Infinity;
          for (const s of activeSlides) {
            if (!excludedSet.has(s.id)) {
              const diff = Math.abs((s.timestamp || 0) - tsSeconds);
              if (diff < 30 && diff < minDiff) { 
                minDiff = diff;
                closestSlide = s;
              }
            }
          }

          if (closestSlide) {
            const imageBuffer = getImageBuffer(closestSlide);
            if (imageBuffer) {
              try {
                docChildren.push(new Paragraph({
                  children: [new TextRun({ text: `📷 Concept Illustration referenced at ${utt.slide_timestamp}`, size: 18, color: "94A3B8", font: FONT_FAMILY })],
                  alignment: AlignmentType.LEFT, spacing: { before: 80, after: 80 }
                }));
                const slideTable = new Table({
                  rows: [
                    new TableRow({
                      children: [new TableCell({
                        children: [
                          new Paragraph({
                            children: [new ImageRun({ data: imageBuffer, transformation: { width: 500, height: 281 }, type: "png" })],
                            alignment: AlignmentType.CENTER,
                          }),
                          ...(closestSlide.extractedText ? [
                            new Paragraph({
                              children: [new TextRun({ text: "Slide OCR Text:", bold: true, size: 18, color: "64748B", font: FONT_FAMILY })],
                              spacing: { before: 120 }
                            }),
                            new Paragraph({
                              children: [new TextRun({ text: closestSlide.extractedText, size: 18, color: "334155", font: FONT_FAMILY })]
                            })
                          ] : [])
                        ],
                        shading: { fill: "F8FAFC" },
                        margins: { top: 100, bottom: 100, left: 100, right: 100 },
                        borders: {
                           top: { style: BorderStyle.SINGLE, size: 2, color: "E2E8F0" },
                           bottom: { style: BorderStyle.SINGLE, size: 2, color: "E2E8F0" },
                           left: { style: BorderStyle.SINGLE, size: 2, color: "E2E8F0" },
                           right: { style: BorderStyle.SINGLE, size: 2, color: "E2E8F0" },
                        }
                      })]
                    })
                  ],
                  width: { size: 100, type: WidthType.PERCENTAGE },
                  borders: noBorders,
                  alignment: AlignmentType.CENTER,
                });
                docChildren.push(slideTable);
                docChildren.push(new Paragraph({ text: "", spacing: { after: 200 } }));
              } catch (imgErr) { console.error("Failed to insert inline docx image:", imgErr); }
            }
          }
        }

        // Timeline Block Table
        const uttTable = new Table({
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  children: [new Paragraph({ text: "" })],
                  shading: { fill: style.accent },
                  width: { size: 2, type: WidthType.PERCENTAGE },
                  borders: noBorders,
                }),
                new TableCell({
                  children: [
                    new Paragraph({
                      children: [
                        new TextRun({ text: utt.speaker, bold: true, size: 20, color: style.textAccent, font: FONT_FAMILY }),
                        new TextRun({ text: `   [${utt.start} - ${utt.end}]`, size: 18, color: "6B7280", font: FONT_FAMILY }),
                      ],
                      spacing: { after: 60 }
                    }),
                    new Paragraph({
                      children: [new TextRun({ text: utt.text || "", size: 20, color: "0F172A", font: FONT_FAMILY })],
                      spacing: { line: 280 }
                    })
                  ],
                  shading: { fill: style.bg },
                  margins: { top: 120, bottom: 120, left: 150, right: 150 },
                  width: { size: 98, type: WidthType.PERCENTAGE },
                  borders: noBorders,
                })
              ]
            })
          ],
          width: { size: 100, type: WidthType.PERCENTAGE },
          borders: noBorders,
        });

        docChildren.push(uttTable);
        docChildren.push(new Paragraph({ text: "", spacing: { after: 80 } }));
      }
    } else {
      docChildren.push(new Paragraph({
        children: [new TextRun({ text: "No transcript utterances available.", size: 20, italics: true, color: "94A3B8" })],
        spacing: { after: 120 }
      }));
    }

  }

  const doc = new Document({
    sections: [{
      properties: {
        page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } }
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            children: [
              new TextRun({ text: "End of Meeting Summary Report", size: 18, color: "6B7280", font: FONT_FAMILY }),
            ],
            alignment: AlignmentType.CENTER,
          })],
        }),
      },
      children: docChildren,
    }],
  });

  return await Packer.toBuffer(doc);
}"""

with open('d:/ai-meeting-summarizer/docxGenerator.ts', 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(r'export async function compileMeetingDocx\([\s\S]*?return await Packer\.toBuffer\(doc\);\n}', replacement, content)

with open('d:/ai-meeting-summarizer/docxGenerator.ts', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replaced compileMeetingDocx successfully with gorgeous themes and new schema.")
