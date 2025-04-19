"""
kit_manager.py

Framework para gerenciamento de kits no HayDay.
Este módulo contém funções genéricas para preencher caixas com itens de kits,
que podem ser reutilizadas por diferentes implementações de kits.
"""

import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Union

# Importações de módulos internos
from cerebro.emulatorInteractFunction import click, wait
from cerebro.state import get_current_state_id
from screenVision.screenshotMain import Screenshotter
from screenVision.templateMatcher import TemplateMatcher

# Cores para formatação de terminal (reutilizando do Kit Terra)
class Colors:
    GREEN = '\033[92m'      # Sucesso
    YELLOW = '\033[93m'     # Aviso/Processando
    RED = '\033[91m'        # Erro
    BLUE = '\033[94m'       # Info
    RESET = '\033[0m'       # Reset

# Coordenadas comuns para todas as operações de kit
ITEM_SELECTION_CLICK = (140, 231)  # Clique para abrir menu de seleção de item
DECREASE_QUANTITY_BUTTON = (378, 173)  # Botão para diminuir quantidade
INCREASE_QUANTITY_BUTTON = (466, 172)  # Botão para aumentar quantidade
MAX_PRICE_BUTTON = (401, 242)  # Botão para definir preço máximo
SELL_BUTTON = (419, 354)  # Botão para confirmar venda

# ROIs comuns
ITEM_SELECTION_ROI = [170, 146, 174, 208]  # ROI para buscar item
QUANTITY_ROI = [363, 156, 122, 43]  # ROI para verificar quantidade

def identify_number(screenshot: Any, numbers_folder: str, roi: List[int], threshold: float = 0.85) -> int:
    """
    Identifica um número na tela dentro do ROI especificado.
    
    Args:
        screenshot: Screenshot atual
        numbers_folder: Pasta contendo as imagens dos números (1.png a 10.png)
        roi: Região de interesse [x, y, width, height]
        threshold: Limiar de confiança para detecção
        
    Returns:
        int: Número identificado (1-10) ou -1 se nenhum número for encontrado
    """
    try:
        template_matcher = TemplateMatcher(default_threshold=threshold)
        
        # Verifica cada número de 1 a 10
        best_match = None
        best_confidence = 0.0
        best_number = -1
        
        for num in range(1, 11):
            template_path = os.path.join(numbers_folder, f"{num}.png")
            
            # Verifica se o arquivo existe
            if not os.path.exists(template_path):
                print(f"{Colors.YELLOW}[KIT MANAGER] AVISO:{Colors.RESET} Template para número {num} não encontrado: {template_path}")
                continue
                
            result = template_matcher.find_template(screenshot, template_path, tuple(roi), threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_number = num
                    best_match = result
        
        if best_number > 0:
            print(f"{Colors.GREEN}[KIT MANAGER] QUANTIDADE:{Colors.RESET} Identificado número {best_number} (confiança: {best_confidence:.4f})")
            return best_number
        else:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Nenhum número identificado no ROI {roi}")
            return -1
            
    except Exception as e:
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao identificar número: {e}")
        return -1

def adjust_quantity(current_quantity: int, target_quantity: int, max_attempts: int = 5) -> bool:
    """
    Ajusta a quantidade de um item para o valor desejado.
    Otimizado para maior velocidade.
    
    Args:
        current_quantity: Quantidade atual identificada
        target_quantity: Quantidade desejada
        max_attempts: Número máximo de tentativas
        
    Returns:
        bool: True se a quantidade foi ajustada com sucesso, False caso contrário
    """
    try:
        # Verifica se a quantidade já está correta
        if current_quantity == target_quantity:
            print(f"{Colors.GREEN}[KIT MANAGER] QUANTIDADE:{Colors.RESET} Já está na quantidade correta ({target_quantity})")
            return True
            
        # Verifica se a quantidade atual é válida
        if current_quantity <= 0 or current_quantity > 10:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Quantidade atual inválida: {current_quantity}")
            return False
            
        # Calcula a diferença e determina se precisa aumentar ou diminuir
        diff = target_quantity - current_quantity
        
        if diff > 0:
            # Precisa aumentar a quantidade
            print(f"{Colors.YELLOW}[KIT MANAGER] AJUSTE:{Colors.RESET} Tentando aumentar quantidade de {current_quantity} para {target_quantity} ({diff} cliques)")
            
            for _ in range(diff):
                if not click(INCREASE_QUANTITY_BUTTON[0], INCREASE_QUANTITY_BUTTON[1]):
                    print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao clicar no botão de aumentar quantidade")
                    return False
                wait(0.02)  # Reduzido de 0.05 para 0.02 segundos
        else:
            # Precisa diminuir a quantidade
            diff = abs(diff)
            print(f"{Colors.YELLOW}[KIT MANAGER] AJUSTE:{Colors.RESET} Tentando diminuir quantidade de {current_quantity} para {target_quantity} ({diff} cliques)")
            
            for _ in range(diff):
                if not click(DECREASE_QUANTITY_BUTTON[0], DECREASE_QUANTITY_BUTTON[1]):
                    print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao clicar no botão de diminuir quantidade")
                    return False
                wait(0.02)  # Reduzido de 0.05 para 0.02 segundos
        
        # Verifica se a quantidade foi ajustada corretamente
        wait(0.1)  # Reduzido de 0.2 para 0.1 segundos
        
        # Captura nova screenshot
        screenshotter = Screenshotter()
        screenshot = screenshotter.take_screenshot(use_pil=False)
        
        if screenshot is None:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao capturar screenshot para verificar quantidade após ajuste")
            return False
            
        # Verifica a quantidade atual
        template_matcher = TemplateMatcher()
        numbers_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "numbers")
        
        # Tenta identificar a quantidade atual
        new_quantity = identify_number(screenshot, numbers_folder, QUANTITY_ROI)
        
        if new_quantity == target_quantity:
            print(f"{Colors.GREEN}[KIT MANAGER] SUCESSO:{Colors.RESET} Quantidade ajustada para {target_quantity}")
            return True
        else:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao ajustar quantidade. Atual: {new_quantity}, Alvo: {target_quantity}")
            return False
        
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Não foi possível ajustar para a quantidade desejada após {max_attempts} tentativas")
        return False
        
    except Exception as e:
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao ajustar quantidade: {e}")
        return False

def select_item(item_template_path: str, max_attempts: int = 3, threshold: float = 0.85) -> bool:
    """
    Seleciona um item na interface de seleção de itens.
    Otimizado para alta velocidade.
    
    Args:
        item_template_path: Caminho para a imagem do template do item
        max_attempts: Número máximo de tentativas
        threshold: Limiar de confiança para detecção
        
    Returns:
        bool: True se o item foi selecionado com sucesso, False caso contrário
    """
    try:
        # Garante que o caminho é absoluto
        if not os.path.isabs(item_template_path):
            item_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), item_template_path)
            
        print(f"{Colors.YELLOW}[KIT MANAGER] SELEÇÃO:{Colors.RESET} Buscando item {os.path.basename(item_template_path)}")
        
        # Inicializa o matcher e screenshotter
        template_matcher = TemplateMatcher(default_threshold=threshold)
        screenshotter = Screenshotter()
        
        for attempt in range(max_attempts):
            # Captura uma screenshot
            screenshot = screenshotter.take_screenshot(use_pil=False)
            if screenshot is None:
                print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao capturar screenshot")
                continue
                
            # Busca o template do item na ROI específica
            result = template_matcher.find_template(screenshot, item_template_path, tuple(ITEM_SELECTION_ROI), threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                
                print(f"{Colors.GREEN}[KIT MANAGER] ITEM ENCONTRADO:{Colors.RESET} Item encontrado na posição {position} (confiança: {confidence:.4f})")
                
                # Clica no item
                if click(position[0], position[1]):
                    print(f"{Colors.GREEN}[KIT MANAGER] SUCESSO:{Colors.RESET} Item selecionado com sucesso")
                    return True
                else:
                    print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao clicar no item")
                    
            if attempt < max_attempts - 1:
                print(f"{Colors.YELLOW}[KIT MANAGER] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Item não encontrado, tentando novamente...")
                wait(0.15)  # Reduzido de 0.3 para 0.15 segundos
        
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Item não encontrado após {max_attempts} tentativas")
        return False
        
    except Exception as e:
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao selecionar item: {e}")
        return False

def fill_box(box_index: int, box_position: Tuple[int, int], item_config: Dict[str, Any], is_first_box: bool = False) -> bool:
    """
    Preenche uma caixa específica com um item configurado.
    Otimizado para maior velocidade de venda.
    
    Args:
        box_index: Índice da caixa (1-10)
        box_position: Posição (x, y) da caixa para clique
        item_config: Configuração do item (template, quantidade)
        is_first_box: Se é a primeira caixa do item (que geralmente tem 9 unidades)
        
    Returns:
        bool: True se a caixa foi preenchida com sucesso, False caso contrário
    """
    try:
        template_path = item_config.get('template_path', '')
        default_quantity = item_config.get('default_quantity', 10)
        first_box_quantity = item_config.get('first_box_quantity', 9)
        
        # Define a quantidade alvo com base em se é primeira caixa ou não
        target_quantity = first_box_quantity if is_first_box else default_quantity
        
        print(f"{Colors.BLUE}[KIT MANAGER] INFO:{Colors.RESET} Preenchendo caixa {box_index} com item {os.path.basename(template_path)} ({target_quantity} unidades)")
        
        # 1. Clica na caixa
        print(f"{Colors.YELLOW}[KIT MANAGER] AÇÃO:{Colors.RESET} Clicando na caixa {box_index} ({box_position})")
        if not click(box_position[0], box_position[1]):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao clicar na caixa {box_index}")
            return False
            
        # 2. Aguarda apenas um tempo mínimo
        wait(0.02)  # Reduzido de 0.05 para 0.02 segundos
        
        # 3. Clica para abrir o menu de seleção de item
        print(f"{Colors.YELLOW}[KIT MANAGER] AÇÃO:{Colors.RESET} Abrindo menu de seleção de item")
        if not click(ITEM_SELECTION_CLICK[0], ITEM_SELECTION_CLICK[1]):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao abrir menu de seleção de item")
            return False
            
        # 4. Aguarda o menu abrir - reduzido em 33%
        wait(0.13)  # Reduzido de 0.2 para 0.13 segundos
        
        # 5. Seleciona o item
        if not select_item(template_path):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao selecionar item para caixa {box_index}")
            return False
            
        # 6. Aguarda a seleção do item - reduzido em 50%
        wait(0.1)  # Reduzido de 0.2 para 0.1 segundos
        
        # 7. Verifica e ajusta a quantidade
        screenshotter = Screenshotter()
        screenshot = screenshotter.take_screenshot(use_pil=False)
        
        if screenshot is None:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao capturar screenshot para verificar quantidade")
            return False
            
        numbers_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "numbers")
        current_quantity = identify_number(screenshot, numbers_folder, QUANTITY_ROI)
        
        if not adjust_quantity(current_quantity, target_quantity):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao ajustar quantidade para caixa {box_index}")
            return False
            
        # 8. Clica no botão de preço máximo
        print(f"{Colors.YELLOW}[KIT MANAGER] AÇÃO:{Colors.RESET} Configurando preço máximo")
        if not click(MAX_PRICE_BUTTON[0], MAX_PRICE_BUTTON[1]):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao configurar preço máximo")
            return False
            
        wait(0.05)  # Reduzido de 0.1 para 0.05 segundos
        
        # 9. Clica no botão de vender
        print(f"{Colors.YELLOW}[KIT MANAGER] AÇÃO:{Colors.RESET} Confirmando venda")
        if not click(SELL_BUTTON[0], SELL_BUTTON[1]):
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao confirmar venda")
            return False
            
        wait(0.12)  # Reduzido de 0.2 para 0.12 segundos
        
        print(f"{Colors.GREEN}[KIT MANAGER] SUCESSO:{Colors.RESET} Caixa {box_index} preenchida com sucesso!")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao preencher caixa {box_index}: {e}")
        return False

def process_kit(kit_config: Dict[str, Any], empty_boxes: List[int]) -> bool:
    """
    Processa um kit completo, preenchendo as caixas vazias com os itens configurados.
    Cada item só será colocado nas caixas especificadas em sua configuração default_boxes.
    
    Args:
        kit_config: Configuração completa do kit
        empty_boxes: Lista de índices das caixas vazias (1-10)
        
    Returns:
        bool: True se o processamento foi bem-sucedido, False caso contrário
    """
    try:
        print(f"{Colors.BLUE}[KIT MANAGER] INÍCIO:{Colors.RESET} Iniciando processamento do kit")
        
        box_positions = kit_config.get('box_positions', {})
        items = kit_config.get('items', [])
        
        if not items:
            print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Nenhum item configurado para o kit")
            return False
            
        if not empty_boxes:
            print(f"{Colors.YELLOW}[KIT MANAGER] AVISO:{Colors.RESET} Nenhuma caixa vazia para processar")
            return True
            
        print(f"{Colors.BLUE}[KIT MANAGER] INFO:{Colors.RESET} Processando {len(items)} tipos de itens para {len(empty_boxes)} caixas vazias")
        
        # Contamos quantas caixas foram preenchidas
        filled_boxes = 0
        
        # Para cada item na lista de itens
        for item_index, item in enumerate(items):
            # Obtém a lista de caixas permitidas para este item
            default_boxes = item.get('default_boxes', [])
            
            if not default_boxes:
                print(f"{Colors.YELLOW}[KIT MANAGER] AVISO:{Colors.RESET} Item {item.get('name', 'desconhecido')} não tem caixas definidas")
                continue
                
            # Determina qual é a VERDADEIRA primeira caixa definida na configuração
            first_box_in_config = min(default_boxes) if default_boxes else 0
            
            # Para cada caixa permitida para este item
            for box_index in default_boxes:
                # Verifica se esta caixa está vazia (está na lista de caixas vazias)
                if box_index not in empty_boxes:
                    print(f"{Colors.BLUE}[KIT MANAGER] INFO:{Colors.RESET} Caixa {box_index} não está vazia, pulando")
                    continue
                    
                # Converte para string para usar como chave no dicionário
                box_key = str(box_index)
                
                if box_key not in box_positions:
                    print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Posição da caixa {box_index} não encontrada")
                    continue
                    
                box_position = box_positions[box_key]
                
                # Determina se esta é realmente a primeira caixa do item segundo a configuração
                is_first_box = (box_index == first_box_in_config)
                
                # Preenche a caixa
                if fill_box(box_index, box_position, item, is_first_box):
                    filled_boxes += 1
                else:
                    print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao preencher caixa {box_index}")
        
        if filled_boxes > 0:
            print(f"{Colors.GREEN}[KIT MANAGER] SUCESSO:{Colors.RESET} Preenchidas {filled_boxes} caixas no total")
        else:
            print(f"{Colors.YELLOW}[KIT MANAGER] AVISO:{Colors.RESET} Nenhuma caixa foi preenchida")
        
        print(f"{Colors.GREEN}[KIT MANAGER] CONCLUSÃO:{Colors.RESET} Processamento do kit concluído!")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}[KIT MANAGER] ERRO:{Colors.RESET} Falha ao processar kit: {e}")
        return False
