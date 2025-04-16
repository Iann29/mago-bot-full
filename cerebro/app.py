import time
import tkinter as tk
import sys
import os
from typing import Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from thread_terminator import wait_for_thread_termination, terminate_all_daemon_threads
from ADBmanager import adb_manager
from screenVision.screenshotMain import config as screenshot_config
from cerebro.ui import HayDayTestApp, show_emulator_closed_message
from cerebro.state import initialize_state_manager, stop_state_monitoring
from cerebro.capture import start_screenshot_capture, stop_screenshot_capture, capture_thread

TARGET_FPS = screenshot_config.get("target_fps", 1)

def initialize_app():
    initialize_state_manager()
    
    return True

def cleanup_app():
    print("Aplicativo está sendo fechado...")
    
    print("Parando monitoramento de estados...")
    stop_state_monitoring()
    
    print("Interface encerrada.")
    
    print("Sinalizando para thread de captura parar...")
    stop_screenshot_capture()
    
    print("Parando monitoramento de estados...")
    
    print("Aguardando a thread de captura encerrar...")
    if capture_thread and capture_thread.is_alive():
        wait_for_thread_termination(capture_thread, timeout=2.0)
    
    terminate_all_daemon_threads()
    
    print("Programa encerrado.")

def run_main_app() -> int:
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        if adb_manager.connect_first_device():
            device = adb_manager.get_device()
            if device:
                if initialize_app():
                    try:
                        start_screenshot_capture(TARGET_FPS, device)
                        
                        root = tk.Tk()
                        app = HayDayTestApp(root)
                        
                        setup_adb_monitor_in_app(app)
                        
                        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))
                        
                        root.mainloop()
                        
                        cleanup_app()
                        return 0
                    except Exception as e:
                        print(f"❌ Erro ao executar aplicação: {e}")
                        cleanup_app()
                        return 1
                else:
                    print("❌ Falha ao inicializar a aplicação.")
                    return 1
            else:
                print("❌ Dispositivo ADB não disponível após conexão.")
        
        retry_count += 1
        
        if not show_emulator_closed_message():
            print("👋 Usuário optou por sair. Encerrando aplicação.")
            return 0
        
        if retry_count >= max_retries:
            print(f"❌ Máximo de tentativas ({max_retries}) atingido. Encerrando aplicação.")
            return 1
    
    return 1

def on_closing(root: tk.Tk, app: Optional[HayDayTestApp]=None) -> None:
    if tk.messagebox.askokcancel("Sair", "Deseja realmente sair da aplicação?"):
        if app is not None:
            try:
                app.on_close()
            except Exception as e:
                print(f"Erro ao fechar a aplicação: {e}")
        
        root.destroy()


def setup_adb_monitor_in_app(app):
    if not hasattr(app, 'emulator_connection_lost'):
        app.emulator_connection_lost = False
    
    app.check_emulator_status()


def on_emulator_connected(app, device_serial):
    if not hasattr(app, 'root') or not app.root.winfo_exists():
        return
        
    app.root.after(0, lambda: handle_emulator_connected(app, device_serial))


def handle_emulator_connected(app, device_serial):
    try:
        app.emulator_connection_lost = False
        app.status_label.config(text="Conectado ✓", foreground="green")
        app.device_label.config(text=f"Dispositivo: {device_serial}")
        
        app.connected_device = adb_manager.get_device()
    except Exception as e:
        print(f"Erro ao processar conexão do emulador: {e}")


def on_emulator_disconnected(app):
    if hasattr(app, 'root') and app.root.winfo_exists():
        app.root.after(0, lambda: handle_emulator_disconnected(app))


def handle_emulator_disconnected(app):
    try:
        import winsound
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
    except Exception:
        pass
        
    app.emulator_connection_lost = True
    app.connected_device = None
    app.status_label.config(text="Desconectado ✗", foreground="red")
    app.device_label.config(text="Dispositivo: Nenhum")
