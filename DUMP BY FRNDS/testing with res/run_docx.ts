import fs from 'fs';
import path from 'path';
import { compileMeetingDocx } from '../../docxGenerator';

async function run() {
    const data = JSON.parse(fs.readFileSync('d:\\ai-meeting-summarizer\\DUMP BY FRNDS\\testing with res\\test3_payload.json', 'utf8'));
    const docBuffer = await compileMeetingDocx(data, []);
    fs.writeFileSync('d:\\ai-meeting-summarizer\\DUMP BY FRNDS\\testing with res\\test3_final.docx', docBuffer);
    console.log("Successfully generated test3_final.docx");
}
run();
