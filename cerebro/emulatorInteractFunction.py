"""
emulatorInteractFunction.py

Este módulo contém funções para interagir com o emulador Android através da biblioteca adbutils.
As funções implementadas aqui serão utilizadas nos arquivos de configuração (CFG) dos diversos kits.
"""

import time
from typing import Union, Optional, Tuple

# Importar o gerenciador ADB para obter a instância do dispositivo
from ADBmanager import adb_manager
from utils.logger import get_logger

# Logger para este módulo
logger = get_logger('emulator_interact')

def get_device():
    """
    Obtém a instância atual do dispositivo conectado via ADB.
    
    Returns:
        AdbDevice: A instância do dispositivo ou None se não houver dispositivo conectado.
    """
    device = adb_manager.get_device()
    if not device:
        logger.error("Nenhum dispositivo ADB conectado")
    return device

def click(x: Union[int, float], y: Union[int, float], duration: float = 0.05) -> bool:
    """
    Realiza um clique na posição especificada na tela do emulador.
    
    Args:
        x: Coordenada X (pode ser absoluta [int] ou relativa [float <= 1.0])
        y: Coordenada Y (pode ser absoluta [int] ou relativa [float <= 1.0])
        duration: Duração do clique em segundos (padrão: 0.05s)
    
    Returns:
        bool: True se o clique foi bem-sucedido, False caso contrário
    """
    device = get_device()
    if not device:
        return False
    
    try:
        # Convertendo para inteiros garantindo que sejam coordenadas absolutas
        x_int = int(x)
        y_int = int(y)
        
        # Usando o comando shell 'input tap' que funciona melhor com o emulador
        result = device.shell(f"input tap {x_int} {y_int}")
        time.sleep(duration)  # Esperamos a duração especificada
        
        logger.info(f"Click realizado em ({x_int}, {y_int}) via input tap com duração {duration}s")
        return True
    except Exception as e:
        logger.error(f"Erro ao realizar click em ({x}, {y}): {e}")
        return False

def swipe(
    x1: Union[int, float], 
    y1: Union[int, float], 
    x2: Union[int, float], 
    y2: Union[int, float], 
    duration: float = 0.5
) -> bool:
    """
    Realiza um swipe na tela do emulador, do ponto (x1, y1) ao ponto (x2, y2).
    
    Args:
        x1: Coordenada X inicial (pode ser absoluta [int] ou relativa [float <= 1.0])
        y1: Coordenada Y inicial (pode ser absoluta [int] ou relativa [float <= 1.0])
        x2: Coordenada X final (pode ser absoluta [int] ou relativa [float <= 1.0])
        y2: Coordenada Y final (pode ser absoluta [int] ou relativa [float <= 1.0])
        duration: Duração do swipe em segundos (padrão: 0.5s)
    
    Returns:
        bool: True se o swipe foi bem-sucedido, False caso contrário
    """
    device = get_device()
    if not device:
        return False
    
    try:
        device.swipe(x1, y1, x2, y2, duration)
        logger.info(f"Swipe realizado de ({x1}, {y1}) para ({x2}, {y2}) com duração {duration}s")
        return True
    except Exception as e:
        logger.error(f"Erro ao realizar swipe de ({x1}, {y1}) para ({x2}, {y2}): {e}")
        return False

def long_click(x: Union[int, float], y: Union[int, float], duration: float = 1.0) -> bool:
    """
    Realiza um clique longo na posição especificada na tela do emulador.
    
    Args:
        x: Coordenada X (pode ser absoluta [int] ou relativa [float <= 1.0])
        y: Coordenada Y (pode ser absoluta [int] ou relativa [float <= 1.0])
        duration: Duração do clique longo em segundos (padrão: 1.0s)
    
    Returns:
        bool: True se o clique longo foi bem-sucedido, False caso contrário
    """
    device = get_device()
    if not device:
        return False
    
    try:
        device.long_click(x, y, duration)
        logger.info(f"Long click realizado em ({x}, {y}) com duração {duration}s")
        return True
    except Exception as e:
        logger.error(f"Erro ao realizar long click em ({x}, {y}): {e}")
        return False

def send_keys(text: str) -> bool:
    """
    Envia texto para o emulador.
    
    Args:
        text: Texto a ser enviado
    
    Returns:
        bool: True se o envio foi bem-sucedido, False caso contrário
    """
    device = get_device()
    if not device:
        return False
    
    try:
        device.send_keys(text)
        logger.info(f"Texto enviado: '{text}'")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar texto '{text}': {e}")
        return False

def press_key(keycode: int) -> bool:
    """
    Pressiona uma tecla específica pelo seu keycode.
    
    Args:
        keycode: Código da tecla a ser pressionada (ex: 4 para BACK, 3 para HOME)
    
    Returns:
        bool: True se o pressionamento foi bem-sucedido, False caso contrário
    """
    device = get_device()
    if not device:
        return False
    
    try:
        device.press(keycode)
        logger.info(f"Tecla pressionada: keycode {keycode}")
        return True
    except Exception as e:
        logger.error(f"Erro ao pressionar tecla {keycode}: {e}")
        return False

def get_screen_resolution() -> Optional[Tuple[int, int]]:
    """
    Obtém a resolução da tela do emulador.
    
    Returns:
        Tuple[int, int]: Tupla com (largura, altura) ou None se falhar
    """
    device = get_device()
    if not device:
        return None
    
    try:
        # Obtém dimensões da tela
        display_info = device.window_size()
        width, height = display_info
        logger.info(f"Resolução da tela: {width}x{height}")
        return width, height
    except Exception as e:
        logger.error(f"Erro ao obter resolução da tela: {e}")
        return None

def wait(seconds: float) -> None:
    """
    Espera um determinado número de segundos.
    
    Args:
        seconds: Número de segundos para esperar
    """
    logger.info(f"Aguardando {seconds} segundos")
    time.sleep(seconds)
