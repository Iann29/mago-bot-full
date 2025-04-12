# stateManager/__init__.py
# Exporta as classes e funções principais para facilitar a importação

from enum import Enum, auto

# Definindo GameState novamente como enum para compatibilidade com código existente
class GameState(Enum):
    """Enum para manter compatibilidade com código existente"""
    UNKNOWN = auto()        # Estado desconhecido
    MOBILE_HOME = auto()    # Tela principal do android
    HAYDAY_APP_ICON = auto() # Ícone do HayDay
    
    def __str__(self):
        return self.name.replace('_', ' ').title()

# Importando StateManager após definir GameState para evitar problemas de importação circular
from .stateManager import StateManager, UNKNOWN_STATE

__all__ = ['StateManager', 'GameState', 'UNKNOWN_STATE']
