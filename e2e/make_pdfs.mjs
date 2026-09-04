import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import { chromium } from "@playwright/test";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "docs", "PDF");
fs.mkdirSync(OUT, { recursive: true });

const STYLE = `
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", Inter, Roboto, Arial, sans-serif;
  color: #101828; font-size: 10.5pt; line-height: 1.55; margin: 0;
}
.brand {
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 10px; margin-bottom: 14px;
  border-bottom: 2px solid #e4e7ec;
  font-weight: 800; font-size: 12pt; color: #0f1726;
}
.brand::before {
  content: "AO";
  display: inline-grid; place-items: center;
  width: 26px; height: 26px; border-radius: 7px;
  background: linear-gradient(135deg, #2dd4bf, #14b8a6 45%, #3b82f6);
  color: #fff; font-size: 10pt;
}
h1 { font-size: 19pt; letter-spacing: -0.02em; margin: 18px 0 10px; color: #0b1220; }
h2 { font-size: 13.5pt; margin: 20px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #eaecf0; color: #0e7c72; }
h3 { font-size: 11.5pt; margin: 14px 0 6px; }
p { margin: 8px 0; }
ul, ol { margin: 8px 0; padding-left: 20px; }
li { margin: 3px 0; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9.5pt; }
th { background: #f2f4f7; text-align: left; }
th, td { border: 1px solid #d0d5dd; padding: 6px 9px; }
code { background: #f2f4f7; border: 1px solid #eaecf0; border-radius: 4px; padding: 1px 5px; font-size: 9pt; }
blockquote { margin: 10px 0; padding: 8px 14px; background: #f0fdfa; border-left: 3px solid #0e7c72; border-radius: 0 6px 6px 0; }
blockquote p { margin: 0; }
a { color: #0e7c72; }
strong { color: #0b1220; }
`;

async function render(mdPath, title, outName) {
  const md = fs.readFileSync(mdPath, "utf-8");
  const html = marked.parse(md);
  const doc = `<!doctype html><html><head><meta charset="utf-8"><style>${STYLE}</style></head>
<body><div class="brand">AIOperator · ${title}</div>${html}</body></html>`;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(doc, { waitUntil: "networkidle" });
  const file = path.join(OUT, outName);
  await page.pdf({ path: file, format: "A4", printBackground: true });
  await browser.close();
  console.log("PDF gerado:", file, `(${Math.round(fs.statSync(file).size / 1024)} KB)`);
}

await render(path.join(ROOT, "docs", "ONBOARDING.md"), "Guia de Onboarding", "AIOperator-Onboarding.pdf");
await render(path.join(ROOT, "docs", "PROPOSTA.md"), "Proposta Comercial", "AIOperator-Proposta.pdf");