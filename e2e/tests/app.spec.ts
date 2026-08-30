import { expect, test } from "@playwright/test";

async function login(page) {
  await page.goto("/");
  await page.getByLabel("E-mail").fill("admin@operator.demo");
  await page.getByLabel("Senha").fill("operator123");
  await page.getByRole("button", { name: "Entrar no workspace →" }).click();
  await expect(page.getByRole("heading", { name: "Operações de venda" })).toBeVisible({
    timeout: 20000,
  });
}

async function upload(page, file) {
  const chooser = page.waitForEvent("filechooser");
  await page.getByText("＋ Novo pedido").click();
  await (await chooser).setFiles(file);
}

test("fluxo completo: login, upload, mapear, executar", async ({ page }) => {
  await login(page);
  await upload(page, "fixtures/pedido_simples.pdf");

  await expect(page.locator(".detail .items .itemRow")).toHaveCount(2, { timeout: 30000 });

  const inputs = page.locator(".erpInput");
  await inputs.nth(0).fill("ERP-CIM-1");
  await inputs.nth(0).press("Tab");
  await inputs.nth(1).fill("ERP-ARE-2");
  await inputs.nth(1).press("Tab");

  await expect(page.locator(".items em.ok")).toHaveCount(2, { timeout: 15000 });
  await expect(page.locator(".execute")).toBeEnabled({ timeout: 10000 });
  await page.locator(".execute").click();
  await expect(page.getByText("Executado com sucesso ✓")).toBeVisible({ timeout: 20000 });

  await page.getByRole("button", { name: /Mapeamentos/ }).click();
  await expect(page.locator(".table .trow").first()).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("ERP-CIM-1")).toBeVisible();
});

test("CNPJ inválido bloqueia execução e vai para revisão", async ({ page }) => {
  await login(page);
  await upload(page, "fixtures/pedido_cnpj_invalido.pdf");

  await expect(page.locator(".issues")).toContainText("CNPJ inválido", { timeout: 30000 });
  await expect(page.locator(".execute")).toBeDisabled();
});

test("cadastro de nova conta cria workspace isolado", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Criar conta", exact: true }).click();
  await page.getByLabel("Nome").fill("Cliente E2E");
  await page.getByLabel("E-mail").fill(`cliente${Date.now()}@e2e.com`);
  await page.getByLabel("Senha").fill("senha123");
  await page.getByRole("button", { name: /Criar conta e entrar/ }).click();
  await expect(page.getByRole("heading", { name: "Operações de venda" })).toBeVisible({
    timeout: 20000,
  });
  await expect(page.getByText("Envie o primeiro PDF para iniciar.")).toBeVisible();
});