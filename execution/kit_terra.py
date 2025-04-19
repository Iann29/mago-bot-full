"""
Kit Terra - Módulo de automação para operações relacionadas a terra/fazenda no HayDay.
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

# Caminho para o arquivo de configuração
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_terraCFG.json")

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
        print(f"{Colors.BLUE}[TERRA]{Colors.RESET} Configuração carregada: {CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
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
        print(f"{Colors.YELLOW}[TERRA] AVISO:{Colors.RESET} Tutorial popup detectado, reiniciando execução...")
        pending_restart = True
    else:
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Estado alterado: {previous_state} -> {new_state_name} (ID: {last_detected_state_id})")

def scan_empty_boxes(template_path: str, threshold: float = 0.85) -> List[int]:
    """
    Verifica quais caixas da loja estão vazias usando template matching.
    Também verifica se há caixas vendidas e coleta moedas automaticamente.
    
    Args:
        template_path: Caminho para a imagem do template da caixa vazia
        threshold: Limiar de confiança para detecção
        
    Returns:
        Lista com os índices das caixas vazias (1-10)
    """
    try:
        # Carrega a configuração
        config = load_config()
        if not config or "kit_terra" not in config:
            print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Configuração inválida")
            return []
        
        # Obtém as ROIs individuais para cada caixa
        box_detection = config["kit_terra"]["box_detection"]
        individual_rois = box_detection["individual_roi"]
        box_positions = config["kit_terra"]["box_positions"]
        
        # Inicializa o matcher e screenshotter
        template_matcher = TemplateMatcher(default_threshold=threshold)
        screenshotter = Screenshotter()
        
        # Garante que o caminho é absoluto para o template de caixa vazia
        if not os.path.isabs(template_path):
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), template_path)
        
        # Caminho para o template de caixa vendida
        sold_box_template = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "others", "boxvendida.png")
        
        # Captura uma screenshot
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Capturando screenshot para análise de caixas")
        screenshot = screenshotter.take_screenshot(use_pil=False)
        if screenshot is None:
            print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao capturar screenshot")
            return []
        
        # Lista para armazenar os índices das caixas vazias
        empty_boxes = []
        
        # Verifica cada caixa individualmente
        for i, roi in enumerate(individual_rois):
            box_index = i + 1  # Índices 1-10
            
            print(f"{Colors.YELLOW}[TERRA] VERIFICANDO:{Colors.RESET} Caixa {box_index} (ROI: {roi})")
            
            # Converte a ROI para o formato esperado pelo template_matcher
            roi_tuple = tuple(roi)
            
            # 1. Primeiro verifica se a caixa está vendida
            sold_result = template_matcher.find_template(screenshot, sold_box_template, roi_tuple, threshold)
            
            if sold_result and sold_result.get('found', False):
                confidence = sold_result.get('confidence', 0.0)
                print(f"{Colors.GREEN}[TERRA] CAIXA VENDIDA:{Colors.RESET} Caixa {box_index} está vendida (confiança: {confidence:.4f})")
                
                # Obtém a posição para clique na caixa
                box_position_key = str(box_index)
                if box_position_key in box_positions:
                    click_x, click_y = box_positions[box_position_key]
                    print(f"{Colors.YELLOW}[TERRA] AÇÃO:{Colors.RESET} Coletando moedas da caixa {box_index}")
                    
                    # Clica na caixa para coletar as moedas
                    if click(click_x, click_y):
                        print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Moedas coletadas da caixa {box_index}")
                        # Espera um curto período para a animação completar
                        wait(0.3)
                    else:
                        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao coletar moedas da caixa {box_index}")
                else:
                    print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Posição da caixa {box_index} não encontrada na configuração")
                    
                # Mesmo que a caixa esteja vendida, depois de coletar, ela estará vazia
                empty_boxes.append(box_index)
                
            else:
                # 2. Se não estiver vendida, verifica se está vazia
                empty_result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold)
                
                if empty_result and empty_result.get('found', False):
                    confidence = empty_result.get('confidence', 0.0)
                    print(f"{Colors.GREEN}[TERRA] CAIXA VAZIA:{Colors.RESET} Caixa {box_index} está vazia (confiança: {confidence:.4f})")
                    empty_boxes.append(box_index)
                else:
                    print(f"{Colors.BLUE}[TERRA] CAIXA OCUPADA:{Colors.RESET} Caixa {box_index} não está vazia nem vendida")
        
        print(f"{Colors.BLUE}[TERRA] RESULTADO:{Colors.RESET} {len(empty_boxes)} caixas vazias/coletadas encontradas: {empty_boxes}")
        return empty_boxes
        
    except Exception as e:
        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao escanear caixas: {e}")
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
        description = action.get("description", "")
        
        print(f"{Colors.YELLOW}[TERRA] AÇÃO:{Colors.RESET} {description}")
        
        if action_type == "click":
            if len(params) >= 2:
                return click(params[0], params[1])
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação click")
                return False
                
        elif action_type == "wait":
            if len(params) >= 1:
                wait(params[0])
                return True
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação wait")
                return False
        
        elif action_type == "searchTemplate":
            if len(params) >= 2:
                template_path = params[0]
                roi = params[1] if len(params) >= 2 else None
                max_attempts = int(action.get("attempts", 2))
                threshold = float(action.get("threshold", 0.8))
                use_mask = action.get("useMask", False)
                
                return search_template(template_path, roi, max_attempts, threshold, use_mask)
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação searchTemplate")
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
                        print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Estado verificado: {current_state_display} (ID: {current_state_id})")
                        return True
                        
                    print(f"{Colors.YELLOW}[TERRA] AGUARDANDO:{Colors.RESET} Estado '{expected_state}', atual: '{current_state_id}' ({current_state_display}) ({attempt+1}/{max_attempts})")
                    wait(0.5)  # Espera 500ms entre as verificações
                
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Estado {expected_state} não encontrado após {max_attempts} tentativas")
                return False
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação verify_state")
                return False
        
        elif action_type == "check_multiple_states":
            if len(params) >= 2:
                expected_states = params  # Lista de estados a verificar
                max_attempts = int(action.get("attempts", 5))  # Padrão: 5 tentativas
                wait_time = float(action.get("wait_time", 0.5))  # Padrão: 500ms entre tentativas
                
                print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Verificando múltiplos estados possíveis: {expected_states}")
                
                # Fazemos várias tentativas para pegar um estado válido
                for attempt in range(max_attempts):
                    # Obtemos o estado atual
                    current_state_id = get_current_state_id()
                    current_state_display = get_current_state()
                    
                    print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Estado atual: {current_state_display} (ID: {current_state_id}) - Tentativa {attempt+1}/{max_attempts}")
                    
                    # Se o estado for 'unknown', esperamos e tentamos novamente
                    if current_state_id == "unknown":
                        print(f"{Colors.YELLOW}[TERRA] AGUARDANDO:{Colors.RESET} Estado em transição (unknown), aguardando...")
                        wait(wait_time)
                        continue
                    
                    # Verificamos se o estado atual é um dos esperados
                    if current_state_id in expected_states:
                        print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Estado atual {current_state_id} está entre os esperados")
                        
                        # Retornamos o estado como uma string extra para informar ao chamador qual estado foi encontrado
                        return (True, current_state_id)
                    
                    # Se não é unknown nem um dos esperados, esperamos um pouco e tentamos novamente
                    print(f"{Colors.YELLOW}[TERRA] AGUARDANDO:{Colors.RESET} Estado atual {current_state_id} não é um dos esperados {expected_states}")
                    wait(wait_time)
                
                # Se chegamos aqui, não encontramos um estado válido após todas as tentativas
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Estado válido não encontrado após {max_attempts} tentativas")
                return (False, None)
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação check_multiple_states")
                return False
        
        elif action_type == "scan_empty_boxes":
            if len(params) >= 1:
                template_path = params[0]
                threshold = float(params[1]) if len(params) >= 2 else 0.85
                
                empty_boxes = scan_empty_boxes(template_path, threshold)
                if empty_boxes:
                    print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Identificadas {len(empty_boxes)} caixas vazias")
                    return True
                else:
                    print(f"{Colors.YELLOW}[TERRA] AVISO:{Colors.RESET} Nenhuma caixa vazia encontrada")
                    return False
            else:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Parâmetros insuficientes para ação scan_empty_boxes")
                return False
                
        else:
            print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao executar ação {action.get('type', 'desconhecida')}: {e}")
        return False

def search_template(template_path: str, roi: List[int], max_attempts: int = 2, threshold: float = 0.8, use_mask: bool = False) -> bool:
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
    # Importa aqui para evitar importação circular
    from screenVision.screenshotMain import Screenshotter
    
    # Escolhe entre template matcher normal ou com máscara
    if use_mask:
        template_matcher = MaskedTemplateMatcher()
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Usando template matcher com máscara")
        
        # Deriva o caminho da máscara
        mask_path = template_path.replace('.png', 'mask.png')
        if not os.path.exists(mask_path):
            # Tenta encontrar em outro formato de nome
            mask_path = os.path.splitext(template_path)[0] + "mask" + os.path.splitext(template_path)[1]
            if not os.path.exists(mask_path):
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Máscara não encontrada para {template_path}")
                return False
    else:
        template_matcher = TemplateMatcher(default_threshold=threshold)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cria uma instância do Screenshotter para capturar screenshots diretamente
    screenshotter = Screenshotter()
    
    # Garante que o caminho é absoluto
    if not os.path.isabs(template_path):
        template_path = os.path.join(project_root, template_path)
    
    # Converte a ROI para o formato esperado pelo template_matcher
    roi_tuple = tuple(roi) if roi else None
    
    if use_mask:
        # Garante que o caminho da máscara é absoluto
        if not os.path.isabs(mask_path):
            mask_path = os.path.join(project_root, mask_path)
        print(f"{Colors.YELLOW}[TERRA] BUSCANDO COM MÁSCARA:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
        print(f"{Colors.YELLOW}[TERRA] MÁSCARA:{Colors.RESET} '{os.path.basename(mask_path)}'")
    else:
        print(f"{Colors.YELLOW}[TERRA] BUSCANDO:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
    
    for attempt in range(max_attempts):
        try:
            # Captura uma nova screenshot diretamente (formato OpenCV - BGR)
            print(f"{Colors.YELLOW}[TERRA] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template")
            screenshot_cv = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot_cv is None:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao capturar screenshot")
                wait(0.5)  # Pequena pausa antes da próxima tentativa
                continue
            
            # Busca o template com ou sem máscara dependendo da configuração
            if use_mask:
                result = template_matcher.find_template(screenshot_cv, template_path, mask_path, roi_tuple)
            else:
                result = template_matcher.find_template(screenshot_cv, template_path, roi_tuple, threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Template {'com máscara ' if use_mask else ''}encontrado na posição {position} (confiança: {confidence:.4f})")
                
                # Tentativas de clique com deslocamentos variados
                # Primeiro tenta na posição original
                print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Tentando clique na posição original {position}")
                success = click(position[0], position[1])
                
                if success:
                    # Aguarda um pouco para ver se o estado muda para inside_shop
                    print(f"{Colors.YELLOW}[TERRA] AGUARDANDO:{Colors.RESET} Verificando se o estado mudou após o clique...")
                    wait(1.0)  # Aguarda 1 segundo para o estado mudar após clique inicial
                    
                    # Verifica se o estado atual é inside_shop
                    current_state_id = get_current_state_id()
                    if current_state_id == "inside_shop":
                        print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Loja aberta com sucesso!")
                        return True
                    
                    # Se não mudou para inside_shop, tenta deslocamentos
                    print(f"{Colors.YELLOW}[TERRA] AVISO:{Colors.RESET} Clique na posição original não abriu a loja. Tentando deslocamentos...")
                    
                    # Lista de deslocamentos a tentar (dx, dy)
                    offsets = [
                        (0, 10),   # 10px abaixo
                        (0, -10),  # 10px acima
                        (10, 0),   # 10px à direita
                        (-10, 0),  # 10px à esquerda
                        (10, 10),  # diagonal inferior direita
                        (-10, 10), # diagonal inferior esquerda
                        (10, -10), # diagonal superior direita
                        (-10, -10) # diagonal superior esquerda
                    ]
                    
                    # Tenta cada deslocamento
                    for i, (dx, dy) in enumerate(offsets):
                        new_x, new_y = position[0] + dx, position[1] + dy
                        print(f"{Colors.YELLOW}[TERRA] TENTATIVA {i+1}/{len(offsets)}:{Colors.RESET} Clicando em posição deslocada ({new_x}, {new_y})")
                        
                        if click(new_x, new_y):
                            # Aguarda por 1.4 segundos para ver se o estado muda (tempo ajustado conforme solicitado)
                            print(f"{Colors.YELLOW}[TERRA] AGUARDANDO:{Colors.RESET} Verificando por 1.4s se o estado mudou após clique com deslocamento...")
                            wait(1.4)  # Aguarda 1.4 segundos para o estado mudar após cliques com deslocamento
                            current_state_id = get_current_state_id()
                            if current_state_id == "inside_shop":
                                print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Loja aberta com sucesso após tentativa com deslocamento!")
                                return True
                    
                    print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Todas as tentativas de clique falharam em abrir a loja")
                    return False
                else:
                    print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao clicar na posição {position}")
                    return False
            
            print(f"{Colors.YELLOW}[TERRA] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Template não encontrado")
        except Exception as e:
            print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao processar screenshot: {e}")
        
        wait(0.5)  # Pequena pausa antes da próxima tentativa
    
    print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Template não encontrado após {max_attempts} tentativas")
    return False

def run() -> bool:
    """
    Executa o kit terra completo, seguindo o fluxo de navegação entre estados,
    verificando caixas vazias e preenchendo-as.
    
    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário.
    """
    print("\n======= KIT TERRA =======\n")
    
    global state_changed_flag, last_detected_state_id, pending_restart
    state_changed_flag = False
    last_detected_state_id = ""
    pending_restart = False
    
    try:
        # Registra o callback para monitorar mudanças de estado durante a execução
        register_state_callback(on_state_change_during_execution)
        print(f"{Colors.GREEN}[TERRA] \u2714\ufe0f{Colors.RESET} Registro de callback de estado concluído.")
        
        # Carrega a configuração
        config = load_config()
        if not config or "kit_terra" not in config:
            print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Configuração inválida ou não encontrada")
            return False
        
        kit_config = config["kit_terra"]
        
        # Obtém o estado atual do jogo
        current_state_id = get_current_state_id()
        current_state_display = get_current_state()
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Estado atual: {current_state_display} (ID: {current_state_id})")
        
        # Loop principal de processamento de estados
        # Permite que possamos navegar entre diferentes estados conforme necessário
        while True:
            # Atualiza o estado atual (pode ter mudado durante a execução)
            current_state_id = get_current_state_id()
            current_state_display = get_current_state()
            print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Estado atual: {current_state_display} (ID: {current_state_id})")
            
            # Verifica se o estado atual está definido na configuração
            if current_state_id not in kit_config["states"]:
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Estado {current_state_id} não está configurado para o Kit Terra")
                return False
                
            # Se o estado atual é "inside_shop", significa que atingimos o objetivo de navegação
            # e podemos prosseguir com as ações específicas do Kit Terra
            if current_state_id == "inside_shop":
                print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Chegamos à loja, prosseguindo com as ações do Kit Terra")
                # Aqui implementaremos a lógica para preencher caixas
                # Por enquanto apenas escaneamos as caixas vazias
                break
            
            # Executa as ações definidas para o estado atual
            actions = kit_config["states"][current_state_id]["actions"]
            next_state = None
            
            print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Executando {len(actions)} ações para o estado '{current_state_display}'")
            
            for i, action in enumerate(actions):
                # Executa a ação
                print(f"{Colors.YELLOW}[TERRA] AÇÃO {i+1}/{len(actions)}:{Colors.RESET} {action.get('description', '')}")
                result = execute_action(action)
                
                # Verifica se a ação retornou uma tupla (caso de check_multiple_states)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, next_state = result
                    if not success:
                        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
                        return False
                    print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Redirecionando para o estado: {next_state}")
                    break  # Sai do loop de ações para processar o próximo estado
                elif not result:
                    print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
                    return False
            
            # Verifica se ocorreu alguma mudança de estado durante a execução das ações
            if state_changed_flag:
                print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Estado mudou para: {get_current_state()} (ID: {last_detected_state_id})")
                state_changed_flag = False
                
                # Se for um tutorial pop-up, reinicia o processo após lidar com ele
                if pending_restart:
                    pending_restart = False
                    print(f"{Colors.YELLOW}[TERRA] REINICIANDO:{Colors.RESET} Após lidar com pop-up de tutorial")
                    continue
                
                # Se estamos na loja, prosseguimos para a próxima fase
                if last_detected_state_id == "inside_shop":
                    print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Chegamos à loja após mudança de estado")
                    break
            
            # Se temos um próximo estado definido, vamos para ele
            if next_state:
                # Se estamos no estado final desejado (inside_shop), terminamos a navegação
                if next_state == "inside_shop":
                    print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Chegamos à loja, prosseguindo com as ações do Kit Terra")
                    break
                # Caso contrário, atualiza o estado atual e continua o processamento
                current_state_id = next_state
                continue
            else:
                # Se o estado atual é o inside_shop, já cumprimos o objetivo
                if current_state_id == "inside_shop":
                    print(f"{Colors.GREEN}[TERRA] SUCESSO:{Colors.RESET} Já estamos na loja")
                    break
                # Se não temos um próximo estado e concluímos todas as ações, espera mudança auto. de estado
                print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Aguardando mudança de estado após ações")
                wait(1.0)  # Espera um segundo antes de verificar novamente
        
        # Agora que estamos na loja, executamos as ações específicas do Kit Terra
        # Por enquanto, apenas verificamos as caixas vazias
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Executando ações específicas da loja")
        
        # Executa as ações da inside_shop
        inside_shop_actions = kit_config["states"]["inside_shop"]["actions"]
        for i, action in enumerate(inside_shop_actions):
            # Executa a ação
            print(f"{Colors.YELLOW}[TERRA] AÇÃO {i+1}/{len(inside_shop_actions)}:{Colors.RESET} {action.get('description', '')}")
            if not execute_action(action):
                print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao executar ação: {action.get('description', '')}")
                return False
        
        # Remove o callback de estado
        unregister_state_callback(on_state_change_during_execution)
        print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Callback de estado removido")
        
        print(f"\n{Colors.GREEN}[TERRA] OPERAÇÃO CONCLUÍDA:{Colors.RESET} Kit Terra executado com sucesso!\n")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[TERRA] ERRO:{Colors.RESET} Falha ao executar Kit Terra: {e}")
        
        # Garante que o callback é removido mesmo em caso de erro
        try:
            unregister_state_callback(on_state_change_during_execution)
            print(f"{Colors.BLUE}[TERRA] INFO:{Colors.RESET} Callback de estado removido após erro")
        except:
            pass
            
        return False

# Para execução direta
if __name__ == "__main__":
    run()
