# /execution/testnew.py

import sys
import os
import cv2 # Importa OpenCV aqui
from datetime import datetime  # Para usar no timestamp das imagens

# Adiciona a raiz do projeto ao PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importa os MÓDULOS necessários
from screenVision.screenshotMain import Screenshotter
from screenVision.maskedTemplateMatcher import MaskedTemplateMatcher
from ADBmanager import adb_manager 

# Configurações de debug
DEBUG_MODE = False  # Sempre ativado para teste
DEBUG_OUTPUT_DIR = os.path.join(project_root, 'output_template_matches')

# Garante que o diretório de saída exista
if not os.path.exists(DEBUG_OUTPUT_DIR):
    os.makedirs(DEBUG_OUTPUT_DIR)

def save_debug_image(image, filename_prefix):
    """
    Salva a imagem de debug no diretório configurado.
    
    Args:
        image (np.ndarray): Imagem a ser salva
        filename_prefix (str): Prefixo para o nome do arquivo
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.png"
    save_path = os.path.join(DEBUG_OUTPUT_DIR, filename)
    
    try:
        cv2.imwrite(save_path, image)
        print(f"✅ Debug: Imagem salva em {save_path}")
    except Exception as e:
        print(f"❌ Debug: Erro ao salvar imagem: {e}")


def run_masked_test():
    """
    Captura screenshot e procura pela 'banca.png' usando 'bancamask.png'.
    Retorna True se encontrado, False caso contrário.
    """
    print("--- Iniciando Teste de Template COM MÁSCARA ---")

    # --- Configurações do Teste ---
    template_relative_path = os.path.join('dataset', 'haydayBuildings', 'banca.png')
    mask_relative_path = os.path.join('dataset', 'haydayBuildings', 'bancamask.png')
    
    template_full_path = os.path.join(project_root, template_relative_path)
    mask_full_path = os.path.join(project_root, mask_relative_path)
    
    # ROI para busca (opcional, pode ser None para buscar na imagem inteira)
    # search_roi = (x, y, w, h) 
    search_roi = None # Busca na imagem inteira para começar

    # Threshold de confiança - TM_CCORR_NORMED geralmente precisa de valores altos
    confidence_threshold = 0.93 # Comece com um valor alto e ajuste se necessário

    # --- 1. Garante Conexão ADB ---
    if not adb_manager.is_connected():
         print("TestNew: ADB não conectado. Tentando conectar...")
         if not adb_manager.find_and_select_device(): 
              print("❌ TestNew: Falha ao conectar/selecionar dispositivo ADB. Teste abortado.")
              return False
         print(f"TestNew: Conectado a {adb_manager.get_target_serial()}")
    
    # --- 2. Inicializa componentes ---
    screenshotter = Screenshotter() 
    masked_matcher = MaskedTemplateMatcher(default_threshold=confidence_threshold, verbose=False)

    # --- 3. Captura Screenshot ---
    print("TestNew: Capturando screenshot...")
    screenshot = screenshotter.take_screenshot(use_pil=False) # Pega como OpenCV (BGR)

    if screenshot is None:
        print("❌ TestNew: Falha ao capturar screenshot. Teste abortado.")
        return False
    print(f"TestNew: Screenshot capturada (Shape: {screenshot.shape}).")

    # --- 4. Verifica se os arquivos existem ---
    print(f"TestNew: Verificando arquivos do template e máscara...")
    if not os.path.exists(template_full_path):
        print(f"❌ TestNew: Arquivo de template não encontrado em '{template_full_path}'.")
        return False
        
    if not os.path.exists(mask_full_path):
        print(f"❌ TestNew: Arquivo de máscara não encontrado em '{mask_full_path}'.")
        return False

    # --- 5. Executa Masked Template Matching ---
    print(f"TestNew: Buscando template com máscara...")
    
    # Usa a nova classe MaskedTemplateMatcher para fazer a busca
    result = masked_matcher.find_template(
        main_image=screenshot,
        template_path=template_full_path,
        mask_path=mask_full_path,
        roi=search_roi,
        threshold=confidence_threshold,
        silent=True
    )

    # --- 6. Processa o Resultado ---
    if result and result.get('found'):
        print(f"✅ Teste: Template ENCONTRADO com Máscara!")
        confidence = result.get('confidence', 0)
        position = result.get('position')
        rect = result.get('rectangle')
        
        print(f"   Confiança: {confidence:.4f}")
        print(f"   Posição (Centro): {position}")
        print(f"   Retângulo: {rect}")

        # Salvar imagem de debug com resultado
        if DEBUG_MODE:
            debug_img = screenshot.copy()
            # Desenha retângulo verde ao redor do template encontrado
            rect = result['rectangle']
            cv2.rectangle(debug_img, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), 2)
            # Desenha círculo vermelho no centro
            center_x, center_y = result['position']
            cv2.circle(debug_img, (center_x, center_y), 5, (0, 0, 255), -1)
            # Desenha a ROI em azul se usada
            if search_roi:
                cv2.rectangle(debug_img, (search_roi[0], search_roi[1]), (search_roi[0]+search_roi[2], search_roi[1]+search_roi[3]), (255,0,0), 1)
            # Adiciona texto informativo na imagem
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(debug_img, f"Confianca: {confidence:.4f}", (10, 30), font, 0.7, (0, 255, 255), 2)
            cv2.putText(debug_img, f"Template: {os.path.basename(template_full_path)}", (10, 60), font, 0.7, (0, 255, 255), 2)
            # Salva a imagem
            save_debug_image(debug_img, f"masked_match_{os.path.basename(template_full_path).split('.')[0]}")
            print(f"✅ TestNew: Imagem de debug com bounding box salva no diretório {DEBUG_OUTPUT_DIR}")
            
        return True
    else:
        print(f"❌ Teste: Template NÃO encontrado com Máscara.")
        # Salvar imagem onde falhou
        if DEBUG_MODE:
            # Adiciona texto informativo na imagem
            debug_img = screenshot.copy()
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(debug_img, f"Falha: Template não encontrado", (10, 30), font, 0.7, (0, 0, 255), 2)
            cv2.putText(debug_img, f"Template: {os.path.basename(template_full_path)}", (10, 60), font, 0.7, (0, 0, 255), 2)
            # Salva a imagem
            save_debug_image(debug_img, f"failed_match_{os.path.basename(template_full_path).split('.')[0]}")
            print(f"❌ TestNew: Imagem de falha salva para análise no diretório {DEBUG_OUTPUT_DIR}")
        return False

# Função para ser chamada pelo main.py
def execute_masked_test():
    """Função principal para executar o teste de template com máscara, chamada pelo main.py"""
    print("--- Iniciando Teste com Máscara ---")
    print(f"Debug Mode: {'ATIVADO' if DEBUG_MODE else 'DESATIVADO'}")
    if DEBUG_MODE:
        print(f"Debug Output Dir: {DEBUG_OUTPUT_DIR}")
        
    encontrado = run_masked_test()
    print(f"--- Teste com Máscara Finalizado ---")
    print(f"Resultado final: {'Encontrado' if encontrado else 'Não Encontrado'}")
    return encontrado