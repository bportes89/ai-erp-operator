# Deploy gratuito (stack sem custo)

Arquitetura 100% gratuita, sem Redis/MinIO/worker:

```
Navegador → Vercel (Next.js) → Render (FastAPI) → Neon (PostgreSQL)
                                          └→ OpenRouter (LLM, pago por uso ~centavos)
```

A extração roda **inline** na API (`EXTRACTION_INLINE=true`) — não precisa de fila nem worker.
O PDF original é guardado no banco (coluna `raw_content`).

---

## 1. Banco de dados — Neon (gratuito)

1. Crie conta em https://neon.tech (plano Free).
2. Novo projeto → região próxima de você.
3. Copie a **connection string** e adicione `+asyncpg` ao driver:
   - `postgresql://user:pass@host/db?sslmode=require`
   - → `postgresql+asyncpg://user:pass@host/db?sslmode=require`

> Alternativa: Supabase (gratuito). Use a string `postgresql://` e troque por
> `postgresql+asyncpg://`.

## 2. API — Render (gratuito)

Opção A — Blueprint (mais rápido):
1. Crie conta em https://render.com.
2. **New → Blueprint** → aponte para este repositório (o `render.yaml` será usado).
3. Preencha as variáveis secretas:
   - `DATABASE_URL` → a string do Neon (com `+asyncpg`)
   - `SECRET_KEY` → gere uma: `python -c "import secrets; print(secrets.token_hex(32))"`
   - `CORS_ORIGINS` → `https://SEU-APP.vercel.app`
   - `LLM_API_KEY` → chave do OpenRouter
4. Deploy. A URL da API será `https://ai-erp-operator-api.onrender.com`.

Opção B — Manual: New → Web Service → pasta `apps/api`,
build `pip install '.[dev]'`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
mesmas variáveis acima.

> ⚠️ No plano Free o Render **dorme após ~15 min** de inatividade: o primeiro
> request após dormir leva ~30 s para "acordar". Alternativa sem sono: **Koyeb**
> (free tier sempre ligado) com os mesmos comandos/variáveis.

## 3. Frontend — Vercel (gratuito)

1. Crie conta em https://vercel.com e importe este repositório.
2. Framework: **Next.js** (detecta automaticamente, pasta `apps/web`).
3. Variável de ambiente:
   - `NEXT_PUBLIC_API_URL` → `https://ai-erp-operator-api.onrender.com/api/v1`
4. Deploy. URL final: `https://SEU-APP.vercel.app`.

Depois do primeiro deploy, **volte ao Render** e atualize `CORS_ORIGINS`
para o domínio real do Vercel.

## 4. Segredos obrigatórios antes de produção

- `SECRET_KEY` diferente do default (o render.yaml marca como `sync: false`).
- Troque ou remova o usuário demo `admin@operator.demo` (seed.py).
- `LLM_API_KEY` vem do OpenRouter; custa só quando usado.

## 5. Verificação pós-deploy

1. `GET https://SUA-API.onrender.com/health` → `"status": "ok"` com checks.
2. Abra o Vercel, **Criar conta** (ou login demo), envie um PDF de `amostras/`.
3. Veja a operação pronta, mapeie itens e execute.

## Notas técnicas

- Tabelas são criadas no boot (`create_all`) — suficiente para MVP.
  Para o primeiro cliente real, migrar para `alembic upgrade head` (ver apps/api/alembic).
- Rate limit já ativo (login 5/min, upload 10/min, cadastro 5/h).
- CORS restrito por `CORS_ORIGINS` — nunca use `*`.
- Armazenamento de documentos: `STORAGE_ENABLED=false` usa o banco.
  Para R2/B2 gratuitos no futuro, basta subir MinIO-compatível e ativar.