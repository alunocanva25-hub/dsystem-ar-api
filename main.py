
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import os
import re
import sqlite3

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

APP_VERSION = "V1.0.0.7_POSTGRES"
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

SQLITE_DB = BASE_DIR / "dsystem_ar_api.db"

app = FastAPI(
    title="DSYSTEM AR API",
    version=APP_VERSION,
    description="API central do DSYSTEM AR Scanner Mobile e AR Painel com suporte PostgreSQL."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class AdminChangePasswordRequest(BaseModel):
    usuario: str
    nova_senha: str


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_conn():
    if USE_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError("psycopg2-binary não está instalado.")
        return psycopg2.connect(
            normalize_database_url(DATABASE_URL),
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def q(sql: str) -> str:
    """Converte placeholders ? para %s quando estiver usando PostgreSQL."""
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def row_to_dict(row):
    return dict(row) if row else None


def fetchone(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(q(sql), params)
        row = cur.fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def fetchall(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(q(sql), params)
        rows = cur.fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(q(sql), params)
        conn.commit()
        return cur
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    try:
        cur = conn.cursor()

        if USE_POSTGRES:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT NOT NULL DEFAULT 'operador',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ars (
                    id SERIAL PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    original_name TEXT,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    file_data BYTEA,
                    mime_type TEXT DEFAULT 'application/pdf',
                    instalacao TEXT,
                    medidor TEXT,
                    nome_cliente TEXT,
                    status TEXT DEFAULT 'Pendente',
                    origem TEXT DEFAULT 'api',
                    observacao TEXT,
                    operador_usuario TEXT,
                    operador_nome TEXT,
                    operador_perfil TEXT
                )
            """)

            # Migrações defensivas para bases antigas
            for col, typ in [
                ("file_data", "BYTEA"),
                ("mime_type", "TEXT DEFAULT 'application/pdf'"),
                ("operador_usuario", "TEXT"),
                ("operador_nome", "TEXT"),
                ("operador_perfil", "TEXT"),
            ]:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='ars' AND column_name=%s
                """, (col,))
                if not cur.fetchone():
                    cur.execute(f"ALTER TABLE ars ADD COLUMN {col} {typ}")

        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT NOT NULL DEFAULT 'operador',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    original_name TEXT,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    file_data BLOB,
                    mime_type TEXT DEFAULT 'application/pdf',
                    instalacao TEXT,
                    medidor TEXT,
                    nome_cliente TEXT,
                    status TEXT DEFAULT 'Pendente',
                    origem TEXT DEFAULT 'api',
                    observacao TEXT,
                    operador_usuario TEXT,
                    operador_nome TEXT,
                    operador_perfil TEXT
                )
            """)

            cols = [r["name"] for r in cur.execute("PRAGMA table_info(ars)").fetchall()]
            migrations = {
                "file_data": "ALTER TABLE ars ADD COLUMN file_data BLOB",
                "mime_type": "ALTER TABLE ars ADD COLUMN mime_type TEXT DEFAULT 'application/pdf'",
                "operador_usuario": "ALTER TABLE ars ADD COLUMN operador_usuario TEXT",
                "operador_nome": "ALTER TABLE ars ADD COLUMN operador_nome TEXT",
                "operador_perfil": "ALTER TABLE ars ADD COLUMN operador_perfil TEXT",
            }
            for col, sql in migrations.items():
                if col not in cols:
                    cur.execute(sql)

        cur.execute(q("SELECT id FROM users WHERE usuario=?"), ("admin",))
        if not cur.fetchone():
            cur.execute(
                q("INSERT INTO users(usuario,nome,senha,perfil) VALUES(?,?,?,?)"),
                ("admin", "Administrador", "admin123", "admin")
            )

        conn.commit()
    finally:
        conn.close()


def sanitize_filename(name: str) -> str:
    name = (name or "").strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_.\-]", "", name)
    return name or "arquivo.pdf"


def media_type_from_ext(ext: str) -> str:
    ext = (ext or "").lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "application/octet-stream"


def build_name(instalacao: str = "", medidor: str = "", ext: str = ".pdf") -> str:
    instalacao = (instalacao or "").strip()
    medidor = (medidor or "").strip()

    if instalacao or medidor:
        return f"AR_CARTACONVITE_INST_{instalacao}_MD_{medidor}{ext}"

    row = fetchone("SELECT COUNT(*) AS total FROM ars WHERE file_name LIKE ?", ("AR_CARTACONVITE_PAG.%",))
    total = (row or {}).get("total", 0) or 0
    return f"AR_CARTACONVITE_PAG.{int(total) + 1:02d}{ext}"


init_db()


@app.get("/")
def root():
    return {
        "app": "DSYSTEM AR API",
        "version": APP_VERSION,
        "status": "online",
        "database": "postgresql" if USE_POSTGRES else "sqlite",
        "storage": "database_file_data",
        "endpoints": [
            "/api/status",
            "/api/login",
            "/api/users",
            "/api/ars",
            "/api/upload",
            "/api/ars/{id}/download",
            "/api/ars/{id}/view"
        ]
    }


@app.get("/api/status")
def status():
    row = fetchone("SELECT COUNT(*) AS total FROM ars")
    users = fetchone("SELECT COUNT(*) AS total FROM users")
    return {
        "status": "online",
        "version": APP_VERSION,
        "database": "postgresql" if USE_POSTGRES else "sqlite",
        "total_ars": int((row or {}).get("total", 0) or 0),
        "total_users": int((users or {}).get("total", 0) or 0)
    }


@app.post("/api/login")
def login(data: LoginRequest):
    user = fetchone(
        "SELECT id, usuario, nome, perfil FROM users WHERE usuario=? AND senha=?",
        (data.usuario, data.senha)
    )
    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    return user


@app.get("/api/users")
def list_users():
    return fetchall("SELECT id, usuario, nome, perfil FROM users ORDER BY id DESC")


@app.post("/api/users")
def create_user(data: CreateUserRequest):
    usuario = (data.usuario or "").strip()
    nome = (data.nome or "").strip()
    senha = data.senha or ""
    perfil = (data.perfil or "operador").strip().lower()

    if perfil not in ["admin", "operador"]:
        perfil = "operador"

    if not usuario or not nome or not senha:
        raise HTTPException(status_code=400, detail="Preencha usuário, nome e senha")

    exists = fetchone("SELECT id FROM users WHERE usuario=?", (usuario,))
    if exists:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    execute(
        "INSERT INTO users(usuario,nome,senha,perfil) VALUES(?,?,?,?)",
        (usuario, nome, senha, perfil)
    )
    return {"success": True}


@app.put("/api/change-password")
def change_password(data: ChangePasswordRequest):
    user = fetchone(
        "SELECT id FROM users WHERE usuario=? AND senha=?",
        (data.usuario, data.senha_atual)
    )
    if not user:
        raise HTTPException(status_code=401, detail="Senha atual inválida")

    execute("UPDATE users SET senha=? WHERE usuario=?", (data.nova_senha, data.usuario))
    return {"success": True}


@app.put("/api/admin/change-password")
def admin_change_password(data: AdminChangePasswordRequest):
    if not data.usuario or not data.nova_senha:
        raise HTTPException(status_code=400, detail="Informe usuário e nova senha")

    user = fetchone("SELECT id FROM users WHERE usuario=?", (data.usuario,))
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    execute("UPDATE users SET senha=? WHERE usuario=?", (data.nova_senha, data.usuario))
    return {"success": True}


@app.delete("/api/users/{usuario}")
def delete_user(usuario: str):
    if usuario == "admin":
        raise HTTPException(status_code=400, detail="Admin padrão não pode ser removido")

    execute("DELETE FROM users WHERE usuario=?", (usuario,))
    return {"success": True}


@app.post("/api/upload")
async def upload_ar(
    file: UploadFile = File(...),
    instalacao: str = Form(""),
    medidor: str = Form(""),
    nome_cliente: str = Form(""),
    origem: str = Form("mobile"),
    operador_usuario: str = Form(""),
    operador_nome: str = Form(""),
    operador_perfil: str = Form("")
):
    original = file.filename or "arquivo.pdf"
    ext = Path(original).suffix.lower() or ".pdf"

    if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato não permitido.")

    final_name = sanitize_filename(build_name(instalacao, medidor, ext))
    mime_type = media_type_from_ext(ext)
    file_bytes = await file.read()

    # Mantém cópia local quando possível, mas a fonte confiável é file_data no banco.
    target = UPLOAD_DIR / final_name
    try:
        if target.exists():
            stem = target.stem
            suffix = target.suffix
            n = 2
            while (UPLOAD_DIR / f"{stem}_{n}{suffix}").exists():
                n += 1
            target = UPLOAD_DIR / f"{stem}_{n}{suffix}"
            final_name = target.name
        target.write_bytes(file_bytes)
        file_path = str(target)
    except Exception:
        file_path = ""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    try:
        cur = conn.cursor()

        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO ars (
                    created_at, original_name, file_name, file_path, file_data, mime_type,
                    instalacao, medidor, nome_cliente, status, origem,
                    operador_usuario, operador_nome, operador_perfil
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                now, original, final_name, file_path, psycopg2.Binary(file_bytes), mime_type,
                instalacao.strip() or None,
                medidor.strip() or None,
                nome_cliente.strip() or None,
                "Pendente",
                origem,
                operador_usuario.strip() or None,
                operador_nome.strip() or None,
                operador_perfil.strip() or None
            ))
            new_id = cur.fetchone()["id"]
        else:
            cur.execute("""
                INSERT INTO ars (
                    created_at, original_name, file_name, file_path, file_data, mime_type,
                    instalacao, medidor, nome_cliente, status, origem,
                    operador_usuario, operador_nome, operador_perfil
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, original, final_name, file_path, file_bytes, mime_type,
                instalacao.strip() or None,
                medidor.strip() or None,
                nome_cliente.strip() or None,
                "Pendente",
                origem,
                operador_usuario.strip() or None,
                operador_nome.strip() or None,
                operador_perfil.strip() or None
            ))
            new_id = cur.lastrowid

        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "id": new_id,
        "file_name": final_name,
        "instalacao": instalacao,
        "medidor": medidor,
        "nome_cliente": nome_cliente,
        "operador_usuario": operador_usuario,
        "operador_nome": operador_nome,
        "operador_perfil": operador_perfil,
        "status": "Pendente"
    }


@app.get("/api/ars")
def list_ars(
    instalacao: str = "",
    medidor: str = "",
    nome_cliente: str = "",
    status: str = ""
):
    sql = """
        SELECT id, created_at, original_name, file_name, file_path, mime_type,
               instalacao, medidor, nome_cliente, status, origem, observacao,
               operador_usuario, operador_nome, operador_perfil
        FROM ars
        WHERE 1=1
    """
    params = []

    like_op = "ILIKE" if USE_POSTGRES else "LIKE"

    if instalacao:
        sql += f" AND instalacao {like_op} ?"
        params.append(f"%{instalacao}%")
    if medidor:
        sql += f" AND medidor {like_op} ?"
        params.append(f"%{medidor}%")
    if nome_cliente:
        sql += f" AND nome_cliente {like_op} ?"
        params.append(f"%{nome_cliente}%")
    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC"
    return fetchall(sql, tuple(params))


@app.get("/api/ars/{ar_id}")
def get_ar(ar_id: int):
    row = fetchone("""
        SELECT id, created_at, original_name, file_name, file_path, mime_type,
               instalacao, medidor, nome_cliente, status, origem, observacao,
               operador_usuario, operador_nome, operador_perfil
        FROM ars
        WHERE id=?
    """, (ar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")
    return row


@app.put("/api/ars/{ar_id}")
def update_ar(
    ar_id: int,
    instalacao: str = Form(""),
    medidor: str = Form(""),
    nome_cliente: str = Form(""),
    status: str = Form("Pendente"),
    observacao: str = Form(""),
    operador_usuario: str = Form(""),
    operador_nome: str = Form(""),
    operador_perfil: str = Form("")
):
    row = fetchone("SELECT * FROM ars WHERE id=?", (ar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    old_name = row.get("file_name") or "arquivo.pdf"
    ext = Path(old_name).suffix or ".pdf"
    new_name = sanitize_filename(build_name(instalacao, medidor, ext))

    execute("""
        UPDATE ars
        SET instalacao=?, medidor=?, nome_cliente=?, status=?, observacao=?,
            file_name=?,
            operador_usuario=COALESCE(NULLIF(?, ''), operador_usuario),
            operador_nome=COALESCE(NULLIF(?, ''), operador_nome),
            operador_perfil=COALESCE(NULLIF(?, ''), operador_perfil)
        WHERE id=?
    """, (
        instalacao.strip() or None,
        medidor.strip() or None,
        nome_cliente.strip() or None,
        status,
        observacao.strip() or None,
        new_name,
        operador_usuario.strip(),
        operador_nome.strip(),
        operador_perfil.strip(),
        ar_id
    ))

    return {"ok": True, "id": ar_id, "file_name": new_name, "status": status}


@app.delete("/api/ars/{ar_id}")
def delete_ar(ar_id: int):
    row = fetchone("SELECT * FROM ars WHERE id=?", (ar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    path = Path(row.get("file_path") or "")
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass

    execute("DELETE FROM ars WHERE id=?", (ar_id,))
    return {"ok": True, "deleted": ar_id}


def file_response_from_row(row):
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    filename = row.get("file_name") or "arquivo.pdf"
    mime_type = row.get("mime_type") or media_type_from_ext(Path(filename).suffix)

    file_data = row.get("file_data")
    if file_data is not None:
        if isinstance(file_data, memoryview):
            file_data = file_data.tobytes()
        return Response(
            content=bytes(file_data),
            media_type=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    path = Path(row.get("file_path") or "")
    if path.exists():
        return FileResponse(path, filename=filename, media_type=mime_type)

    raise HTTPException(status_code=404, detail="Arquivo não encontrado.")


@app.get("/api/ars/{ar_id}/download")
def download_ar(ar_id: int):
    row = fetchone("SELECT * FROM ars WHERE id=?", (ar_id,))
    return file_response_from_row(row)


@app.get("/api/download/{ar_id}")
def download_ar_alias(ar_id: int):
    row = fetchone("SELECT * FROM ars WHERE id=?", (ar_id,))
    return file_response_from_row(row)


@app.get("/api/ars/{ar_id}/view")
def view_ar(ar_id: int):
    row = fetchone("SELECT * FROM ars WHERE id=?", (ar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    filename = row.get("file_name") or "arquivo.pdf"
    mime_type = row.get("mime_type") or media_type_from_ext(Path(filename).suffix)
    file_data = row.get("file_data")

    if file_data is not None:
        if isinstance(file_data, memoryview):
            file_data = file_data.tobytes()
        return Response(content=bytes(file_data), media_type=mime_type)

    path = Path(row.get("file_path") or "")
    if path.exists():
        return FileResponse(path, media_type=mime_type)

    raise HTTPException(status_code=404, detail="Arquivo não encontrado.")


@app.get("/TESTE_UPLOAD.html")
def teste_upload_html():
    teste = BASE_DIR / "TESTE_UPLOAD.html"
    if not teste.exists():
        raise HTTPException(status_code=404, detail="TESTE_UPLOAD.html não encontrado.")
    return FileResponse(teste, media_type="text/html")
