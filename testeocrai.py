import sys
import os
import base64
import cv2
import numpy as np
import io
import logging
from io import BytesIO
from PIL import Image
from openai import OpenAI

# Desativar logs indesejados
logging.basicConfig(level=logging.ERROR)

# Adiciona a raiz do projeto ao PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importa os módulos necessários do projeto
from screenVision.screenshotMain import Screenshotter
from ADBmanager import adb_manager

# Suprime saída padrão temporariamente durante importações específicas
original_stdout = sys.stdout

def capture_screenshot():
    """Captura uma screenshot usando o Screenshotter do projeto"""
    print("📸 Capturando screenshot...")
    
    # Suprime saída temporariamente
    sys.stdout = io.StringIO()
    
    try:
        # Verifica se o ADB está conectado
        if not adb_manager.is_connected():
            if not adb_manager.find_and_select_device():
                # Restaura saída
                sys.stdout = original_stdout
                print("❌ Falha ao conectar com o dispositivo Android. Verifique se o emulador está aberto.")
                return None
        
        # Inicializa o Screenshotter
        screenshotter = Screenshotter()
        
        # Captura a screenshot (como OpenCV image em BGR)
        screenshot = screenshotter.take_screenshot(use_pil=False)
        
        # Restaura saída
        sys.stdout = original_stdout
        
        if screenshot is None:
            print("❌ Falha ao capturar screenshot.")
            return None
        
        print(f"✅ Screenshot capturada com sucesso: {screenshot.shape}")
        return screenshot
    except Exception as e:
        # Restaura saída em caso de erro
        sys.stdout = original_stdout
        print(f"❌ Erro ao capturar screenshot: {e}")
        return None

def extract_roi(image, roi):
    """Extrai uma região de interesse (ROI) da imagem"""
    if image is None:
        return None
        
    x, y, w, h = roi
    return image[y:y+h, x:x+w]

def convert_to_base64(image):
    """Converte uma imagem OpenCV para base64"""
    if image is None:
        return None
        
    # Converter de BGR para RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Converter para PIL Image
    pil_image = Image.fromarray(rgb_image)
    
    # Salvar em buffer na memória
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    buffer.seek(0)
    
    # Converter para base64
    base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return base64_image

def analyze_image_with_gpt(base64_image):
    """Analisa a imagem usando OpenAI GPT-4.1-mini"""
    if base64_image is None:
        return None
        
    # Inicializa o cliente OpenAI
    client = OpenAI(api_key="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")
    
    print("🧠 Enviando imagem para análise com GPT-4.1-mini...")
    
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
    
    return response.choices[0].message.content

# Função de debug removida conforme solicitado

def main():
    # Definir o ROI (x, y, largura, altura)
    roi = (331, 118, 111, 37)
    
    # Capturar screenshot
    screenshot = capture_screenshot()
    if screenshot is None:
        return
    
    # Extrair ROI
    roi_image = extract_roi(screenshot, roi)
    if roi_image is None:
        print("❌ Falha ao extrair ROI.")
        return
    
    # Funcionalidade de debug removida conforme solicitado
    
    # Converter para base64
    base64_image = convert_to_base64(roi_image)
    if base64_image is None:
        print("❌ Falha ao converter imagem para base64.")
        return
    
    # Analisar com GPT
    result = analyze_image_with_gpt(base64_image)
    
    # Exibir resultado
    print("\n🎯 Resultado da análise:")
    print(result)

if __name__ == "__main__":
    print("🚀 Iniciando teste de OCR com IA...")
    main()
    print("✅ Teste concluído!")
