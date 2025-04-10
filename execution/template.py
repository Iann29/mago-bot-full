# /execution/template.py

import sys
import os
import time 
import json
import cv2
import numpy as np
from datetime import datetime

# Adiciona a raiz do projeto ao PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importa os MÓDULOS que fazem o trabalho pesado
from screenVision.screenshotMain import Screenshotter
from screenVision.templateMatcher import TemplateMatcher
from ADBmanager import adb_manager # Importa o Singleton manager

# Carrega as configurações específicas do template
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templateCFG.json')
try:
    with open(config_path, 'r') as f:
        template_config = json.load(f)
    print(f"Configurações de template carregadas de {config_path}")
except Exception as e:
    print(f"Erro ao carregar configurações de template: {e}")
    template_config = {}  # Configuração vazia se falhar

# Configurações de debug do template
DEBUG_MODE = template_config.get("debug_mode", False)  # Configuração específica para templates
DEBUG_OUTPUT_DIR = template_config.get("debug_output_dir", "output_template_matches")
DEFAULT_CONFIDENCE = template_config.get("default_confidence_threshold", 0.7)
DEFAULT_TEMPLATE_FOLDER = template_config.get("default_template_folder", "dataset/outsideHayDay")
COMMON_TEMPLATES = template_config.get("common_templates", {})

# Cria o diretório de saída para as imagens de debug se necessário
debug_output_path = os.path.join(project_root, DEBUG_OUTPUT_DIR)
os.makedirs(debug_output_path, exist_ok=True)

def draw_bounds_on_image(image, result, template_name):
    """
    Desenha os limites (bounding box) onde o template foi encontrado na imagem.
    
    Args:
        image (np.ndarray): Imagem original onde o template foi encontrado
        result (dict): Resultado retornado pelo TemplateMatcher.find_template
        template_name (str): Nome do template para incluir na legenda
        
    Returns:
        np.ndarray: Imagem com os bounds desenhados
    """
    if not result or not result.get('found'):
        return image.copy()
    
    # Faz uma cópia da imagem para não modificar a original
    debug_image = image.copy()
    
    # Obtém as coordenadas do retângulo
    rect = result.get('rectangle')
    if not rect or len(rect) != 4:
        return debug_image
    
    x_min, y_min, x_max, y_max = rect
    
    # Desenha o retângulo verde
    cv2.rectangle(debug_image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
    
    # Adiciona texto com o nome do template e confiança
    confidence = result.get('confidence', 0.0)
    text = f"{os.path.basename(template_name)} ({confidence:.2f})"
    cv2.putText(debug_image, text, (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Desenha o ponto central
    center_x, center_y = result.get('position')
    cv2.circle(debug_image, (center_x, center_y), 5, (0, 0, 255), -1)
    
    return debug_image


def save_debug_image(image, filename_prefix):
    """
    Salva a imagem de debug no diretório configurado.
    
    Args:
        image (np.ndarray): Imagem a ser salva
        filename_prefix (str): Prefixo para o nome do arquivo
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.png"
    save_path = os.path.join(debug_output_path, filename)
    
    try:
        cv2.imwrite(save_path, image)
        print(f"✅ Debug: Imagem salva em {save_path}")
    except Exception as e:
        print(f"❌ Debug: Erro ao salvar imagem: {e}")


def find_template(template_name=None, custom_path=None, roi=None, confidence_threshold=None, silent=False):
    """
    Usa os módulos existentes para capturar uma screenshot e procurar um template.
    
    Args:
        template_name (str, optional): Nome de um template definido no arquivo de configuração.
        custom_path (str, optional): Caminho personalizado para um template não definido no config.
        roi (tuple, optional): Região de interesse personalizada (x, y, w, h).
        confidence_threshold (float, optional): Nível de confiança personalizado.
        
    Returns:
        dict or None: O resultado da busca ou None se falhou
    """
    if not silent:
        print("--- Iniciando Busca de Template ---")
        
        if DEBUG_MODE:
            print(f"Modo Debug ATIVADO para templates. Imagens serão salvas em: '{debug_output_path}'")

    # --- Configurações do Teste ---
    if template_name and template_name in COMMON_TEMPLATES:
        # Usar um template predefinido do arquivo de configuração
        template_info = COMMON_TEMPLATES[template_name]
        template_relative_path = os.path.join(DEFAULT_TEMPLATE_FOLDER, template_info["path"])
        search_roi = template_info.get("default_roi", None)
    elif custom_path:
        # Usar um caminho personalizado
        template_relative_path = custom_path
        search_roi = roi
    else:
        if not silent:
            print("❌ Error: Você deve fornecer um template_name válido ou um custom_path.")
        return None
    
    template_full_path = os.path.join(project_root, template_relative_path)
    
    # Usar ROI e threshold personalizados se fornecidos
    search_roi = roi if roi is not None else search_roi
    confidence_threshold = confidence_threshold if confidence_threshold is not None else DEFAULT_CONFIDENCE

    # --- 1. Garante Conexão ADB via Manager ---
    if not adb_manager.is_connected():
         print("Template: ADB não conectado pelo manager. Tentando conectar...")
         # Tenta conectar/selecionar (sem especificar serial, deixa o manager decidir)
         if not adb_manager.find_and_select_device(): 
              if not silent:
               print("❌ Template: Falha ao conectar/selecionar dispositivo ADB via Manager. Busca abortada.")
              return None
         print(f"Template: Conectado a {adb_manager.get_target_serial()}")
    
    # --- 2. Inicializa Componentes (se necessário) ---
    # O Screenshotter agora é inicializado SEM o device, pois ele pega do manager
    screenshotter = Screenshotter() 
    matcher = TemplateMatcher(default_threshold=confidence_threshold)

    # --- 3. Captura Screenshot USANDO o Screenshotter ---
    if not silent:
        print("Template: Capturando screenshot via Screenshotter...")
    # O Screenshotter internamente usa adb_manager.get_device()
    screenshot = screenshotter.take_screenshot(use_pil=False) # Pega como OpenCV

    if screenshot is None:
        if not silent:
            print("❌ Template: Falha ao capturar screenshot via Screenshotter. Busca abortada.")
        # Tentativa de diagnóstico rápido
        if not adb_manager.is_connected():
             if not silent:
                  print("   -> Causa provável: Conexão ADB perdida.")
        return None

    if not silent:
        print(f"Template: Screenshot capturada (Shape: {screenshot.shape}).")

    # --- 4. Procurar Template na ROI USANDO o Matcher ---
    if not silent:
        print(f"Template: Procurando template '{os.path.basename(template_full_path)}' na ROI {search_roi}...")
    
    if not os.path.exists(template_full_path):
        if not silent:
            print(f"❌ Template: Arquivo de template não encontrado em '{template_full_path}'. Busca abortada.")
        return None
        
    result = matcher.find_template(screenshot, template_full_path, roi=search_roi, threshold=confidence_threshold)

    # --- 5. Resultado ---
    if result and result.get('found'):
        if not silent:
            print(f"✅ Template: ENCONTRADO!")
            print(f"   Confiança: {result.get('confidence', 0):.4f}")
            print(f"   Posição (Centro): {result.get('position')}")
        
        # Se o modo debug estiver ativado, salva a imagem com os boundings
        if DEBUG_MODE and screenshot is not None:
            # Desenha os limites na imagem
            debug_img = draw_bounds_on_image(screenshot, result, template_full_path)
            # Salva a imagem com os boundings
            save_debug_image(debug_img, f"template_match_{os.path.basename(template_full_path).split('.')[0]}")
            if not silent:
                print(f"✅ Template: Imagem de debug com bounding box salva no diretório {DEBUG_OUTPUT_DIR}")
        
        # Retorna o resultado completo
        return result
    else:
        if not silent:
            print(f"❌ Template: NÃO encontrado (ou confiança < {confidence_threshold}).")  
        
        # Se o modo debug estiver ativado, salva a screenshot original para análise
        if DEBUG_MODE and screenshot is not None:
            save_debug_image(screenshot, f"failed_match_{os.path.basename(template_full_path).split('.')[0]}")
            if not silent:
                print(f"❌ Template: Imagem original salva para análise no diretório {DEBUG_OUTPUT_DIR}")
        
        return None

def run_test(silent=False):
    """
    Função de teste compatível com o código anterior.
    Executa um teste simples com o ícone do HayDay.
    
    Args:
        silent (bool): Se True, não imprime mensagens de conclusão (usado quando chamado de outro módulo)
    
    Returns:
        bool: True se o template foi encontrado, False caso contrário
    """
    if not silent:
        print("--- Executando Teste de Template ---")
    
    result = find_template("hayday_app_icon", silent=silent)
    
    if result and result.get('found'):
        if not silent:
            print(f"✅ TESTE CONCLUÍDO: Template encontrado com sucesso!")
        return True
    else:
        if not silent:
            print(f"❌ TESTE CONCLUÍDO: Template não encontrado.")
        return False

# Executa a função principal se o script for chamado diretamente
if __name__ == "__main__":
    # Exibe informações das configurações de debug
    print(f"Debug Mode: {'ATIVADO' if DEBUG_MODE else 'DESATIVADO'}")
    if DEBUG_MODE:
        print(f"Debug Output Dir: {debug_output_path}")
        
    # Executa o teste
    encontrado = run_test()
    print(f"\n--- Teste Finalizado ---")
    print(f"Resultado final: {'Encontrado' if encontrado else 'Não Encontrado'}")
