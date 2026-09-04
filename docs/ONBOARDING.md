# AIOperator — Guia de Onboarding do Cliente

Guia prático, do primeiro acesso ao uso diário, para quem vai **operar** o sistema
(analistas de pedidos, equipe de vendas internas, supervisores e administradores).

---

## 1. Primeiro acesso

### 1.1 Criar a conta da empresa

1. Acesse o endereço da plataforma fornecido pelo comercial (ex.: `https://ai-erp-operator.vercel.app`).
2. Na tela de entrada, clique em **"Criar conta"**.
3. Preencha:
   - **Nome** — seu nome completo
   - **Empresa** — nome da organização (opcional, mas recomendado)
   - **E-mail** — e-mail corporativo (será seu login)
   - **Senha** — mínimo 6 caracteres
4. Clique em **"Criar conta e entrar"**.

> Cada conta cria uma **empresa isolada**: os dados de uma organização nunca são
> vistos por outra. O primeiro usuário criado é o **administrador** da empresa.

### 1.2 O que você vê ao entrar

A tela principal (**Operações**) é o painel de comando:

- **Barra do topo**: seção atual + contadores em tempo real + status "Sistemas operacionais".
- **Métricas**: pedidos totais, aguardando, completados e valor processado.
- **Gráfico de tendência**: operações e valor dos últimos dias.
- **À esquerda**: menu de navegação (Operações, Mapeamentos, Auditoria, ROI, Webhooks, Regras, Processos).
- **No rodapé da barra lateral**: alternância de tema (claro/escuro) e sair.

---

## 2. Fluxo do dia a dia: do PDF ao pedido no ERP

### 2.1 Enviar um pedido

1. Na tela **Operações**, clique em **"Novo pedido"** (canto superior direito).
2. Escolha o arquivo PDF do pedido do cliente.
3. Opcional: selecione um **Processo** antes de enviar (ex.: "Pedido de Venda") — o sistema
   usará as regras daquele processo para extração e validação.

### 2.2 Acompanhar a extração

- O pedido entra na fila com status **em processamento** (skeleton na tela).
- A IA lê o PDF (inclusive **escaneados**, via OCR) e preenche: referência, cliente, CNPJ,
  vencimento, centro de custo, total e os **itens** (código, descrição, quantidade, preço).
- Em segundos o pedido fica em um destes estados:

| Estado | Significado | O que fazer |
|---|---|---|
| **processing** | Extração em andamento | Aguardar |
| **review** | Precisa de revisão humana | Corrigir campos/itens (ver seção 3) |
| **ready** | Pronto para executar | Revisar e executar |
| **pending_approval** | Acima do limite de aprovação | Administrador aprova ou recusa |
| **completed** | Executado no ERP | Nada a fazer |
| **failed** | Falhou no processamento | Reenviar o PDF |

### 2.3 Revisar uma operação (status *review*)

Quando o sistema encontra algo que não confia, mostra uma **lista de problemas** em amarelo, por exemplo:

- `CNPJ inválido` — o dígito verificador do CNPJ extraído não bate.
- `Soma dos itens diverge do total` — os valores não fecham.
- `Campo obrigatório ausente: vencimento` — o processo exige um campo que não veio.

Para corrigir:
1. Clique no pedido na fila.
2. Edite os campos (cliente, CNPJ, referência, vencimento, centro de custo) — a alteração
   **salva automaticamente** ao sair do campo.
3. Os itens precisam ter **código ERP** para executar. Você pode:
   - Digitar o código ERP em cada item; ou
   - Criar os mapeamentos na aba **Mapeamentos** e clicar em **"Sincronizar mapeamentos"**.
4. Quando não houver mais problemas, o botão **"Aprovar e executar no ERP"** fica habilitado.

### 2.4 Executar no ERP

1. Com o pedido **ready** (e itens mapeados), clique em **"Aprovar e executar no ERP"**.
2. O sistema registra no ERP e o status muda para **completed**.
3. A execução é **idempotente**: mesmo que a tela seja recarregada ou o botão seja clicado
   de novo, o pedido **não é duplicado**.

> Para pedidos acima do limite configurado, a execução só acontece após um administrador
> clicar em **"Aprovar pedido"** (ou **"Recusar"** para devolver à revisão).

---

## 3. Mapeamentos (a memória do sistema)

A aba **Mapeamentos** guarda a correspondência entre o código que o cliente usa no pedido
e o código interno do ERP.

- **Criar**: `código do cliente → código ERP` + descrição.
- **Aprender automaticamente**: quando você digita o código ERP direto num item, o sistema
  **memoriza** aquele mapeamento sozinho.
- **Reutilizar**: no próximo pedido do mesmo produto, o item já chega mapeado e pronto.
- A coluna **usos** mostra quantas vezes cada mapeamento foi aplicado.

> Quanto mais pedidos passam por revisão, menos revisão é necessária. É o sistema
> **aprendendo a operação da sua empresa**.

---

## 4. Regras e aprovações

Na aba **Regras** (administradores):

- Defina o **limite de valor** a partir do qual um pedido exige aprovação.
- Pedidos acima do limite entram em **aguardando aprovação**; o administrador vê os botões
  **Aprovar** / **Recusar** no detalhe da operação.
- Todo ato (aprovar, recusar, corrigir) fica registrado na **Auditoria**.

---

## 5. Auditoria

A aba **Auditoria** mostra a **trilha completa** de cada pedido, em linha do tempo colorida:

- Extração, correções, mapeamentos aprendidos, execução no ERP, aprovações.
- Cada evento guarda o **hash do anterior** (encadeamento), o que **evidencia** qualquer
  alteração — não é possível apagar um evento sem quebrar a cadeia.
- Passe o mouse nos hashes para ver os detalhes.

---

## 6. ROI

A aba **ROI** traduz a operação em impacto:

- Operações totais, valor processado, **taxa de automação** (o que seguiu sem intervenção)
  vs. **exceções** (o que exigiu revisão).
- Tempo médio até o ERP, horas economizadas e confiança média.
- Série diária dos últimos 14 dias (gráfico com tooltip).

---

## 7. Processos (recipes)

Na aba **Processos**, o administrador cria **configurações reutilizáveis** de processo:

- **Nome** (ex.: "Pedido de Venda", "Cotação", "Nota fiscal → contas a pagar").
- **Tipo de operação** no ERP.
- **Campos obrigatórios** (CNPJ, vencimento, centro de custo) — se faltarem, o pedido vai para revisão.

No envio do pedido, o operador pode escolher qual processo aplicar. Clientes semelhantes
começam com a mesma configuração — **não do zero**.

---

## 8. Exportar e integrar

- No detalhe de uma operação: **Exportar CSV** ou **Exportar XML** — o pedido no formato
  canônico para importar em qualquer sistema.
- Na aba **Webhooks** (administradores/TI): receba eventos assinados (**HMAC**) quando um
  pedido fica pronto (`operation.ready`) ou é executado (`erp.executed`), para sincronizar
  outros sistemas.

---

## 9. Papéis

| Papel | O que pode |
|---|---|
| **Operador** | Enviar pedidos, revisar, corrigir, mapear e executar |
| **Administrador** | Tudo do operador + mapeamentos em massa, regras, webhooks, processos, aprovações e cadastro |

---

## 10. Dicas rápidas

- **PDF escaneado?** Envie normalmente — o OCR por visão lê documentos escaneados e fotos.
- **Pedido repetido** (mesmo cliente, mesmos produtos): os mapeamentos já aprendidos fazem o
  pedido chegar pronto — é só executar.
- **Botão de execução desabilitado?** O texto abaixo explica o motivo (itens sem mapeamento,
  problemas a corrigir ou aguardando aprovação).
- **Tema**: use o botão de lua/sol (tela de login e barra lateral) para alternar claro/escuro.
- **Não duplica**: a mesma operação pode ser reexecutada com segurança (idempotência).

---

## 11. Perguntas frequentes

**O pedido foi executado, mas preciso refazer/estornar no ERP.**
A execução não pode ser "desfeita" pelo sistema — o estorno deve ser feito no ERP. O sistema
registra o evento na auditoria para rastreabilidade.

**A IA errou um campo.**
Corrija no painel de revisão; o sistema aprende com a correção (mapeamentos, campos recorrentes).

**Por que alguns pedidos sempre caem em revisão?**
Normalmente por: CNPJ inválido, soma dos itens diferente do total, ou campo obrigatório do
processo ausente. Revise os **problemas listados** — eles indicam exatamente o que corrigir.

**Um item não tem código ERP.**
Digite o código ERP do produto no item (ou crie o mapeamento e use **Sincronizar mapeamentos**).
A execução é bloqueada enquanto existirem itens sem mapeamento.

**Esqueci minha senha.**
Fale com o administrador da sua organização — ele pode recriar seu acesso (no plano atual,
a recuperação automática de senha é feita pelo time AIOperator).

---

© 2026 AIOperator · https://ai-erp-operator.vercel.app