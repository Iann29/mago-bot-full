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

from adb_monitor import setup_adb_monitor_in_app, cleanup_adb_monitor_on_exit
from thread_terminator import wait_for_thread_termination, terminate_all_daemon_threads
from auth.login_ui import start_login_window
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
    print("💻🔒 MAIN: Aplicativo está sendo fechado...")
    
    # Limpa o monitor ADB
    cleanup_adb_monitor_on_exit()
    print("💻⏹️ MAIN: Monitoramento de conexão ADB encerrado.")
    
    # Para o monitoramento de estados
    print("💻⏹️ MAIN: Parando monitoramento de estados...")
    stop_state_monitoring()
    
    # Para a interface gráfica (se houver)
    print("💻🚫 MAIN: Interface encerrada.")
    
    # Sinaliza para a thread de captura parar
    print("💻⛔ MAIN: Sinalizando para thread de captura parar...")
    stop_screenshot_capture()
    
    # Para o monitoramento de estados (redundante mas seguro)
    print("💻⏹️ MAIN: Parando monitoramento de estados...")
    
    # Aguarda a thread de captura encerrar
    print("💻⏸️ MAIN: Aguardando a thread de captura encerrar...")
    if capture_thread and capture_thread.is_alive():
        wait_for_thread_termination(capture_thread, timeout=2.0)
    
    # Finaliza threads daemon remanescentes
    terminate_all_daemon_threads()
    
    print("💻✨ MAIN: Programa encerrado.")

def start_app_with_auth():
    """
    Inicia a aplicação com autenticação.
    
    Returns:
        int: Código de saída da aplicação (0 para sucesso)
    """
    # Mostra janela de login e aguarda autenticação
    print("🌟--- Iniciando HayDay Test Tool ---🌟")
    print("🔐 Iniciando autenticação...")
    
    # Invoca o sistema de autenticação
    user_data = start_login_window()
    
    # Se autenticação falhou, encerra
    if not user_data:
        print("❌ Autenticação falhou. Encerrando aplicação.")
        return 1
    
    # Autenticação bem-sucedida, continua com a aplicação
    print(f"✅ Usuário {user_data['username']} autenticado com sucesso!")
    
    # Inicia a aplicação principal
    return run_main_app(user_data)

def run_main_app(user_data: Dict[str, Any]) -> int:
    """
    Executa a aplicação principal após autenticação bem-sucedida.
    
    Args:
        user_data: Dados do usuário autenticado
        
    Returns:
        int: Código de saída da aplicação (0 para sucesso)
    """
    # Exibe configurações
    print(f"⚙️ Configurações: FPS={TARGET_FPS} (do screenshotCFG.json)")
    
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
                        # Identifica o usuário para transmissão
                        username = user_data.get('html_id', user_data.get('username', ''))
                        print(f"💻📁 Identificador de tela para transmissão: {username}")
                        
                        # Inicia a thread de captura com username
                        start_screenshot_capture(TARGET_FPS, device, username)
                        
                        # Cria a interface gráfica
                        root = tk.Tk()
                        app = HayDayTestApp(root, user_data)
                        
                        # Configuração do monitor ADB - deve ser feita APÓS criar a app
                        setup_adb_monitor_in_app(app)
                        
                        # Configura o callback de fechamento
                        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
                        
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

def on_closing(root: tk.Tk) -> None:
    """
    Trata o fechamento da janela principal.
    
    Args:
        root: Objeto raiz do Tkinter
    """
    # Pergunta ao usuário se deseja realmente sair
    if tk.messagebox.askokcancel("Sair", "Deseja realmente sair da aplicação?"):
        # Destroi a janela para encerrar o mainloop
        root.destroy()
