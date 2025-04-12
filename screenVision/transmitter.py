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
    
    def __init__(self, server_url: str = "https://socket.magodohayday.com:8000", 
                api_endpoint: str = "/api/send-image",
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
        self.status_thread = None
        self.username = None
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
        
        # Inicia thread de processamento assíncrono
        self._start_worker()
        
        print(f"📡 Transmissor inicializado - Servidor: {server_url}")
    
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
        
        # Inicia thread para status periódico
        self.status_thread = threading.Thread(target=self._periodic_status, daemon=True)
        self.status_thread.start()
        
        print("📡▶️ Thread de transmissão iniciada")
    
    def _periodic_status(self):
        """Exibe estatísticas de transmissão periodicamente."""
        while self.transmitting and not self.stop_event.is_set():
            # Usa wait com timeout em vez de sleep para responder mais rápido à parada
            # Espera no máximo 30 segundos, mas pode ser interrompido pelo evento de parada
            if self.stop_event.wait(timeout=5.0):  # Verifica a cada 5 segundos
                break
            
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
        print("📡⏹️ Transmissor: Parando threads...")
        self.transmitting = False
        
        # Sinaliza para as threads pararem imediatamente
        self.stop_event.set()
        
        # Limpa a fila para evitar bloqueios
        while not image_queue.empty():
            try:
                image_queue.get_nowait()
                image_queue.task_done()
            except queue.Empty:
                break
                
        # Aguarda as threads terminarem (breve timeout)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
            
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
            
        print("📡✅ Transmissor: Threads de transmissão paradas.")
    
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
                self.username = f"screen-{username.lower()}"
            else:
                self.username = username.lower()
                
            # Só exibe mensagem se for uma configuração inicial ou mudança
            if old_username != self.username:
                print(f"📡👤 Transmissor configurado para usuário: {username}")
                
    def set_transmission_callback(self, callback_function):
        """Define um callback para ser chamado quando uma transmissão ocorrer.
        
        Args:
            callback_function: Função a ser chamada quando houver transmissão
        """
        self.transmission_callback = callback_function
        print("📡🔗 Callback de transmissão configurado")
    
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
            
        # Garante o formato correto do ID (deve ser: screen-username)
        if not screen_id.startswith("screen-"):
            screen_id = f"screen-{screen_id.lower()}"
        
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

# Instância global para uso em toda a aplicação
transmitter = ScreenTransmitter()
