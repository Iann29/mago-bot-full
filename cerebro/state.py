# /cerebro/state.py
# Módulo para gerenciamento de estados do jogo

import threading
from typing import Optional, List, Callable

from stateManager import StateManager, GameState
from cerebro.capture import screenshot_queue

# Variável global para o gerenciador de estados
state_manager: Optional[StateManager] = None

def initialize_state_manager() -> StateManager:
    """
    Inicializa o gerenciador de estados e inicia o monitoramento.
    
    Returns:
        StateManager: Instância do gerenciador de estados
    """
    global state_manager
    
    # Cria uma nova instância se não existir
    if state_manager is None:
        # Inicializa o state manager com valores padrão
        state_manager = StateManager(check_interval=0.5, verbose=False)
        print("🔔✅ StateManager inicializado e monitoramento iniciado.")
    
    # Inicia o monitoramento da fila de screenshots
    state_manager.start_monitoring(screenshot_queue)
    
    return state_manager

def register_state_callback(callback: Callable[[str, str], None]) -> None:
    """
    Registra uma função de callback para mudanças de estado.
    
    Args:
        callback: Função a ser chamada quando ocorrer mudança de estado
    """
    global state_manager
    
    if state_manager:
        # Criamos um wrapper que converte os state_ids para display_names
        def state_callback_wrapper(prev_state_id: str, new_state_id: str):
            # Obtemos o nome amigável para exibição em vez do ID
            if state_manager.state_configs and new_state_id in state_manager.state_configs:
                new_state_display = state_manager.state_configs[new_state_id].display_name
            else:
                new_state_display = new_state_id.replace('_', ' ').title()
                
            if state_manager.state_configs and prev_state_id in state_manager.state_configs:
                prev_state_display = state_manager.state_configs[prev_state_id].display_name
            else:
                prev_state_display = prev_state_id.replace('_', ' ').title()
            
            # Chama o callback original passando os nomes amigáveis
            callback(prev_state_display, new_state_display)
            
        state_manager.register_state_change_callback(state_callback_wrapper)
        print("🔔✅ Registro de callback de estado concluído.")
    else:
        print("⚠️ StateManager não inicializado. Inicialize antes de registrar callbacks.")

def get_current_state() -> str:
    """
    Retorna o estado atual do jogo.
    
    Returns:
        str: Nome amigável (display_name) do estado atual ou "Desconhecido" se não inicializado
    """
    if state_manager:
        current_state_id = state_manager.current_state
        # Verifica se o estado atual tem um nome amigável para exibição
        if state_manager.state_configs and current_state_id in state_manager.state_configs:
            return state_manager.state_configs[current_state_id].display_name
        else:
            # Formata o ID do estado para exibição
            return current_state_id.replace('_', ' ').title()
    return "Desconhecido"

def stop_state_monitoring() -> None:
    """Para o monitoramento de estados."""
    global state_manager
    
    if state_manager:
        state_manager.stop_monitoring()
        print("🔔⏹️ StateManager: Monitoramento de estados parado.")
