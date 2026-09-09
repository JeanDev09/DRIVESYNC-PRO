import os
from pathlib import Path
from storage.persistence import (
    obtener_source,
    guardar_source,
    obtener_inventario_source
)
from utils.formatting import format_bytes


def format_size(value):
    return format_bytes(value)


def analizar_origen(nombre, origen, tui=None, forzar=False):
    """
    Crea o reutiliza el inventario persistente de un origen usando formato JSON optimizado.
    """
    origen = Path(origen)
    if not origen.is_dir():
        raise FileNotFoundError(f"No existe el origen: {origen}")

    cached = obtener_source(nombre)
    if not forzar and cached:
        # Verificamos si la ruta sigue siendo la misma
        misma_ruta = cached["ruta"] == str(origen) or cached["ruta"] == str(origen.resolve())

        if misma_ruta:
            # Obtenemos el inventario decodificado desde el JSON de la DB
            inventario = obtener_inventario_source(cached["id"])
            if inventario:
                if tui:
                    tui.log(
                        f"Inventario reutilizado: {len(inventario):,} archivos.",
                        "OK",
                    )
                return {
                    "source_id": cached["id"],
                    "nombre": nombre,
                    "ruta": origen,
                    "archivos": cached["archivos"],
                    "tamano": cached["tamano"],
                    "inventario": inventario,
                    "desde_cache": True,
                }

    if tui:
        tui.log(f"Analizando contenido de: {nombre}", "INFO")

    archivos = []
    tamano_total = 0

    # Escaneamos el disco en tiempo real
    for root, dirs, files in os.walk(origen):
        root_path = Path(root)
        for filename in files:
            src = root_path / filename
            try:
                stat = src.stat()
                relative = src.relative_to(origen)
                item = {
                    "ruta": str(relative),  # Convertimos a string para guardarlo en JSON
                    "tamano": stat.st_size,
                    "mtime": stat.st_mtime,
                }
                archivos.append(item)
                tamano_total += stat.st_size
            except OSError as e:
                if tui:
                    tui.log(f"No se pudo analizar {src.name}: {e}", "WARN")

    mtime_origen = origen.stat().st_mtime if origen.exists() else 0.0

    # Guardamos todo el paquete en una sola transacción rápida en la base de datos
    source_id = guardar_source(
        nombre=nombre,
        ruta=str(origen),
        archivos=len(archivos),
        tamano=tamano_total,
        mtime=mtime_origen,
        inventario=archivos
    )

    if tui:
        tui.log(
            f"Inventario guardado: {len(archivos):,} archivos | {format_size(tamano_total)}",
            "OK",
        )

    return {
        "source_id": source_id,
        "nombre": nombre,
        "ruta": origen,
        "archivos": len(archivos),
        "tamano": tamano_total,
        "inventario": archivos,
        "desde_cache": False,
    }


def calcular_espacio_necesario(origenes):
    total_archivos = 0
    total_bytes = 0
    for origen in origenes:
        total_archivos += origen["archivos"]
        total_bytes += origen["tamano"]
    return {
        "archivos": total_archivos,
        "bytes": total_bytes,
    }


def obtener_archivos_seleccionados(origenes):
    resultado = []
    for origen in origenes:
        for archivo in origen["inventario"]:
            resultado.append({
                "source_id": origen["source_id"],
                "source_name": origen["nombre"],
                "ruta": archivo["ruta"],  # Ya viene como string desde el JSON
                "tamano": archivo["tamano"],
                "mtime": archivo["mtime"],
            })
    return resultado