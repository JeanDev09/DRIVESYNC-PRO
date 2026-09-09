import sys
import threading
import time
import subprocess
import hashlib
import os
import platform
import uuid
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

# Importaciones de módulos internos
from drive.detector import detectar_unidades_drive
from ui.interactive import menu_radio
from ui.destination import seleccionar_carpeta_local
from ui.setup import confirmar_inicio, preparar_seleccion
from ui.tui import ReelsTUI
from ui.final import mostrar_final
from ui.theme import clear_view
from sync.copier import ejecutar_sincronizacion
from storage.persistence import init_database

console = Console()


# =====================================================================
# SISTEMA DE LICENCIAS OFFLINE (HWID)
# =====================================================================
def obtener_hwid():
    try:
        sistema = platform.system()

        if sistema == "Windows":
            # Usamos PowerShell, es más seguro y no sufre la deprecación de wmic
            cmd = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"],
                capture_output=True, text=True, shell=True
            )
            hwid = cmd.stdout.strip()
            if hwid:
                return hwid

        elif sistema == "Linux":
            # Para que puedas testear el programa localmente sin que te bloquee
            try:
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            except FileNotFoundError:
                pass

        # Fallback universal si todo falla: Dirección MAC física del equipo
        mac_node = uuid.getnode()
        return str(mac_node)

    except Exception:
        return "HWID_FALLBACK_123"


def validar_licencia(consola):
    hwid = obtener_hwid()
    # Tu palabra secreta para generar los hashes.
    palabra_secreta = "JeanDev_DriveSync_Pro_2026_Secreta"
    licencia_esperada = hashlib.sha256((hwid + palabra_secreta).encode()).hexdigest()

    sistema = platform.system()
    ruta_registro = r"Software\JeanDev\DriveSyncPro"

    # Funciones auxiliares para guardar/leer según el sistema operativo
    def leer_licencia():
        if sistema == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta_registro, 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(key, "LicenseKey")
                winreg.CloseKey(key)
                return val.strip()
            except Exception:
                return None
        else:
            # Fallback para que puedas testear el programa en tu entorno Linux
            try:
                with open("licencia.key", "r") as f:
                    return f.read().strip()
            except Exception:
                return None

    def guardar_licencia(lic):
        if sistema == "Windows":
            try:
                import winreg
                # Crea la carpeta en el registro si no existe
                winreg.CreateKey(winreg.HKEY_CURRENT_USER, ruta_registro)
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta_registro, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "LicenseKey", 0, winreg.REG_SZ, lic)
                winreg.CloseKey(key)
            except Exception as e:
                consola.print(f"[red]Error guardando en el registro: {e}[/red]")
        else:
            with open("licencia.key", "w") as f:
                f.write(lic)

    # 1. Comprobación silenciosa al abrir el programa
    licencia_actual = leer_licencia()
    if licencia_actual == licencia_esperada:
        return  # Todo correcto, el programa continúa al menú principal automáticamente

    # 2. Si no hay licencia o es inválida, entramos al menú interactivo de activación
    while True:
        clear_view(consola)
        consola.print(Panel.fit(
            f"[bold red]❌ LICENCIA NO ENCONTRADA O INVÁLIDA[/bold red]\n\n"
            f"Por favor, envía tu HWID al desarrollador para obtener tu clave de acceso.\n\n"
            f"[bold yellow]TU HWID:[/bold yellow] [bold cyan]{hwid}[/bold cyan]\n\n"
            f"Si ya tienes tu clave, pégala a continuación.",
            title="DriveSync Pro - Activación", border_style="red"
        ))

        # Pedimos el input del usuario usando Rich
        llave_ingresada = Prompt.ask("\n[bold green]🔑 Pega tu clave de licencia[/bold green]").strip()

        if llave_ingresada == licencia_esperada:
            guardar_licencia(llave_ingresada)
            clear_view(consola)
            consola.print("\n[bold green]✅ Licencia validada y guardada correctamente. Iniciando DriveSync Pro...[/bold green]")
            time.sleep(1.5)
            break
        else:
            clear_view(consola)
            consola.print(Panel.fit(
                "[bold red]❌ CLAVE INCORRECTA[/bold red]\n"
                "La clave ingresada no es válida para este equipo.\n"
                "Asegúrate de copiarla sin espacios al inicio o final.",
                border_style="red"
            ))
            Prompt.ask("\n[dim]Presiona ENTER para intentar de nuevo...[/dim]")


# =====================================================================
# LÓGICA PRINCIPAL DEL PROGRAMA
# =====================================================================
def flujo_principal():
    clear_view(console)
    unidades = detectar_unidades_drive()
    if not unidades:
        console.print("\n[bold red]⚠️ No se detectaron unidades de Google Drive en este equipo.[/bold red]")
        Prompt.ask("Presiona ENTER para volver...")
        return

    opciones_origen = [{"titulo": u.nombre_limpio, "detalle": f"Google Drive • {u.libre_gb:.1f} GB Libres"} for u in
                       unidades]
    idx_origen = menu_radio(console, "UNIDADES GOOGLE DRIVE DETECTADAS", opciones_origen)
    if idx_origen is None: return
    unidad_origen = unidades[idx_origen]

    clear_view(console)
    opciones_destino = [
        {"titulo": "PC / Disco externo", "detalle": "Seleccionar una carpeta local en tu equipo"},
        {"titulo": "Google Drive", "detalle": "Copiar directamente a una unidad en la nube"}
    ]
    idx_tipo_destino = menu_radio(console, "DESTINO DE LA COPIA", opciones_destino)
    if idx_tipo_destino is None: return

    clear_view(console)
    if idx_tipo_destino == 0:
        ruta_destino = seleccionar_carpeta_local(console)
        if not ruta_destino: return
    else:
        idx_dest_drive = menu_radio(console, "CUENTA DE GOOGLE DRIVE DESTINO", opciones_origen)
        if idx_dest_drive is None: return
        ruta_destino = unidades[idx_dest_drive].ruta_unidad

    clear_view(console)
    opciones_escaneo = [
        {"titulo": "Escanear shortcuts o accesos directos",
         "detalle": "Detecta enlaces .lnk y carpetas compartidas ancladas a tu Drive"},
        {"titulo": "Escanear carpetas", "detalle": "Detecta únicamente carpetas normales dentro de tu unidad"}
    ]
    idx_escaneo = menu_radio(console, "MÉTODO DE ESCANEO", opciones_escaneo)
    if idx_escaneo is None: return

    clear_view(console)
    plan = preparar_seleccion(
        console=console,
        drive_raiz=unidad_origen.ruta_unidad,
        destino=ruta_destino,
        modo_escaneo=idx_escaneo
    )

    if not plan: return
    if not confirmar_inicio(console):
        return

    clear_view(console)

    tui = ReelsTUI(unidad_origen.ruta_unidad, ruta_destino)
    # Al llamar start(), Rich inicia automáticamente un hilo seguro a 10 FPS para dibujar.
    tui.start()

    # --- INICIO: CENTRALIZACIÓN DE DIBUJADO Y CONTROL DE CONCURRENCIA ---
    cancelado = False
    ui_lock = threading.Lock()  # Candado para evitar colisiones de hilos

    # Interceptamos el método refresh de TUI.
    # El hilo de copiado llamará aquí, pero NO dibujará. Solo actualizará el modelo.
    def hilo_seguro_refresh():
        if cancelado:
            raise KeyboardInterrupt

        # Centralizamos y serializamos la actualización de datos
        with ui_lock:
            now = time.monotonic()
            if now - tui._last_render < 0.08:
                return
            tui._last_render = now
            tui._samples.append((now, tui.bytes_copied))
            if len(tui._samples) >= 2:
                started, start_bytes = tui._samples[0]
                elapsed = now - started
                copied = tui.bytes_copied - start_bytes
                tui.current_speed = copied / elapsed if elapsed >= 0.35 and copied >= 0 else 0.0

            # MAGIA AQUÍ: refresh=False.
            # Actualizamos la vista en memoria, pero NO forzamos a la consola a pintar.
            # El hilo nativo de Rich tomará este diseño y lo pintará de forma 100% segura.
            tui.live.update(tui._generate_layout(), refresh=False)

    # Inyectamos nuestra función segura
    tui.refresh = hilo_seguro_refresh
    excepcion_hilo = None

    def tarea_sincronizacion():
        nonlocal excepcion_hilo
        try:
            ejecutar_sincronizacion(plan, tui)
        except BaseException as e:
            excepcion_hilo = e

    # Lanzamos el copiado de archivos en su propio hilo
    hilo = threading.Thread(target=tarea_sincronizacion, daemon=True)
    hilo.start()

    try:
        # El hilo principal (este) ahora solo sirve para vigilar el Ctrl+C.
        # No bloquea nada y no interfiere con la UI.
        while hilo.is_alive():
            time.sleep(0.1)

        if excepcion_hilo:
            raise excepcion_hilo

    except KeyboardInterrupt:
        cancelado = True  # Ordena al hilo de copiado que aborte
        hilo.join(timeout=1.5)  # Le damos tiempo a que cierre los archivos

        tui.set_status("CANCELLED", "Interrumpido por el usuario (Progreso guardado)")
        tui.log("Sincronización cancelada por el usuario. El progreso parcial se conserva.", "WARN")
        # Forzamos un último dibujado seguro antes de cerrar
        tui.live.update(tui._generate_layout(), refresh=True)
    finally:
        tui.stop()

    mostrar_final(tui)


def mostrar_menu_principal():
    while True:
        clear_view(console)
        try:
            opc = menu_radio(console, "Inicio", [
                {"titulo": "Iniciar sincronización",
                 "detalle": "Clona contenido de Google Drive a una ubicación elegida."},
                {"titulo": "Salir", "detalle": "Cerrar DriveSync Pro."},
            ], show_contact=True)
        except (KeyboardInterrupt, EOFError):
            break
        if opc == 0:
            flujo_principal()
        elif opc in (1, None):
            break


def main():
    try:
        validar_licencia(console)
        init_database()
        mostrar_menu_principal()

    except KeyboardInterrupt:
        console.print("\n\n[dim]Programa finalizado por el usuario.[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error inesperado:[/bold red] {e}\n")

    finally:
        # La consola NO se cierra automáticamente.
        console.print("\n[dim]Presiona ENTER para cerrar el programa...[/dim]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass


if __name__ == "__main__":
    main()
