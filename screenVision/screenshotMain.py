# /screenVision/screenshotMain.py

# Não importa mais adbutils diretamente aqui, mas importa tipos/exceções
from adbutils import AdbError, AdbDevice
from PIL import Image
import io
import time
import os 
import json # Para carregar o CFG
from datetime import datetime 
from typing import Optional, Dict, Any, Union
import numpy as np 
import cv2 

# Importa o transmissor de screenshots
from screenVision.transmitter import transmitter

# Importa o singleton adb_manager
from ADBmanager import adb_manager

# --- Carregar Configuração Específica deste Módulo ---
def load_screenshot_config() -> Dict[str, Any]:
    """Carrega a configuração do arquivo cfg/screenshotCFG.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'screenshotCFG.json') 
    default_config = {"capture_method": "adb", "target_fps": 1, "debug_mode": False, "debug_output_dir": "output_error"}
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Validação básica
            if "capture_method" not in config or "target_fps" not in config:
                 print("⚠️ Alerta: Configuração screenshotCFG.json inválida ou incompleta. Usando defaults.")
                 return default_config
            return config
    except FileNotFoundError:
        print(f"⚠️ Alerta: Arquivo screenshotCFG.json não encontrado em {config_path}. Usando defaults.")
        return default_config
    except json.JSONDecodeError:
        print(f"❌ Erro: Arquivo screenshotCFG.json mal formatado em {config_path}. Usando defaults.")
        return default_config

# Carrega a configuração específica deste módulo
config = load_screenshot_config()

class Screenshotter:
    """Responsável por tirar screenshots usando o método definido na configuração."""

    def __init__(self, adb_device: Optional[AdbDevice] = None):
        """Inicializa o Screenshotter com base na configuração carregada e o dispositivo ADB fornecido.
        
        Args:
            adb_device: Dispositivo ADB para uso. Se None, usará o dispositivo do adb_manager global.
        """
        self.config = config 
        self.method = self.config.get("capture_method", "adb")
        self.debug_mode = self.config.get("debug_mode", False)
        self.output_dir = self.config.get("debug_output_dir", "output_screenshots")
        self.frame_counter = 0
        self.device: Optional[AdbDevice] = adb_device  # Pode ser None
        self.output_dir_abs: Optional[str] = None

        # Verifica o dispositivo - permite None para usar o adb_manager depois
        if self.device is None:
            print("📸⚠️ Screenshotter: Nenhum dispositivo fornecido, usará o adb_manager global quando necessário.")
        elif not isinstance(self.device, AdbDevice):
            # Invalidação apenas se o dispositivo for fornecido mas for de tipo inválido
            print("❌ Erro: Screenshotter recebeu um objeto que não é AdbDevice.")
            raise ValueError("Quando fornecido, Screenshotter requer um objeto AdbDevice válido.")

        # Cria diretório de debug se necessário e modo debug ativo
        if self.debug_mode:
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Vai para a raiz do projeto
                self.output_dir_abs = os.path.join(project_root, self.output_dir)
                os.makedirs(self.output_dir_abs, exist_ok=True)
                print(f"📸📦 Modo Debug ATIVADO. Screenshots serão salvas em: '{self.output_dir_abs}'")
            except OSError as e:
                 print(f"❌ Erro ao criar diretório de debug '{self.output_dir_abs}': {e}")
                 print("Modo Debug será desativado.")
                 self.debug_mode = False
        else:
            print("📸✨ Screenshotter inicializado (Modo Debug DESATIVADO).")

        # Validação inicial do método
        if self.method not in ["adb"]: # Adicionar outros métodos aqui se implementados
             print(f"⚠️ Alerta: Método de captura '{self.method}' não suportado. Usando 'adb'.")
             self.method = "adb"

    def _save_debug_screenshot(self, image_data: Optional[object], format_type: str):
         """Salva a screenshot no modo debug."""
         if not self.debug_mode or image_data is None or self.output_dir_abs is None:
              return 

         self.frame_counter += 1
         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3] 
         filename = f"frame_{self.frame_counter:05d}_{timestamp}_{self.method}.png" 
         save_path = os.path.join(self.output_dir_abs, filename) 

         try:
              if format_type == "PIL" and isinstance(image_data, Image.Image):
                   image_data.save(save_path)
              elif format_type == "OpenCV" and isinstance(image_data, np.ndarray):
                   cv2.imwrite(save_path, image_data)
         except Exception as e:
              print(f"❌ Debug: Erro ao salvar screenshot em {save_path}: {e}")


    def _take_screenshot_adb(self, use_pil: bool) -> Optional[Image.Image | object]:
        """Tira screenshot usando ADB."""
        # Se não tiver um dispositivo, tenta obter do adb_manager
        device_to_use = self.device
        
        if not device_to_use:
            # Tenta obter o dispositivo do adb_manager global
            if not adb_manager.is_connected():
                print("Screenshotter: ADB não está conectado, tentando conectar via manager...")
                if not adb_manager.connect_first_device():
                    print("❌ Screenshotter: Falha ao conectar dispositivo via ADBManager")
                    return None
            
            device_to_use = adb_manager.get_device()
            if not device_to_use:
                print("❌ Screenshotter: ADBManager conectado, mas não retornou um objeto de dispositivo válido")
                return None

        pil_image: Optional[Image.Image] = None
        try:
            # Método 1 (adbutils direto)
            pil_image = device_to_use.screenshot()
            if pil_image is None: raise AdbError("device.screenshot() retornou None")
            
        except AdbError as e1:
            # print(f"Erro no Método 1 (device.screenshot): {e1}. Tentando Método 2...") # Log verboso removido
            try:
                # Método 2 (Fallback via shell screencap)
                png_data = device_to_use.shell("screencap -p", encoding=None)
                if not png_data: 
                    print("Erro: screencap retornou dados vazios.")
                    return None
                pil_image = Image.open(io.BytesIO(png_data)) 
            except AdbError as e2:
                print(f"Erro ADB no Método 2 (shell screencap): {e2}") 
                return None
            except Exception as e_pil:
                 print(f"Erro ao processar imagem do screencap: {e_pil}")
                 return None
        except Exception as e_gen:
             print(f"Erro inesperado ao tirar screenshot ADB: {e_gen}")
             return None

        # Se temos uma imagem PIL, converte se necessário e retorna
        if pil_image:
            if use_pil:
                return pil_image
            else:
                try:
                    # Garante conversão correta PIL(RGB) para OpenCV(BGR)
                    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                except Exception as cv_e: 
                     print(f"Erro ao converter PIL para OpenCV: {cv_e}")
                     return None
        return None # Se não conseguiu imagem


    def take_screenshot(self, use_pil: bool = False, username: Optional[str] = None, transmit: bool = True) -> Optional[Union[Image.Image, np.ndarray]]:
        """
        Tira uma screenshot usando o método configurado. Salva se debug_mode=True.
        Se transmit=True e username fornecido, envia a imagem para a VPS.

        Args:
            use_pil (bool): Define o formato de retorno (PIL ou OpenCV). Padrão False (OpenCV).
            username (str, opcional): Username associado à captura para identificação na VPS.
            transmit (bool): Se True, transmite a imagem para a VPS. Padrão True.

        Returns:
            PIL.Image or numpy.ndarray or None: A imagem capturada ou None se falhar.
        """
        image_data: Optional[object] = None
        format_used = "PIL" if use_pil else "OpenCV"

        if self.method == "adb":
            image_data = self._take_screenshot_adb(use_pil)
        # elif self.method == "pyautogui": # Espaço para futura implementação
        #    image_data = self._take_screenshot_pyautogui(use_pil)
        else:
            print(f"Erro: Método de captura '{self.method}' não configurado ou suportado.")
            return None 

        # Salva apenas se a captura foi bem sucedida
        if image_data is not None:
            self._save_debug_screenshot(image_data, format_used)
            
            # Transmite a imagem se solicitado - sempre deve tentar enviar
            if transmit and transmitter.transmission_enabled:
                # Define o ID para identificação (usa username se fornecido, senão usa "screen")
                screen_id = username if username else "screen"
                
                # O callback de transmissão cuidará de atualizar a GUI
                # A mensagem de log foi removida para evitar flood no terminal
                
                # Garante que o transmissor tem o username configurado
                if username:
                    transmitter.set_username(username)
                
                # Envia a imagem para a fila de transmissão
                transmitter.queue_image(image_data, screen_id)
            
        return image_data