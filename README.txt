DSYSTEM AR API
V1.0.0.7_POSTGRES

OBJETIVO
- Persistir usuários, registros e arquivos enviados no PostgreSQL.
- Evita perder usuários/ARs quando o Render reiniciar ou redeployar.
- Mantém fallback SQLite local se DATABASE_URL não existir.

LOGIN PADRÃO
admin / admin123

RENDER - COMO USAR POSTGRESQL
1. No Render, crie um PostgreSQL Database.
2. Copie a Internal Database URL ou External Database URL.
3. No Web Service da API, vá em Environment.
4. Adicione:
   DATABASE_URL=<URL do PostgreSQL>
5. Faça redeploy.

BUILD COMMAND
pip install -r requirements.txt

START COMMAND
uvicorn main:app --host 0.0.0.0 --port $PORT

ROTAS PRINCIPAIS
GET  /api/status
POST /api/login
GET  /api/users
POST /api/users
PUT  /api/change-password
PUT  /api/admin/change-password
DELETE /api/users/{usuario}
POST /api/upload
GET  /api/ars
GET  /api/ars/{id}/download
GET  /api/ars/{id}/view

OBSERVAÇÃO IMPORTANTE
Esta versão salva os arquivos em file_data no banco PostgreSQL.
Assim, os PDFs não dependem mais da pasta local uploads do Render.

V1.0.0.8_POSTGRES_BASE_XLSX
- Adiciona cache/processamento de XLSX na API.
- A base XLSX é processada no servidor da API e salva no PostgreSQL.
- Não duplica registros idênticos: usa chave aba + instalação + medidor + nome_cliente.
- Se a mesma informação for importada novamente, atualiza o registro.
- Se instalação for igual mas medidor/nome forem diferentes, adiciona como novo registro.
- Endpoints compatíveis com painel:
  POST /api/upload-base-cache
  GET /api/base/sheets
  GET /api/base/columns
  POST /api/import-base
  GET /api/base/find
  GET /api/base/stats


V1.0.0.9_BASE_FIND_FLEX
- Corrige busca na base XLSX.
- Normaliza instalação/medidor/nome removendo espaços, pontos, barras e hífens.
- Busca por instalação+medidor, depois medidor, depois instalação, depois nome.
- Adiciona fallback parcial para evitar "não encontrado" por diferenças de formatação.
- Adiciona POST /api/base/reindex para reindexar bases já importadas.
