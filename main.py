from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
import sqlite3
import shutil
import re
import os

APP_VERSION = "V1.0.0.4"
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "dsystem_ar_api.db"

UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="DSYSTEM AR API",
    version=APP_VERSION,
    description="API ponte para DSYSTEM AR Scanner Mobile e AR Painel."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            original_name TEXT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
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
        cols = [r['name'] for r in conn.execute('PRAGMA table_info(ars)').fetchall()]
        if 'operador_usuario' not in cols:
            conn.execute("ALTER TABLE ars ADD COLUMN operador_usuario TEXT")
        if 'operador_nome' not in cols:
            conn.execute("ALTER TABLE ars ADD COLUMN operador_nome TEXT")
        if 'operador_perfil' not in cols:
            conn.execute("ALTER TABLE ars ADD COLUMN operador_perfil TEXT")
        conn.commit()

def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_.\-]", "", name)
    return name or "arquivo.pdf"

def build_name(instalacao: str = "", medidor: str = "", ext: str = ".pdf") -> str:
    instalacao = (instalacao or "").strip()
    medidor = (medidor or "").strip()
    if instalacao or medidor:
        return f"AR_CARTACONVITE_INST_{instalacao}_MD_{medidor}{ext}"
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS total FROM ars WHERE file_name LIKE 'AR_CARTACONVITE_PAG.%'"
        ).fetchone()["total"] + 1
    return f"AR_CARTACONVITE_PAG.{count:02d}{ext}"

init_db()

@app.get("/")
def root():
    return {
        "app": "DSYSTEM AR API",
        "version": APP_VERSION,
        "status": "online",
        "endpoints": [
            "/api/status",
            "/api/ars",
            "/api/upload",
            "/api/ars/{id}",
            "/api/ars/{id}/download",
            "/api/ars/{id}/view"
        ]
    }

@app.get("/api/status")
def status():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS total FROM ars").fetchone()["total"]
    return {"status": "online", "version": APP_VERSION, "total_ars": total}

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
    target = UPLOAD_DIR / final_name

    # evita sobrescrever
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        n = 2
        while (UPLOAD_DIR / f"{stem}_{n}{suffix}").exists():
            n += 1
        target = UPLOAD_DIR / f"{stem}_{n}{suffix}"
        final_name = target.name

    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO ars (
                created_at, original_name, file_name, file_path,
                instalacao, medidor, nome_cliente, status, origem,
                operador_usuario, operador_nome, operador_perfil
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, original, final_name, str(target),
            instalacao.strip() or None,
            medidor.strip() or None,
            nome_cliente.strip() or None,
            "Pendente",
            origem,
            operador_usuario.strip() or None,
            operador_nome.strip() or None,
            operador_perfil.strip() or None
        ))
        conn.commit()
        new_id = cur.lastrowid

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
    sql = "SELECT * FROM ars WHERE 1=1"
    params = []

    if instalacao:
        sql += " AND instalacao LIKE ?"
        params.append(f"%{instalacao}%")
    if medidor:
        sql += " AND medidor LIKE ?"
        params.append(f"%{medidor}%")
    if nome_cliente:
        sql += " AND nome_cliente LIKE ?"
        params.append(f"%{nome_cliente}%")
    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY id DESC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]

@app.get("/api/ars/{ar_id}")
def get_ar(ar_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ars WHERE id = ?", (ar_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")
    return dict(row)

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
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ars WHERE id = ?", (ar_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AR não encontrado.")

        old_path = Path(row["file_path"])
        ext = old_path.suffix or ".pdf"
        new_name = sanitize_filename(build_name(instalacao, medidor, ext))
        new_path = UPLOAD_DIR / new_name

        if old_path.exists() and old_path.name != new_name:
            if new_path.exists():
                stem = new_path.stem
                suffix = new_path.suffix
                n = 2
                while (UPLOAD_DIR / f"{stem}_{n}{suffix}").exists():
                    n += 1
                new_path = UPLOAD_DIR / f"{stem}_{n}{suffix}"
                new_name = new_path.name
            old_path.rename(new_path)
        else:
            new_path = old_path
            new_name = old_path.name

        conn.execute("""
            UPDATE ars
            SET instalacao = ?, medidor = ?, nome_cliente = ?, status = ?,
                observacao = ?, file_name = ?, file_path = ?,
                operador_usuario = COALESCE(NULLIF(?, ''), operador_usuario),
                operador_nome = COALESCE(NULLIF(?, ''), operador_nome),
                operador_perfil = COALESCE(NULLIF(?, ''), operador_perfil)
            WHERE id = ?
        """, (
            instalacao.strip() or None,
            medidor.strip() or None,
            nome_cliente.strip() or None,
            status,
            observacao.strip() or None,
            new_name,
            str(new_path),
            operador_usuario.strip(),
            operador_nome.strip(),
            operador_perfil.strip(),
            ar_id
        ))
        conn.commit()

    return {"ok": True, "id": ar_id, "file_name": new_name, "status": status}

@app.delete("/api/ars/{ar_id}")
def delete_ar(ar_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ars WHERE id = ?", (ar_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AR não encontrado.")

        path = Path(row["file_path"])
        if path.exists():
            path.unlink()

        conn.execute("DELETE FROM ars WHERE id = ?", (ar_id,))
        conn.commit()

    return {"ok": True, "deleted": ar_id}

@app.get("/api/ars/{ar_id}/download")
def download_ar(ar_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ars WHERE id = ?", (ar_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(path, filename=row["file_name"], media_type="application/octet-stream")

@app.get("/api/ars/{ar_id}/view")
def view_ar(ar_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ars WHERE id = ?", (ar_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AR não encontrado.")

    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    ext = path.suffix.lower()
    media = "application/pdf" if ext == ".pdf" else "image/jpeg"
    return FileResponse(path, media_type=media)

@app.get("/TESTE_UPLOAD.html")
def teste_upload_html():
    teste = BASE_DIR / "TESTE_UPLOAD.html"
    if not teste.exists():
        raise HTTPException(status_code=404, detail="TESTE_UPLOAD.html não encontrado.")
    return FileResponse(teste, media_type="text/html")
