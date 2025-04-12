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

def register_state_callback(callback: Callable[[GameState, GameState], None]) -> None:
    """
    Registra uma função de callback para mudanças de estado.
    
    Args:
        callback: Função a ser chamada quando ocorrer mudança de estado
    """
    global state_manager
    
    if state_manager:
        state_manager.register_state_change_callback(callback)
        print("🔔✅ Registro de callback de estado concluído.")
    else:
        print("⚠️ StateManager não inicializado. Inicialize antes de registrar callbacks.")

def get_current_state() -> GameState:
    """
    Retorna o estado atual do jogo.
    
    Returns:
        GameState: Estado atual ou UNKNOWN se não inicializado
    """
    if state_manager:
        return state_manager.current_state
    return GameState.UNKNOWN

def stop_state_monitoring() -> None:
    """Para o monitoramento de estados."""
    global state_manager
    
    if state_manager:
        state_manager.stop_monitoring()
        print("🔔⏹️ StateManager: Monitoramento de estados parado.")
