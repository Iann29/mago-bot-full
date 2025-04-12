# Regras de Logging para HayDay Bot

## Sistema de Logs

O HayDay Bot usa um sistema de logs em dois níveis:

1. **Logs em Arquivo**: Todas as mensagens de log (DEBUG, INFO, WARNING, ERROR, CRITICAL) são automaticamente salvas em arquivos dentro da pasta `logs/`.
   - Os arquivos têm formato `hayday_20250412_115342.log` (data e hora da execução)
   - Contêm informações detalhadas de todas as operações do sistema

2. **Logs no Terminal**: Por padrão, **nada é mostrado no terminal**. Para que uma mensagem apareça no terminal, deve-se usar especificamente `logger.terminal()`.

## Como usar

### Para logs que só aparecem em arquivo (maioria dos casos):

```python
# Obtém o logger para o módulo
logger = get_logger('nome_do_modulo')

# Logs normais - só aparecem no arquivo, não no terminal
logger.debug("Mensagem detalhada para depuração")
logger.info("Informação normal")
logger.warning("Aviso sobre algo incomum")
logger.error("Erro que ocorreu")
logger.critical("Erro crítico que pode derrubar o sistema")
```

### Para logs que devem aparecer no terminal:

```python
# Obtém o logger para o módulo
logger = get_logger('nome_do_modulo')

# Log que aparece tanto no arquivo quanto no terminal
logger.terminal("Mensagem importante para o usuário ver")

# OU usando a função auxiliar
from utils.logger import terminal_debug
terminal_debug('nome_do_modulo', "Mensagem importante para o usuário ver")
```

## Níveis de Log

- **DEBUG**: Informações detalhadas para debug (nível mais baixo)
- **INFO**: Informações gerais sobre o fluxo de execução
- **TERMINAL**: Mensagens que devem aparecer no terminal do usuário
- **WARNING**: Avisos sobre comportamentos incomuns
- **ERROR**: Erros que permitem que o programa continue
- **CRITICAL**: Erros críticos que podem encerrar o programa

## Configuração de Níveis de Log

Os níveis de log podem ser configurados no arquivo `utils/logging_config.py`:

- `GLOBAL_LOG_LEVEL`: Define o nível global mínimo para logs
- `MODULE_LOG_LEVELS`: Permite personalizar níveis por módulo
- `DISABLED_MODULES`: Lista de módulos onde os logs são completamente desativados

## Observações

- Os arquivos de log são automaticamente gerados na pasta `logs/`, que é ignorada pelo git
- Para ver logs de qualquer nível, consulte os arquivos de log
- Se você estiver procurando um log e não o encontrar no terminal, lembre-se de verificar os arquivos de log
