"""
Configurações para determinar quais mensagens aparecem no terminal.
Este módulo garante que apenas as mensagens relacionadas a estados e transmissão
de imagens para VPS aparecerão no terminal.
"""

# Abordagem negativa para filtragem: bloqueie tudo exceto o que é explicitamente permitido

# Lista EXATA de padrões que podem aparecer no terminal
# APENAS as mensagens que contêm exatamente estes padrões aparecerão no terminal
TERMINAL_MESSAGE_PATTERNS = [
    # APENAS mensagens de estado
    "Estado alterado:",
    "→ Mobile Home",
    "→ Unknown",
    
    # APENAS mensagens de transmissão de imagens para VPS
    "Status: ",
    "imagens enviadas",
    "imagens transmitidas"
]

# Para ignorar explicitamente mensagens mesmo que contenham padrões acima
# Útil para filtrar mensagens que contêm padrões desejados mas não são as mensagens alvo
IGNORE_PATTERNS = [
    "ADB",
    "Conectando",
    "conectado",
    "Transmissor",
    "Thread",
    "encerrar",
    "configurado",
    "TemplateMatcher",
    "inicializado",
    "StateManager",
    "Callback",
    "registrado",
    "inicializando",
    "aguardando",
    "limpando",
    "liberando",
    "daemons"
]

# Funções de verificação
def should_show_in_terminal(message: str) -> bool:
    """
    Verifica se uma mensagem deve ser exibida no terminal.
    
    Args:
        message: A mensagem a ser verificada
        
    Returns:
        True se a mensagem deve ser exibida no terminal, False caso contrário
    """
    # Primeiro verifica se a mensagem contém algum padrão a ser ignorado
    if any(ignore_pattern in message for ignore_pattern in IGNORE_PATTERNS):
        return False
        
    # Depois verifica se a mensagem contém algum padrão permitido
    return any(pattern in message for pattern in TERMINAL_MESSAGE_PATTERNS)
