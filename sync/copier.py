import shutil
import time
from pathlib import Path
from storage.persistence import (
    guardar_plan, guardar_sync_file, actualizar_estado_sync_file, buscar_plan
)


def copiar_con_reanudacion(src, dst, tui, source_size, bytes_ya_escritos=0):
    dst.parent.mkdir(parents=True, exist_ok=True)
    chunk_size = 1024 * 1024 * 2
    mode_dst = 'ab' if bytes_ya_escritos > 0 else 'wb'

    tui.current_file_size = source_size
    tui.current_file_copied = bytes_ya_escritos

    if bytes_ya_escritos > 0:
        tui.bytes_copied += bytes_ya_escritos

    last_refresh = time.monotonic()

    try:
        with open(src, 'rb') as fsrc, open(dst, mode_dst) as fdst:
            if bytes_ya_escritos > 0:
                fsrc.seek(bytes_ya_escritos)

            while True:
                buf = fsrc.read(chunk_size)
                if not buf: break
                fdst.write(buf)

                tui.bytes_copied += len(buf)
                tui.current_file_copied += len(buf)

                now = time.monotonic()
                if now - last_refresh > 0.1:
                    tui.refresh()
                    last_refresh = now

        shutil.copystat(src, dst)
        tui.refresh()
    except BaseException as e:
        raise e


def ejecutar_sincronizacion(plan, tui):
    # --- CORRECCIÓN DEL BUG: INYECTAMOS LOS TOTALES A LA TUI ---
    tui.bytes_total = plan["bytes"]
    tui.global_total = plan["archivos"]
    # -----------------------------------------------------------

    destino = Path(plan["base_dir"])
    destino.mkdir(parents=True, exist_ok=True)

    seleccion = [item["nombre"] for item in plan["seleccion"]]
    cached_plan = buscar_plan(destino.parent, plan["nombre_raiz"], seleccion)

    if cached_plan:
        plan_id = cached_plan["id"]
        tui.log("Plan de sincronización recuperado.", "OK")
    else:
        plan_id = guardar_plan(destino.parent, plan["nombre_raiz"], seleccion, plan["bytes"], plan["archivos"])
        for origen in plan["origenes"]:
            for archivo in origen["inventario"]:
                guardar_sync_file(plan_id, origen["source_id"], archivo["ruta"], archivo["tamano"])
        tui.log("Nuevo plan de sincronización guardado.", "OK")

    for origen in plan["origenes"]:
        source_root = Path(origen["ruta"])
        source_id = origen["source_id"]

        tui.batch_index += 1
        tui.current_batch = origen["nombre"]
        tui.batch_total = origen["archivos"]
        tui.batch_processed = 0
        tui.batch_copied = 0
        tui.batch_skipped = 0
        tui.batch_errors = 0

        tui.set_status("COPYING", "Sincronizando archivos...")
        tui.refresh()

        for archivo in origen["inventario"]:
            relative = Path(archivo["ruta"])
            src = source_root / relative
            dst = destino / origen["nombre"] / relative

            tui.current_file = relative.name
            tui.current_source = str(src)
            tui.current_destination = str(dst)
            tui.current_file_size = 0
            tui.current_file_copied = 0

            try:
                if not src.exists(): raise FileNotFoundError(f"No existe: {src}")
                source_size = src.stat().st_size

                if dst.exists():
                    dest_size = dst.stat().st_size
                    if dest_size == source_size:
                        tui.batch_skipped += 1
                        tui.global_skipped += 1
                        tui.bytes_copied += source_size
                        actualizar_estado_sync_file(plan_id, source_id, relative, "OMITIDO")
                        tui.log(f"Omitido: {relative.name}", "INFO")
                    elif dest_size < source_size:
                        tui.log(f"Reanudando desde {dest_size / 1024 / 1024:.1f}MB: {relative.name}", "WARN")
                        copiar_con_reanudacion(src, dst, tui, source_size, bytes_ya_escritos=dest_size)
                        tui.batch_copied += 1
                        tui.global_copied += 1
                        actualizar_estado_sync_file(plan_id, source_id, relative, "COPIADO")
                    else:
                        tui.log(f"Sobrescribiendo corrupto: {relative.name}", "WARN")
                        copiar_con_reanudacion(src, dst, tui, source_size, 0)
                        tui.batch_copied += 1
                        tui.global_copied += 1
                        actualizar_estado_sync_file(plan_id, source_id, relative, "COPIADO")
                else:
                    copiar_con_reanudacion(src, dst, tui, source_size, 0)
                    tui.batch_copied += 1
                    tui.global_copied += 1
                    actualizar_estado_sync_file(plan_id, source_id, relative, "COPIADO")
                    tui.log(f"Copiado: {relative.name}", "INFO")

            except KeyboardInterrupt:
                tui.log(f"Pausado: {relative.name}", "WARN")
                raise
            except Exception as e:
                tui.batch_errors += 1
                tui.global_errors += 1
                actualizar_estado_sync_file(plan_id, source_id, relative, "ERROR")
                tui.log(f"{relative.name}: {e}", "ERROR")
            finally:
                tui.batch_processed += 1
                tui.global_processed += 1
                tui.refresh()

        tui.set_status("COMPLETED", "Lote completado.")
        tui.refresh()
        time.sleep(0.5)

    if tui.global_errors:
        tui.set_status("ERROR", "Proceso finalizado con errores.")
    else:
        tui.set_status("FINISHED", "Sincronización completada.")
    tui.refresh()