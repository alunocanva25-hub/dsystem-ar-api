
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from pathlib import Path

APP_VERSION = "V1.0.0.5_LOGIN_USERS"

app = FastAPI(title="DSYSTEM AR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = Path("database.db")

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        nome TEXT,
        senha TEXT,
        perfil TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ar_records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    admin = cur.execute(
        "SELECT * FROM users WHERE usuario='admin'"
    ).fetchone()

    if not admin:
        cur.execute("""
        INSERT INTO users(usuario,nome,senha,perfil)
        VALUES(?,?,?,?)
        """, ("admin", "Administrador", "admin123", "admin"))

    conn.commit()
    conn.close()

init_db()

class LoginRequest(BaseModel):
    usuario: str
    senha: str

class CreateUserRequest(BaseModel):
    usuario: str
    nome: str
    senha: str
    perfil: str = "operador"

class ChangePasswordRequest(BaseModel):
    usuario: str
    senha_atual: str
    nova_senha: str

@app.get("/")
def root():
    return {
        "app": "DSYSTEM AR API",
        "version": APP_VERSION,
        "status": "online"
    }

@app.post("/api/login")
def login(data: LoginRequest):
    conn = get_conn()
    cur = conn.cursor()

    user = cur.execute("""
    SELECT id,usuario,nome,perfil
    FROM users
    WHERE usuario=? AND senha=?
    """, (data.usuario, data.senha)).fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    return dict(user)

@app.get("/api/users")
def list_users():
    conn = get_conn()
    cur = conn.cursor()

    users = cur.execute("""
    SELECT id,usuario,nome,perfil
    FROM users
    ORDER BY id DESC
    """).fetchall()

    conn.close()

    return [dict(x) for x in users]

@app.post("/api/users")
def create_user(data: CreateUserRequest):
    conn = get_conn()
    cur = conn.cursor()

    exists = cur.execute("""
    SELECT id FROM users WHERE usuario=?
    """, (data.usuario,)).fetchone()

    if exists:
        conn.close()
        raise HTTPException(status_code=400, detail="Usuário já existe")

    cur.execute("""
    INSERT INTO users(usuario,nome,senha,perfil)
    VALUES(?,?,?,?)
    """, (
        data.usuario,
        data.nome,
        data.senha,
        data.perfil
    ))

    conn.commit()
    conn.close()

    return {"success": True}

@app.put("/api/change-password")
def change_password(data: ChangePasswordRequest):
    conn = get_conn()
    cur = conn.cursor()

    user = cur.execute("""
    SELECT * FROM users
    WHERE usuario=? AND senha=?
    """, (data.usuario, data.senha_atual)).fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Senha atual inválida")

    cur.execute("""
    UPDATE users
    SET senha=?
    WHERE usuario=?
    """, (data.nova_senha, data.usuario))

    conn.commit()
    conn.close()

    return {"success": True}

@app.delete("/api/users/{usuario}")
def delete_user(usuario: str):
    if usuario == "admin":
        raise HTTPException(status_code=400, detail="Admin não pode ser removido")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM users
    WHERE usuario=?
    """, (usuario,))

    conn.commit()
    conn.close()

    return {"success": True}
