# DSYSTEM AR API V1.0.0.0

API inicial para conectar o DSYSTEM AR Scanner Mobile ao DSYSTEM AR Painel.

## Como rodar local

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Execute:

```bash
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

Ou clique em:

```text
INICIAR_API_REDE.bat
```

## Acessos

API:
```text
http://SEU_IP:8010
```

Status:
```text
http://SEU_IP:8010/api/status
```

Documentação Swagger:
```text
http://SEU_IP:8010/docs
```

## Rotas principais

- `POST /api/upload`
- `GET /api/ars`
- `GET /api/ars/{id}`
- `PUT /api/ars/{id}`
- `DELETE /api/ars/{id}`
- `GET /api/ars/{id}/view`
- `GET /api/ars/{id}/download`

## Nomeação

- Com instalação e medidor:
`AR_CARTACONVITE_INST_123_MD_456.pdf`

- Só instalação:
`AR_CARTACONVITE_INST_123_MD_.pdf`

- Só medidor:
`AR_CARTACONVITE_INST__MD_456.pdf`

- Sem dados:
`AR_CARTACONVITE_PAG.01.pdf`


## Como testar se está funcionando

### 1. Testar a API
Execute:

```text
INICIAR_API_REDE.bat
```

Depois abra:

```text
http://localhost:8010/docs
```

ou no celular/rede:

```text
http://SEU_IP:8010/docs
```

Também pode executar:

```text
TESTAR_STATUS_API.bat
```

Se aparecer algo como `status: online`, a API está funcionando.

---

### 2. Testar upload pelo navegador
Com a API ligada, abra:

```text
http://localhost:8010/TESTE_UPLOAD.html
```

Selecione um PDF/imagem, informe instalação/medidor e envie.

Depois confira a lista:

```text
http://localhost:8010/api/ars
```

---

### 3. Testar integração com o APP MOBILE
Por enquanto o app mobile precisa ser ajustado para enviar o PDF para:

```text
http://SEU_IP:8010/api/upload
```

Campos esperados:

```text
file
instalacao
medidor
nome_cliente
origem=mobile
```

---

### 4. Testar integração com o PAINEL DESKTOP
O painel desktop também precisa ser ajustado para consumir:

```text
GET  http://SEU_IP:8010/api/ars
POST http://SEU_IP:8010/api/upload
PUT  http://SEU_IP:8010/api/ars/{id}
GET  http://SEU_IP:8010/api/ars/{id}/view
GET  http://SEU_IP:8010/api/ars/{id}/download
```

Nesta versão da API, ela já está pronta. O próximo patch será no APP e no PAINEL para apontarem para essa API.


## Correção V1.0.0.2
- Corrigida abertura do TESTE_UPLOAD.html pela API.
- Formulário de teste refeito para enviar para `/api/upload`.


## V1.0.0.3
- TESTE_UPLOAD.html mantém o design e agora permite informar a URL da API.
- Incluído ABRIR_TESTE_UPLOAD.bat.
- Corrige erro TypeError: Failed to fetch quando o HTML é aberto fora da origem da API.


## V1.0.0.4_OPERADOR
- API agora recebe e salva:
  - operador_usuario
  - operador_nome
  - operador_perfil
- Compatível com app mobile com login interno.

V1.0.0.6_COMPLETA_LOGIN_USERS
- Mantém upload/listagem/visualização/download/exclusão de ARs.
- Adiciona login centralizado.
- Admin padrão: admin/admin123.
- Adiciona criação, exclusão e troca de senha de usuários via API.
