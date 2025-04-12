"""
Configurações do sistema de logging para o HayDay Bot.
Altere os níveis para controlar a quantidade de mensagens.
"""

from utils.logger import LogLevel

# Configuração global de logs
# Valores possíveis:
# - LogLevel.SILENT: Não mostra nenhum log
# - LogLevel.ERROR: Mostra apenas erros
# - LogLevel.WARNING: Mostra avisos e erros
# - LogLevel.INFO: Mostra informações, avisos e erros (recomendado para usuários)
# - LogLevel.DEBUG: Mostra todos os logs (para desenvolvimento)
# - LogLevel.VERBOSE: Mostra absolutamente tudo (para debug detalhado)

# Nível global de log para o console
GLOBAL_LOG_LEVEL = LogLevel.INFO

# Configurações específicas por módulo
# Valores podem ser diferentes do global para mostrar mais ou menos detalhes
MODULE_LOG_LEVELS = {
    # Core do aplicativo
    'main': LogLevel.INFO,
    'app': LogLevel.INFO,
    'capture': LogLevel.INFO,
    'state': LogLevel.INFO,
    
    # Infraestrutura
    'adb': LogLevel.WARNING,  # Reduz as mensagens do ADB (muitas mensagens de conexão)
    'transmitter': LogLevel.INFO,
    
    # Outros módulos
    'stateManager': LogLevel.WARNING,
    'templateMatcher': LogLevel.WARNING,
    'screenshotter': LogLevel.INFO,
    
    # Auth - evita mostrar informações sensíveis
    'auth': LogLevel.WARNING,
}

# Desabilitar completamente logs para certos módulos
# Adicione aqui nomes de módulos que você deseja silenciar completamente
DISABLED_MODULES = [
    # 'adb', # Descomente esta linha para desativar todos os logs do ADB
]

# Configurar para salvar logs em arquivo (além do console)
LOG_TO_FILE = True
