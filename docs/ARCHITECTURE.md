# Arquitetura de produção

## Princípios

1. O domínio não conhece um ERP específico.
2. Uma execução é idempotente e verificável.
3. IA sugere; regras determinísticas autorizam ou bloqueiam.
4. Exceções são revisadas por pessoas.
5. Toda alteração relevante produz um evento de auditoria.
6. Dados são isolados por organização.

## Limites dos componentes

### Web

Nunca acessa banco ou ERP diretamente. Consome somente a API autenticada.

### API

Autoriza, valida e persiste o estado transacional. Operações longas devem ser enviadas ao worker.

### Worker

Executa OCR, LLM, enriquecimento e integrações sujeitas a espera. Jobs devem ser repetíveis e idempotentes.

### ERP Adapter

Converte o schema canônico para o contrato externo. Cada adaptador implementa criação, consulta, verificação e health check.

### Auditoria

Eventos possuem o hash do evento anterior. Isso evidencia alterações, mas não substitui assinatura digital ou armazenamento WORM.

## Schema canônico

```json
{
  "operation": "sales_order.create",
  "reference": "PC-2026-2041",
  "customer": {"tax_id": "42.781.923/0001-04"},
  "items": [{"customer_code": "NOTE-15", "erp_code": "INF-NB-015", "quantity": 6}],
  "total": 18420.00,
  "currency": "BRL"
}
```

## Regra de decisão inicial

- Confiança menor que 85%: revisão obrigatória.
- Produto sem mapeamento: execução bloqueada.
- Operação já executada: rejeitar nova execução.
- Mesma chave de idempotência: devolver a primeira resposta.
- Valor acima do limite da organização: exigir aprovação adicional.
