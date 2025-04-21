"""
Kit Celeiro - Módulo de automação para operações relacionadas ao celeiro no HayDay.
"""

import json
import os
import time
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union

# Importações de módulos internos
from cerebro.emulatorInteractFunction import click, wait, send_keys
from cerebro.state import get_current_state, get_current_state_id, register_state_callback, unregister_state_callback
from cerebro.kit_manager import process_kit
from screenVision.screenshotMain import Screenshotter
from screenVision.templateMatcher import TemplateMatcher
from screenVision.maskedTemplateMatcher import MaskedTemplateMatcher

# Cores para formatação de terminal
class Colors:
    GREEN = '\033[92m'      # Sucesso
    YELLOW = '\033[93m'     # Aviso/Processando
    RED = '\033[91m'        # Erro
    BLUE = '\033[94m'       # Info
    RESET = '\033[0m'       # Reset

# Caminhos para os arquivos de configuração
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_celeiroCFG.json")
ITEMS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_celeiro_items.json")

# Controle global de estado
state_changed_flag = False
last_detected_state_id = ""
pending_restart = False

def load_config() -> Dict:
    """
    Carrega a configuração do arquivo JSON.

    Returns:
        Dict: Configuração carregada
    """
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Colors.BLUE}[CELEIRO]{Colors.RESET} Configuração carregada: {CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
        return {}
        
def load_items_config() -> Dict:
    """
    Carrega a configuração de itens do kit Celeiro.

    Returns:
        Dict: Configuração de itens carregada
    """
    try:
        with open(ITEMS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Colors.BLUE}[CELEIRO]{Colors.RESET} Configuração de itens carregada: {ITEMS_CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao carregar configuração de itens: {e}")
        return {}

def on_state_change_during_execution(previous_state: str, new_state_name: str) -> None:
    """
    Callback para monitorar mudanças de estado durante a execução.

    Args:
        previous_state: Estado anterior
        new_state_name: Novo estado detectado
    """
    global state_changed_flag, last_detected_state_id, pending_restart

    last_detected_state_id = get_current_state_id()
    state_changed_flag = True

    if last_detected_state_id == "aba_tutorial_colher":
        print(f"{Colors.YELLOW}[CELEIRO] AVISO:{Colors.RESET} Tutorial popup detectado, reiniciando execução...")
        pending_restart = True
    else:
        print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Estado alterado: {previous_state} -> {new_state_name} (ID: {last_detected_state_id})")

def scan_empty_boxes(template_path: str, threshold: float = 0.85) -> List[int]:
    """
    Verifica quais caixas da loja estão vazias usando template matching.
    Também verifica se há caixas vendidas e coleta moedas automaticamente.
    Otimizado para maior velocidade na coleta de moedas.
    
    Args:
        template_path: Caminho para a imagem do template da caixa vazia
        threshold: Limiar de confiança para detecção
        
    Returns:
        Lista com os índices das caixas vazias (1-10)
    """
    try:
        # Carrega a configuração
        config = load_config()
        if not config or "kit_celeiro" not in config:
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Configuração inválida")
            return []
        
        # Obtém as ROIs individuais para cada caixa
        box_detection = config["kit_celeiro"]["box_detection"]
        individual_rois = box_detection["individual_roi"]
        box_positions = config["kit_celeiro"]["box_positions"]
        
        # Inicializa o matcher e screenshotter
        template_matcher = TemplateMatcher(default_threshold=threshold)
        screenshotter = Screenshotter()
        
        # Garante que o caminho é absoluto para o template de caixa vazia
        if not os.path.isabs(template_path):
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), template_path)
        
        # Caminho para o template de caixa vendida
        sold_box_template = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "others", "boxvendida.png")
        
        # Captura uma screenshot
        print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Capturando screenshot para análise de caixas")
        screenshot = screenshotter.take_screenshot(use_pil=False)
        if screenshot is None:
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao capturar screenshot")
            return []
        
        # Listas para armazenar os índices das caixas vazias e vendidas
        empty_boxes = []
        sold_boxes = []
        
        # PASSO 1: Identifica todas as caixas vazias e vendidas em uma única passagem
        print(f"{Colors.BLUE}[CELEIRO] ETAPA 1:{Colors.RESET} Identificando status de todas as caixas...")
        for i, roi in enumerate(individual_rois):
            box_index = i + 1  # Índices 1-10
            
            # Converte a ROI para o formato esperado pelo template_matcher
            roi_tuple = tuple(roi)
            
            # 1. Primeiro verifica se a caixa está vendida
            sold_result = template_matcher.find_template(screenshot, sold_box_template, roi_tuple, threshold)
            
            if sold_result and sold_result.get('found', False):
                confidence = sold_result.get('confidence', 0.0)
                print(f"{Colors.GREEN}[CELEIRO] CAIXA VENDIDA:{Colors.RESET} Caixa {box_index} (confiança: {confidence:.4f})")
                sold_boxes.append(box_index)
                # Também adicionamos às caixas vazias, pois estarão vazias após coletar
                empty_boxes.append(box_index)
            else:
                # 2. Se não estiver vendida, verifica se está vazia
                empty_result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold)
                
                if empty_result and empty_result.get('found', False):
                    confidence = empty_result.get('confidence', 0.0)
                    print(f"{Colors.GREEN}[CELEIRO] CAIXA VAZIA:{Colors.RESET} Caixa {box_index} (confiança: {confidence:.4f})")
                    empty_boxes.append(box_index)
                else:
                    print(f"{Colors.BLUE}[CELEIRO] CAIXA OCUPADA:{Colors.RESET} Caixa {box_index}")
        
        # PASSO 2: Coleta rápida de moedas para todas as caixas vendidas
        if sold_boxes:
            print(f"{Colors.BLUE}[CELEIRO] ETAPA 2:{Colors.RESET} Coletando moedas de {len(sold_boxes)} caixas vendidas...")
            
            # Inicialmente usamos uma espera mínima entre cliques para aumentar a velocidade
            wait_time = 0.05  # 50ms entre cliques, 6x mais rápido que antes
            
            for box_index in sold_boxes:
                box_position_key = str(box_index)
                if box_position_key in box_positions:
                    click_x, click_y = box_positions[box_position_key]
                    # Clique rápido sem log detalhado para cada caixa
                    if click(click_x, click_y):
                        wait(wait_time)  # Espera mínima entre cliques
                    else:
                        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao coletar moedas da caixa {box_index}")
            
            # Espera final após coletar todas as moedas para garantir que as animações terminem
            wait(0.2)  # Espera final para garantir que todas as animações terminaram
            print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Moedas coletadas de todas as caixas vendidas")
        
        print(f"{Colors.BLUE}[CELEIRO] RESULTADO:{Colors.RESET} {len(empty_boxes)} caixas vazias/coletadas encontradas: {empty_boxes}")
        return empty_boxes
        
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao escanear caixas: {e}")
        return []

def execute_action(action: Dict[str, Any]) -> Union[bool, Tuple[bool, str]]:
    """
    Executa uma ação específica de acordo com o tipo.
    
    Args:
        action: Dicionário com informações da ação
    
    Returns:
        bool: True se a ação foi executada com sucesso, False caso contrário
        ou tupla (bool, str) no caso de check_multiple_states
    """
    try:
        action_type = action.get("type", "")
        params = action.get("params", [])
        description = action.get("description", "Ação sem descrição")
        attempts = action.get("attempts", 1)
        threshold = action.get("threshold", 0.8)
        wait_time = action.get("wait_time", 0.5)
        use_mask = action.get("useMask", False)
        
        if action_type == "":
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Tipo de ação não especificado")
            return False
            
        # Processamento de acordo com o tipo de ação
        if action_type == "click":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            x, y = params
            return click(x, y)
            
        elif action_type == "wait":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            seconds = params[0]
            wait(seconds)
            return True
            
        elif action_type == "send_keys":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            text = params[0]
            return send_keys(text)
            
        elif action_type == "searchTemplate":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            template_path, roi = params
            return search_template(template_path, roi, attempts, threshold, use_mask)
            
        elif action_type == "scan_empty_boxes":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            template_path, scan_threshold = params
            empty_boxes = scan_empty_boxes(template_path, scan_threshold)
            
            if empty_boxes and len(empty_boxes) > 0:
                # Carrega a configuração de itens
                items_config = load_items_config()
                if not items_config:
                    print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao carregar configuração de itens")
                    return False
                    
                # Processa o kit com as caixas vazias encontradas
                print(f"{Colors.YELLOW}[CELEIRO] PROCESSANDO:{Colors.RESET} Preenchendo {len(empty_boxes)} caixas vazias...")
                result = process_kit(items_config, empty_boxes)
                
                if result:
                    print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Caixas preenchidas com sucesso!")
                else:
                    print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao preencher caixas")
                    
                return result
            else:
                print(f"{Colors.YELLOW}[CELEIRO] AVISO:{Colors.RESET} Nenhuma caixa vazia encontrada")
                return True  # Consideramos sucesso mesmo sem caixas vazias
                
        elif action_type == "check_multiple_states":
            print(f"{Colors.BLUE}[CELEIRO] AÇÃO:{Colors.RESET} {description}")
            expected_states = params
            
            for attempt in range(1, attempts + 1):
                current_state = get_current_state_id()
                
                if current_state in expected_states:
                    print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Estado verificado: {get_current_state()['name']} (ID: {current_state})")
                    return True, current_state
                    
                print(f"{Colors.YELLOW}[CELEIRO] AGUARDANDO:{Colors.RESET} Estado {expected_states}, atual: '{current_state}' ({get_current_state()['name']}) ({attempt}/{attempts})")
                
                if attempt < attempts:
                    wait(wait_time)
                    
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Estado esperado {expected_states} não encontrado após {attempts} tentativas")
            return False, get_current_state_id()
            
        else:
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao executar ação: {e}")
        return False

def search_template(template_path: str, roi: List[int], max_attempts: int = 2, threshold: float = 0.8, use_mask: bool = False):
    """
    Busca um template na tela atual e clica nele se encontrado.
    
    Args:
        template_path: Caminho para a imagem do template
        roi: Região de interesse [x, y, w, h] onde procurar o template
        max_attempts: Número máximo de tentativas
        threshold: Limiar de confiança para considerar que o template foi encontrado
        use_mask: Se deve usar máscara para matching
    
    Returns:
        bool: True se o template foi encontrado e clicado, False caso contrário
    """
    try:
        # Garante que o caminho é absoluto
        if not os.path.isabs(template_path):
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), template_path)
            
        print(f"{Colors.YELLOW}[CELEIRO] BUSCANDO:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
        
        # Inicializa o screenshotter
        screenshotter = Screenshotter()
        
        # Seleciona o matcher apropriado (com ou sem máscara)
        if use_mask:
            # Configura o MaskedTemplateMatcher
            template_matcher = MaskedTemplateMatcher(threshold=threshold)
        else:
            # Configura o TemplateMatcher padrão
            template_matcher = TemplateMatcher(default_threshold=threshold)
            
        # Verifica se o arquivo existe
        if not os.path.exists(template_path):
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Template não encontrado: {template_path}")
            return False
            
        # Converte a ROI para uma tupla se for uma lista
        roi_tuple = tuple(roi)
        
        # Tenta encontrar o template pelo número de tentativas especificado
        for attempt in range(1, max_attempts + 1):
            # Captura uma nova screenshot
            print(f"{Colors.BLUE}[CELEIRO] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template")
            screenshot = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot is None:
                print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao capturar screenshot na tentativa {attempt}")
                continue
                
            # Busca o template
            if use_mask:
                # Usa o matcher com máscara
                result = template_matcher.find_template_with_mask(screenshot, template_path, roi_tuple)
            else:
                # Usa o matcher padrão
                result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold)
                
            # Verifica se o template foi encontrado
            if result and result.get('found', False):
                # Extrai coordenadas e confiança
                x, y = result.get('position', (0, 0))
                confidence = result.get('confidence', 0.0)
                
                print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Template encontrado na posição ({x}, {y}) (confiança: {confidence:.4f})")
                
                # Clica na posição encontrada
                click_result = click(x, y)
                
                if click_result:
                    print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Clique realizado com sucesso na posição ({x}, {y})")
                    return True
                else:
                    print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao clicar na posição ({x}, {y})")
                    return False
                    
            else:
                print(f"{Colors.YELLOW}[CELEIRO] AVISO:{Colors.RESET} Template não encontrado na tentativa {attempt}/{max_attempts}")
                
            # Aguarda um pouco antes da próxima tentativa
            if attempt < max_attempts:
                wait(0.3)  # 300ms entre tentativas
                
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Template '{os.path.basename(template_path)}' não encontrado após {max_attempts} tentativas")
        return False
        
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Falha ao buscar template: {e}")
        return False

def run() -> bool:
    """
    Executa o kit celeiro completo, seguindo o fluxo de navegação entre estados,
    verificando caixas vazias e preenchendo-as.
    
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário.
    """
    try:
        global state_changed_flag, last_detected_state_id, pending_restart
        
        print(f"{Colors.BLUE}[CELEIRO] INICIANDO:{Colors.RESET} Execução do Kit Celeiro...")
        
        # Carrega a configuração
        config = load_config()
        if not config or "kit_celeiro" not in config:
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Configuração inválida ou não encontrada")
            return False
            
        # Carrega a configuração de estados e ações
        states_config = config["kit_celeiro"]["states"]
        
        # Registra o callback de estado para ser notificado de mudanças durante a execução
        register_state_callback(on_state_change_during_execution)
        print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Callback de estado registrado")
        
        # Loop principal de execução
        max_iterations = 20  # Limite de segurança para o loop
        iteration = 0
        success = False
        
        while iteration < max_iterations:
            iteration += 1
            pending_restart = False
            
            print(f"\n{Colors.BLUE}[CELEIRO] ITERAÇÃO {iteration}/{max_iterations}:{Colors.RESET} Verificando estado atual...")
            
            # Reseta a flag de mudança de estado
            state_changed_flag = False
            
            # Obtém o estado atual
            current_state = get_current_state_id()
            print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Estado atual: '{current_state}' ({get_current_state()['name']})")
            
            # Verifica se o estado atual está na configuração
            if current_state in states_config:
                # Obtém as ações para o estado atual
                actions = states_config[current_state]["actions"]
                
                # Executa cada ação sequencialmente
                for action in actions:
                    result = execute_action(action)
                    
                    # Se a ação for check_multiple_states, result é uma tupla (bool, str)
                    if isinstance(result, tuple):
                        success, detected_state = result
                        if success and detected_state == "jogo_aberto" and current_state != "jogo_aberto":
                            # Se voltamos para o estado inicial a partir de outro estado, reiniciamos o loop
                            print(f"{Colors.GREEN}[CELEIRO] REINICIANDO:{Colors.RESET} Retorno ao estado inicial detectado")
                            break
                    else:
                        success = result
                        
                    # Verifica se a ação falhou
                    if not success:
                        print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Ação falhou, tentando continuar...")
                        # Continuamos mesmo com falha em uma ação
                    
                    # Verifica se houve mudança de estado durante a execução da ação
                    if state_changed_flag:
                        print(f"{Colors.YELLOW}[CELEIRO] AVISO:{Colors.RESET} Estado alterado durante execução, ajustando fluxo...")
                        state_changed_flag = False  # Reseta a flag
                        break  # Interrompe o loop de ações para reavaliar o novo estado
                        
                    # Verifica se há necessidade de reiniciar devido a um popup de tutorial
                    if pending_restart:
                        print(f"{Colors.YELLOW}[CELEIRO] REINICIANDO:{Colors.RESET} Tutorial detectado, reiniciando execução...")
                        pending_restart = False
                        break  # Interrompe o loop de ações para reiniciar
                        
                # Verifica se o estado é inside_shop e as ações foram concluídas
                if current_state == "inside_shop" and not state_changed_flag and not pending_restart:
                    print(f"{Colors.GREEN}[CELEIRO] CONCLUÍDO:{Colors.RESET} Operações de kit celeiro finalizadas com sucesso!")
                    success = True
                    break  # Sai do loop principal
                    
            else:
                print(f"{Colors.YELLOW}[CELEIRO] AVISO:{Colors.RESET} Estado atual '{current_state}' não configurado no kit")
                
                # Caso especial: se estamos na loja, mesmo que não esteja no estado correto no config
                if "shop" in current_state.lower():
                    print(f"{Colors.YELLOW}[CELEIRO] TENTATIVA:{Colors.RESET} Possível estado de loja detectado, tentando executar ações de inside_shop")
                    
                    if "inside_shop" in states_config:
                        actions = states_config["inside_shop"]["actions"]
                        for action in actions:
                            execute_action(action)
                            
                # Espera um pouco antes de tentar novamente
                wait(1.0)
                
            # Pequena pausa entre iterações
            wait(0.5)
            
        # Cancela o registro do callback ao finalizar
        unregister_state_callback(on_state_change_during_execution)
        print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Callback de estado removido")
        
        if success:
            print(f"{Colors.GREEN}[CELEIRO] SUCESSO:{Colors.RESET} Kit Celeiro executado com sucesso após {iteration} iterações!")
        else:
            print(f"{Colors.RED}[CELEIRO] ERRO:{Colors.RESET} Kit Celeiro não conseguiu completar após {max_iterations} iterações")
            
        return success
        
    except Exception as e:
        print(f"{Colors.RED}[CELEIRO] ERRO FATAL:{Colors.RESET} {e}")
        # Garante que o callback seja removido mesmo em caso de erro
        try:
            unregister_state_callback(on_state_change_during_execution)
            print(f"{Colors.BLUE}[CELEIRO] INFO:{Colors.RESET} Callback de estado removido após erro")
        except Exception:
            pass
        return False

# Para execução direta
if __name__ == "__main__":
    run()
