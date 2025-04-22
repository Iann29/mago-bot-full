"""
Módulo para verificar o lucro da conta no HayDay.
"""

import json
import os
import time
import cv2
import numpy as np
import queue
import base64
import sys
import io
from io import BytesIO
from PIL import Image
from openai import OpenAI
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
                
                return search_template(template_path, roi, max_attempts, threshold, use_mask)
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

def search_template(template_path: str, roi: List[int], max_attempts: int = 2, threshold: float = 0.8, use_mask: bool = False) -> bool:
    """
    Busca um template na tela atual e clica nele se encontrado.
    Implementa uma estratégia avançada de cliques com deslocamentos para garantir abertura da loja.
    
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
        print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Usando template matcher com máscara")
        
        # Deriva o caminho da máscara
        mask_path = template_path.replace('.png', 'mask.png')
        if not os.path.exists(mask_path):
            # Tenta encontrar em outro formato de nome
            mask_path = os.path.splitext(template_path)[0] + "mask" + os.path.splitext(template_path)[1]
            if not os.path.exists(mask_path):
                print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Máscara não encontrada para {template_path}")
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
        print(f"{Colors.YELLOW}[LUCRO] BUSCANDO COM MÁSCARA:{Colors.RESET} Template '{os.path.basename(template_path)}' (ROI: {roi})")
        print(f"{Colors.YELLOW}[LUCRO] MÁSCARA:{Colors.RESET} '{os.path.basename(mask_path)}'")
    else:
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
            
            # Busca o template com ou sem máscara dependendo da configuração
            if use_mask:
                result = template_matcher.find_template(screenshot_cv, template_path, mask_path, roi_tuple)
            else:
                result = template_matcher.find_template(screenshot_cv, template_path, roi_tuple, threshold)
            
            if result and result.get('found', False):
                confidence = result.get('confidence', 0.0)
                position = result.get('position', (0, 0))
                print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Template {'com máscara ' if use_mask else ''}encontrado na posição {position} (confiança: {confidence:.4f})")
                
                # Tentativas de clique com deslocamentos variados
                # Primeiro tenta na posição original
                print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Tentando clique na posição original {position}")
                success = click(position[0], position[1])
                
                if success:
                    # Aguarda um pouco para ver se o estado muda para inside_shop
                    print(f"{Colors.YELLOW}[LUCRO] AGUARDANDO:{Colors.RESET} Verificando se o estado mudou após o clique... (1.5s)")
                    wait(1.5)  # Aguarda 1.5 segundos para o estado mudar após clique inicial
                    
                    # Verifica se o estado atual é loja_aberta ou algum estado subsequente (como "escolhendo_item")
                    current_state_id = get_current_state_id()
                    current_state_name = get_current_state()
                    
                    # Lista de estados válidos que indicam que a loja foi aberta com sucesso
                    success_states = ["loja_aberta", "escolhendo_item", "inside_shop"]
                    
                    if current_state_id in success_states:
                        print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Loja aberta com sucesso! (Estado: {current_state_name})")
                        
                        # Capturar e analisar o nome da conta via OCR
                        account_info = extract_account_name()
                        if account_info:
                            print(f"{Colors.GREEN}[LUCRO] INFO:{Colors.RESET} Informações da conta extraídas: {account_info}")
                            
                            # Realizar cliques nas coordenadas especificadas
                            print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas (177, 207)")
                            click(177, 207)
                            wait(0.5)  # Aguarda meio segundo
                            
                            print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas do item_selection_click (140, 231)")
                            click(140, 231)
                            wait(0.5)  # Aguarda meio segundo
                        
                        return True
                    
                    # Se não mudou para loja_aberta, tenta deslocamentos
                    print(f"{Colors.YELLOW}[LUCRO] AVISO:{Colors.RESET} Clique na posição original não abriu a loja. Tentando deslocamentos...")
                    
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
                        # Verifica o estado atual ANTES de tentar um novo deslocamento
                        # Se já estamos na loja ou em algum menu, não precisa continuar tentando
                        current_state_before_click = get_current_state_id()
                        current_state_name = get_current_state()
                        
                        # Lista de estados válidos que indicam que a loja foi aberta com sucesso
                        success_states = ["loja_aberta", "escolhendo_item", "inside_shop"]
                        
                        if current_state_before_click in success_states:
                            print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Loja já está aberta (Estado: {current_state_name}), não é necessário continuar tentando deslocamentos")
                            return True
                            
                        new_x, new_y = position[0] + dx, position[1] + dy
                        print(f"{Colors.YELLOW}[LUCRO] TENTATIVA {i+1}/{len(offsets)}:{Colors.RESET} Clicando em posição deslocada ({new_x}, {new_y})")
                        
                        if click(new_x, new_y):
                            # Aguarda por 1.4 segundos para ver se o estado muda
                            print(f"{Colors.YELLOW}[LUCRO] AGUARDANDO:{Colors.RESET} Verificando por 1.4s se o estado mudou após clique com deslocamento...")
                            wait(1.4)  # Aguarda 1.4 segundos para o estado mudar após cliques com deslocamento
                            current_state_id = get_current_state_id()
                            # Lista de estados válidos que indicam que a loja foi aberta com sucesso
                            success_states = ["loja_aberta", "escolhendo_item", "inside_shop"]
                            
                            if current_state_id in success_states:
                                print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Loja aberta com sucesso após tentativa com deslocamento! (Estado: {get_current_state()})")
                                
                                # Capturar e analisar o nome da conta via OCR
                                account_info = extract_account_name()
                                if account_info:
                                    print(f"{Colors.GREEN}[LUCRO] INFO:{Colors.RESET} Informações da conta extraídas: {account_info}")
                                    
                                    # Realizar cliques nas coordenadas especificadas
                                    print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas (177, 207)")
                                    click(177, 207)
                                    wait(0.5)  # Aguarda meio segundo
                                    
                                    print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas do item_selection_click (140, 231)")
                                    click(140, 231)
                                    wait(0.5)  # Aguarda meio segundo
                                
                                return True
                    
                    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Todas as tentativas de clique falharam em abrir a loja")
                    return False
                else:
                    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao clicar na posição {position}")
                    return False
            
            print(f"{Colors.YELLOW}[LUCRO] TENTATIVA {attempt+1}/{max_attempts}:{Colors.RESET} Template não encontrado")
        except Exception as e:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao processar screenshot: {e}")
        
        wait(0.5)  # Pequena pausa antes da próxima tentativa
    
    print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Template não encontrado após {max_attempts} tentativas")
    return False

# Função para extrair o nome da conta via OCR usando OpenAI
def extract_account_name():
    """Extrai o nome da conta usando OCR via OpenAI."""
    try:
        print(f"{Colors.BLUE}[LUCRO] OCR:{Colors.RESET} Extraindo nome da conta...")
        
        # ROI de onde está o nome da conta (ajustar conforme necessário)
        roi = (331, 118, 111, 37)  # (x, y, largura, altura)
        
        # Guarda o stdout original e suprime mensagens de log
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            # Importa aqui para evitar importação circular
            from screenVision.screenshotMain import Screenshotter
            
            # Captura screenshot de forma silenciosa
            screenshotter = Screenshotter()
            screenshot = screenshotter.take_screenshot(use_pil=False)
        finally:
            # Restaura o stdout independente do resultado
            sys.stdout = original_stdout
        
        if screenshot is None:
            print(f"{Colors.RED}[LUCRO] OCR ERRO:{Colors.RESET} Falha ao capturar screenshot")
            return None
            
        # Extrai ROI
        x, y, w, h = roi
        roi_image = screenshot[y:y+h, x:x+w]
        
        # Converte para base64
        # Converter de BGR para RGB
        rgb_image = cv2.cvtColor(roi_image, cv2.COLOR_BGR2RGB)
        
        # Converter para PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Salvar em buffer na memória
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Converter para base64
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Analisar com GPT
        client = OpenAI(api_key="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")
        
        print(f"{Colors.BLUE}[LUCRO] OCR:{Colors.RESET} Enviando imagem para análise com GPT-4.1-mini...")
        
        # Criar a requisição
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "text": "Look at the attached image and return exactly what is written starting from the @ symbol.\n\nThe format is always: @magodohayday-(X)-N-(Y)\n\n- The middle character is always \"N\", even if it looks different, it must be corrected to \"N\".\n- X can be: T, S, C, Se, Pa, Ma, M\n- Y is always a number, and it can be **one or more digits** (e.g., 1, 2, 12, 25, etc.)\n\nYou must return the **full number**, without cutting or guessing.\n\nReturn this in JSON format, without modifying other parts.\n\nExample:\n{\n  \"accountName\": \"@magodohayday-T-N-12\"\n}\n",
                            "type": "text"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_object"
            },
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False
        )
        
        result = response.choices[0].message.content
        
        # Retorna o JSON com o nome da conta
        return result
    except Exception as e:
        print(f"{Colors.RED}[LUCRO] OCR ERRO:{Colors.RESET} {e}")
        return None

state_changed_flag = False
last_detected_state_id = None
pending_restart = False

# Variável global para rastrear se ainda estamos aguardando o OCR ser executado
waiting_for_ocr = False

def on_state_change_during_execution(previous_state, new_state_name):
    """
    Função de callback para detectar mudanças de estado durante a execução.
    
    Args:
        previous_state: Estado anterior
        new_state_name: Nome do novo estado
    """
    global state_changed_flag, last_detected_state_id, pending_restart, ocr_executed, waiting_for_ocr, ocr_success
    
    # Obtém o ID do novo estado usando a função global
    from cerebro.state import get_current_state_id
    
    # Obtém o ID do estado atual
    last_detected_state_id = get_current_state_id()
    
    # Sinaliza que o estado mudou durante a execução
    state_changed_flag = True
    
    # Se o estado mudou para aba_tutorial_colher, sinaliza para reiniciar a execução
    if last_detected_state_id == "aba_tutorial_colher":
        print(f"{Colors.YELLOW}[LUCRO] DETECTADO:{Colors.RESET} O popup de tutorial apareceu! Interrompendo ação atual...")
        pending_restart = True
    
    # Se o estado mudou para inside_shop, estávamos esperando por isso, e ainda não executamos o OCR    
    if waiting_for_ocr and last_detected_state_id == "inside_shop" and not ocr_executed:
        wait(1.0)  # Aguarda 1 segundo para estabilizar a tela
        print(f"{Colors.BLUE}[LUCRO] DETECTADO:{Colors.RESET} Estado '{new_state_name}' detectado. Executando OCR...")
        account_info = extract_account_name()
        if account_info:
            print(f"{Colors.GREEN}[LUCRO] INFO:{Colors.RESET} Informações da conta extraídas: {account_info}")
            ocr_executed = True  # Marca que o OCR já foi executado para não repetir
            
            # Agora que temos o nome da conta, realizamos os cliques nas coordenadas especificadas
            print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas (177, 207)")
            click(177, 207)
            wait(0.5)  # Aguarda meio segundo
            
            print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas do item_selection_click (140, 231)")
            click(140, 231)
            wait(0.5)  # Aguarda meio segundo
            
            # Marca que o OCR foi concluído com sucesso - IMPORTANTE: essa variável é verificada na função principal
            waiting_for_ocr = False
            ocr_success = True
            print(f"{Colors.GREEN}[LUCRO] OCR CONCLUÍDO:{Colors.RESET} Análise de conta finalizada com sucesso!")

# Flags para controlar o estado da execução
ocr_executed = False
ocr_complete = False  # Nova flag para indicar se o OCR foi concluído com sucesso

# Variável global para indicar que o OCR foi concluído com sucesso
ocr_success = False

def verificar_lucro() -> bool:
    """
    Verifica o lucro da conta no HayDay.
    
    Returns:
        bool: True se a operação foi concluída com sucesso, False caso contrário
    """
    global state_changed_flag, last_detected_state_id, pending_restart, ocr_executed, waiting_for_ocr, ocr_success
    
    # Reset de todas as variáveis de estado
    state_changed_flag = False
    last_detected_state_id = None
    pending_restart = False
    ocr_executed = False
    waiting_for_ocr = False
    ocr_success = False
    
    # Flag para controlar se o callback foi registrado
    callback_registered = False
    
    try:
        # Registra o callback para detectar mudanças de estado durante a execução
        from cerebro.state import register_state_callback
        
        try:
            # Registra o callback
            register_state_callback(on_state_change_during_execution)
            callback_registered = True
        except Exception as e:
            print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} Não foi possível registrar o callback de estado: {e}")

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
            
        # Loop principal - permite reiniciar a execução se o estado mudar para aba_tutorial_colher
        max_restarts = 3  # Número máximo de reinicializações permitidas
        restart_count = 0
        
        while restart_count <= max_restarts:
            # Reinicia as flags
            state_changed_flag = False
            pending_restart = False
            
            # Obtém o estado atual
            current_state_id = get_current_state_id()
            current_state = get_current_state()
            
            print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Estado atual: {current_state} (ID: {current_state_id})")
            
            # Verifica se já estamos em inside_shop e executa OCR se necessário
            if not ocr_executed and current_state_id == "inside_shop":
                print(f"{Colors.BLUE}[LUCRO] DETECTADO:{Colors.RESET} Já estamos no estado '{current_state}'. Executando OCR...")
                account_info = extract_account_name()
                if account_info:
                    print(f"{Colors.GREEN}[LUCRO] INFO:{Colors.RESET} Informações da conta extraídas: {account_info}")
                    ocr_executed = True
                    
                    # Agora que temos o nome da conta, realizamos os cliques nas coordenadas especificadas
                    print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas (177, 207)")
                    click(177, 207)
                    wait(0.5)  # Aguarda meio segundo
                    
                    print(f"{Colors.BLUE}[LUCRO] AÇÃO:{Colors.RESET} Clicando nas coordenadas do item_selection_click (140, 231)")
                    click(140, 231)
                    wait(0.5)  # Aguarda meio segundo
                    
                    # Marca que o OCR foi concluído com sucesso
                    ocr_complete = True
            
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
                    
                    # Executa a ação atual
                    result = execute_action(action)
                    
                    # Se for uma ação searchTemplate e for bem-sucedida, mostramos o estado atual
                    if action.get("type") == "searchTemplate" and result:
                        current_state = get_current_state()
                        current_state_id = get_current_state_id()
                        print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Template encontrado e clicado! Estado atual: {current_state} (ID: {current_state_id})")
                    
                    # Se qualquer ação falhar, interrompemos o processo
                    if not result:
                        print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha ao executar ação {i+1}")
                        return False
                    
                    # Verificamos apenas se a ação searchTemplate foi bem-sucedida
                # Se chegamos aqui, significa que todas as ações foram executadas
                if current_state_id == "inside_shop":
                    # Se estamos na loja, aguarda até que o OCR seja concluído
                    if not ocr_complete:
                        print(f"{Colors.YELLOW}[LUCRO] AGUARDANDO:{Colors.RESET} Aguardando conclusão do OCR...")
                        for _ in range(10):  # Tenta por até 5 segundos
                            if ocr_complete:
                                break
                            wait(0.5)
                    
                    if ocr_complete:
                        print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Detecção, OCR e acesso à banca concluídos com sucesso")
                        return True
                    else:
                        print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} OCR não foi concluído no tempo esperado")
                        return False
                else:
                    # Estado item_shop_list - este é o estado importante onde precisamos bloquear até que o OCR seja concluído
                    if current_state_id == "item_shop_list":
                        # PRIMEIRO: clica para verificar o lucro
                        print(f"{Colors.YELLOW}[LUCRO] BLOQUEANDO:{Colors.RESET} Aguardando até a conclusão do OCR...")
                        waiting_for_ocr = True
                        
                        # SEGUNDO: aguarda até que o OCR seja concluído com sucesso
                        max_wait_seconds = 60  # Aumentamos o tempo de espera para 60 segundos
                        start_time = time.time()
                        
                        print(f"{Colors.YELLOW}[LUCRO] IMPORTANTE:{Colors.RESET} NÃO CLIQUE EM NADA! Aguardando execução do OCR...")
                        
                        # Loop de espera que só termina quando ocr_success = True (definido no callback)
                        while time.time() - start_time < max_wait_seconds:
                            # SUCESSO: OCR foi executado com sucesso
                            if ocr_success:
                                print(f"{Colors.GREEN}[LUCRO] DESBLOQUEADO:{Colors.RESET} OCR concluído com sucesso!")
                                return True
                            
                            # Verifica mudança de estado
                            if state_changed_flag and last_detected_state_id == "inside_shop":
                                print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Estado atual: inside_shop. Aguardando execução do OCR...")
                            
                            # Pequena pausa para não sobrecarregar a CPU
                            wait(0.5)
                        
                        # Se chegou aqui, o tempo limite foi excedido
                        print(f"{Colors.RED}[LUCRO] TIMEOUT:{Colors.RESET} Tempo limite de {max_wait_seconds}s excedido aguardando OCR.")
                        return False
                    else:
                        # Se não estamos na loja nem no item_shop_list, apenas finaliza normalmente
                        print(f"{Colors.GREEN}[LUCRO] SUCESSO:{Colors.RESET} Detecção e acesso à banca concluído com sucesso")
                        return True
            else:
                print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} Não há configuração para o estado atual '{current_state}' (ID: {current_state_id})")
                states_available = list(states_config.keys())
                print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Estados configurados disponíveis: {states_available}")
                return False
            
            # Se chegou aqui, é porque todas as ações foram executadas com sucesso
            break
            
        # Verifica se excedeu o número máximo de tentativas
        if restart_count > max_restarts:
            print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Excedeu o número máximo de reinicializações ({max_restarts})")
            return False
            
        return True
            
    except Exception as e:
        print(f"{Colors.RED}[LUCRO] ERRO:{Colors.RESET} Falha geral na verificação de lucro: {e}")
        return False
    finally:
        # Remove o callback para evitar problemas
        if callback_registered:
            try:
                from cerebro.state import register_state_callback
                # Como não temos unregister_state_callback, registramos um callback vazio para substituir
                # O callback anterior será sobrescrito, o que efetivamente o desregistra
                def empty_callback(prev, new):
                    pass
                register_state_callback(empty_callback)
                print(f"{Colors.BLUE}[LUCRO] INFO:{Colors.RESET} Callback de estado removido")
            except Exception as e:
                print(f"{Colors.YELLOW}[LUCRO] ALERTA:{Colors.RESET} Não foi possível remover o callback: {e}")

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
    # Executa o teste (o callback já é registrado dentro da função verificar_lucro)
    run()
