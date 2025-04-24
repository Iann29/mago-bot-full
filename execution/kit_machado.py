"""
Kit Machado - Módulo de automação para operações relacionadas ao machado no HayDay.
Diferente dos outros kits, este é composto por apenas um tipo de item (Machado) para todas as 10 caixas.
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
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_machadoCFG.json")
ITEMS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit_machado_items.json")

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
        print(f"{Colors.BLUE}[MACHADO]{Colors.RESET} Configuração carregada: {CONFIG_PATH}")
        return config
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
        return {}

def load_items_config() -> Dict:
    """
    Carrega a configuração de itens do kit Machado.

    Returns:
        Dict: Configuração de itens carregada
    """
    try:
        with open(ITEMS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            items_config = json.load(f)
        print(f"{Colors.BLUE}[MACHADO]{Colors.RESET} Configuração de itens carregada: {ITEMS_CONFIG_PATH}")
        return items_config
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao carregar configuração de itens: {e}")
        return {}

def on_state_change_during_execution(previous_state: str, new_state_name: str):
    """
    Callback para monitorar mudanças de estado durante a execução.

    Args:
        previous_state: Estado anterior
        new_state_name: Novo estado detectado
    """
    global state_changed_flag, last_detected_state_id
    
    # Atualiza o estado global
    state_changed_flag = True
    last_detected_state_id = new_state_name
    
    # Loga a mudança de estado para diagnóstico
    print(f"{Colors.BLUE}[MACHADO] ESTADO ALTERADO:{Colors.RESET} {previous_state} -> {new_state_name}")

def scan_empty_boxes(template_path: str, threshold: float = 0.75) -> List[int]:
    """
    Escaneia todas as caixas e identifica quais estão vazias.

    Args:
        template_path: Caminho para o template de caixa vazia
        threshold: Limite de confiança para detecção

    Returns:
        List[int]: Lista com os índices das caixas vazias (1-10)
    """
    try:
        # Carrega a configuração do kit
        kit_config = load_config()
        
        if not kit_config:
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao carregar configuração do kit")
            return []
            
        # Obtém os ROIs das caixas individuais do arquivo de configuração
        kit_machado_config = kit_config["kit_machado"]
        box_positions = kit_machado_config.get("box_positions", {})
        
        # Obtém os ROIs completos diretamente do arquivo de configuração
        box_detection = kit_machado_config.get("box_detection", {})
        individual_rois = box_detection.get("individual_roi", [])
        
        # Verifica se as configurações estão completas
        if len(individual_rois) != 10 or not box_positions or len(box_positions) != 10:
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Configuração incompleta, faltam posições ou ROIs de caixas")
            return []
            
        # Prepara o matcher e carrega a screenshot atual
        template_matcher = TemplateMatcher(default_threshold=threshold)
        screenshotter = Screenshotter()
        screenshot = screenshotter.take_screenshot(use_pil=False)
        
        if screenshot is None:
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao obter screenshot")
            return []
        
        # Garante que o caminho é absoluto para o template de caixa vazia
        if not os.path.isabs(template_path):
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), template_path)
            
        # Carrega o template de caixa vendida
        sold_box_template = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "dataset", "others", "boxvendida.png"
        )
        
        # Verifica se o template existe
        if not os.path.exists(sold_box_template):
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Template de caixa vendida não encontrado: {sold_box_template}")
            return []
        
        # Listas para armazenar os índices das caixas vazias e vendidas
        empty_boxes = []
        sold_boxes = []
        
        # Verifica cada caixa individualmente
        for i, roi in enumerate(individual_rois):
            box_index = i + 1  # índices de 1 a 10
            roi_tuple = tuple(roi)
            
            print(f"{Colors.BLUE}[MACHADO] VERIFICANDO CAIXA {box_index}:{Colors.RESET} ROI: {roi}")
            
            # Verifica se está vendida
            sold_result = template_matcher.find_template(screenshot, sold_box_template, roi_tuple, threshold)
            if sold_result and sold_result.get('found', False):
                # Encontrou caixa vendida, clique para coletar moedas
                x, y = sold_result.get('position', (0, 0))
                # Ajusta as coordenadas de acordo com a ROI
                x_absolute = x
                y_absolute = y
                
                print(f"{Colors.GREEN}[MACHADO] VENDIDA:{Colors.RESET} Caixa {box_index} vendida, coletando moedas em ({x_absolute}, {y_absolute})")
                
                # Clica para coletar as moedas
                click(x_absolute, y_absolute)
                wait(0.5)  # Espera um pouco para a animação
                
                sold_boxes.append(box_index)
                empty_boxes.append(box_index)  # Caixas vendidas são consideradas vazias para preenchimento
                continue  # Pula para a próxima caixa
            
            # Se não está vendida, verifica se está vazia
            empty_result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold)
            if empty_result and empty_result.get('found', False):
                # Encontrou caixa vazia
                print(f"{Colors.YELLOW}[MACHADO] VAZIA:{Colors.RESET} Caixa {box_index} está vazia")
                empty_boxes.append(box_index)
            else:
                # Não está vazia nem vendida
                print(f"{Colors.BLUE}[MACHADO] OCUPADA:{Colors.RESET} Caixa {box_index} não está vazia/vendida")
        
        # Removemos completamente a lógica que forçava todas as caixas a serem consideradas vazias
        # Agora só retornamos as caixas que foram realmente detectadas como vazias ou vendidas
        if len(empty_boxes) < 10:
            print(f"{Colors.YELLOW}[MACHADO] AVISO:{Colors.RESET} Apenas {len(empty_boxes)} caixas vazias detectadas. Preenchendo apenas estas caixas.")
        
        # Ordena as caixas para processamento consistente
        empty_boxes.sort()
        
        print(f"{Colors.BLUE}[MACHADO] RESULTADO:{Colors.RESET} {len(empty_boxes)} caixas a serem preenchidas: {empty_boxes}")
        return empty_boxes
    
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao escanear caixas vazias: {e}")
        return []

def execute_action(action: Dict[str, Any]) -> Union[bool, Tuple[bool, str], List[int]]:
    """
    Executa uma ação específica de acordo com o tipo.
    
    Args:
        action: Dicionário com informações da ação
    
    Returns:
        bool: True se a ação foi executada com sucesso, False caso contrário
        ou tupla (bool, str) no caso de check_multiple_states
        ou lista de inteiros no caso de scan_empty_boxes
    """
    try:
        action_type = action.get("type", "")
        params = action.get("params", [])
        description = action.get("description", "")
        
        print(f"{Colors.YELLOW}[MACHADO] AÇÃO:{Colors.RESET} {description}")
        
        if action_type == "click":
            if len(params) >= 2:
                return click(params[0], params[1])
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação click")
                return False
                
        elif action_type == "wait":
            if len(params) >= 1:
                wait(params[0])
                return True
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação wait")
                return False
                
        elif action_type == "send_keys":
            if len(params) >= 1:
                return send_keys(params[0])
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação send_keys")
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
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação searchTemplate")
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
                        print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Estado verificado: {current_state_display} (ID: {current_state_id})")
                        return True
                        
                    print(f"{Colors.YELLOW}[MACHADO] AGUARDANDO:{Colors.RESET} Estado '{expected_state}', atual: '{current_state_id}' ({current_state_display}) ({attempt+1}/{max_attempts})")
                    wait(0.5)  # Espera 500ms entre as verificações
                
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Estado {expected_state} não encontrado após {max_attempts} tentativas")
                return False
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação verify_state")
                return False
                
        elif action_type == "check_multiple_states":
            if len(params) >= 2:
                expected_states = params  # Lista de estados a verificar
                max_attempts = int(action.get("attempts", 5))  # Padrão: 5 tentativas
                wait_time = float(action.get("wait_time", 0.5))  # Padrão: 500ms entre tentativas
                
                print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Verificando múltiplos estados possíveis: {expected_states}")
                
                # Fazemos várias tentativas para pegar um estado válido
                for attempt in range(max_attempts):
                    # Obtemos o estado atual
                    current_state_id = get_current_state_id()
                    current_state_display = get_current_state()
                    
                    print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Estado atual: {current_state_display} (ID: {current_state_id}) - Tentativa {attempt+1}/{max_attempts}")
                    
                    # Se o estado for 'unknown', esperamos e tentamos novamente
                    if current_state_id == "unknown":
                        print(f"{Colors.YELLOW}[MACHADO] AGUARDANDO:{Colors.RESET} Estado em transição (unknown), aguardando...")
                        wait(wait_time)
                        continue
                    
                    # Verificamos se o estado atual é um dos estados esperados
                    if current_state_id in expected_states:
                        print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Estado {current_state_id} encontrado!")
                        return (True, current_state_id)  # Retorna o estado encontrado
                    
                    # Se não for um dos estados esperados, aguarda e tenta novamente
                    print(f"{Colors.YELLOW}[MACHADO] AGUARDANDO:{Colors.RESET} Estado {current_state_id} não é um dos esperados, tentando novamente...")
                    wait(wait_time)
                
                # Se após todas as tentativas, nenhum dos estados foi encontrado
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Nenhum dos estados esperados foi encontrado após {max_attempts} tentativas")
                return (False, "")
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação check_multiple_states")
                return (False, "")
                
        elif action_type == "scan_empty_boxes":
            if len(params) >= 1:
                template_path = params[0]
                threshold = float(action.get("threshold", 0.75))
                
                # Executa o scan de caixas vazias
                print(f"{Colors.BLUE}[MACHADO] VERIFICANDO:{Colors.RESET} Buscando caixas vazias...")
                empty_boxes = scan_empty_boxes(template_path, threshold)
                
                return empty_boxes
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Parâmetros insuficientes para ação scan_empty_boxes")
                return []
        
        else:
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Tipo de ação desconhecido: {action_type}")
            return False
    
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao executar ação: {e}")
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
    try:
        # Garante que o caminho é absoluto
        if not os.path.isabs(template_path):
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), template_path)
            
        print(f"{Colors.YELLOW}[MACHADO] BUSCANDO:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
        
        # Inicializa o screenshotter
        screenshotter = Screenshotter()
        
        # Escolhe entre template matcher normal ou com máscara
        if use_mask:
            # Deriva o caminho da máscara
            mask_path = template_path.replace('.png', 'mask.png')
            if not os.path.exists(mask_path):
                # Tenta encontrar em outro formato de nome
                mask_path = os.path.splitext(template_path)[0] + "mask" + os.path.splitext(template_path)[1]
                if not os.path.exists(mask_path):
                    print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Máscara não encontrada para {template_path}")
                    return False
            
            # Configura o MaskedTemplateMatcher
            template_matcher = MaskedTemplateMatcher(default_threshold=threshold, verbose=False)
            print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Usando template matcher com máscara")
        else:
            # Configura o TemplateMatcher padrão
            template_matcher = TemplateMatcher(default_threshold=threshold)
            
        # Verifica se o arquivo existe
        if not os.path.exists(template_path):
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Template não encontrado: {template_path}")
            return False
            
        # Converte a ROI para uma tupla se for uma lista
        roi_tuple = tuple(roi) if roi else None
        
        # Tenta encontrar o template pelo número de tentativas especificado
        for attempt in range(1, max_attempts + 1):
            # Captura uma nova screenshot
            print(f"{Colors.BLUE}[MACHADO] CAPTURANDO:{Colors.RESET} Nova screenshot para busca de template (tentativa {attempt}/{max_attempts})")
            screenshot = screenshotter.take_screenshot(use_pil=False)
            
            if screenshot is None:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao capturar screenshot na tentativa {attempt}")
                wait(0.5)  # Pequena pausa antes da próxima tentativa
                continue
                
            # Busca o template
            if use_mask:
                # Usa o matcher com máscara
                result = template_matcher.find_template(
                    main_image=screenshot,
                    template_path=template_path,
                    mask_path=mask_path,
                    roi=roi_tuple,
                    threshold=threshold
                )
            else:
                # Usa o matcher padrão
                result = template_matcher.find_template(
                    main_image=screenshot,
                    template_path=template_path,
                    roi=roi_tuple,
                    threshold=threshold
                )
                
            # Verifica se o template foi encontrado
            if result and result.get('found', False):
                # Extrai coordenadas e confiança
                x, y = result.get('position', (0, 0))
                confidence = result.get('confidence', 0.0)
                
                print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Template encontrado na posição ({x}, {y}) (confiança: {confidence:.4f})")
                
                # Clica na posição encontrada
                click_result = click(x, y)
                
                if click_result:
                    print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Clique realizado com sucesso na posição ({x}, {y})")
                    # Aguarda um pouco para ver se o estado muda para inside_shop
                    print(f"{Colors.YELLOW}[MACHADO] AGUARDANDO:{Colors.RESET} Verificando se o estado mudou após o clique...")
                    wait(2.5)  # Aguarda 2.5 segundos para o estado mudar após clique inicial
                    
                    # Verifica se o estado atual é inside_shop
                    current_state_id = get_current_state_id()
                    if current_state_id == "inside_shop":
                        print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Loja aberta com sucesso!")
                        return True
                    
                    # Se não mudou para inside_shop, tenta deslocamentos
                    print(f"{Colors.YELLOW}[MACHADO] AVISO:{Colors.RESET} Clique na posição original não abriu a loja. Tentando deslocamentos...")
                else:
                    print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao clicar na posição ({x}, {y})")
                    
                # Tenta deslocamentos alternativos se o clique falhar ou não abrir a loja
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
                    # Verifica o estado atual ANTES de tentar um novo deslocamento
                    # Se já estamos na loja, não precisa continuar tentando
                    current_state_before_click = get_current_state_id()
                    if current_state_before_click == "inside_shop":
                        print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Loja já está aberta, não é necessário continuar tentando deslocamentos")
                        return True
                        
                    new_x, new_y = x + dx, y + dy
                    print(f"{Colors.YELLOW}[MACHADO] TENTATIVA {i+1}/{len(offsets)}:{Colors.RESET} Clicando em posição deslocada ({new_x}, {new_y})")
                    
                    if click(new_x, new_y):
                        # Aguarda por 1.4 segundos para ver se o estado muda (tempo ajustado conforme kit_terra)
                        print(f"{Colors.YELLOW}[MACHADO] AGUARDANDO:{Colors.RESET} Verificando por 1.4s se o estado mudou após clique com deslocamento...")
                        wait(1.4)  # Aguarda 1.4 segundos para o estado mudar após cliques com deslocamento
                        current_state_id = get_current_state_id()
                        if current_state_id == "inside_shop":
                            print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Loja aberta com sucesso após tentativa com deslocamento!")
                            return True
                
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Todas as tentativas de clique falharam em abrir a loja")
                return False
            else:
                print(f"{Colors.YELLOW}[MACHADO] AVISO:{Colors.RESET} Template não encontrado na tentativa {attempt}/{max_attempts}")
                
            # Aguarda um pouco antes da próxima tentativa
            if attempt < max_attempts:
                wait(0.3)  # 300ms entre tentativas
                
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Template '{os.path.basename(template_path)}' não encontrado após {max_attempts} tentativas")
        return False
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao buscar template: {e}")
        return False

def run() -> bool:
    """
    Função principal que executa o fluxo do kit Machado.
    Carrega a configuração, navega através dos estados, detecta caixas vazias
    e preenche com o item Machado.
    
    Returns:
        bool: True se a execução foi bem-sucedida, False caso contrário
    """
    try:
        print(f"\n{Colors.BLUE}[MACHADO] INICIANDO KIT MACHADO{Colors.RESET}\n")
        
        # Carrega as configurações
        start_time = time.time()
        kit_config = load_config()
        items_config = load_items_config()
        
        if not kit_config or "kit_machado" not in kit_config or not items_config:
            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao carregar configurações")
            return False
        
        print(f"{Colors.GREEN}[MACHADO] CONFIG:{Colors.RESET} Configurações carregadas com sucesso")
        
        # Obtém o estado atual do sistema
        current_state_id = get_current_state_id()
        current_state_display = get_current_state()
        print(f"{Colors.BLUE}[MACHADO] ESTADO ATUAL:{Colors.RESET} {current_state_display} (ID: {current_state_id})")
        
        # Kit Machado config reference
        kit_machado_config = kit_config["kit_machado"]
        
        # Verifica se já estamos na loja, caso sim, podemos pular a navegação
        if current_state_id == "inside_shop":
            print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Já estamos na loja! Pulando a navegação.")
        # Tratamento especial para o estado item_shop_list (lista de itens aberta)
        elif current_state_id == "item_shop_list":
            print(f"{Colors.BLUE}[MACHADO] ESTADO:{Colors.RESET} {current_state_id} ({current_state_display}) - Fechando lista de itens")
            # Busca a ação para fechar a lista de itens
            back_action = next((action for action in kit_machado_config["states"]["item_shop_list"]["actions"] 
                               if action.get("description", "").lower().find("fechar") >= 0), None)
            
            if back_action:
                # Executa apenas a ação de fechar a lista uma única vez
                print(f"{Colors.BLUE}[MACHADO] AÇÃO:{Colors.RESET} {back_action.get('description', 'Fechando lista de itens')}")
                execute_action(back_action)
                
                # Espera a mudança de estado
                wait(0.5)
                current_state_id = get_current_state_id()
                current_state_display = get_current_state()
                print(f"{Colors.BLUE}[MACHADO] ESTADO APÓS FECHAR:{Colors.RESET} {current_state_display} (ID: {current_state_id})")
                
                # Continua o fluxo de navegação normal
                if current_state_id == "inside_shop":
                    print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Loja aberta com sucesso!")
                else:
                    # Inicia o loop de navegação normal
                    print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Iniciando navegação para a loja")
            else:
                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Não foi possível encontrar a ação para fechar a lista")
                return False
        else:       
            # Loop principal de navegação entre estados até chegar na loja
            print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Iniciando navegação para a loja")
            while True:
                # Atualiza o estado atual a cada iteração do loop
                current_state_id = get_current_state_id()
                current_state_display = get_current_state()
                
                # Verifica se o estado atual existe na configuração
                if current_state_id not in kit_machado_config["states"]:
                    print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Estado desconhecido: {current_state_id}")
                    return False
                    
                # Se já estamos dentro da loja, saímos do loop de navegação
                if current_state_id == "inside_shop":
                    print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Loja aberta com sucesso!")
                    break
                    
                # Obtém as ações para o estado atual
                actions = kit_machado_config["states"][current_state_id]["actions"]
                print(f"{Colors.BLUE}[MACHADO] ESTADO:{Colors.RESET} {current_state_id} ({current_state_display}) - {len(actions)} ações")
                
                # Executa as ações do estado atual
                for i, action in enumerate(actions):
                    print(f"{Colors.BLUE}[MACHADO] EXECUTANDO:{Colors.RESET} Ação {i+1}/{len(actions)} do estado {current_state_id}")
                    result = execute_action(action)
                    
                    # Verifica se o estado mudou após a ação
                    new_state_id = get_current_state_id()
                    if new_state_id != current_state_id:
                        print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Estado mudou para {new_state_id} após a ação. Recomeçando loop.")
                        # Atualiza o estado atual e reinicia o loop
                        current_state_id = new_state_id
                        break
                        
                    # Verifica o resultado da ação
                    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
                        # Caso especial para check_multiple_states
                        success, next_state = result
                        if success and next_state:
                            # Atualiza o estado atual baseado no retorno
                            prev_state = current_state_id
                            current_state_id = next_state
                            # Chama o callback para lidar com a transição
                            on_state_change_during_execution(prev_state, current_state_id)
                            # Reinicia o loop para processar as ações do novo estado
                            break
                    elif not result:
                        # Se alguma ação falhar, sai do loop e retorna False
                        print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha na ação {i+1}/{len(actions)} do estado {current_state_id}")
                        return False
        
        # Agora estamos dentro da loja, vamos escanear as caixas vazias
        inside_shop_actions = kit_config["kit_machado"]["states"]["inside_shop"]["actions"]
        empty_boxes = []
        
        for i, action in enumerate(inside_shop_actions):
            if action.get("type") == "scan_empty_boxes":
                print(f"{Colors.BLUE}[MACHADO] ESCANEANDO:{Colors.RESET} Buscando caixas vazias...")
                result = execute_action(action)
                
                if isinstance(result, list):
                    empty_boxes = result
                    print(f"{Colors.GREEN}[MACHADO] CAIXAS:{Colors.RESET} Encontradas {len(empty_boxes)} caixas vazias: {empty_boxes}")
                    
                    # Preenche as caixas vazias com o item machado
                    if len(empty_boxes) > 0:
                        print(f"{Colors.BLUE}[MACHADO] PROCESSANDO:{Colors.RESET} Preenchendo {len(empty_boxes)} caixas com Machado")
                        
                        # Carrega a configuração de itens do kit
                        items_config = load_items_config()
                        if items_config:
                            print(f"{Colors.BLUE}[MACHADO] INFO:{Colors.RESET} Iniciando preenchimento de caixas com Kit Machado")
                            
                            # Usa o framework para preencher as caixas com os itens do kit
                            kit_result = process_kit(items_config, empty_boxes)
                            if kit_result:
                                print(f"{Colors.GREEN}[MACHADO] SUCESSO:{Colors.RESET} Kit Machado aplicado com sucesso!")
                            else:
                                print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao aplicar Kit Machado")
                                return False  # Retorna False se o processamento do kit falhar
                        else:
                            print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Não foi possível carregar a configuração de itens do Kit Machado")
                            return False
                    else:
                        print(f"{Colors.YELLOW}[MACHADO] AVISO:{Colors.RESET} Nenhuma caixa vazia para preencher")
                else:
                    print(f"{Colors.RED}[MACHADO] ERRO:{Colors.RESET} Falha ao escanear caixas vazias")
                    return False
                    
                # Executou a ação de scan_empty_boxes, não precisamos continuar com as outras ações
                break
        
        # Calcula o tempo total de execução
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{Colors.GREEN}[MACHADO] FINALIZADO:{Colors.RESET} Kit Machado executado com sucesso em {execution_time:.2f} segundos")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[MACHADO] ERRO FATAL:{Colors.RESET} {e}")
        import traceback
        traceback.print_exc()
        return False

# Para execução direta
if __name__ == "__main__":
    print("\n======= KIT MACHADO =======\n")
    print("Para executar o kit, use `python main.py -k machado`\n")
    # Executa o kit
    run()
