# /cerebro/app.py
# Módulo central para coordenação da aplicação

import time
import tkinter as tk
import sys
import os
from typing import Optional, Dict, Any

# Adiciona a raiz do projeto ao PYTHONPATH para garantir importações corretas
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Agora usamos diretamente o ADBManager em vez do adb_monitor
# Esta abordagem elimina a duplicação de código
from thread_terminator import wait_for_thread_termination, terminate_all_daemon_threads
from ADBmanager import adb_manager
from screenVision.screenshotMain import config as screenshot_config
from cerebro.ui import HayDayTestApp, show_emulator_closed_message
from cerebro.state import initialize_state_manager, stop_state_monitoring
from cerebro.capture import start_screenshot_capture, stop_screenshot_capture, capture_thread

# --- Configurações Lidas do JSON ---
TARGET_FPS = screenshot_config.get("target_fps", 1)  # Pega do CFG, default 1

def initialize_app():
    """
    Inicializa componentes principais da aplicação.
    
    Returns:
        bool: True se inicialização foi bem sucedida, False caso contrário
    """
    # Inicializa o gerenciador de estados
    initialize_state_manager()
    
    return True

def cleanup_app():
    """Limpa recursos e encerra threads antes de fechar a aplicação."""
    print("Aplicativo está sendo fechado...")
    
    # Limpa o monitor ADB
    cleanup_adb_monitor_on_exit()
    print("Monitoramento de conexão ADB encerrado.")
    
    # Para o monitoramento de estados
    print("Parando monitoramento de estados...")
    stop_state_monitoring()
    
    # Para a interface gráfica (se houver)
    print("Interface encerrada.")
    
    # Sinaliza para a thread de captura parar
    print("Sinalizando para thread de captura parar...")
    stop_screenshot_capture()
    
    # Para o monitoramento de estados (redundante mas seguro)
    print("Parando monitoramento de estados...")
    
    # Aguarda a thread de captura encerrar
    print("Aguardando a thread de captura encerrar...")
    if capture_thread and capture_thread.is_alive():
        wait_for_thread_termination(capture_thread, timeout=2.0)
    
    # Finaliza threads daemon remanescentes
    terminate_all_daemon_threads()
    
    print("Programa encerrado.")

def run_main_app() -> int:
    """
    Executa a aplicação principal.
    
    Returns:
        int: Código de saída da aplicação (0 para sucesso)
    """
    # Remove configuration log
    # Exibe configurações
    # print(f"Configurações: FPS={TARGET_FPS} (do screenshotCFG.json)")
    
    # Exibe mensagem se o emulador estiver fechado
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        # Tenta conectar ao emulador
        if adb_manager.connect_first_device():
            # Obtém o dispositivo conectado
            device = adb_manager.get_device()
            if device:
                # Inicializa a aplicação
                if initialize_app():
                    try:
                        # Inicia a thread de captura
                        start_screenshot_capture(TARGET_FPS, device)
                        
                        # Cria a interface gráfica
                        root = tk.Tk()
                        app = HayDayTestApp(root)
                        
                        # Configuração do monitor ADB - deve ser feita APÓS criar a app
                        setup_adb_monitor_in_app(app)
                        
                        # Configura o callback de fechamento
                        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, app))
                        
                        # Inicia o loop principal da interface
                        root.mainloop()
                        
                        # Limpa recursos antes de sair
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
        
        # Se chegou aqui, não conseguiu conectar ou inicializar
        retry_count += 1
        
        # Pergunta ao usuário se deseja tentar novamente
        if not show_emulator_closed_message():
            print("👋 Usuário optou por sair. Encerrando aplicação.")
            return 0
        
        # Se usuário quer tentar novamente mas já esgotou tentativas
        if retry_count >= max_retries:
            print(f"❌ Máximo de tentativas ({max_retries}) atingido. Encerrando aplicação.")
            return 1
    
    # Não deveria chegar aqui, mas por segurança
    return 1

def on_closing(root: tk.Tk, app=None) -> None:
    """
    Trata o fechamento da janela principal.
    
    Args:
        root: Objeto raiz do Tkinter
        app: Instância da aplicação HayDayTestApp
    """
    # Pergunta ao usuário se deseja realmente sair
    if tk.messagebox.askokcancel("Sair", "Deseja realmente sair da aplicação?"):
        # Notifica a aplicação para limpar recursos da UI
        if app is not None:
            try:
                app.on_close()
            except Exception as e:
                print(f"Erro ao fechar a aplicação: {e}")
        
        # Destroi a janela para encerrar o mainloop
        root.destroy()


# --- Funções de substituição do antigo adb_monitor.py ---
# Estas funções usam diretamente o ADBManager para evitar duplicação de código

def setup_adb_monitor_in_app(app):
    """
    Configura a verificação de status ADB para o aplicativo HayDayTestApp.
    
    Args:
        app: Instância da classe HayDayTestApp
    """
    # Adiciona atributo para rastrear status do emulador se não existir
    if not hasattr(app, 'emulator_connection_lost'):
        app.emulator_connection_lost = False
    
    # Faz uma verificação inicial do status
    # O resto das verificações será feito via botão na interface
    app.check_emulator_status()


def cleanup_adb_monitor_on_exit():
    """
    Limpa recursos relacionados ao ADB ao encerrar a aplicação.
    """
    # A thread de monitoramento não existe mais, então não precisamos pará-la
    # Esse método está mantido por compatibilidade com o código existente
    print("ADB: Liberando recursos")


def on_emulator_connected(app, device_serial):
    """
    Callback chamado quando o emulador é conectado/reconectado.
    """
    if not hasattr(app, 'root') or not app.root.winfo_exists():
        return  # Janela foi fechada
        
    # Executa operações na thread do Tkinter
    app.root.after(0, lambda: handle_emulator_connected(app, device_serial))


def handle_emulator_connected(app, device_serial):
    """
    Manipula o evento de conexão do emulador na thread da interface gráfica.
    """
    try:
        # Atualiza a interface para refletir a conexão
        app.emulator_connection_lost = False
        app.status_label.config(text="Conectado ✓", foreground="green")
        app.device_label.config(text=f"Dispositivo: {device_serial}")
        
        # Obtém a referência ao dispositivo
        app.connected_device = adb_manager.get_device()
    except Exception as e:
        print(f"Erro ao processar conexão do emulador: {e}")


def on_emulator_disconnected(app):
    """
    Callback chamado quando o emulador é desconectado.
    """
    # Agenda para execução na thread da interface
    if hasattr(app, 'root') and app.root.winfo_exists():
        app.root.after(0, lambda: handle_emulator_disconnected(app))


def handle_emulator_disconnected(app):
    """
    Manipula o evento de desconexão do emulador na thread da interface gráfica.
    """
    try:
        import winsound
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
    except Exception:
        pass  # Ignora erros de som
        
    app.emulator_connection_lost = True
    app.connected_device = None
    app.status_label.config(text="Desconectado ✗", foreground="red")
    app.device_label.config(text="Dispositivo: Nenhum")
