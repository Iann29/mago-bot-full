"""
Módulo para transmissão de imagens capturadas para o servidor WebSocket.
Responsável por enviar as capturas de tela para o servidor VPS para visualização remota.
"""

import time
import threading
import queue
import base64
import requests
from io import BytesIO
from typing import Any, Optional, Dict
from PIL import Image
from datetime import datetime
import urllib3

import numpy as np
import cv2

# Sistema de logs removido

# Desativa avisos de certificado SSL inseguro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fila compartilhada para transmissão de imagens
image_queue = queue.Queue(maxsize=30)  # Limita para evitar uso excessivo de memória

class ScreenTransmitter:
    """Cliente para transmissão de capturas de tela para o servidor WebSocket."""
    
    def __init__(self, server_url: str = "https://socket.magodohayday.com:8000", 
                api_endpoint: str = "/api/send-image",
                transmission_enabled: bool = False): 
        """
        Inicializa o transmissor de capturas de tela.
        
        Args:
            server_url: URL base do servidor WebSocket
            api_endpoint: Endpoint da API para envio de imagens
            transmission_enabled: Se a transmissão está habilitada
        """
        self.server_url = server_url
        self.api_endpoint = api_endpoint
        self.full_url = f"{server_url}{api_endpoint}"
        self.transmission_enabled = transmission_enabled
        self.last_transmission_time = 0
        self.min_interval = 0.5  # Intervalo mínimo entre transmissões (500ms)
        self.compression_quality = 70  # Qualidade de compressão JPEG (0-100)
        self.transmitting = False
        self.worker_thread = None
        self.stats = {}  # Dicionário para armazenar estatísticas
        
        # Evento para sinalizar encerramento - mais responsivo que uma flag booleana
        self.stop_event = threading.Event()
        
        # Callback para notificar a GUI sobre transmissões
        self.transmission_callback = None
        
        # Desativa verificação de certificado (temporário - para certificados auto-assinados)
        self.verify_ssl = False
        
        # Adiciona tratamento para falhas de conexão
        self.connection_retry_count = 0
        self.max_connection_retries = 3
        
        # Inicia thread de processamento assíncrono ONLY IF ENABLED
        if self.transmission_enabled:
            self._start_worker()
    
    def _start_worker(self):
        """Inicia a thread de processamento de imagens para envio."""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
            
        # Reseta o evento de parada
        self.stop_event.clear()
        self.transmitting = True
        
        # Inicia a thread principal de processamento
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
    def stop(self):
        """Para a transmissão de imagens."""
        self.transmitting = False
        
        # Sinaliza para as threads pararem imediatamente
        self.stop_event.set()
        
        # Limpa a fila para evitar bloqueios
        # Check if queue exists and clear it - Important if threads never started
        global image_queue
        while not image_queue.empty():
            try:
                image_queue.get_nowait()
                image_queue.task_done()
            except queue.Empty:
                break
                
        # Aguarda as threads terminarem (breve timeout) - ONLY IF STARTED
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
            
    def set_transmission_callback(self, callback_function):
        """Define um callback para ser chamado quando uma transmissão ocorrer.
        
        Args:
            callback_function: Função a ser chamada quando houver transmissão
        """
        self.transmission_callback = callback_function
    
    def add_to_queue(self, image: Any):
        """Adiciona uma imagem à fila para transmissão."""
        if not self.transmission_enabled or self.stop_event.is_set():
            return
            
        try:
            # Usa screen_id padrão se não for fornecido
            item = (image, "screen") # Use default 'screen' id
            
            # Tenta adicionar à fila sem bloquear indefinidamente
            # Se a fila estiver cheia, descarta a imagem mais antiga (non-blocking put)
            try:
                image_queue.put_nowait(item)
            except queue.Full:
                # Se a fila estiver cheia, remove um item antigo e tenta novamente
                try:
                    image_queue.get_nowait()
                    image_queue.task_done() # Marca como concluído para não travar joins
                    image_queue.put_nowait(item) # Tenta adicionar novamente
                except queue.Empty:
                    pass # Fila esvaziou enquanto tentávamos, ignora
                except queue.Full:
                    # Ainda cheia, descarta a imagem atual
                    print("⚠️ Fila de transmissão cheia, descartando imagem.")
                    pass 
                    
        except Exception as e:
            print(f"Erro ao adicionar imagem à fila: {e}")

    def _send_image(self, image: Any, screen_id: str = "screen"): 
        """Envia uma única imagem para o servidor via API HTTP POST."""
        # Verifica o intervalo mínimo entre transmissões
        now = time.time()
        if now - self.last_transmission_time < self.min_interval:
            return
        self.last_transmission_time = now
        
        # Resetar contador de tentativas se for uma nova imagem
        retry_count = 0
        max_retries = self.max_connection_retries
        try:
            # Converter de OpenCV para PIL se necessário
            pil_image = None
            if isinstance(image, np.ndarray):
                # Converte BGR (OpenCV) para RGB (PIL)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_image)
            elif isinstance(image, Image.Image):
                pil_image = image
            else:
                print(f"❌ Tipo de imagem não suportado: {type(image)}")
                return
            
            # Converte a imagem para JPEG base64
            buffered = BytesIO()
            pil_image.save(buffered, format="JPEG", quality=self.compression_quality)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Cria payload
            payload = {
                "screen_id": screen_id,
                "image_data": img_base64
            }
            
            # Notifica a GUI sobre a transmissão via callback
            if self.transmission_callback and callable(self.transmission_callback):
                try:
                    self.transmission_callback()
                except Exception as e:
                    # Falha silenciosa para não interromper a transmissão
                    pass
            
            # Contador de transmissões bem-sucedidas para este ID
            if screen_id not in self.stats:
                self.stats[screen_id] = {"sent": 0, "errors": 0, "last_log_time": 0}
            
            # Envia para o servidor
            # Tenta enviar a imagem (com retríveis se falhar)
            while retry_count <= max_retries:
                try:
                    response = requests.post(
                        self.full_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=5,  # Aumentado para 5 segundos
                        verify=self.verify_ssl  # Controla verificação SSL
                    )
                    # Se o envio for bem-sucedido, resetamos o contador global
                    self.connection_retry_count = 0
                    break  # Sai do loop se a requisição for bem-sucedida
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    retry_count += 1
                    if retry_count <= max_retries:
                        # Tenta novamente se não excedeu o limite
                        print(f"📡⚠️ Falha ao conectar. Tentativa {retry_count}/{max_retries}")
                        time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
                    else:
                        # Re-lança a exceção se todas as tentativas falharem
                        raise
            
            # Já desativamos os avisos de certificado no início do arquivo
            
            current_time = time.time()
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.stats[screen_id]["sent"] += 1
                    clients = data.get("sent_to", 0)
                    
                except Exception as e:
                    # Erro silencioso no log - não vai aparecer no terminal
                    pass
            else:
                self.stats[screen_id]["errors"] += 1
                # Mostra erros sempre pois são importantes
                print(f"📡❌ Erro {response.status_code} ao enviar imagem para {screen_id}")
                
        except requests.exceptions.ConnectionError:
            # Incrementa contador de erros
            if screen_id in self.stats:
                self.stats[screen_id]["errors"] += 1
            
            # Incrementa o contador de tentativas de conexão global
            self.connection_retry_count += 1
            
            # Log mais detalhado com informações para debug
            print(f"📡❌ Falha de conexão com o servidor: {self.full_url} (Tentativa {self.connection_retry_count}/{self.max_connection_retries})")
            
            # Se tiver muitas falhas seguidas, sugere verificar configuração
            if self.connection_retry_count >= self.max_connection_retries:
                print(f"📡⚠️ Múltiplas falhas de conexão. Verifique:")  
                print(f"  1. Se o domínio está correto: {self.server_url}")  
                print(f"  2. Se o servidor está online")  
                print(f"  3. Se a porta 8000 está acessível")
                # Reset o contador após mostrar mensagem
                self.connection_retry_count = 0
        except requests.exceptions.Timeout:
            # Incrementa contador de erros
            if screen_id in self.stats:
                self.stats[screen_id]["errors"] += 1
            print(f"📡⏱️ Timeout ao enviar imagem para {self.full_url}")
        except Exception as e:
            # Incrementa contador de erros
            if screen_id in self.stats:
                self.stats[screen_id]["errors"] += 1
            print(f"📡❌ Erro ao processar/enviar imagem: {str(e)}")

    def _process_queue(self):
        """Processa a fila de imagens e envia para o servidor."""
        # Contadores para estatísticas
        images_sent = 0
        error_count = 0
        last_status_time = time.time()
        status_interval = 30  # Mostra status a cada 30 segundos
        
        while self.transmitting and not self.stop_event.is_set():
            try:
                # Espera por um item na fila com timeout curto para responder melhor ao encerramento
                try:
                    # Reduzido o timeout para 0.5s para responder mais rapidamente à parada
                    item = image_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Desempacota os dados da fila
                if isinstance(item, tuple) and len(item) == 2:
                    image, screen_id = item
                    
                    # Verifica se há identificação de usuário
                    if not screen_id:
                        screen_id = "screen"  # Default se nada for fornecido
                    
                    try:
                        # Tenta enviar a imagem
                        self._send_image(image, screen_id)
                        images_sent += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Erro ao enviar imagem: {e}")
                
                # Marca a tarefa como concluída
                image_queue.task_done()
                
            except Exception as e:
                print(f"Erro na thread de processamento: {e}")
                time.sleep(1)  # Pausa para evitar loop muito rápido em caso de erro

# Instância global para uso em toda a aplicação
transmitter = ScreenTransmitter()
