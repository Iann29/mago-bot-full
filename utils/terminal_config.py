"""
Configurações para determinar quais mensagens aparecem no terminal.
Este módulo garante que apenas as mensagens relacionadas a estados e transmissão
de imagens para VPS aparecerão no terminal.
"""

# Abordagem negativa para filtragem: bloqueie tudo exceto o que é explicitamente permitido

# MODIFICAÇÃO: Lista muito mais restrita de padrões permitidos
TERMINAL_MESSAGE_PATTERNS = [
    # APENAS as mensagens mais essenciais
    "Iniciando HayDay Test Tool",
    "Usuário autenticado com sucesso",
    "Thread de captura iniciada"
]

# Para ignorar explicitamente mensagens mesmo que contenham padrões acima
# MODIFICAÇÃO: Lista mais abrangente de padrões a ignorar
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
    "inicializando",
    "aguardando",
    "limpando",
    "liberando",
    "daemons",
    "Status",
    "estado",
    "Estado",
    "Debug",
    "debug",
    "template",
    "Template",
    "encontrado",
    "Erro",
    "erro",
    "falha",
    "Falha"
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
    # MODIFICAÇÃO: Por padrão, retorna False para quase tudo
    # Primeiro verifica se a mensagem contém algum padrão a ser ignorado
    if any(ignore_pattern in message for ignore_pattern in IGNORE_PATTERNS):
        return False
        
    # Depois verifica se a mensagem contém algum padrão permitido
    return any(pattern in message for pattern in TERMINAL_MESSAGE_PATTERNS)