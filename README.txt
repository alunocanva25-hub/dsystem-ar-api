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