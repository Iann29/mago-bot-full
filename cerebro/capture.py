# /cerebro/capture.py
# Módulo para gerenciamento de captura de tela

import time
import threading
import queue
from typing import Optional

from adbutils import AdbDevice
from screenVision.screenshotMain import Screenshotter
from screenVision.transmitter import transmitter

# Variáveis globais
screenshot_queue = queue.Queue(maxsize=5)
capture_thread = None

# Evento que sinaliza a parada da thread (mais responsivo que uma flag booleana)
stop_capture_event = threading.Event()

def capture_worker(fps: float, adb_device: AdbDevice):
    """Função que roda em uma thread separada para capturar screenshots."""
    global stop_capture_event
    
    # Inicializa o Screenshotter passando o device conectado
    # A instância do Screenshotter é local para esta thread
    screenshotter = Screenshotter(adb_device=adb_device)
    
    capture_interval = 1.0 / fps
    last_capture_time = time.time()
    consecutive_failures = 0
    max_failures = 2

    while not stop_capture_event.is_set():
        try:
            current_time = time.time()
            if current_time - last_capture_time >= capture_interval:
                time_before_capture = time.time() 
                
                screenshot = screenshotter.take_screenshot(use_pil=False, transmit=True)
                
                time_after_capture = time.time() 
                capture_duration = time_after_capture - time_before_capture
                
                last_capture_time = time_before_capture 

                if screenshot is not None:
                    consecutive_failures = 0
                    if screenshot_queue.full():
                        try: 
                            screenshot_queue.get_nowait() 
                        except queue.Empty: 
                            pass 
                    screenshot_queue.put(screenshot)
                else:
                    consecutive_failures += 1
                    print(f"Falha na captura ({capture_duration:.3f}s) ({consecutive_failures}/{max_failures})")
                    if consecutive_failures >= max_failures:
                         print("Máximo de falhas atingido. Encerrando thread de captura")
                         stop_capture_event.set()
                         break
                    time.sleep(0.5)

        except Exception as e:
            consecutive_failures += 1
            print(f"Erro inesperado na captura: {e} ({consecutive_failures}/{max_failures})")
            if consecutive_failures >= max_failures:
                 print("Máximo de falhas atingido. Encerrando thread de captura")
                 stop_capture_event.set()
                 break
            time.sleep(0.5)

        sleep_time = max(0.01, capture_interval - (time.time() - last_capture_time))
        sleep_fraction = 0.1
        sleep_count = int(sleep_time / sleep_fraction)
        
        for _ in range(sleep_count):
            if stop_capture_event.is_set():
                break
            time.sleep(sleep_fraction)

    print("Thread de captura encerrando...")

def start_screenshot_capture(fps: float, device: AdbDevice) -> Optional[threading.Thread]:
    """
    Inicia a captura de screenshots em thread separada.
    
    Args:
        fps: Taxa de frames por segundo desejada
        device: Dispositivo ADB conectado
        
    Returns:
        Thread de captura ou None se falhar
    """
    global capture_thread, stop_capture_event
    
    stop_capture_event.clear()
    
    capture_thread = threading.Thread(
        target=capture_worker,
        args=(fps, device),
        daemon=True
    )
    
    capture_thread.start()
    print(f"Thread de captura iniciada (FPS={fps})")
    
    return capture_thread

def stop_screenshot_capture() -> None:
    """Para a thread de captura de screenshots."""
    global stop_capture_event, capture_thread
    
    stop_capture_event.set()
    
    if capture_thread and capture_thread.is_alive():
        print("Aguardando thread de captura encerrar (timeout=1.5s)...")
        capture_thread.join(timeout=1.5)
        
        if capture_thread.is_alive():
            print("Thread de captura não encerrou no tempo esperado")
        else:
            print("Thread de captura encerrada com sucesso")
