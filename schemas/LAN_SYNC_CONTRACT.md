# Contrato de sincronização LAN manual

```json
{
  "protocol_version": 1,
  "addon_id": "plugin.video.stv",
  "device_id": "uuid-local",
  "exported_at": "2026-01-01T00:00:00Z",
  "entities": [
    {
      "entity": "favorite",
      "scope": "vod",
      "key": "123",
      "updated_at": "2026-01-01T00:00:00Z",
      "deleted": false,
      "payload": {}
    }
  ]
}
```

## Regras

- Operação iniciada exclusivamente pelo usuário.
- Um banco independente por dispositivo e add-on.
- Catálogos e caches não são sincronizados.
- Segredos e URLs de mídia são rejeitados pelo schema.
- Versão de protocolo incompatível aborta sem alterar dados.
- Aplicação em transação, com resumo e rollback em falha.
