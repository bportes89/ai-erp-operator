# AI ERP Operator

SaaS para transformar pedidos B2B recebidos em PDF em operações validadas e executadas no ERP, com revisão humana, memória operacional, idempotência e auditoria.

## Estado atual

Esta é a fundação de produção (alpha). Ela já contém autenticação multiempresa, upload, extração textual de PDF, persistência, mapeamentos, execução em ERP Demo, auditoria encadeada e frontend. OCR de documentos escaneados e conectores de ERP reais são as próximas integrações.

## Arquitetura

- `apps/web`: Next.js e TypeScript.
- `apps/api`: FastAPI, SQLAlchemy assíncrono e Alembic.
- `worker`: consumidor Redis preparado para OCR/LLM assíncrono.
- PostgreSQL: organizações, usuários, pedidos, itens, mapeamentos e auditoria.
- MinIO: documentos originais, compatível com S3.
- ERP Adapter: contrato isolado, com implementação Demo segura.

## Executar localmente

Requisitos: Docker Desktop e Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
docker compose run --rm api python -m app.seed
```

Acesse `http://localhost:3000`.

Credenciais de desenvolvimento:

- E-mail: `admin@operator.demo`
- Senha: `operator123`

API e documentação interativa: `http://localhost:8000/docs`.

## Fluxo principal

1. Usuário autentica na organização.
2. Envia um PDF de pedido.
3. API armazena o original e extrai campos.
4. Motor calcula confiança e direciona para revisão ou estado pronto.
5. Produtos são associados aos códigos internos do ERP.
6. Execução exige uma chave de idempotência.
7. Adaptador registra o pedido e devolve identificador externo.
8. Evento é acrescentado à cadeia de auditoria.

## Segurança antes de produção

- Trocar `SECRET_KEY` e todas as senhas.
- Restringir CORS aos domínios do produto.
- Usar HTTPS e cofre de segredos.
- Implementar renovação/revogação de tokens.
- Ativar antivírus e validação aprofundada de uploads.
- Definir retenção, criptografia e política LGPD.
- Aplicar migrations explícitas em vez de `create_all`.
- Adicionar rate limiting e logs sem dados sensíveis.

## Próximas entregas

1. OCR e extração estruturada com saída validada.
2. Interface de correção dos itens e campos.
3. Primeiro adaptador de ERP real.
4. Motor configurável de regras e aprovações.
5. Métricas de ROI calculadas a partir dos eventos.
6. Testes de integração e E2E.

## Comandos

```bash
make up
make seed
make test
make lint
make down
```
