"""
Terra Turbo - Módulo de automação ultra-rápido para o kit terra no HayDay.
Versão otimizada para velocidade máxima com tempos de espera mínimos.
"""

import json
import os
import time
from typing import Dict, List, Any, Tuple, Optional, Union

# Importações específicas para maximizar velocidade
from cerebro.emulatorInteractFunction import click, wait, get_device
from screenVision.screenshotMain import Screenshotter
from screenVision.templateMatcher import TemplateMatcher

# Cores para logs
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

# Caminhos de configuração
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "execution", "kit_terraCFG.json")
ITEMS_CONFIG_PATH = os.path.join(PROJECT_ROOT, "execution", "kit_terra_items.json")

# Posições e configurações fixas para maior velocidade
BOX_POSITIONS = {
    "1": [177, 207],
    "2": [177, 280],
    "3": [246, 207],
    "4": [246, 280],
    "5": [315, 207],
    "6": [315, 282],
    "7": [384, 207],
    "8": [384, 280],
    "9": [452, 207],
    "10": [452, 280]
}

# ROI para detectar itens
ITEM_DETECTION_ROI = [170, 146, 174, 208]

# Posições de interação fixas
INVENTORY_BUTTON_POS = [140, 231]
MINUS_QUANTITY_POS = [378, 173]
CONFIRM_POS = [401, 242]
FINAL_CONFIRM_POS = [419, 354]

# Configuração pré-definida para o Kit Terra Turbo
KIT_TERRA_CONFIG = [
    {"box": "1", "name": "Estaca", "qty": 9, "template": "dataset\\itens\\kitterra\\estaca.png"},
    {"box": "2", "name": "Estaca", "qty": 10, "template": "dataset\\itens\\kitterra\\estaca.png"},
    {"box": "3", "name": "Estaca", "qty": 10, "template": "dataset\\itens\\kitterra\\estaca.png"},
    {"box": "4", "name": "Marreta", "qty": 10, "template": "dataset\\itens\\kitterra\\marreta.png"},
    {"box": "5", "name": "Marreta", "qty": 10, "template": "dataset\\itens\\kitterra\\marreta.png"},
    {"box": "6", "name": "Marreta", "qty": 10, "template": "dataset\\itens\\kitterra\\marreta.png"},
    {"box": "7", "name": "Escritura", "qty": 10, "template": "dataset\\itens\\kitterra\\escritura.png"},
    {"box": "8", "name": "Escritura", "qty": 10, "template": "dataset\\itens\\kitterra\\escritura.png"},
    {"box": "9", "name": "Escritura", "qty": 10, "template": "dataset\\itens\\kitterra\\escritura.png"}
]

# Inicialização de objetos reutilizáveis para evitar sobrecarga
screenshotter = Screenshotter()
template_matcher = TemplateMatcher(default_threshold=0.8)

def load_config() -> Dict:
    """Carrega configuração do kit terra (versão rápida)"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Colors.BLUE}[TERRA-TURBO]{Colors.RESET} Configuração carregada")
        return config
    except Exception as e:
        print(f"{Colors.RED}[TERRA-TURBO] ERRO:{Colors.RESET} Falha ao carregar configuração: {e}")
        return {}

def quick_find_template(template_path: str, roi: List[int]) -> Tuple[bool, Tuple[int, int]]:
    """
    Versão ultra-rápida para encontrar um template na tela
    
    Args:
        template_path: Caminho para a imagem do template
        roi: Região de interesse [x, y, w, h]
        
    Returns:
        Tuple[bool, Tuple[int, int]]: (encontrado, (x, y))
    """
    # Garante que o caminho é absoluto
    if not os.path.isabs(template_path):
        template_path = os.path.join(PROJECT_ROOT, template_path)
    
    # Captura screenshot diretamente (formato OpenCV)
    screenshot = screenshotter.take_screenshot(use_pil=False)
    if screenshot is None:
        return False, (0, 0)
    
    # Converte ROI para o formato esperado
    roi_tuple = tuple(roi) if roi else None
    
    # Busca o template com threshold otimizado
    result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold=0.75)
    
    if result and result.get('found', False):
        position = result.get('position', (0, 0))
        return True, position
    
    return False, (0, 0)

def fill_box(box_config: Dict[str, Any], is_first_box: bool = False) -> bool:
    """
    Preenche uma caixa específica com o item configurado
    
    Args:
        box_config: Configuração da caixa a ser preenchida
        is_first_box: Se é a primeira caixa (precisa clicar no botão de inventário)
        
    Returns:
        bool: True se preencheu com sucesso
    """
    try:
        box_number = box_config["box"]
        template_path = box_config["template"]
        qty = box_config["qty"]
        name = box_config["name"]
        
        # Posição da caixa
        box_pos = BOX_POSITIONS[box_number]
        
        print(f"{Colors.BLUE}[TERRA-TURBO]{Colors.RESET} Preenchendo caixa {box_number} com {qty} {name}")
        
        # 1. Clique na caixa
        if not click(box_pos[0], box_pos[1]):
            return False
        
        # Espera mínima possível
        wait(0.02)  # 20ms
        
        # 2. Clique no botão de inventário (somente na primeira caixa)
        if is_first_box:
            if not click(INVENTORY_BUTTON_POS[0], INVENTORY_BUTTON_POS[1]):
                return False
            # Espera para o inventário abrir
            wait(0.03)  # 30ms
        
        # 3. Busca o item pelo template
        found, position = quick_find_template(template_path, ITEM_DETECTION_ROI)
        if not found:
            print(f"{Colors.RED}[TERRA-TURBO] ERRO:{Colors.RESET} Item {name} não encontrado")
            return False
        
        # 4. Clica no item
        if not click(position[0], position[1]):
            return False
        
        # 5. Ajusta a quantidade (apenas para a primeira caixa de estacas)
        if box_number == "1" and name == "Estaca" and qty < 10:
            # Precisa reduzir a quantidade
            wait(0.01)  # 10ms
            for _ in range(10 - qty):
                if not click(MINUS_QUANTITY_POS[0], MINUS_QUANTITY_POS[1]):
                    return False
                wait(0.01)  # 10ms espera entre cliques
        
        # 6. Confirma a seleção
        wait(0.01)  # 10ms
        if not click(CONFIRM_POS[0], CONFIRM_POS[1]):
            return False
        
        # 7. Confirma a colocação final
        if not click(FINAL_CONFIRM_POS[0], FINAL_CONFIRM_POS[1]):
            return False
        
        print(f"{Colors.GREEN}[TERRA-TURBO] SUCESSO:{Colors.RESET} Caixa {box_number} preenchida com {qty} {name}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[TERRA-TURBO] ERRO:{Colors.RESET} Falha ao preencher caixa {box_config.get('box', '?')}: {e}")
        return False

def check_connection() -> bool:
    """Verifica se há conexão com o dispositivo"""
    device = get_device()
    if not device:
        print(f"{Colors.RED}[TERRA-TURBO] ERRO:{Colors.RESET} Nenhum dispositivo conectado")
        return False
    return True

def scan_empty_boxes() -> List[str]:
    """
    Versão simplificada para verificar caixas vazias.
    No modo turbo, assumimos que todas as caixas estão vazias para maior velocidade.
    
    Returns:
        List[str]: Lista de caixas vazias (1-9)
    """
    return [str(i) for i in range(1, 10)]

def run() -> bool:
    """
    Executa o kit terra no modo turbo (ultra-rápido)
    
    Returns:
        bool: True se executado com sucesso
    """
    print(f"\n{Colors.YELLOW}===== INICIANDO TERRA TURBO ====={Colors.RESET}")
    
    # Verifica conexão
    if not check_connection():
        return False
    
    # No modo turbo, assumimos que estamos na loja e todas as caixas estão vazias
    # Isso elimina a necessidade de verificar o estado e escanear caixas
    
    first_box = True
    for i, box_config in enumerate(KIT_TERRA_CONFIG):
        # Preenche a caixa
        success = fill_box(box_config, is_first_box=first_box)
        if not success:
            print(f"{Colors.RED}[TERRA-TURBO] ERRO:{Colors.RESET} Falha ao preencher caixa {box_config['box']}")
            return False
        
        # Depois da primeira caixa, não precisamos mais clicar no botão de inventário
        if first_box:
            first_box = False
    
    print(f"{Colors.GREEN}[TERRA-TURBO] CONCLUÍDO:{Colors.RESET} Kit Terra preenchido com sucesso no modo TURBO!")
    return True

def run_with_gui_check(turbo_enabled: bool) -> bool:
    """
    Função para ser chamada diretamente da GUI
    
    Args:
        turbo_enabled: Se o modo turbo está ativado no GUI
        
    Returns:
        bool: True se executado com sucesso
    """
    if not turbo_enabled:
        print(f"{Colors.YELLOW}[TERRA-TURBO] INFO:{Colors.RESET} Modo Turbo desativado na interface. Usando kit normal.")
        # Importa e executa o kit normal
        import execution.kit_terra as kit_terra
        return kit_terra.run()
    
    # Modo turbo ativado
    return run()

# Para execução direta
if __name__ == "__main__":
    run()
