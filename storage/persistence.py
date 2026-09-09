import sqlite3
import os
import json
from datetime import datetime
from config import DB_PATH


def _get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_database():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_plans (
                id INTEGER KEY,
                fecha TEXT,
                destino TEXT,
                carpeta_raiz TEXT,
                seleccion_json TEXT,
                espacio_necesario INTEGER,
                archivos INTEGER,
                completado BOOLEAN DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER,
                source_id INTEGER,
                ruta_relativa TEXT,
                tamano INTEGER,
                estado TEXT DEFAULT 'PENDIENTE',
                fecha_actualizacion TEXT,
                FOREIGN KEY(plan_id) REFERENCES sync_plans(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                ruta TEXT,
                archivos INTEGER,
                tamano INTEGER,
                mtime REAL,
                inventario_json TEXT,
                actualizado TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS folder_cache (
                ruta TEXT PRIMARY KEY,
                tamano INTEGER
            )
        """)


def obtener_source(nombre):
    with _get_connection() as conn:
        row = conn.execute("""
            SELECT id, nombre, ruta, archivos, tamano, mtime, actualizado 
            FROM sources WHERE nombre = ?
        """, (nombre,)).fetchone()

        if not row: return None
        return {
            "id": row[0],
            "nombre": row[1],
            "ruta": row[2],
            "archivos": row[3],
            "tamano": row[4],
            "mtime": row[5],
            "actualizado": row[6]
        }


def guardar_source(nombre, ruta, archivos, tamano, mtime, inventario):
    now = datetime.now().isoformat()
    inv_json = json.dumps(inventario)
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO sources (nombre, ruta, archivos, tamano, mtime, inventario_json, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET
                ruta=excluded.ruta,
                archivos=excluded.archivos,
                tamano=excluded.tamano,
                mtime=excluded.mtime,
                inventario_json=excluded.inventario_json,
                actualizado=excluded.actualizado
        """, (nombre, str(ruta), archivos, tamano, mtime, inv_json, now))
        return conn.execute("SELECT id FROM sources WHERE nombre=?", (nombre,)).fetchone()[0]


def obtener_inventario_source(source_id):
    with _get_connection() as conn:
        row = conn.execute("SELECT inventario_json FROM sources WHERE id=?", (source_id,)).fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return []


def buscar_plan(destino, carpeta_raiz, seleccion):
    sel_json = json.dumps(sorted(seleccion))
    with _get_connection() as conn:
        row = conn.execute("""
            SELECT id, completado FROM sync_plans
            WHERE destino = ? AND carpeta_raiz = ? AND seleccion_json = ?
            ORDER BY id DESC LIMIT 1
        """, (str(destino), carpeta_raiz, sel_json)).fetchone()
        if row:
            return {"id": row[0], "completado": bool(row[1])}
    return None


def guardar_plan(destino, carpeta_raiz, seleccion, espacio_necesario, archivos):
    now = datetime.now().isoformat()
    sel_json = json.dumps(sorted(seleccion))
    with _get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO sync_plans (fecha, destino, carpeta_raiz, seleccion_json, espacio_necesario, archivos)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, str(destino), carpeta_raiz, sel_json, espacio_necesario, archivos))
        return cur.lastrowid


def guardar_sync_file(plan_id, source_id, ruta_relativa, tamano):
    now = datetime.now().isoformat()
    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO sync_files (plan_id, source_id, ruta_relativa, tamano, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?)
        """, (plan_id, source_id, str(ruta_relativa), tamano, now))


def actualizar_estado_sync_file(plan_id, source_id, ruta_relativa, estado):
    now = datetime.now().isoformat()
    with _get_connection() as conn:
        conn.execute("""
            UPDATE sync_files 
            SET estado = ?, fecha_actualizacion = ?
            WHERE plan_id = ? AND source_id = ? AND ruta_relativa = ?
        """, (estado, now, plan_id, source_id, str(ruta_relativa)))


def obtener_tamano_carpeta_persistente(ruta_str: str) -> int:
    """Calcula el tamaño de una carpeta y lo guarda en base de datos para consultas futuras instantáneas."""
    with _get_connection() as conn:
        row = conn.execute("SELECT tamano FROM folder_cache WHERE ruta = ?", (ruta_str,)).fetchone()
        if row: return row[0]

    total = 0
    try:
        for root, _, files in os.walk(ruta_str):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
    except Exception:
        pass

    with _get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO folder_cache (ruta, tamano) VALUES (?, ?)", (ruta_str, total))

    return total