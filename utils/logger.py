"""
Módulo de gerenciamento de logs para o HayDay Bot.
Permite controlar o nível de detalhamento dos logs e formatação.
"""

import logging
import os
import sys
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, List, Union

# Criar diretório de logs se não existir
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configuração padrão
DEFAULT_LOG_LEVEL = logging.INFO
CONSOLE_FORMAT = "%(emoji)s %(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Dicionário para armazenar a configuração por módulo
module_log_levels: Dict[str, int] = {}

# Nível personalizado para mensagens que devem aparecer no terminal
TERMINAL_DEBUG = 25  # Entre INFO (20) e WARNING (30)
logging.addLevelName(TERMINAL_DEBUG, "TERMINAL")

# Enums para níveis de log com emojis
class LogEmoji(Enum):
    DEBUG = "🔍"
    INFO = "ℹ️"
    TERMINAL = "💻"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🔥"
    
    @classmethod
    def get(cls, level: int) -> str:
        if level == logging.DEBUG:
            return cls.DEBUG.value
        elif level == logging.INFO:
            return cls.INFO.value
        elif level == TERMINAL_DEBUG:
            return cls.TERMINAL.value
        elif level == logging.WARNING:
            return cls.WARNING.value
        elif level == logging.ERROR:
            return cls.ERROR.value
        elif level == logging.CRITICAL:
            return cls.CRITICAL.value
        return ""

# Formatter personalizado que adiciona emojis
class EmojiFormatter(logging.Formatter):
    def format(self, record):
        # Adiciona emoji ao record
        record.emoji = LogEmoji.get(record.levelno)
        return super().format(record)

# Importa configurações de mensagens para o terminal
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("terminal_config", 
                                            os.path.join(os.path.dirname(__file__), "terminal_config.py"))
terminal_config = importlib.util.module_from_spec(spec)
sys.modules["terminal_config"] = terminal_config
spec.loader.exec_module(terminal_config)

# Filtro personalizado para permitir apenas mensagens relacionadas a estado e transmissão de imagens
class TerminalFilter(logging.Filter):
    def filter(self, record):
        # Permite mensagens do nível TERMINAL_DEBUG no console
        if record.levelno >= TERMINAL_DEBUG:
            return True
            
        # Verifica o conteúdo da mensagem para mensagens de qualquer nível
        try:
            # Formata a mensagem antes de verificar os padrões
            message = self.format_message(record)
            # Verifica se a mensagem contém padrões relacionados a estado ou transmissão
            should_show = terminal_config.should_show_in_terminal(message)
            return should_show
        except Exception:
            # Em caso de erro, não mostra no terminal
            return False
                
        return False
    
    def format_message(self, record):
        """Formata a mensagem do record para verificação."""
        if isinstance(record.msg, str):
            return record.msg % record.args if record.args else record.msg
        return str(record.msg)

# Configuração global
def setup_logging(console_level: int = DEFAULT_LOG_LEVEL, 
                 file_level: int = logging.DEBUG,
                 log_to_file: bool = True) -> None:
    """
    Configura o sistema de logging global.
    
    Args:
        console_level: Nível de log para console (apenas para TERMINAL_DEBUG e superiores)
        file_level: Nível de log para arquivo
        log_to_file: Se True, salva logs em arquivo
    """
    # Configuração do root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Captura tudo, os handlers filtrarão
    
    # Remove handlers existentes para evitar duplicação
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler com formatador de emoji e filtro para mostrar apenas TERMINAL_DEBUG
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Permite todos os níveis, mas usamos filtro
    console_handler.addFilter(TerminalFilter())  # Aplica filtro para mostrar apenas TERMINAL_DEBUG ou superior
    console_formatter = EmojiFormatter(CONSOLE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (sempre ativado para capturar todos os logs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"hayday_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(FILE_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

# Função para obter logger de módulo
def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo especificado.
    
    Args:
        module_name: Nome do módulo para criar o logger
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(module_name)
    
    # Configura nível específico do módulo se existir
    if module_name in module_log_levels:
        logger.setLevel(module_log_levels[module_name])
    
    return logger

# Funções para logging no terminal
def terminal_debug(logger_name: str, message: str, *args, **kwargs) -> None:
    """
    Registra uma mensagem no nível TERMINAL_DEBUG.
    Esta mensagem aparecerá tanto no console quanto no arquivo de log.
    
    Args:
        logger_name: Nome do logger (módulo)
        message: Mensagem para registrar
        *args, **kwargs: Argumentos para formatar a mensagem
    """
    logger = logging.getLogger(logger_name)
    logger.log(TERMINAL_DEBUG, message, *args, **kwargs)

# Adicionamos o método terminal() a todos os loggers criados
class LoggerWithTerminal(logging.Logger):
    def terminal(self, msg, *args, **kwargs):
        if self.isEnabledFor(TERMINAL_DEBUG):
            self._log(TERMINAL_DEBUG, msg, args, **kwargs)

# Configura o novo tipo de logger
logging.setLoggerClass(LoggerWithTerminal)

# Funções para ajustar nível de log
def set_global_log_level(level: int) -> None:
    """Define o nível de log global para o console."""
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setLevel(level)

def set_module_log_level(module_name: str, level: int) -> None:
    """Define o nível de log para um módulo específico."""
    module_log_levels[module_name] = level
    logging.getLogger(module_name).setLevel(level)

def disable_module_logs(module_name: str) -> None:
    """Desativa logs para um módulo específico."""
    set_module_log_level(module_name, logging.CRITICAL + 1)

# Níveis de log pré-definidos
class LogLevel:
    SILENT = logging.CRITICAL + 1
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    TERMINAL = TERMINAL_DEBUG  # Nível personalizado para mensagens no terminal
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    VERBOSE = logging.DEBUG - 5  # Nível personalizado para logs muito detalhados

# Inicializa o sistema de logging
# Nota: A inicialização completa é feita ao importar o módulo
# A função setup_logging é chamada no main_refactored.py
