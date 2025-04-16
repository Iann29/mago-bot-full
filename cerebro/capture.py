# /cerebro/capture.py
# Módulo para gerenciamento de captura de tela

import time
import threading
import queue
from typing import Optional

# Sistema de logs removido

from adbutils import AdbDevice
from screenVision.screenshotMain import Screenshotter
from screenVision.transmitter import transmitter

# Variáveis globais
screenshot_queue = queue.Queue(maxsize=5)
stop_capture_thread = False
capture_thread = None

# Evento que sinaliza a parada da thread (mais responsivo que uma flag booleana)
stop_capture_event = threading.Event()

def capture_worker(fps: float, adb_device: AdbDevice, username: str = None):
    """Função que roda em uma thread separada para capturar screenshots."""
    global stop_capture_thread, stop_capture_event
    
    # Inicializa o Screenshotter passando o device conectado
    # A instância do Screenshotter é local para esta thread
    screenshotter = Screenshotter(adb_device=adb_device)
    
    # Configura o transmissor com o nome de usuário
    if username:
        transmitter.set_username(username)
        print(f"Transmissor configurado para usuário: {username}")
    
    capture_interval = 1.0 / fps
    last_capture_time = time.time()
    consecutive_failures = 0  # Contador de falhas consecutivas
    max_failures = 2  # Número máximo de falhas antes de parar a thread
    
    print(f"Thread de captura iniciada, capturando a ~{fps} FPS")

    while not stop_capture_thread and not stop_capture_event.is_set():
        # Tenta capturar e colocar na fila
        try:
            current_time = time.time()
            # Lógica para tentar manter o FPS alvo
            if current_time - last_capture_time >= capture_interval:
                time_before_capture = time.time() 
                
                # Tira screenshot (padrão OpenCV/BGR) e transmite para VPS
                screenshot = screenshotter.take_screenshot(use_pil=False, username=username, transmit=True)
                
                time_after_capture = time.time() 
                capture_duration = time_after_capture - time_before_capture
                
                # Atualiza o tempo da última tentativa de captura
                last_capture_time = time_before_capture 

                if screenshot is not None:
                    consecutive_failures = 0  # Reseta contador de falhas
                    # Coloca na fila se tiver espaço, senão descarta a antiga
                    if screenshot_queue.full():
                        try: 
                            screenshot_queue.get_nowait() 
                        except queue.Empty: 
                            pass 
                    screenshot_queue.put(screenshot)
                    # print(f"CAPTURE_THREAD: Screenshot OK ({capture_duration:.3f}s). Fila: {screenshot_queue.qsize()}") # Debug
                else:
                    consecutive_failures += 1
                    print(f"Falha na captura ({capture_duration:.3f}s) ({consecutive_failures}/{max_failures})")
                    if consecutive_failures >= max_failures:
                         print("Máximo de falhas atingido. Encerrando thread de captura")
                         stop_capture_thread = True
                         break  # Sai do loop
                    time.sleep(0.5)  # Pausa curta após falha na captura

        except Exception as e:
            consecutive_failures += 1
            print(f"Erro inesperado na captura: {e} ({consecutive_failures}/{max_failures})")
            if consecutive_failures >= max_failures:
                 print("Máximo de falhas atingido. Encerrando thread de captura")
                 stop_capture_thread = True
                 break  # Sai do loop
            time.sleep(0.5)  # Pausa curta após falha na captura

        # Dormir para controlar o FPS e não usar 100% CPU, mas permitindo interrupção rápida
        sleep_time = max(0.01, capture_interval - (time.time() - last_capture_time))  # Garante um sleep mínimo
        # Usa sleep fracionado com verificações de parada para poder parar mais rapidamente
        sleep_fraction = 0.1  # Fragmenta o sleep em blocos de 100ms para checar stop_event
        sleep_count = int(sleep_time / sleep_fraction)
        
        for _ in range(sleep_count):
            if stop_capture_thread or stop_capture_event.is_set():
                break
            time.sleep(sleep_fraction)

    print("Thread de captura encerrando...")

def start_screenshot_capture(fps: float, device: AdbDevice, username: str = None) -> Optional[threading.Thread]:
    """
    Inicia a captura de screenshots em thread separada.
    
    Args:
        fps: Taxa de frames por segundo desejada
        device: Dispositivo ADB conectado
        username: Nome de usuário para identificação na transmissão
        
    Returns:
        Thread de captura ou None se falhar
    """
    global capture_thread, stop_capture_thread, stop_capture_event
    
    # Reseta a flag e o evento de parada
    stop_capture_thread = False
    stop_capture_event.clear()
    
    # Cria uma nova thread para a captura de screenshots
    capture_thread = threading.Thread(
        target=capture_worker,
        args=(fps, device, username),
        daemon=True
    )
    
    # Inicia a thread
    capture_thread.start()
    print(f"Thread de captura iniciada (FPS={fps})")
    
    return capture_thread

def stop_screenshot_capture() -> None:
    """Para a thread de captura de screenshots."""
    global stop_capture_thread, capture_thread
    
    # Sinaliza para a thread parar por ambos os mecanismos
    stop_capture_thread = True
    stop_capture_event.set()
    
    # Espera a thread terminar com timeout curto
    if capture_thread and capture_thread.is_alive():
        print("Aguardando thread de captura encerrar (timeout=1.5s)...")
        capture_thread.join(timeout=1.5)
        
        if capture_thread.is_alive():
            print("Thread de captura não encerrou no tempo esperado")
        else:
            print("Thread de captura encerrada com sucesso")
