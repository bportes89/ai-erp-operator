# AIOperator — Checklist de Implantação

Roteiro de configuração para a equipe de implantação **antes e durante o piloto**.
Siga em ordem; cada bloco tem dono e critério de aceite.

---

## Fase 0 — Preparação (antes do piloto)

- [ ] Definir escopo do piloto: **um processo** (ex.: Pedido PDF → Pedido de Venda) e **uma filial/papel**.
- [ ] Coletar **10 a 20 PDFs reais** de pedidos do cliente (variados: digitados e escaneados).
- [ ] Definir contato de cada papel no cliente:
  - [ ] Administrador (configura regras, aprova, mapeamentos em massa)
  - [ ] Operadores (revisam e executam)
- [ ] Confirmar o **ERP de destino** e o formato esperado do pedido (códigos de produto, centro de custo).

## Fase 1 — Conta e segurança

- [ ] Criar a conta da empresa (ou usar a conta de demonstração).
- [ ] Trocar a senha do administrador.
- [ ] (Produção) Garantir `SECRET_KEY` própria e HTTPS.
- [ ] Definir quem é **operador** vs. **administrador**.

## Fase 2 — Configuração da plataforma

### Processos (recipes)
- [ ] Criar o processo do piloto (ex.: "Pedido de Venda").
- [ ] Definir **campos obrigatórios** (ex.: CNPJ, vencimento).
- [ ] Definir **tipo de operação** no ERP.

### Regras
- [ ] Configurar o **limite de aprovação** (valor a partir do qual exige aprovação).
- [ ] Definir quem aprova (papel administrador).

### Mapeamentos iniciais
- [ ] Carregar os **20 produtos mais pedidos** do cliente (`código cliente → código ERP`).
- [ ] Conferir descrições para o matching automático.

### Webhooks (opcional, para TI)
- [ ] Criar webhook de `operation.ready` e/ou `erp.executed`.
- [ ] Validar o recebimento e a assinatura HMAC em ambiente de teste.

## Fase 3 — Validação com PDFs reais

- [ ] Enviar os **PDFs coletados** e registrar o resultado esperado vs. obtido.
- [ ] Para cada PDF, conferir:
  - [ ] Campos do cabeçalho (referência, cliente, CNPJ, vencimento, total)
  - [ ] Itens (código, quantidade, preço, total)
  - [ ] Validações (CNPJ válido, soma dos itens = total)
- [ ] Corrigir os erros e **verificar se o sistema aprendeu** (mapeamentos memorizados).
- [ ] Testar um **PDF escaneado** (OCR por visão).
- [ ] Testar o fluxo de **aprovação** (pedido acima do limite).
- [ ] Testar **execução + idempotência** (executar duas vezes = sem duplicar).

### Critério de aceite da Fase 3
- [ ] ≥ 80% dos PDFs reais extraídos **sem intervenção humana**.
- [ ] 100% sem erro de valor (soma/total conferido).

## Fase 4 — Treinamento do cliente

- [ ] Apresentar o **Guia de Onboarding** (`docs/ONBOARDING.md`).
- [ ] Treinar operadores: enviar, revisar, corrigir, mapear, executar.
- [ ] Treinar administrador: regras, aprovações, mapeamentos em massa, processos.
- [ ] Deixar um **PDF de exemplo** para o cliente repetir o fluxo sozinho.

## Fase 5 — Go-live e acompanhamento

- [ ] Data de início do acompanhamento (30 dias).
- [ ] Registrar a **linha de base** antes do piloto:
  - [ ] Pedidos/mês, minutos por pedido, horas mensais
- [ ] Semanalmente, conferir na aba **ROI**:
  - [ ] Taxa de automação (meta: subir a cada semana)
  - [ ] Exceções (meta: cair com os mapeamentos aprendidos)
  - [ ] Tempo médio até o ERP
- [ ] Revisar a **Auditoria** para identificar gargalos ou correções recorrentes.
- [ ] Decisão ao fim dos 30 dias: conversão para contrato recorrente ou ajuste de escopo.

---

## Riscos comuns e mitigação

| Risco | Mitigação |
|---|---|
| PDFs com layouts muito diferentes | Começar com um processo único e expandir depois |
| Produtos sem código no ERP | Carregar mapeamentos iniciais e ensinar por revisão |
| Exceções demais na 1ª semana | Revisar validações e mapeamentos; não mudar regras toda hora |
| Expectativa de "100% automático" | Combinar a meta (≥80%) e o papel da revisão humana |
| Tempo no ERP não conferido | Validar em ambiente de teste antes do piloto |

---

© 2026 AIOperator · Documento interno de implantação