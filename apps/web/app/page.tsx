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
type View = "operations" | "mappings" | "audit" | "roi" | "webhooks";

export default function Page() {
  const [token, setToken] = useState("");
  const [view, setView] = useState<View>("operations");
  const [operations, setOperations] = useState<Operation[]>([]);
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [audits, setAudits] = useState<AuditEvent[]>([]);
  const [roi, setRoi] = useState<ROI | null>(null);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
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

  function navigate(next: View) {
    setView(next);
    if (next === "mappings") loadMappings();
    if (next === "audit") loadAudit();
    if (next === "roi") loadRoi();
    if (next === "webhooks") loadWebhooks();
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
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/operations`, {
        method: "POST",
        headers: headers() as HeadersInit,
        body: form,
      });
      if (r.ok) await load();
      else setError((await r.json()).detail || "Não foi possível processar o PDF");
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

  if (!token)
    return (
      <main className="login">
        <section>
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
      ? selected.issues.length > 0
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
            ⌁ Operações <i>{operations.length}</i>
          </button>
          <button className={view === "mappings" ? "active" : ""} onClick={() => navigate("mappings")}>
            ≡ Mapeamentos <i>{mappings.length}</i>
          </button>
          <button className={view === "audit" ? "active" : ""} onClick={() => navigate("audit")}>
            ✓ Auditoria <i>{audits.length}</i>
          </button>
          <button className={view === "roi" ? "active" : ""} onClick={() => navigate("roi")}>
            ↗ ROI
          </button>
          <button className={view === "webhooks" ? "active" : ""} onClick={() => navigate("webhooks")}>
            ⚙ Webhooks
          </button>
        </nav>
        <div className="user">
          <b>AD</b>
          <p>
            Administrador<span>Empresa Demonstração</span>
          </p>
          <button onClick={logout} className="logout">
            Sair
          </button>
        </div>
      </aside>
      <section className="main">
        <header>
          <b>{view === "operations" ? "Central de operações" : view === "mappings" ? "Mapeamentos de produtos" : view === "audit" ? "Auditoria" : view === "roi" ? "ROI e desempenho" : "Integrações e webhooks"}</b>
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
                <label className="upload">
                  ＋ Novo pedido
                  <input
                    hidden
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => upload(e.target.files?.[0])}
                  />
                </label>
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
                          <span>OPERAÇÃO</span>
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
                            <span key={issue}>⚠ {issue}</span>
                          ))}
                        </div>
                      )}
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
                          <div key={item.id}>
                            <p>
                              <b>{item.description}</b>
                              <small>
                                {item.customer_code || "sem código"} · {item.quantity} ×{" "}
                                {money.format(item.unit_price)}
                                {item.matched ? (
                                  <em className="ok"> ✓ mapeado</em>
                                ) : (
                                  <em className="no"> sem mapeamento</em>
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
                      <button
                        className="execute"
                        disabled={loading || selected.status === "completed" || !canExecute}
                        onClick={execute}
                      >
                        {selected.status === "completed"
                          ? "Executado com sucesso ✓"
                          : loading
                          ? "Executando..."
                          : "Aprovar e executar no ERP ✓"}
                      </button>
                      {blockedReason && <p className="blocked">{blockedReason}</p>}
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
        </div>
      </section>
    </main>
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