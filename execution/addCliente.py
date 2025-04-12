"""
Módulo para adicionar clientes no HayDay através de IDs.
"""

import json
import os
import time
from typing import Dict, List, Any, Optional

# Importa as funções de interação com o emulador
from cerebro.emulatorInteractFunction import click, wait, send_keys
from cerebro.state import get_current_state, get_current_state_id

# Cores para formatação de terminal
class Colors:
    GREEN = '\033[92m'      # Sucesso
    YELLOW = '\033[93m'     # Aviso/Processando
    RED = '\033[91m'        # Erro
    BLUE = '\033[94m'       # Info
    RESET = '\033[0m'       # Reset

# Caminho para o arquivo de configuração
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "addClienteCFG.json")

def load_config() -> Dict:
    """
    Carrega a configuração do arquivo JSON.
    
    Returns:
        Dict: Configuração carregada
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Colors.BLUE}[CLIENTE]{Colors.RESET} Configuração carregada: {CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
        return {}

def execute_action(action: Dict[str, Any], customer_id: str) -> bool:
    """
    Executa uma ação específica de acordo com o tipo.
    
    Args:
        action: Dicionário com informações da ação
        customer_id: ID do cliente a ser adicionado
    
    Returns:
        bool: True se a ação foi executada com sucesso, False caso contrário
    """
    try:
        action_type = action.get("type", "")
        params = action.get("params", [])
        description = action.get("description", "")
        
        print(f"{Colors.YELLOW}[CLIENTE] AÇÃO:{Colors.RESET} {description}")
        
        if action_type == "click":
            if len(params) >= 2:
                return click(params[0], params[1])
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação click")
                return False
                
        elif action_type == "wait":
            if len(params) >= 1:
                wait(params[0])
                return True
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação wait")
                return False
                
        elif action_type == "send_keys":
            if len(params) >= 1:
                # Substitui <customer_id> pelo valor real
                text = params[0].replace("<customer_id>", customer_id)
                return send_keys(text)
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação send_keys")
                return False
                
        elif action_type == "verify_state":
            if len(params) >= 2:
                expected_state = params[0]
                max_attempts = params[1]
                
                for attempt in range(max_attempts):
                    # Usamos get_current_state_id para comparar com os IDs internos
                    current_state_id = get_current_state_id()
                    current_state_display = get_current_state()
                    
                    # Comparamos diretamente com o ID do estado
                    if expected_state == current_state_id:
                        print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Estado verificado: {current_state_display} (ID: {current_state_id})")
                        return True
                        
                    print(f"{Colors.YELLOW}[CLIENTE] AGUARDANDO:{Colors.RESET} Estado '{expected_state}', atual: '{current_state_id}' ({current_state_display}) ({attempt+1}/{max_attempts})")
                    wait(0.5)  # Espera 500ms entre as verificações
                
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Estado {expected_state} não encontrado após {max_attempts} tentativas")
                return False
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação verify_state")
                return False
        
        else:
            print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao executar ação {action.get('type', 'desconhecida')}: {e}")
        return False

def add_client(customer_id: str) -> bool:
    """
    Adiciona um cliente utilizando sua tag/ID.
    
    Args:
        customer_id: ID do cliente a ser adicionado
    
    Returns:
        bool: True se o cliente foi adicionado com sucesso, False caso contrário
    """
    print(f"{Colors.BLUE}[CLIENTE] INICIANDO:{Colors.RESET} Adição de cliente '{customer_id}'")
    
    # Carrega a configuração
    config = load_config()
    if not config:
        return False
    
    # Verifica se a configuração para adicionar cliente existe
    if "addCliente" not in config:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Configuração 'addCliente' não encontrada")
        return False
    
    # Obtém a configuração de adição de cliente
    add_client_config = config["addCliente"]
    
    # Verifica o estado atual
    required_state = add_client_config.get("state", "")
    current_state_id = get_current_state_id()
    current_state_display = get_current_state()
    
    # Verifica se o estado atual é o esperado - comparando IDs diretamente
    if required_state and required_state != current_state_id:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Estado atual '{current_state_id}' ({current_state_display}) não corresponde ao esperado '{required_state}'")
        return False
    
    # Executa as ações configuradas
    actions = add_client_config.get("actions", [])
    for action in actions:
        success = execute_action(action, customer_id)
        if not success:
            print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
            return False
        
        # Pequena pausa entre ações
        wait(0.1)
    
    print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Cliente '{customer_id}' adicionado com sucesso!")
    return True

# Função para execução direta
def run(customer_id: Optional[str] = None) -> bool:
    """
    Função para execução direta do módulo.
    
    Args:
        customer_id: ID do cliente (opcional, será solicitado se não fornecido)
    
    Returns:
        bool: True se a operação foi concluída com sucesso
    """
    # Se não for fornecido um ID, usa um padrão
    if not customer_id:
        customer_id = "#TESTE123"
        print(f"{Colors.YELLOW}[CLIENTE] AVISO:{Colors.RESET} ID do cliente não fornecido, usando padrão: {customer_id}")
    
    return add_client(customer_id)

# Para execução direta
if __name__ == "__main__":
    run()
