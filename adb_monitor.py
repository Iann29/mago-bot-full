"""
Módulo de monitoramento proativo de conexão ADB para o bot HayDay
Este módulo detecta quando o emulador é desconectado ou fechado e notifica
a aplicação para tomar medidas adequadas.
"""

import time
import threading
from typing import Callable, List, Optional
import tkinter as tk
from tkinter import messagebox
import winsound

# Importa o ADBManager singleton
from ADBmanager import adb_manager

class ADBMonitor:
    """
    Monitora o estado da conexão ADB e executa callbacks quando
    detecta conectividade ou desconexão do emulador.
    """
    def __init__(self):
        self._monitor_thread = None
        self._stop_monitor = False
        self._connection_callbacks = []
        self._disconnect_callbacks = []
        self._monitor_interval = 3.0  # Verificar a cada 3 segundos
        self._last_known_state = False  # Estado inicial de conexão desconhecido
        
        # Evento para sinalizar parada de forma mais responsiva
        self._stop_event = threading.Event()
        
        # Registra callbacks no ADBManager
        adb_manager.register_connection_callback = self.register_connection_callback
        adb_manager.register_disconnect_callback = self.register_disconnect_callback
        adb_manager.start_connection_monitoring = self.start_monitoring
        adb_manager.stop_connection_monitoring = self.stop_monitoring
        
    def register_connection_callback(self, callback: Callable) -> None:
        """Registra uma função callback para quando o emulador for conectado."""
        if callback not in self._connection_callbacks:
            self._connection_callbacks.append(callback)
            
    def register_disconnect_callback(self, callback: Callable) -> None:
        """Registra uma função callback para quando o emulador for desconectado."""
        if callback not in self._disconnect_callbacks:
            self._disconnect_callbacks.append(callback)
            
    def start_monitoring(self) -> None:
        """Inicia o monitoramento da conexão ADB em uma thread separada."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            print("🔔⚠️ ADB Monitor: Monitoramento já está ativo.")
            return
            
        # Reseta sinais de parada
        self._stop_monitor = False
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(target=self._connection_monitor_worker, daemon=True)
        self._monitor_thread.start()
        print("🔔✅ ADB Monitor: Monitoramento de conexão iniciado.")
    
    def stop_monitoring(self) -> None:
        """Para o monitoramento da conexão ADB."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            return
            
        print("🔔⏹️ ADB Monitor: Parando monitoramento...")
        
        # Usa ambos os mecanismos de parada para garantir
        self._stop_monitor = True
        self._stop_event.set()  # Sinaliza para a thread parar imediatamente
        
        # Reduzimos o timeout para 1.0s já que o evento vai responder mais rapidamente
        self._monitor_thread.join(timeout=1.0)
        
        if self._monitor_thread.is_alive():
            print("🔔⚠️ ADB Monitor: Thread de monitoramento não encerrou a tempo.")
        else:
            print("🔔🔇 ADB Monitor: Thread de monitoramento encerrada.")
            
        print("🔔⏹️ ADB Monitor: Monitoramento de conexão encerrado.")
    
    def _connection_monitor_worker(self) -> None:
        """Thread de trabalho que monitora continuamente o estado da conexão ADB."""
        # Verifica status inicial
        was_connected = adb_manager.is_connected()
        self._last_known_state = was_connected
        
        # Se estiver conectado na inicialização, notifica os callbacks
        if was_connected:
            device_serial = adb_manager.get_target_serial()
            for callback in self._connection_callbacks:
                try:
                    callback(device_serial)
                except Exception as e:
                    print(f"🔔❌ ADB Monitor: Erro ao chamar callback de conexão: {e}")
        
        # Checa tanto a flag quanto o evento de parada
        while not self._stop_monitor and not self._stop_event.is_set():
            try:
                # Verificação de estado atual
                is_connected_now = adb_manager.is_connected()
                
                # Detecta mudança de estado
                if is_connected_now != was_connected:
                    if is_connected_now:
                        device_serial = adb_manager.get_target_serial()
                        print(f"🔔📱 ADB Monitor: Conexão detectada com '{device_serial}'")
                        # Notifica callbacks de conexão
                        for callback in self._connection_callbacks:
                            try:
                                callback(device_serial)
                            except Exception as e:
                                print(f"🔔❌ ADB Monitor: Erro ao chamar callback de conexão: {e}")
                    else:
                        print("🔔⛔ ADB Monitor: Desconexão detectada!")
                        # Notifica callbacks de desconexão
                        for callback in self._disconnect_callbacks:
                            try:
                                callback()
                            except Exception as e:
                                print(f"🔔❌ ADB Monitor: Erro ao chamar callback de desconexão: {e}")
                
                # Atualiza o estado anterior
                was_connected = is_connected_now
                self._last_known_state = is_connected_now
                
            except Exception as e:
                print(f"🔔⚠️ ADB Monitor: Erro durante monitoramento: {e}")
            
            # Pausa entre verificações, mas permite interrupção
            # Em vez de sleep fixo, usa wait com timeout para poder interromper mais rápido
            if self._stop_event.wait(timeout=1.0):  # Verifica a cada 1 segundo, independente do intervalo
                break  # Se o evento for sinalizado, sai do loop imediatamente
        
        print("🔔🔇 ADB Monitor: Thread de monitoramento encerrada.")


# Integração com HayDayTestApp
def setup_adb_monitor_in_app(app):
    """
    Configura o monitoramento de ADB para o aplicativo HayDayTestApp.
    
    Args:
        app: Instância da classe HayDayTestApp
    """
    # Adiciona atributo para rastrear status do emulador
    if not hasattr(app, 'emulator_connection_lost'):
        app.emulator_connection_lost = False
    
    # Registra callbacks
    adb_manager.register_connection_callback(lambda serial: on_emulator_connected(app, serial))
    adb_manager.register_disconnect_callback(lambda: on_emulator_disconnected(app))
    
    # Inicia monitoramento
    adb_manager.start_connection_monitoring()
    
def on_emulator_connected(app, device_serial):
    """Callback chamado quando o emulador é conectado/reconectado."""
    if not hasattr(app, 'root') or not app.root.winfo_exists():
        return  # Janela foi fechada
        
    # Executa operações na thread do Tkinter
    app.root.after(0, lambda: handle_emulator_connected(app, device_serial))

def handle_emulator_connected(app, device_serial):
    """Manipula o evento de conexão do emulador na thread da interface gráfica."""
    if app.emulator_connection_lost:
        app.log(f"📱✅ Emulador reconectado! Serial: {device_serial}")
        app.status_label.config(text="Reconectado")
        app.device_label.config(text=f"Dispositivo: {device_serial}")
        
        # Habilita os botões
        app.test_button.config(state="normal")
        app.masked_test_button.config(state="normal")
        
        # Reset flag
        app.emulator_connection_lost = False

def on_emulator_disconnected(app):
    """Callback chamado quando o emulador é desconectado."""
    if not hasattr(app, 'root') or not app.root.winfo_exists():
        return  # Janela foi fechada
        
    # Executa operações na thread do Tkinter
    app.root.after(0, lambda: handle_emulator_disconnected(app))

def handle_emulator_disconnected(app):
    """Manipula o evento de desconexão do emulador na thread da interface gráfica."""
    app.log("📱❌ Emulador desconectado!")
    app.status_label.config(text="Desconectado", foreground="red")
    app.device_label.config(text="Dispositivo: Nenhum")
    
    # Desabilita os botões
    app.test_button.config(state="disabled")
    app.masked_test_button.config(state="disabled")
    
    # Toca som de alerta
    try:
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
    except Exception as sound_error:
        app.log(f"Erro ao reproduzir som: {sound_error}")
    
    # Mostra popup informando que o emulador foi fechado
    try:
        # Verifica se o popup já está sendo exibido
        if not app.emulator_connection_lost:
            app.root.after(100, lambda: messagebox.showwarning("Emulador Fechado", 
                                                        "Emulador foi fechado ou desconectado!\n" +
                                                        "Reabra o emulador para continuar."))
    except Exception as e:
        app.log(f"Erro ao mostrar popup: {e}")
        
    # Define flag de perda de conexão
    app.emulator_connection_lost = True

# Função para encerrar o monitor ao fechar a aplicação
def cleanup_adb_monitor_on_exit():
    """Para o monitoramento de ADB ao encerrar a aplicação."""
    adb_manager.stop_connection_monitoring()
    print("💻⏹️ MAIN: Monitoramento de conexão ADB encerrado.")

# Cria uma instância do ADBMonitor e aplica monkey patching no adb_manager
adb_monitor = ADBMonitor()
