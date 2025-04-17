"""
Módulo para adicionar clientes no HayDay através de IDs.
"""

import json
import os
import time
import cv2
import numpy as np
import queue
from typing import Dict, List, Any, Optional, Tuple

# Importa as funções de interação com o emulador
from cerebro.emulatorInteractFunction import click, wait, send_keys
from cerebro.state import get_current_state, get_current_state_id
from cerebro.capture import screenshot_queue
from screenVision.templateMatcher import TemplateMatcher

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
        
        elif action_type == "searchTemplate":
            if len(params) >= 2:
                template_path = params[0]
                roi = params[1] if len(params) >= 2 else None
                max_attempts = int(action.get("attempts", 2))
                threshold = float(action.get("threshold", 0.8))
                
                return search_template(template_path, roi, max_attempts, threshold)
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação searchTemplate")
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
                
        elif action_type == "check_multiple_states":
            if len(params) >= 2:
                expected_states = params  # Lista de estados a verificar
                max_attempts = int(action.get("attempts", 5))  # Padrão: 5 tentativas
                wait_time = float(action.get("wait_time", 0.5))  # Padrão: 500ms entre tentativas
                
                print(f"{Colors.BLUE}[CLIENTE] INFO:{Colors.RESET} Verificando múltiplos estados possíveis: {expected_states}")
                
                # Fazemos várias tentativas para pegar um estado válido
                for attempt in range(max_attempts):
                    # Obtemos o estado atual
                    current_state_id = get_current_state_id()
                    current_state_display = get_current_state()
                    
                    print(f"{Colors.BLUE}[CLIENTE] INFO:{Colors.RESET} Estado atual: {current_state_display} (ID: {current_state_id}) - Tentativa {attempt+1}/{max_attempts}")
                    
                    # Se o estado for 'unknown', esperamos e tentamos novamente
                    if current_state_id == "unknown":
                        print(f"{Colors.YELLOW}[CLIENTE] AGUARDANDO:{Colors.RESET} Estado em transição (unknown), aguardando...")
                        wait(wait_time)
                        continue
                    
                    # Verificamos se o estado atual é um dos esperados
                    if current_state_id in expected_states:
                        print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Estado atual {current_state_id} está entre os esperados")
                        
                        # Retornamos o estado como uma string extra para informar ao chamador qual estado foi encontrado
                        # Este valor será utilizado no add_client para saber qual estado executar em seguida
                        return (True, current_state_id)
                    
                    # Se não é unknown nem um dos esperados, esperamos um pouco e tentamos novamente
                    print(f"{Colors.YELLOW}[CLIENTE] AGUARDANDO:{Colors.RESET} Estado atual {current_state_id} não é um dos esperados {expected_states}")
                    wait(wait_time)
                
                # Se chegamos aqui, não encontramos um estado válido após todas as tentativas
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Estado válido não encontrado após {max_attempts} tentativas")
                return (False, None)
            else:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Parâmetros insuficientes para ação check_multiple_states")
                return False
        
        else:
            print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao executar ação {action.get('type', 'desconhecida')}: {e}")
        return False

def search_template(template_path: str, roi: List[int], max_attempts: int = 2, threshold: float = 0.8) -> bool:
    """
    Busca um template na tela atual e verifica se ele foi encontrado.
    
    Args:
        template_path: Caminho para a imagem do template
        roi: Região de interesse [x, y, w, h] onde procurar o template
        max_attempts: Número máximo de tentativas
        threshold: Limiar de confiança para considerar que o template foi encontrado
    
    Returns:
        bool: True se o template foi encontrado, False caso contrário
    """
    # Importa aqui para evitar importação circular
    from screenVision.screenshotMain import Screenshotter
    
    template_matcher = TemplateMatcher(default_threshold=threshold)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cria uma instância do Screenshotter para capturar screenshots diretamente
    screenshotter = Screenshotter()
    
    # Garante que o caminho é absoluto
    if not os.path.isabs(template_path):
        template_path = os.path.join(project_root, template_path)
    
    # Converte a ROI para o formato esperado pelo template_matcher
    roi_tuple = tuple(roi) if roi else None
    
    print(f"{Colors.YELLOW}[CLIENTE] BUSCANDO:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
    
    for attempt in range(max_attempts):
        try:
            # Captura uma nova screenshot diretamente (formato OpenCV - BGR)
            print(f"{Colors.YELLOW}[CLIENTE] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template")
            screenshot_cv = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot_cv is None:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao capturar screenshot")
                wait(0.5)  # Pequena pausa antes da próxima tentativa
                continue
            
            # Busca o template na screenshot capturada
            result = template_matcher.find_template(screenshot_cv, template_path, roi_tuple, threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Template encontrado na posição {position} (confiança: {confidence:.4f})")
                return True
            
            print(f"{Colors.YELLOW}[CLIENTE] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Template não encontrado")
        except Exception as e:
            print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao processar screenshot: {e}")
        
        wait(0.5)  # Pequena pausa antes da próxima tentativa
    
    print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Template não encontrado após {max_attempts} tentativas")
    return False

def add_client(customer_id: str) -> bool:
    """
    Adiciona um cliente utilizando sua tag/ID.
    
    Args:
        customer_id: ID do cliente a ser adicionado
    
    Returns:
        bool: True se o cliente foi adicionado com sucesso, False caso contrário
    """
    try:
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
        
        # Verifica se a estrutura "states" existe na configuração
        if "states" not in add_client_config:
            print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Configuração de estados não encontrada")
            return False
            
        # Iniciar o processamento a partir do estado atual
        current_state_id = get_current_state_id()
        
        # Loop principal de processamento de estados
        # Permite que possamos navegar entre diferentes estados conforme necessário
        while True:
            # Atualiza o estado atual (pode ter mudado durante a execução)
            current_state_id = get_current_state_id()
            current_state_display = get_current_state()
            print(f"{Colors.BLUE}[CLIENTE] INFO:{Colors.RESET} Estado atual: '{current_state_display}' (ID: {current_state_id})")
            
            # Verifica se o estado atual está definido na configuração
            if current_state_id not in add_client_config['states']:
                print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Estado {current_state_id} não está configurado para adição de cliente")
                return False
                
            # Executa as ações definidas para o estado atual
            actions = add_client_config['states'][current_state_id]['actions']
            next_state = None
            
            for i, action in enumerate(actions):
                # Executa a ação
                result = execute_action(action, customer_id)
                
                # Verifica se a ação retornou uma tupla (caso de check_multiple_states)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, next_state = result
                    if not success:
                        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
                        return False
                    print(f"{Colors.BLUE}[CLIENTE] INFO:{Colors.RESET} Redirecionando para o estado: {next_state}")
                    break  # Sai do loop de ações para processar o próximo estado
                elif not result:
                    print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
                    return False
            
            # Se temos um próximo estado definido, vamos para ele
            if next_state:
                # Verificamos se é um dos estados finais (sucesso/conclusão)
                if next_state in ['jogo_aberto', 'book_interface']:
                    print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Cliente {customer_id} processado com sucesso!")
                    # Passa para o próximo estado
                    current_state_id = next_state
                    continue
                # Caso contrário, atualiza o estado atual e continua o processamento
                current_state_id = next_state
                continue
            else:
                # Se não temos um próximo estado e concluímos todas as ações, terminamos com sucesso
                break
        
        print(f"{Colors.GREEN}[CLIENTE] SUCESSO:{Colors.RESET} Cliente {customer_id} adicionado com sucesso!")
        return True
            
    except Exception as e:
        print(f"{Colors.RED}[CLIENTE] ERRO:{Colors.RESET} Falha ao adicionar cliente: {e}")
        return False

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
