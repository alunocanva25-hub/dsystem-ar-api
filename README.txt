DSYSTEM AR API
V1.0.0.5_LOGIN_USERS

LOGIN PADRÃO:
admin
admin123

ROTAS:
POST /api/login
GET /api/users
POST /api/users
PUT /api/change-password
DELETE /api/users/{usuario}

RENDER:
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT