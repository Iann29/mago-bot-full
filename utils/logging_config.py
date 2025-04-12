"""
Configurações do sistema de logging para o HayDay Bot.
Altere os níveis para controlar a quantidade de mensagens.
"""

from utils.logger import LogLevel

# Configuração global de logs
# MODIFICAÇÃO: Ajustar para mostrar apenas TERMINAL e superiores
GLOBAL_LOG_LEVEL = LogLevel.TERMINAL  # Mostra apenas TERMINAL ou superior no console

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

# Desabilitar completamente logs para certos módulos
# MODIFICAÇÃO: Adicionar mais módulos para desativar completamente
DISABLED_MODULES = [
    'adb',  # Desativa todos os logs do ADB
    'screenshotter',  # Desativa logs do Screenshotter
    'templateMatcher',  # Desativa logs do TemplateMatcher
]

# Configurar para salvar logs em arquivo (além do console)
LOG_TO_FILE = True
