import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "screenshots");
fs.mkdirSync(OUT, { recursive: true });

const api = spawn(process.env.PYTHON || "python", [path.join(ROOT, "e2e", "run_api.py")], {
  cwd: ROOT,
  stdio: "inherit",
});
const web = spawn("npx", ["next", "dev", "-p", "3001"], {
  cwd: path.join(ROOT, "apps", "web"),
  env: {
    ...process.env,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001/api/v1",
  },
  stdio: "inherit",
  shell: true,
});

async function wait(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name), fullPage: false });
  console.log("  shot:", name);
}

const { chromium } = await import("@playwright/test");

try {
  await wait("http://127.0.0.1:8001/health");
  await wait("http://127.0.0.1:3001");

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

  await page.goto("http://127.0.0.1:3001");
  await page.waitForSelector(".loginShell", { timeout: 20000 });
  await page.waitForTimeout(700);
  await shot(page, "01-login.png");

  await page.getByLabel("E-mail").fill("admin@operator.demo");
  await page.getByLabel("Senha").fill("operator123");
  await page.getByRole("button", { name: "Entrar no workspace →" }).click();
  await page.getByRole("heading", { name: "Operações de venda" }).waitFor({ timeout: 20000 });

  async function upload(file) {
    const chooser = page.waitForEvent("filechooser");
    await page.getByText(/Novo pedido/).click();
    await (await chooser).setFiles(file);
    await page.locator(".detail .items .itemRow").first().waitFor({ timeout: 30000 });
    await page.waitForTimeout(1200);
  }

  // 1º pedido: mapear e executar
  await upload(path.join(ROOT, "e2e", "fixtures", "pedido_simples.pdf"));
  const inputs = page.locator(".erpInput");
  await inputs.nth(0).fill("ERP-CIM-1");
  await inputs.nth(0).press("Tab");
  await inputs.nth(1).fill("ERP-ARE-2");
  await inputs.nth(1).press("Tab");
  await page.locator(".items em.ok").first().waitFor({ timeout: 15000 });
  await page.locator(".execute").click();
  await page.getByText("Executado com sucesso").waitFor({ timeout: 20000 });
  await page.waitForTimeout(900);

  // 2º pedido (pronto, sem mapeamento) + 3º (CNPJ inválido → revisão)
  await upload(path.join(ROOT, "e2e", "fixtures", "pedido_simples.pdf"));
  await upload(path.join(ROOT, "e2e", "fixtures", "pedido_cnpj_invalido.pdf"));
  await page.locator(".issues").filter({ hasText: "CNPJ inválido" }).first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1200);
  await shot(page, "02-operacoes.png");

  await page.getByRole("button", { name: /Mapeamentos/ }).click();
  await page.locator(".table .trow").first().waitFor({ timeout: 15000 });
  await page.waitForTimeout(700);
  await shot(page, "03-mapeamentos.png");

  await page.getByRole("button", { name: /Auditoria/ }).click();
  await page.locator(".tlItem").first().waitFor({ timeout: 15000 });
  await page.waitForTimeout(700);
  await shot(page, "04-auditoria.png");

  await page.getByRole("button", { name: /ROI/ }).click();
  await page.locator(".roiMetric").first().waitFor({ timeout: 15000 });
  await page.waitForTimeout(700);
  await shot(page, "05-roi.png");

  await browser.close();
  console.log("Screenshots salvos em", OUT);
} catch (err) {
  console.error("FALHA:", err);
  process.exitCode = 1;
} finally {
  api.kill();
  web.kill();
  setTimeout(() => process.exit(), 1500);
}