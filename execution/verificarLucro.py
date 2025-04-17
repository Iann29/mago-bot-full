"""
Módulo para verificar o lucro da conta no HayDay.
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
from screenVision.maskedTemplateMatcher import MaskedTemplateMatcher

# Cores para formatação de terminal
class Colors:
    GREEN = '\033[92m'      # Sucesso
    YELLOW = '\033[93m'     # Aviso/Processando
    RED = '\033[91m'        # Erro
    BLUE = '\033[94m'       # Info
    RESET = '\033[0m'       # Reset

# Caminho para o arquivo de configuração
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verificarLucroCFG.json")

def load_config() -> Dict:
    """
    Carrega a configuração do arquivo JSON.
    
    Returns:
        Dict: Configuração carregada
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Colors.BLUE}[LUCRO]{Colors.RESET} Configuração carregada: {CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
        return {}

def execute_action(action: Dict[str, Any]) -> bool:
    """
    Executa uma ação específica de acordo com o tipo.
    
    Args:
        action: Dicionário com informações da ação
    
    Returns:
        bool: True se a ação foi executada com sucesso, False caso contrário
    """
    try:
        action_type = action.get("type", "")
        params = action.get("params", [])
        description = action.get("description", "")
        
        print(f"{Colors.YELLOW}[LUCRO] AÇÃO:{Colors.RESET} {description}")
        
        if action_type == "click":
            if len(params) >= 2:
                return click(params[0], params[1])
            else:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação click")
                return False
                
        elif action_type == "wait":
            if len(params) >= 1:
                wait(params[0])
                return True
            else:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação wait")
                return False
                
        elif action_type == "send_keys":
            if len(params) >= 1:
                return send_keys(params[0])
            else:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação send_keys")
                return False
        
        elif action_type == "searchTemplate":
            if len(params) >= 2:
                template_path = params[0]
                roi = params[1] if len(params) >= 2 else None
                max_attempts = int(action.get("attempts", 2))
                threshold = float(action.get("threshold", 0.8))
                use_mask = action.get("useMask", False)
                
                if use_mask:
                    return search_masked_template(template_path, roi, max_attempts, threshold)
                else:
                    return search_template(template_path, roi, max_attempts, threshold)
            else:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação searchTemplate")
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
                        print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Estado verificado: {current_state_display} (ID: {current_state_id})")
                        return True
                        
                    print(f"{Colors.YELLOW}[LUCRO] AGUARDANDO:{Colors.RESET} Estado '{expected_state}', atual: '{current_state_id}' ({current_state_display}) ({attempt+1}/{max_attempts})")
                    wait(0.5)  # Espera 500ms entre as verificações
                
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Estado {expected_state} não encontrado após {max_attempts} tentativas")
                return False
            else:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação verify_state")
                return False
        
        else:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao executar ação {action.get('type', 'desconhecida')}: {e}")
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
    
    print(f"{Colors.YELLOW}[LUCRO] BUSCANDO:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
    
    for attempt in range(max_attempts):
        try:
            # Captura uma nova screenshot diretamente (formato OpenCV - BGR)
            print(f"{Colors.YELLOW}[LUCRO] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template")
            screenshot_cv = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot_cv is None:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao capturar screenshot")
                wait(0.5)  # Pequena pausa antes da próxima tentativa
                continue
            
            # Busca o template na screenshot capturada
            result = template_matcher.find_template(screenshot_cv, template_path, roi_tuple, threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Template encontrado na posição {position} (confiança: {confidence:.4f})")
                
                # Realiza um clique na posição onde o template foi encontrado
                click(position[0], position[1])
                return True
            
            print(f"{Colors.YELLOW}[LUCRO] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Template não encontrado")
        except Exception as e:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao processar screenshot: {e}")
        
        wait(0.5)  # Pequena pausa antes da próxima tentativa
    
    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Template não encontrado após {max_attempts} tentativas")
    return False

def search_masked_template(template_path: str, roi: List[int], max_attempts: int = 2, threshold: float = 0.8) -> bool:
    """
    Busca um template na tela atual utilizando máscara e verifica se ele foi encontrado.
    
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
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cria uma instância do Screenshotter para capturar screenshots diretamente
    screenshotter = Screenshotter()
    
    # Garante que o caminho é absoluto
    if not os.path.isabs(template_path):
        template_path = os.path.join(project_root, template_path)
    
    # Gera o caminho da máscara adicionando "mask" ao final do nome do arquivo
    mask_path = template_path.replace('.png', 'mask.png')
    
    # Converte a ROI para o formato esperado
    roi_tuple = tuple(roi) if roi else None
    
    print(f"{Colors.YELLOW}[LUCRO] BUSCANDO COM MÁSCARA:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
    print(f"{Colors.YELLOW}[LUCRO] MÁSCARA:{Colors.RESET} '{os.path.basename(mask_path)}'")
    
    # Cria uma instância do MaskedTemplateMatcher
    masked_matcher = MaskedTemplateMatcher(default_threshold=threshold, verbose=True)
    
    for attempt in range(max_attempts):
        try:
            # Captura uma nova screenshot diretamente (formato OpenCV - BGR)
            print(f"{Colors.YELLOW}[LUCRO] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template com máscara")
            screenshot_cv = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot_cv is None:
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao capturar screenshot")
                wait(0.5)  # Pequena pausa antes da próxima tentativa
                continue
            
            # Busca o template com máscara na screenshot capturada
            result = masked_matcher.find_template(
                screenshot_cv, 
                template_path, 
                mask_path, 
                roi_tuple, 
                threshold
            )
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Template com máscara encontrado na posição {position} (confiança: {confidence:.4f})")
                
                # Realiza um clique na posição onde o template foi encontrado
                click(position[0], position[1])
                return True
            
            print(f"{Colors.YELLOW}[LUCRO] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Template com máscara não encontrado")
        except Exception as e:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao processar screenshot com máscara: {e}")
        
        wait(0.5)  # Pequena pausa antes da próxima tentativa
    
    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Template com máscara não encontrado após {max_attempts} tentativas")
    return False

def verificar_lucro() -> bool:
    """
    Verifica o lucro da conta no HayDay.
    
    Returns:
        bool: True se a operação foi concluída com sucesso, False caso contrário
    """
    try:
        # Carrega a configuração
        config = load_config()
        if not config:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Configuração não encontrada ou inválida")
            return False
            
        # Obtém a configuração específica para o módulo
        verificar_lucro_config = config.get("verificarLucro", {})
        if not verificar_lucro_config:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Configuração para 'verificarLucro' não encontrada")
            return False
            
        # Obtém os estados configurados
        states_config = verificar_lucro_config.get("states", {})
        if not states_config:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Configuração de estados não encontrada")
            return False
            
        # Obtém o estado atual
        current_state_id = get_current_state_id()
        current_state = get_current_state()
        
        print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Estado atual: {current_state} (ID: {current_state_id})")
        
        # Verifica se há uma configuração para o estado atual
        if current_state_id in states_config:
            state_actions = states_config[current_state_id].get("actions", [])
            
            if not state_actions:
                print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} Nenhuma ação definida para o estado '{current_state}'")
                return False
                
            print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Executando {len(state_actions)} ações para o estado '{current_state}'")
            
            # Executa cada ação configurada para o estado atual
            for i, action in enumerate(state_actions):
                print(f"{Colors.BLUE}[LUCRO] AÇÃO {i+1}/{len(state_actions)}:{Colors.RESET} {action.get('description', 'Sem descrição')}")
                
                if not execute_action(action):
                    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao executar ação {i+1}")
                    return False
                    
            print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Verificação de lucro concluída com sucesso")
            return True
        else:
            print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} Não há configuração para o estado atual '{current_state}' (ID: {current_state_id})")
            states_available = list(states_config.keys())
            print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Estados configurados disponíveis: {states_available}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha geral na verificação de lucro: {e}")
        return False

def run() -> bool:
    """
    Função para execução direta do módulo.
    
    Returns:
        bool: True se a operação foi concluída com sucesso
    """
    print(f"\n{Colors.BLUE}======= VERIFICAÇÃO DE LUCRO =======\n{Colors.RESET}")
    
    try:
        # Executa a verificação de lucro
        if verificar_lucro():
            print(f"\n{Colors.GREEN}[LUCRO] OPERAÇÃO CONCLUÍDA:{Colors.RESET} Verificação de lucro realizada com sucesso!")
            return True
        else:
            print(f"\n{Colors.RED}[LUCRO] OPERAÇÃO FALHOU:{Colors.RESET} Não foi possível verificar o lucro.")
            return False
    except Exception as e:
        print(f"\n{Colors.RED}[LUCRO] ERRO FATAL:{Colors.RESET} {e}")
        return False

# Para execução direta
if __name__ == "__main__":
    run()
