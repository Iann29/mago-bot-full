from typing import Optional, Callable, Dict

from stateManager import StateManager
from cerebro.capture import screenshot_queue

state_manager: Optional[StateManager] = None

# Dicionário para manter rastreamento dos callbacks e seus wrappers
_callback_wrappers: Dict[Callable, Callable] = {}

def initialize_state_manager() -> StateManager:
    global state_manager
    
    if state_manager is None:
        state_manager = StateManager(check_interval=0.5, verbose=False)
        print("🔔✅ StateManager inicializado e monitoramento iniciado.")
    
    state_manager.start_monitoring(screenshot_queue)
    
    return state_manager

def register_state_callback(callback: Callable[[str, str], None]) -> None:
    global state_manager, _callback_wrappers
    
    if state_manager:
        # Se callback for None, não faz nada (não registra None como callback)
        if callback is None:
            print("⚠️ Tentativa de registrar callback None detectada. Use unregister_state_callback() para remover callbacks.")
            return
            
        def state_callback_wrapper(prev_state_id: str, new_state_id: str):
            if state_manager.state_configs and new_state_id in state_manager.state_configs:
                new_state_display = state_manager.state_configs[new_state_id].display_name
            else:
                new_state_display = new_state_id.replace('_', ' ').title()
                
            if state_manager.state_configs and prev_state_id in state_manager.state_configs:
                prev_state_display = state_manager.state_configs[prev_state_id].display_name
            else:
                prev_state_display = prev_state_id.replace('_', ' ').title()
            
            callback(prev_state_display, new_state_display)
        
        # Armazena o wrapper para poder removê-lo depois
        _callback_wrappers[callback] = state_callback_wrapper
            
        state_manager.register_state_change_callback(state_callback_wrapper)
        print("🔔✅ Registro de callback de estado concluído.")
    else:
        print("⚠️ StateManager não inicializado. Inicialize antes de registrar callbacks.")

def unregister_state_callback(callback: Callable[[str, str], None]) -> None:
    """Remove um callback de estado previamente registrado."""
    global state_manager, _callback_wrappers
    
    if state_manager and callback in _callback_wrappers:
        wrapper = _callback_wrappers[callback]
        state_manager.unregister_state_change_callback(wrapper)
        _callback_wrappers.pop(callback)  # Remove do dicionário
        print("🔔✅ Callback de estado removido com sucesso.")
    else:
        print("⚠️ Callback não encontrado ou StateManager não inicializado.")

def get_current_state() -> str:
    if state_manager:
        current_state_id = state_manager.current_state
        if state_manager.state_configs and current_state_id in state_manager.state_configs:
            return state_manager.state_configs[current_state_id].display_name
        else:
            return current_state_id.replace('_', ' ').title()
    return "Desconhecido"

def get_current_state_id() -> str:
    if state_manager:
        return state_manager.current_state
    return "unknown"

def stop_state_monitoring() -> None:
    global state_manager
    
    if state_manager:
        state_manager.stop_monitoring()
        print("🔔⏹️ StateManager: Monitoramento de estados parado.")