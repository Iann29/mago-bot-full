#!/usr/bin/env python
"""
Script para testar a conexão com o servidor WebSocket e verificar os endpoints.
"""

import requests
import json
import base64
from PIL import Image
import io
import time

SERVER_URL = "http://89.117.32.119:8000"
API_ENDPOINT = "/api/send-image"
FULL_URL = f"{SERVER_URL}{API_ENDPOINT}"

def test_server_status():
    """Testa o status do servidor."""
    try:
        response = requests.get(SERVER_URL)
        print(f"Status do servidor: {response.status_code}")
        print(f"Resposta: {response.text[:150]}...")
        return True
    except Exception as e:
        print(f"Erro ao acessar o servidor: {e}")
        return False

def test_available_endpoints():
    """Testa quais endpoints estão disponíveis no servidor."""
    endpoints = [
        "/",
        "/api",
        "/api/status",
        "/api/send-image",
        "/ws",
        "/docs"
    ]
    
    print("\nEndpoints disponíveis:")
    for endpoint in endpoints:
        try:
            response = requests.get(f"{SERVER_URL}{endpoint}")
            print(f"{endpoint}: {response.status_code} {response.reason}")
        except Exception as e:
            print(f"{endpoint}: Erro - {e}")

def test_send_small_image():
    """Testa o envio de uma pequena imagem de teste."""
    # Cria uma pequena imagem de teste
    img = Image.new('RGB', (100, 100), color='red')
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Cria payload
    payload = {
        "screen_id": "test-client",
        "image_data": img_base64
    }
    
    # Tenta diferentes endpoints
    endpoints = [
        "/api/send-image",
        "/api/image",
        "/send-image",
        "/image"
    ]
    
    print("\nTestando envio de imagem para diferentes endpoints:")
    for endpoint in endpoints:
        full_url = f"{SERVER_URL}{endpoint}"
        try:
            print(f"Enviando para: {full_url}")
            response = requests.post(
                full_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            print(f"Resposta: {response.status_code} {response.reason}")
            if response.text:
                print(f"Conteúdo: {response.text[:150]}...")
        except Exception as e:
            print(f"Erro ao enviar para {endpoint}: {e}")
        
        # Pausa entre os testes
        time.sleep(1)

if __name__ == "__main__":
    print("=== TESTE DE CONEXÃO COM O SERVIDOR ===")
    if test_server_status():
        test_available_endpoints()
        test_send_small_image()
    print("\nTeste concluído!")
