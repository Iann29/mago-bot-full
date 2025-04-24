"""
Celeiro Turbo - Módulo de automação ultra-rápido para o kit celeiro no HayDay.
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

# Cores para logs essenciais
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

# Caminhos de configuração
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "execution", "kit_celeiroCFG.json")
ITEMS_CONFIG_PATH = os.path.join(PROJECT_ROOT, "execution", "kit_celeiro_items.json")

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

# Configuração pré-definida para o Kit Celeiro Turbo
KIT_CELEIRO_CONFIG = [
    {"box": "1", "name": "Rebite", "qty": 9, "template": "dataset\\itens\\kitceleiro\\rebite.png"},
    {"box": "2", "name": "Rebite", "qty": 10, "template": "dataset\\itens\\kitceleiro\\rebite.png"},
    {"box": "3", "name": "Rebite", "qty": 10, "template": "dataset\\itens\\kitceleiro\\rebite.png"},
    {"box": "4", "name": "Tábua", "qty": 10, "template": "dataset\\itens\\kitceleiro\\tabua.png"},
    {"box": "5", "name": "Tábua", "qty": 10, "template": "dataset\\itens\\kitceleiro\\tabua.png"},
    {"box": "6", "name": "Tábua", "qty": 10, "template": "dataset\\itens\\kitceleiro\\tabua.png"},
    {"box": "7", "name": "Fita", "qty": 10, "template": "dataset\\itens\\kitceleiro\\fita.png"},
    {"box": "8", "name": "Fita", "qty": 10, "template": "dataset\\itens\\kitceleiro\\fita.png"},
    {"box": "9", "name": "Fita", "qty": 10, "template": "dataset\\itens\\kitceleiro\\fita.png"}
]

# Inicialização de objetos reutilizáveis para evitar sobrecarga
screenshotter = Screenshotter()
template_matcher = TemplateMatcher(default_threshold=0.8)

def quick_find_template(template_path: str, roi: List[int], max_attempts: int = 3) -> Tuple[bool, Tuple[int, int]]:
    """
    Versão melhorada para encontrar um template na tela com múltiplas tentativas
    
    Args:
        template_path: Caminho para a imagem do template
        roi: Região de interesse [x, y, w, h]
        max_attempts: Número máximo de tentativas
        
    Returns:
        Tuple[bool, Tuple[int, int]]: (encontrado, (x, y))
    """
    # Garante que o caminho é absoluto
    if not os.path.isabs(template_path):
        template_path = os.path.join(PROJECT_ROOT, template_path)
    
    # Converte ROI para o formato esperado
    roi_tuple = tuple(roi) if roi else None
    
    # Faz múltiplas tentativas para encontrar o template
    for attempt in range(max_attempts):
        # Captura screenshot diretamente (formato OpenCV)
        screenshot = screenshotter.take_screenshot(use_pil=False)
        if screenshot is None:
            continue
        
        # Busca o template com threshold otimizado (mais baixo para maior sensibilidade)
        result = template_matcher.find_template(screenshot, template_path, roi_tuple, threshold=0.72)
        
        if result and result.get('found', False):
            position = result.get('position', (0, 0))
            confidence = result.get('confidence', 0.0)
            print(f"Item encontrado (confiança: {confidence:.4f}) na posição {position}")
            return True, position
        
        # Pequena espera entre tentativas, mas não espera fixa no final
        if attempt < max_attempts - 1:
            wait(0.05)  # 50ms entre tentativas
    
    # Após tentar o número máximo de vezes sem sucesso
    return False, (0, 0)

def fill_box(box_config: Dict[str, Any], is_first_box: bool = False) -> bool:
    """
    Preenche uma caixa específica com o item configurado - versão ultra-rápida sem logs
    
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
        
        print(f"{Colors.GREEN}[TURBO]{Colors.RESET} Caixa {box_number}: {name} ({qty})")
        
        # 1. Clique na caixa
        click(box_pos[0], box_pos[1])
        wait(0.02)  # 20ms - espera mínima para a interface responder
        
        # 2. Clique no botão de inventário (somente na primeira caixa)
        if is_first_box:
            click(INVENTORY_BUTTON_POS[0], INVENTORY_BUTTON_POS[1])
            wait(0.05)  # 50ms para o menu abrir
        
        # 3. Busca o item pelo template - com múltiplas tentativas
        found, position = quick_find_template(template_path, ITEM_DETECTION_ROI, max_attempts=4)
        if not found:
            print(f"{Colors.RED}[TURBO-ERRO]{Colors.RESET} Item {name} não encontrado após múltiplas tentativas")
            return False
        
        # 4. Clica no item encontrado
        click(position[0], position[1])
        wait(0.05)  # 50ms para garantir que o clique foi processado
        
        # 5. Ajusta a quantidade (apenas para a primeira caixa de rebites)
        if box_number == "1" and name == "Rebite" and qty < 10:
            for _ in range(10 - qty):
                click(MINUS_QUANTITY_POS[0], MINUS_QUANTITY_POS[1])
                wait(0.02)  # 20ms entre cliques de ajuste
        
        # 6. Confirma a seleção (preço máximo)
        wait(0.05)  # 50ms antes de confirmar
        click(CONFIRM_POS[0], CONFIRM_POS[1])
        wait(0.05)  # 50ms entre botões
        
        # 7. Confirma a colocação final (vender)
        click(FINAL_CONFIRM_POS[0], FINAL_CONFIRM_POS[1])
        wait(0.05)  # 50ms após a confirmação final
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[TURBO-ERRO]{Colors.RESET} Caixa {box_config.get('box', '?')}: {e}")
        return False

def check_connection() -> bool:
    """Verifica se há conexão com o dispositivo"""
    device = get_device()
    if not device:
        print(f"{Colors.RED}[TURBO-ERRO]{Colors.RESET} Sem conexão")
        return False
    return True

# Função não utilizada no fluxo principal, mantida apenas como referência
def scan_empty_boxes() -> List[str]:
    """Retorna as caixas 1-9 (sem verificação)"""
    return [str(i) for i in range(1, 10)]

def run() -> bool:
    """
    Executa o kit celeiro no modo turbo (ultra-rápido)
    
    Returns:
        bool: True se executado com sucesso
    """
    print(f"{Colors.GREEN}[TURBO]{Colors.RESET} Iniciando")
    
    # Verifica conexão uma única vez no início
    if not check_connection():
        return False
    
    # No modo turbo, assumimos que estamos na loja e todas as caixas estão vazias
    # Isso elimina a necessidade de verificar o estado e escanear caixas
    
    first_box = True
    for box_config in KIT_CELEIRO_CONFIG:
        # Preenche a caixa
        if not fill_box(box_config, is_first_box=first_box):
            return False
        
        # Depois da primeira caixa, não precisamos mais clicar no botão de inventário
        if first_box:
            first_box = False
    
    print(f"{Colors.GREEN}[TURBO]{Colors.RESET} Concluído!")
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
        # Usa o kit normal
        import execution.kit_celeiro as kit_celeiro
        return kit_celeiro.run()
    
    # Modo turbo ativado
    return run()

# Para execução direta
if __name__ == "__main__":
    run()
