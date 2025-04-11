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

# Desativa avisos de certificado SSL inseguro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fila compartilhada para transmissão de imagens
image_queue = queue.Queue(maxsize=30)  # Limita para evitar uso excessivo de memória

class ScreenTransmitter:
    """Cliente para transmissão de capturas de tela para o servidor WebSocket."""
    
    def __init__(self, server_url: str = "https://89.117.32.119:8000", 
                 api_endpoint: str = "/api/send-image",  # Usando HTTPS para o servidor com SSL
                 transmission_enabled: bool = True):
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
        self.username = None
        self.stats = {}  # Dicionário para armazenar estatísticas de transmissão por screen_id
        
        # Inicia thread de processamento assíncrono
        self._start_worker()
        
        print(f"📡 Transmissor inicializado - Servidor: {server_url}")
    
    def _start_worker(self):
        """Inicia a thread de processamento de imagens para envio."""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
            
        self.transmitting = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        # Inicia thread para status periódico
        self.status_thread = threading.Thread(target=self._periodic_status, daemon=True)
        self.status_thread.start()
        
        print("📡▶️ Thread de transmissão iniciada")
    
    def _periodic_status(self):
        """Exibe estatísticas de transmissão periodicamente."""
        while self.transmitting:
            time.sleep(30)  # Atualiza a cada 30 segundos
            
            # Se existem estatísticas, mostra um resumo consolidado
            total_sent = sum(stat["sent"] for stat in self.stats.values())
            total_errors = sum(stat["errors"] for stat in self.stats.values())
            
            if total_sent > 0:
                print(f"📡📊 Resumo: {total_sent} imagens transmitidas, {total_errors} erros, {len(self.stats)} streams ativos")
                
                # Mostra detalhes por stream apenas se houver mais de um
                if len(self.stats) > 1:
                    for screen_id, stat in self.stats.items():
                        if stat["sent"] > 0:
                            print(f"  → {screen_id}: {stat['sent']} imagens, {stat['errors']} erros")
            
            # Limpa as estatísticas após exibir
            self.stats = {id: {"sent": 0, "errors": 0, "last_log_time": time.time()} 
                          for id in self.stats}
    
    def stop(self):
        """Para a transmissão de imagens."""
        self.transmitting = False
        # Limpa a fila
        while not image_queue.empty():
            try:
                image_queue.get_nowait()
                image_queue.task_done()
            except queue.Empty:
                break
    
    def _process_queue(self):
        """Processa a fila de imagens e envia para o servidor."""
        # Contadores para estatísticas
        images_sent = 0
        error_count = 0
        last_status_time = time.time()
        status_interval = 30  # Mostra status a cada 30 segundos
        
        while self.transmitting:
            try:
                # Espera por um item na fila (timeout para permitir check de self.transmitting)
                try:
                    item = image_queue.get(timeout=1.0)
                except queue.Empty:
                    # Verifica se é hora de mostrar estatísticas
                    current_time = time.time()
                    if current_time - last_status_time > status_interval:
                        queue_size = image_queue.qsize()
                        print(f"📡📊 Status: {images_sent} imagens enviadas, {error_count} erros, fila: {queue_size}")
                        last_status_time = current_time
                    continue
                
                # Desempacota os dados da fila
                if isinstance(item, tuple) and len(item) == 2:
                    image, screen_id = item
                    
                    # Verifica se há identificação de usuário
                    if self.username and not screen_id:
                        screen_id = self.username
                    elif not screen_id:
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
    
    def set_username(self, username: str):
        """Define o username para identificação do stream."""
        if username:
            # Verifica se é uma mudança de usuário antes de logar
            old_username = self.username
            
            # Adiciona prefixo "screen-" se já não tiver
            if not username.startswith("screen-"):
                self.username = f"screen-{username}"
            else:
                self.username = username
                
            # Só exibe mensagem se for uma configuração inicial ou mudança
            if old_username != self.username:
                print(f"📡👤 Transmissor configurado para usuário: {username}")
    
    def queue_image(self, image: Any, username: Optional[str] = None):
        """
        Adiciona uma imagem à fila para transmissão.
        
        Args:
            image: Imagem PIL ou OpenCV para transmitir
            username: Nome de usuário para identificação (opcional)
        """
        if not self.transmission_enabled or image is None:
            return
        
        # Define o screen_id baseado no username fornecido ou armazenado
        screen_id = username if username else self.username
        if not screen_id:
            screen_id = "screen"
        
        # Verifica o ID do stream para logs - removida impressão repetitiva
        
        # Limita taxa de transmissão
        now = time.time()
        if now - self.last_transmission_time < self.min_interval:
            return
        self.last_transmission_time = now
        
        # Se a fila estiver cheia, remove o item mais antigo
        if image_queue.full():
            try:
                # Remove o item mais antigo para fazer espaço
                image_queue.get_nowait()
                image_queue.task_done()
            except queue.Empty:
                pass
        
        # Adiciona a imagem à fila
        try:
            image_queue.put((image, screen_id), block=False)
        except queue.Full:
            pass  # Ignora se ainda estiver cheia
    
    def _send_image(self, image: Any, screen_id: str):
        """
        Envia uma imagem para o servidor.
        
        Args:
            image: Imagem PIL ou OpenCV para transmitir
            screen_id: Identificador da tela
        """
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
            
            # Contador de transmissões bem-sucedidas para este ID
            if screen_id not in self.stats:
                self.stats[screen_id] = {"sent": 0, "errors": 0, "last_log_time": 0}
            
            # Envia para o servidor
            response = requests.post(
                self.full_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3,  # Timeout para evitar bloqueio
                verify=False  # Permite certificados auto-assinados
            )
            
            # Já desativamos os avisos de certificado no início do arquivo
            
            current_time = time.time()
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.stats[screen_id]["sent"] += 1
                    clients = data.get("sent_to", 0)
                    
                    # Mostra um log resumido apenas a cada 20 transmissões
                    if self.stats[screen_id]["sent"] % 20 == 0:
                        print(f"📡📊 Status: {self.stats[screen_id]['sent']} imagens enviadas, {self.stats[screen_id]['errors']} erros, fila: {image_queue.qsize()}")
                        self.stats[screen_id]["last_log_time"] = current_time
                        
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
            print("📡❌ Falha de conexão com o servidor")
        except requests.exceptions.Timeout:
            # Incrementa contador de erros
            if screen_id in self.stats:
                self.stats[screen_id]["errors"] += 1
            print("📡⏱️ Timeout ao enviar imagem")
        except Exception as e:
            # Incrementa contador de erros
            if screen_id in self.stats:
                self.stats[screen_id]["errors"] += 1
            print(f"📡❌ Erro ao processar/enviar imagem: {str(e)}")

# Instância global para uso em toda a aplicação
transmitter = ScreenTransmitter()
