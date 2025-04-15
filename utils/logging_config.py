"""
Configurações do sistema de logging para o HayDay Bot.
Altere os níveis para controlar a quantidade de mensagens.
"""

from utils.logger import LogLevel

# Configuração global de logs
# MODIFICAÇÃO: Ajustar para mostrar todos os níveis de log no console
GLOBAL_LOG_LEVEL = LogLevel.DEBUG  # Mostra todos os níveis de log no console

# Configurações específicas por módulo
# MODIFICAÇÃO: Ajustar níveis para reduzir o volume de logs
MODULE_LOG_LEVELS = {
    # Core do aplicativo
    'main': LogLevel.INFO,
    'app': LogLevel.INFO,
    'capture': LogLevel.INFO,
    'state': LogLevel.INFO,
    
    # Infraestrutura
    'adb': LogLevel.WARNING,  # Reduz as mensagens do ADB (muitas mensagens de conexão)
    'transmitter': LogLevel.WARNING,  # Aumentado para WARNING
    
    # Outros módulos - todos aumentados para WARNING ou ERROR
    'stateManager': LogLevel.ERROR,
    'templateMatcher': LogLevel.ERROR,
    'screenshotter': LogLevel.WARNING,
    
    # Auth - evita mostrar informações sensíveis
    'auth': LogLevel.ERROR,
}

# Módulos com log desativado
# MODIFICAÇÃO: Reduzir a lista para mostrar mais logs no console
DISABLED_MODULES = [
    # Removido a maioria dos módulos desativados para permitir que os logs apareçam no console
]

# Configurar para salvar logs em arquivo (além do console)
LOG_TO_FILE = True
