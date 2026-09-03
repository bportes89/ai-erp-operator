"use client";
import { FormEvent, useEffect, useState } from "react";

type Item = {
  id: string;
  description: string;
  customer_code: string | null;
  erp_code: string | null;
  quantity: number;
  unit_price: number;
  total: number;
  matched: boolean;
};
type Operation = {
  id: string;
  reference: string;
  recipe_id: string | null;
  supplier: string | null;
  tax_id: string | null;
  due_date: string | null;
  cost_center: string | null;
  total: number;
  confidence: number;
  status: string;
  issues: string[];
  created_at: string;
  items: Item[];
};
type Mapping = {
  id: string;
  customer_code: string;
  description: string;
  erp_code: string;
  usage_count: number;
};
type AuditEvent = {
  id: string;
  event_type: string;
  operation_id: string | null;
  payload: Record<string, unknown>;
  hash: string;
  previous_hash: string | null;
  created_at: string;
};
type Daily = { date: string; operations: number; completed: number; value: number };
type Webhook = {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
};
type Delivery = {
  id: string;
  event: string;
  status: string;
  attempts: number;
  created_at: string;
};
type Recipe = {
  id: string;
  name: string;
  description: string | null;
  operation_type: string;
  field_aliases: Record<string, unknown>;
  required_fields: string[];
  approval_threshold: number | null;
  active: boolean;
  created_at: string;
};
type ROI = {
  total_operations: number;
  completed: number;
  pending: number;
  automation_rate: number;
  exception_rate: number;
  avg_processing_seconds: number;
  avg_time_to_erp_seconds: number;
  processed_value: number;
  hours_saved: number;
  avg_confidence: number;
  daily: Daily[];
};
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
type View = "operations" | "mappings" | "audit" | "roi" | "webhooks" | "rules" | "recipes";

export default function Page() {
  const [token, setToken] = useState("");
  const [view, setView] = useState<View>("operations");
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof document !== "undefined" &&
    document.documentElement.getAttribute("data-theme") === "dark"
      ? "dark"
      : "light"
  );
  const [operations, setOperations] = useState<Operation[]>([]);
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [audits, setAudits] = useState<AuditEvent[]>([]);
  const [roi, setRoi] = useState<ROI | null>(null);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [threshold, setThreshold] = useState<string>("");
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [uploadRecipeId, setUploadRecipeId] = useState<string>("");
  const [selected, setSelected] = useState<Operation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");

  const headers = () => ({ Authorization: token ? `Bearer ${token}` : "" });

  async function load(access = token) {
    try {
      const response = await fetch(`${API}/operations`, {
        headers: { Authorization: `Bearer ${access}` },
      });
      if (response.status === 401) {
        localStorage.removeItem("operator_token");
        setToken("");
        return;
      }
      if (!response.ok) return;
      const rows: Operation[] = await response.json();
      setOperations(rows);
      setSelected((prev) => rows.find((r) => r.id === prev?.id) ?? rows[0] ?? null);
    } catch {
      setError("API indisponível");
    }
  }

  async function loadMappings() {
    try {
      const r = await fetch(`${API}/mappings`, { headers: headers() as HeadersInit });
      if (r.ok) setMappings(await r.json());
    } catch {
      setError("API indisponível");
    }
  }

  async function loadAudit() {
    try {
      const r = await fetch(`${API}/audit`, { headers: headers() as HeadersInit });
      if (r.ok) setAudits(await r.json());
    } catch {
      setError("API indisponível");
    }
  }

  async function loadRoi() {
    try {
      const r = await fetch(`${API}/roi`, { headers: headers() as HeadersInit });
      if (r.ok) setRoi(await r.json());
    } catch {
      setError("API indisponível");
    }
  }

  async function loadWebhooks() {
    try {
      const r = await fetch(`${API}/webhooks`, { headers: headers() as HeadersInit });
      if (r.ok) setWebhooks(await r.json());
      const d = await fetch(`${API}/webhooks/deliveries`, { headers: headers() as HeadersInit });
      if (d.ok) setDeliveries(await d.json());
    } catch {
      setError("API indisponível");
    }
  }

  async function addWebhook(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const data = new FormData(e.currentTarget);
    const events = data.getAll("events").map(String);
    const r = await fetch(`${API}/webhooks`, {
      method: "POST",
      headers: { ...headers(), "content-type": "application/json" },
      body: JSON.stringify({ url: data.get("url"), events }),
    });
    if (r.ok) {
      (e.target as HTMLFormElement).reset();
      await loadWebhooks();
    } else setError((await r.json()).detail || "Falha ao criar webhook");
  }

  async function removeWebhook(id: string) {
    const r = await fetch(`${API}/webhooks/${id}`, {
      method: "DELETE",
      headers: headers() as HeadersInit,
    });
    if (r.ok) await loadWebhooks();
    else setError("Falha ao remover webhook");
  }

  async function loadSettings() {
    try {
      const r = await fetch(`${API}/organization/settings`, { headers: headers() as HeadersInit });
      if (r.ok) {
        const body = await r.json();
        setThreshold(String(body.approval_threshold));
      }
    } catch {
      setError("API indisponível");
    }
  }

  async function saveSettings(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const r = await fetch(`${API}/organization/settings`, {
      method: "PATCH",
      headers: { ...headers(), "content-type": "application/json" },
      body: JSON.stringify({ approval_threshold: Number(threshold) }),
    });
    if (r.ok) await loadSettings();
    else setError((await r.json()).detail || "Falha ao salvar regra");
  }

  async function approve() {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations/${selected.id}/approve`, {
        method: "POST",
        headers: headers() as HeadersInit,
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Falha ao aprovar");
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  async function reject() {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations/${selected.id}/reject`, {
        method: "POST",
        headers: headers() as HeadersInit,
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Falha ao recusar");
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  async function loadRecipes() {
    try {
      const r = await fetch(`${API}/recipes`, { headers: headers() as HeadersInit });
      if (r.ok) setRecipes(await r.json());
    } catch {
      setError("API indisponível");
    }
  }

  async function addRecipe(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const data = new FormData(e.currentTarget);
    const required = data.getAll("required").map(String);
    const r = await fetch(`${API}/recipes`, {
      method: "POST",
      headers: { ...headers(), "content-type": "application/json" },
      body: JSON.stringify({
        name: data.get("name"),
        operation_type: data.get("operation_type"),
        required_fields: required,
      }),
    });
    if (r.ok) {
      (e.target as HTMLFormElement).reset();
      await loadRecipes();
    } else setError((await r.json()).detail || "Falha ao criar processo");
  }

  async function toggleRecipe(id: string, active: boolean) {
    const r = await fetch(`${API}/recipes/${id}`, {
      method: "PATCH",
      headers: { ...headers(), "content-type": "application/json" },
      body: JSON.stringify({ active }),
    });
    if (r.ok) await loadRecipes();
    else setError("Falha ao atualizar processo");
  }

  function navigate(next: View) {
    setView(next);
    if (next === "mappings") loadMappings();
    if (next === "audit") loadAudit();
    if (next === "roi") loadRoi();
    if (next === "webhooks") loadWebhooks();
    if (next === "rules") loadSettings();
    if (next === "recipes") loadRecipes();
  }

  useEffect(() => {
    const saved = localStorage.getItem("operator_token");
    if (saved) {
      setToken(saved);
      load(saved);
    }
  }, []);

  useEffect(() => {
    if (!token || view !== "operations") return;
    const interval = setInterval(() => {
      if (operations.some((o) => o.status === "processing")) load();
    }, 2500);
    return () => clearInterval(interval);
  }, [token, view, operations]);

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(e.currentTarget);
    try {
      const r = await fetch(`${API}/auth/${authMode}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(
          authMode === "login"
            ? { email: data.get("email"), password: data.get("password") }
            : {
                name: data.get("name"),
                email: data.get("email"),
                password: data.get("password"),
                organization: data.get("organization"),
              }
        ),
      });
      if (r.ok) {
        const body = await r.json();
        localStorage.setItem("operator_token", body.access_token);
        setToken(body.access_token);
        await load(body.access_token);
      } else {
        const detail = (await r.json()).detail;
        setError(typeof detail === "string" ? detail : "Não foi possível continuar");
      }
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  async function upload(file?: File) {
    if (!file) return;
    if (file.type !== "application/pdf") return setError("Envie um arquivo PDF");
    const form = new FormData();
    form.append("file", file);
    if (uploadRecipeId) form.append("recipe_id", uploadRecipeId);
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations`, {
        method: "POST",
        headers: headers() as HeadersInit,
        body: form,
      });
      if (r.ok) {
        const created = await r.json();
        await load();
        setSelected(created);
      } else setError((await r.json()).detail || "Não foi possível processar o PDF");
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  async function patchOperation(body: Record<string, string | number>) {
    if (!selected) return;
    try {
      const r = await fetch(`${API}/operations/${selected.id}`, {
        method: "PATCH",
        headers: { ...headers(), "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Falha ao salvar");
    } catch {
      setError("API indisponível");
    }
  }

  async function patchItem(itemId: string, body: Record<string, string | number>) {
    if (!selected) return;
    try {
      const r = await fetch(`${API}/operations/${selected.id}/items/${itemId}`, {
        method: "PATCH",
        headers: { ...headers(), "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Falha ao salvar item");
    } catch {
      setError("API indisponível");
    }
  }

  async function rematch() {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations/${selected.id}/rematch`, {
        method: "POST",
        headers: headers() as HeadersInit,
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Falha ao sincronizar mapeamentos");
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  async function addMapping(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    const data = new FormData(e.currentTarget);
    const r = await fetch(`${API}/mappings`, {
      method: "POST",
      headers: { ...headers(), "content-type": "application/json" },
      body: JSON.stringify({
        customer_code: data.get("customer_code"),
        description: data.get("description"),
        erp_code: data.get("erp_code"),
      }),
    });
    if (r.ok) {
      (e.target as HTMLFormElement).reset();
      await loadMappings();
    } else setError((await r.json()).detail || "Falha ao criar mapeamento");
  }

  async function exportOperation(format: "csv" | "xml") {
    if (!selected) return;
    try {
      const r = await fetch(`${API}/operations/${selected.id}/export?format=${format}`, {
        headers: headers() as HeadersInit,
      });
      if (!r.ok) return setError("Falha na exportação");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selected.reference}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("API indisponível");
    }
  }

  async function execute() {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations/${selected.id}/execute`, {
        method: "POST",
        headers: { ...headers(), "Idempotency-Key": `${selected.id}-execute-v1` },
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Operação bloqueada");
    } catch {
      setError("API indisponível");
    }
    setLoading(false);
  }

  function logout() {
    localStorage.removeItem("operator_token");
    setToken("");
    setOperations([]);
    setSelected(null);
    setView("operations");
  }

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("ao_theme", next);
    } catch {
      /* ignore */
    }
  }

  if (!token)
    return (
      <main className="login">
        <section>
          <button
            className="themeFab"
            onClick={toggleTheme}
            aria-label={theme === "light" ? "Modo escuro" : "Modo claro"}
            title={theme === "light" ? "Modo escuro" : "Modo claro"}
          >
            <Icon name={theme === "light" ? "moon" : "sun"} />
          </button>
          <div className="logo">AO</div>
          <span>AI ERP OPERATOR</span>
          <h1>
            Operações no ERP,
            <br />
            sem digitação manual.
          </h1>
          <p>Entre no ambiente da sua empresa para revisar e executar pedidos B2B.</p>
          <div className="authTabs">
            <button
              className={authMode === "login" ? "active" : ""}
              onClick={() => setAuthMode("login")}
            >
              Entrar
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              onClick={() => setAuthMode("register")}
            >
              Criar conta
            </button>
          </div>
          <form onSubmit={login}>
            {authMode === "register" && (
              <>
                <label>
                  Nome
                  <input name="name" type="text" placeholder="Seu nome" minLength={2} required />
                </label>
                <label>
                  Empresa
                  <input name="organization" type="text" placeholder="Nome da empresa" />
                </label>
              </>
            )}
            <label>
              E-mail
              <input name="email" type="email" placeholder="voce@empresa.com" required />
            </label>
            <label>
              Senha
              <input name="password" type="password" placeholder="••••••••" minLength={6} required />
            </label>
            {error && <b className="error">{error}</b>}
            <button disabled={loading}>
              {loading ? "Aguarde..." : authMode === "login" ? "Entrar no workspace →" : "Criar conta e entrar →"}
            </button>
          </form>
          <small>
            {authMode === "login"
              ? "Demonstração: admin@operator.demo · senha operator123"
              : "Cada conta cria uma empresa separada, com dados isolados."}
          </small>
        </section>
      </main>
    );

  const pending = operations.filter((o) => o.status !== "completed").length;
  const completed = operations.filter((o) => o.status === "completed").length;
  const processedValue = operations
    .filter((o) => o.status === "completed")
    .reduce((sum, o) => sum + o.total, 0);
  const canExecute =
    selected &&
    selected.status !== "completed" &&
    selected.issues.length === 0 &&
    selected.items.every((i) => i.matched);
  const unmappedCount = selected ? selected.items.filter((i) => !i.matched).length : 0;
  const blockedReason =
    selected && selected.status !== "completed"
      ? selected.status === "pending_approval"
        ? "Pedido acima do limite — requer aprovação de um administrador"
        : selected.issues.length > 0
        ? "Corrija os problemas listados acima antes de executar"
        : unmappedCount > 0
        ? `${unmappedCount} item(ns) sem mapeamento — digite o código ERP ou sincronize os mapeamentos`
        : ""
      : "";

  return (
    <main className="app">
      <aside>
        <div className="brand">
          <b>AO</b>
          <p>
            AI Operator<span>Pedidos B2B → ERP</span>
          </p>
        </div>
        <nav>
          <button className={view === "operations" ? "active" : ""} onClick={() => navigate("operations")}>
            <Icon name="operations" /> Operações <i>{operations.length}</i>
          </button>
          <button className={view === "mappings" ? "active" : ""} onClick={() => navigate("mappings")}>
            <Icon name="mappings" /> Mapeamentos <i>{mappings.length}</i>
          </button>
          <button className={view === "audit" ? "active" : ""} onClick={() => navigate("audit")}>
            <Icon name="audit" /> Auditoria <i>{audits.length}</i>
          </button>
          <button className={view === "roi" ? "active" : ""} onClick={() => navigate("roi")}>
            <Icon name="roi" /> ROI
          </button>
          <button className={view === "webhooks" ? "active" : ""} onClick={() => navigate("webhooks")}>
            <Icon name="webhooks" /> Webhooks
          </button>
          <button className={view === "rules" ? "active" : ""} onClick={() => navigate("rules")}>
            <Icon name="rules" /> Regras
          </button>
          <button className={view === "recipes" ? "active" : ""} onClick={() => navigate("recipes")}>
            <Icon name="recipes" /> Processos
          </button>
        </nav>
        <div className="user">
          <b>AD</b>
          <p>
            Administrador<span>Empresa Demonstração</span>
          </p>
          <button
            onClick={toggleTheme}
            className="logout"
            aria-label={theme === "light" ? "Modo escuro" : "Modo claro"}
            title={theme === "light" ? "Modo escuro" : "Modo claro"}
          >
            <Icon name={theme === "light" ? "moon" : "sun"} />
          </button>
          <button onClick={logout} className="logout" aria-label="Sair" title="Sair">
            <Icon name="logout" />
          </button>
        </div>
      </aside>
      <section className="main">
        <header>
          <b>{view === "operations" ? "Central de operações" : view === "mappings" ? "Mapeamentos de produtos" : view === "audit" ? "Auditoria" : view === "roi" ? "ROI e desempenho" : view === "rules" ? "Regras da empresa" : view === "recipes" ? "Processos (recipes)" : "Integrações e webhooks"}</b>
          <span>
            <i /> API e ERP Demo operacionais
          </span>
        </header>
        <div className="content">
          {error && (
            <div className="alert">
              {error}
              <button onClick={() => setError("")}>×</button>
            </div>
          )}
          {view === "operations" && (
            <>
              <div className="title">
                <div>
                  <span>PEDIDOS B2B</span>
                  <h1>Operações de venda</h1>
                  <p>Revise exceções e execute pedidos no sistema de destino.</p>
                </div>
                <div className="uploadRow">
                  {recipes.length > 0 && (
                    <select
                      className="recipeSelect"
                      value={uploadRecipeId}
                      onChange={(e) => setUploadRecipeId(e.target.value)}
                    >
                      <option value="">Processo padrão</option>
                      {recipes.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                        </option>
                      ))}
                    </select>
                  )}
                  <label className="upload">
                    <Icon name="plus" /> Novo pedido
                    <input
                      hidden
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => upload(e.target.files?.[0])}
                    />
                  </label>
                </div>
              </div>
              <div className="metrics">
                <Metric label="PEDIDOS" value={String(operations.length)} />
                <Metric label="AGUARDANDO" value={String(pending)} />
                <Metric label="COMPLETADOS" value={String(completed)} />
                <Metric label="VALOR PROCESSADO" value={money.format(processedValue)} />
              </div>
              <div className="grid">
                <section className="list">
                  <h2>Fila de pedidos</h2>
                  {operations.length === 0 && (
                    <div className="empty">Envie o primeiro PDF para iniciar.</div>
                  )}
                  {operations.map((op) => (
                    <button
                      key={op.id}
                      className={selected?.id === op.id ? "selected" : ""}
                      onClick={() => setSelected(op)}
                    >
                      <i>PDF</i>
                      <p>
                        <b>{op.supplier || "Em processamento"}</b>
                        <span>{op.reference}</span>
                      </p>
                      <strong>{money.format(op.total)}</strong>
                      <em className={op.status}>{op.status}</em>
                    </button>
                  ))}
                </section>
                <section className="detail">
                  {selected ? (
                    <>
                      <div className="detailHead">
                        <div>
                          <span>OPERAÇÃO · {recipes.find((r) => r.id === selected.recipe_id)?.name || "padrão"}</span>
                          <h2>{selected.reference}</h2>
                        </div>
                        <b>{selected.confidence}% confiança</b>
                      </div>
                      {selected.status === "processing" && (
                        <div className="issues">
                          <span className="spin" /> Extração em andamento…
                        </div>
                      )}
                      {selected.issues.length > 0 && (
                        <div className="issues">
                          {selected.issues.map((issue) => (
                            <span key={issue}>{issue}</span>
                          ))}
                        </div>
                      )}
                      {selected.status === "processing" ? (
                        <div className="skeleton" aria-hidden="true">
                          <span className="sk sk-line w40" />
                          <span className="sk sk-line w70" />
                          <span className="sk sk-line w55" />
                          <span className="sk sk-line w80" />
                          <span className="sk sk-line w65" />
                          <span className="sk sk-line w45" />
                        </div>
                      ) : (
                      <>
                      <div className="fields">
                        <Field
                          label="Cliente"
                          value={selected.supplier || ""}
                          onCommit={(v) => patchOperation({ supplier: v })}
                        />
                        <Field
                          label="CNPJ"
                          value={selected.tax_id || ""}
                          onCommit={(v) => patchOperation({ tax_id: v })}
                        />
                        <Field
                          label="Referência"
                          value={selected.reference}
                          onCommit={(v) => patchOperation({ reference: v })}
                        />
                        <Field
                          label="Vencimento"
                          value={selected.due_date || ""}
                          onCommit={(v) => patchOperation({ due_date: v })}
                        />
                        <Field
                          label="Centro de custo"
                          value={selected.cost_center || ""}
                          onCommit={(v) => patchOperation({ cost_center: v })}
                        />
                      </div>
                      <div className="items">
                        <span>ITENS DO PEDIDO</span>
                        {selected.items.length > 0 && unmappedCount > 0 && (
                          <div className="mapHint">
                            <span>
                              {unmappedCount} item(ns) sem código ERP. Crie os mapeamentos na aba
                              "Mapeamentos" e sincronize, ou digite o código diretamente em cada item.
                            </span>
                            <button onClick={rematch} disabled={loading}>
                              ⟳ Sincronizar mapeamentos
                            </button>
                          </div>
                        )}
                        {selected.items.length === 0 && (
                          <div className="empty">Nenhum item identificado no documento.</div>
                        )}
                        {selected.items.map((item) => (
                          <div key={item.id} className="itemRow">
                            <p>
                              <b>{item.description}</b>
                              <small>
                                {item.customer_code || "sem código"} · {item.quantity} ×{" "}
                                {money.format(item.unit_price)}
                                {item.matched ? (
                                  <em className="ok">mapeado</em>
                                ) : (
                                  <em className="no">sem mapeamento</em>
                                )}
                              </small>
                            </p>
                            <div className="itemRight">
                              <input
                                className="erpInput"
                                defaultValue={item.erp_code || ""}
                                placeholder="Código ERP"
                                onBlur={(e) => {
                                  if (e.target.value !== (item.erp_code || ""))
                                    patchItem(item.id, { erp_code: e.target.value });
                                }}
                              />
                              <strong>{money.format(item.total)}</strong>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="exportRow">
                        <button className="exportBtn" onClick={() => exportOperation("csv")}>
                          Exportar CSV
                        </button>
                        <button className="exportBtn" onClick={() => exportOperation("xml")}>
                          Exportar XML
                        </button>
                      </div>
                      {selected.status === "pending_approval" && (
                        <div className="approvalRow">
                          <button className="approve" onClick={approve} disabled={loading}>
                            <Icon name="check" /> Aprovar pedido
                          </button>
                          <button className="reject" onClick={reject} disabled={loading}>
                            <Icon name="x" /> Recusar
                          </button>
                        </div>
                      )}
                      <button
                        className="execute"
                        disabled={loading || selected.status === "completed" || !canExecute}
                        onClick={execute}
                      >
                        {selected.status === "completed"
                          ? "Executado com sucesso"
                          : loading
                          ? "Executando..."
                          : "Aprovar e executar no ERP"}
                      </button>
                      {blockedReason && <p className="blocked">{blockedReason}</p>}
                      </>
                      )}
                    </>
                  ) : (
                    <div className="empty">Selecione uma operação.</div>
                  )}
                </section>
              </div>
            </>
          )}
          {view === "mappings" && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>MEMÓRIA OPERACIONAL</span>
                  <h1>Mapeamentos de produtos</h1>
                  <p>
                    Códigos do cliente convertidos para códigos do ERP. Correções de itens
                    aprendem estes mapeamentos automaticamente.
                  </p>
                </div>
              </div>
              <form className="mapForm" onSubmit={addMapping}>
                <input name="customer_code" placeholder="Código do cliente" required />
                <input name="description" placeholder="Descrição" />
                <input name="erp_code" placeholder="Código ERP" required />
                <button disabled={loading}>Adicionar</button>
              </form>
              <div className="table">
                <div className="thead">
                  <span>Código cliente</span>
                  <span>Descrição</span>
                  <span>Código ERP</span>
                  <span>Usos</span>
                </div>
                {mappings.length === 0 && <div className="empty">Nenhum mapeamento ainda.</div>}
                {mappings.map((m) => (
                  <div className="trow" key={m.id}>
                    <span>{m.customer_code}</span>
                    <span>{m.description}</span>
                    <span>{m.erp_code}</span>
                    <span>{m.usage_count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {view === "audit" && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>TRILHA DE AUDITORIA</span>
                  <h1>Eventos encadeados</h1>
                  <p>Cada evento guarda o hash do anterior, evidenciando alterações.</p>
                </div>
              </div>
              <div className="table">
                <div className="thead">
                  <span>Evento</span>
                  <span>Payload</span>
                  <span>Hash</span>
                  <span>Data</span>
                </div>
                {audits.length === 0 && <div className="empty">Nenhum evento ainda.</div>}
                {audits.map((a) => (
                  <div className="trow" key={a.id}>
                    <span>{a.event_type}</span>
                    <span className="mono">{JSON.stringify(a.payload)}</span>
                    <span className="mono">{a.hash.slice(0, 12)}…</span>
                    <span>{new Date(a.created_at).toLocaleString("pt-BR")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {view === "roi" && roi && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>RETORNO SOBRE O INVESTIMENTO</span>
                  <h1>Impacto operacional</h1>
                  <p>
                    Métricas calculadas a partir dos eventos reais de auditoria — tempo por
                    operação, automação e valor processado.
                  </p>
                </div>
              </div>
              <div className="roiGrid">
                <RoiMetric label="Operações totais" value={String(roi.total_operations)} />
                <RoiMetric label="Valor processado" value={money.format(roi.processed_value)} />
                <RoiMetric label="Taxa de automação" value={`${roi.automation_rate}%`} />
                <RoiMetric label="Exceções (revisão)" value={`${roi.exception_rate}%`} />
                <RoiMetric
                  label="Tempo médio até o ERP"
                  value={`${formatSeconds(roi.avg_time_to_erp_seconds)}`}
                />
                <RoiMetric label="Horas economizadas" value={`${roi.hours_saved}h`} />
                <RoiMetric label="Confiança média" value={`${roi.avg_confidence}%`} />
                <RoiMetric label="Processamento/extração" value={`${formatSeconds(roi.avg_processing_seconds)}`} />
              </div>
              {roi.daily.length > 0 && (
                <div className="chart">
                  <span className="chartTitle">ÚLTIMOS {roi.daily.length} DIAS — OPERAÇÕES</span>
                  <div className="bars">
                    {roi.daily.map((d) => (
                      <div className="barCol" key={d.date} title={`${d.date}: ${d.operations} operações · ${money.format(d.value)}`}>
                        <span className="barTip">
                          {d.date} · {d.operations} ops · {money.format(d.value)}
                        </span>
                        <span className="barVal">{d.operations}</span>
                        <div className="bar">
                          <div
                            className="barFill"
                            style={{ height: `${Math.max(6, (d.operations / maxDaily(roi.daily)) * 100)}%` }}
                          />
                        </div>
                        <span className="barLabel">{shortDate(d.date)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {view === "webhooks" && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>INTEGRAÇÕES</span>
                  <h1>Webhooks de operações</h1>
                  <p>
                    Receba eventos assinados (HMAC) quando uma operação fica pronta ou é executada
                    no ERP. Use para sincronizar sistemas ou disparar fluxos externos.
                  </p>
                </div>
              </div>
              <form className="webhookForm" onSubmit={addWebhook}>
                <input name="url" placeholder="https://seu-sistema.com/hook" required />
                <div className="evts">
                  <label>
                    <input type="checkbox" name="events" value="operation.ready" defaultChecked />
                    operation.ready
                  </label>
                  <label>
                    <input type="checkbox" name="events" value="erp.executed" defaultChecked />
                    erp.executed
                  </label>
                </div>
                <button disabled={loading}>Adicionar webhook</button>
              </form>
              <div className="table">
                <div className="thead">
                  <span>URL</span>
                  <span>Eventos</span>
                  <span>Status</span>
                  <span></span>
                </div>
                {webhooks.length === 0 && <div className="empty">Nenhum webhook configurado.</div>}
                {webhooks.map((w) => (
                  <div className="trow" key={w.id}>
                    <span className="mono">{w.url}</span>
                    <span>{w.events.join(", ")}</span>
                    <span>{w.active ? "ativo" : "inativo"}</span>
                    <button className="linkBtn" onClick={() => removeWebhook(w.id)}>
                      Remover
                    </button>
                  </div>
                ))}
              </div>
              {deliveries.length > 0 && (
                <>
                  <span className="chartTitle" style={{ display: "block", marginTop: 26 }}>
                    ENTREGAS RECENTES
                  </span>
                  <div className="table" style={{ marginTop: 10 }}>
                    <div className="thead">
                      <span>Evento</span>
                      <span>Status</span>
                      <span>Tentativas</span>
                      <span>Data</span>
                    </div>
                    {deliveries.map((d) => (
                      <div className="trow" key={d.id}>
                        <span>{d.event}</span>
                        <span className={d.status === "delivered" ? "ok" : "no"}>{d.status}</span>
                        <span>{d.attempts}</span>
                        <span>{new Date(d.created_at).toLocaleString("pt-BR")}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
          {view === "rules" && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>REGRAS OPERACIONAIS</span>
                  <h1>Limites e aprovações</h1>
                  <p>
                    Regras determinísticas autorizam ou bloqueiam antes da execução. Pedidos acima
                    do limite exigem aprovação de um administrador.
                  </p>
                </div>
              </div>
              <form className="ruleForm" onSubmit={saveSettings}>
                <label>
                  Limite para exigir aprovação (R$)
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                  />
                </label>
                <button disabled={loading}>Salvar regra</button>
              </form>
              <div className="ruleNote">
                Como funciona: após a extração, se o valor do pedido for{" "}
                <b>&ge; {money.format(Number(threshold) || 0)}</b>, a operação entra em
                "aguardando aprovação" e só executa após um administrador aprovar.
              </div>
            </div>
          )}
          {view === "recipes" && (
            <div className="panel">
              <div className="title">
                <div>
                  <span>BIBLIOTECA DE PROCESSOS</span>
                  <h1>Process recipes</h1>
                  <p>
                    Configurações reutilizáveis de processo: como extrair, quais campos são
                    obrigatórios e qual operação alimenta no ERP. O próximo cliente semelhante não
                    começa do zero.
                  </p>
                </div>
              </div>
              <form className="mapForm" onSubmit={addRecipe}>
                <input name="name" placeholder="Nome do processo (ex.: Pedido de Venda)" required />
                <select name="operation_type" className="recipeSelect">
                  <option value="sales_order.create">Pedido de venda</option>
                  <option value="purchase.create">Compra</option>
                  <option value="quote.create">Cotação/Proposta</option>
                  <option value="invoice.payable">Nota fiscal (contas a pagar)</option>
                </select>
                <div className="reqFields">
                  <span>Obrigatórios:</span>
                  <label>
                    <input type="checkbox" name="required" value="tax_id" /> CNPJ
                  </label>
                  <label>
                    <input type="checkbox" name="required" value="due_date" /> Vencimento
                  </label>
                  <label>
                    <input type="checkbox" name="required" value="cost_center" /> Centro de custo
                  </label>
                </div>
                <button disabled={loading}>Criar processo</button>
              </form>
              <div className="table">
                <div className="thead">
                  <span>Processo</span>
                  <span>Operação no ERP</span>
                  <span>Campos obrigatórios</span>
                  <span></span>
                </div>
                {recipes.length === 0 && <div className="empty">Nenhum processo criado.</div>}
                {recipes.map((r) => (
                  <div className="trow" key={r.id}>
                    <span>
                      <b>{r.name}</b>
                      <br />
                      <small className="muted">{r.active ? "ativo" : "inativo"}</small>
                    </span>
                    <span className="mono">{r.operation_type}</span>
                    <span>{(r.required_fields || []).join(", ") || "—"}</span>
                    <button className="linkBtn" onClick={() => toggleRecipe(r.id, !r.active)}>
                      {r.active ? "Desativar" : "Ativar"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function Icon({ name }: { name: string }) {
  const paths: Record<string, React.ReactElement> = {
    operations: (
      <>
        <line x1="9" y1="6" x2="21" y2="6" />
        <line x1="9" y1="12" x2="21" y2="12" />
        <line x1="9" y1="18" x2="21" y2="18" />
        <circle cx="4.5" cy="6" r="1" />
        <circle cx="4.5" cy="12" r="1" />
        <circle cx="4.5" cy="18" r="1" />
      </>
    ),
    mappings: (
      <>
        <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.83z" />
        <line x1="7" y1="7" x2="7.01" y2="7" />
      </>
    ),
    audit: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    roi: (
      <>
        <path d="m22 7-8.5 8.5-5-5L2 17" />
        <path d="M16 7h6v6" />
      </>
    ),
    webhooks: (
      <>
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </>
    ),
    rules: (
      <>
        <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z" />
        <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z" />
        <path d="M7 21h10" />
        <path d="M12 3v18" />
        <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
      </>
    ),
    recipes: (
      <>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </>
    ),
    check: <path d="M20 6 9 17l-5-5" />,
    x: (
      <>
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </>
    ),
    logout: (
      <>
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
        <path d="m16 17 5-5-5-5" />
        <path d="M21 12H9" />
      </>
    ),
    moon: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />,
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2" />
        <path d="M12 20v2" />
        <path d="m4.93 4.93 1.41 1.41" />
        <path d="m17.66 17.66 1.41 1.41" />
        <path d="M2 12h2" />
        <path d="M20 12h2" />
        <path d="m6.34 17.66-1.41 1.41" />
        <path d="m19.07 4.93-1.41 1.41" />
      </>
    ),
  };
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <article>
      <span>{label}</span>
      <b>{value}</b>
    </article>
  );
}

function Field({
  label,
  value,
  onCommit,
}: {
  label: string;
  value: string;
  onCommit: (value: string) => void;
}) {
  const [editing, setEditing] = useState(value);
  useEffect(() => setEditing(value), [value]);
  return (
    <label>
      {label}
      <input
        value={editing}
        onChange={(e) => setEditing(e.target.value)}
        onBlur={(e) => {
          if (e.target.value !== value) onCommit(e.target.value);
        }}
      />
    </label>
  );
}

function RoiMetric({ label, value }: { label: string; value: string }) {
  return (
    <article className="roiMetric">
      <span>{label}</span>
      <b>{value}</b>
    </article>
  );
}

function formatSeconds(total: number) {
  if (total <= 0) return "—";
  if (total < 60) return `${Math.round(total)}s`;
  const m = Math.floor(total / 60);
  const s = Math.round(total % 60);
  return `${m}m ${s}s`;
}

function maxDaily(daily: Daily[]) {
  return Math.max(1, ...daily.map((d) => d.operations));
}

function shortDate(iso: string) {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}