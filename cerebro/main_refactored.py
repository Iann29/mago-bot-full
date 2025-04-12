# /cerebro/main_refactored.py
# Versão refatorada e modular do arquivo main.py original

import sys
import logging

# Importa configurações de log e sistema de logging
from utils.logger import setup_logging, get_logger, LogLevel, set_module_log_level, disable_module_logs
from utils.logging_config import GLOBAL_LOG_LEVEL, MODULE_LOG_LEVELS, DISABLED_MODULES, LOG_TO_FILE
from cerebro.app import start_app_with_auth

# Obter logger para o módulo principal
logger = get_logger('main')

def main():
    """Função principal de entrada do programa."""
    # Configura o sistema de logs com as configurações definidas
    # MODIFICAÇÃO: Adicionar redirect_output=True para redirecionar stdout e stderr
    setup_logging(console_level=GLOBAL_LOG_LEVEL, log_to_file=LOG_TO_FILE, redirect_output=True)
    
    # Configura os níveis de log para cada módulo
    for module, level in MODULE_LOG_LEVELS.items():
        set_module_log_level(module, level)
    
    # Desativa os logs para módulos específicos
    for module in DISABLED_MODULES:
        disable_module_logs(module)
    
    # Log de inicialização - usando terminal para mostrar mensagem importante
    logger.terminal("--- Iniciando HayDay Test Tool ---")
    
    try:
        # Inicia a aplicação com autenticação
        exit_code = start_app_with_auth()
        return exit_code
    except Exception as e:
        logger.error(f"Erro crítico na aplicação: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    # Executa a função principal e usa o código de saída retornado
    sys.exit(main())