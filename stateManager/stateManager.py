# stateManager/stateManager.py

import os
import cv2
import time
import threading
import numpy as np
from enum import Enum, auto
from typing import Dict, Optional, List, Tuple, Callable

# Importando o template matcher existente para aproveitar o código
from screenVision.templateMatcher import TemplateMatcher

# Definição dos estados possíveis do jogo
class GameState(Enum):
    UNKNOWN = auto()        # Estado desconhecido ou não identificado
    MOBILE_HOME = auto()    # Tela principal do android
    # Adicionar outros estados conforme necessário
    
    def __str__(self):
        return self.name.replace('_', ' ').title()

class StateManager:
    """
    Gerenciador de estados que monitora screenshots para identificar
    em qual estado o jogo se encontra baseado em imagens de referência.
    """
    
    def __init__(self, 
                 image_states_dir: str = None, 
                 threshold: float = 0.75,
                 check_interval: float = 0.2,
                 verbose: bool = False):
        """
        Inicializa o gerenciador de estados.
        
        Args:
            image_states_dir: Diretório com as imagens de referência para estados
            threshold: Limiar de confiança para correspondência de templates
            check_interval: Intervalo em segundos para verificação de estados
            verbose: Se True, imprime mensagens de debug detalhadas
        """
        # Obtém o diretório do projeto
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define o diretório de imagens de estados
        if image_states_dir is None:
            self.image_states_dir = os.path.join(self.project_root, "dataset", "imageStates")
        else:
            self.image_states_dir = image_states_dir
            
        # Verifica se o diretório existe
        if not os.path.exists(self.image_states_dir):
            raise ValueError(f"Diretório de estados não encontrado: {self.image_states_dir}")
        
        # Configurações
        self.threshold = threshold
        self.check_interval = check_interval
        self.verbose = verbose
        
        # Estado atual
        self.current_state = GameState.UNKNOWN
        self._previous_state = GameState.UNKNOWN
        self._last_state_change_time = time.time()
        
        # Mapeamento de arquivos de imagem para estados
        self.state_images: Dict[GameState, str] = {
            GameState.MOBILE_HOME: os.path.join(self.image_states_dir, "mobilehome.png"),
            # Adicionar outros mapeamentos conforme necessário
        }
        
        # Carrega as imagens dos estados
        self.state_templates: Dict[GameState, np.ndarray] = {}
        self._load_state_templates()
        
        # Instancia o template matcher para uso na detecção
        self.template_matcher = TemplateMatcher(default_threshold=self.threshold)
        
        # Configurações para thread
        self._running = False
        self._state_thread = None
        self._lock = threading.Lock()
        
        # Callbacks
        self._state_change_callbacks: List[Callable[[GameState, GameState], None]] = []
        
        if self.verbose:
            print(f"StateManager inicializado. {len(self.state_templates)} templates de estado carregados.")
    
    def _load_state_templates(self) -> None:
        """Carrega as imagens de templates para cada estado"""
        for state, image_path in self.state_images.items():
            if os.path.exists(image_path):
                try:
                    # Carrega imagem em escala de cinza para matching mais eficiente
                    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.state_templates[state] = template
                        if self.verbose:
                            print(f"Carregado template para estado {state}: {image_path}")
                    else:
                        print(f"❌ Erro ao carregar template para estado {state}: {image_path}")
                except Exception as e:
                    print(f"❌ Erro ao processar template para estado {state}: {e}")
            else:
                print(f"❌ Arquivo de template não encontrado para estado {state}: {image_path}")
    
    def register_state_change_callback(self, callback: Callable[[GameState, GameState], None]) -> None:
        """
        Registra uma função de callback que será chamada quando o estado mudar.
        
        Args:
            callback: Função que recebe o estado anterior e o novo estado como parâmetros
        """
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)
    
    def unregister_state_change_callback(self, callback: Callable[[GameState, GameState], None]) -> None:
        """Remove um callback de mudança de estado"""
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
    
    def _notify_state_change(self, previous_state: GameState, new_state: GameState) -> None:
        """Notifica todos os callbacks registrados sobre a mudança de estado"""
        for callback in self._state_change_callbacks:
            try:
                callback(previous_state, new_state)
            except Exception as e:
                print(f"❌ Erro ao executar callback de mudança de estado: {e}")
    
    def start_monitoring(self, screenshot_queue) -> None:
        """
        Inicia o monitoramento de estados em uma thread separada.
        
        Args:
            screenshot_queue: Fila de screenshots a ser monitorada
        """
        if self._running:
            print("StateManager já está em execução.")
            return
        
        self._running = True
        self._state_thread = threading.Thread(
            target=self._monitor_state_thread,
            args=(screenshot_queue,),
            daemon=True
        )
        self._state_thread.start()
        print("StateManager: Monitoramento de estados iniciado.")
    
    def stop_monitoring(self) -> None:
        """Para o monitoramento de estados"""
        self._running = False
        if self._state_thread and self._state_thread.is_alive():
            self._state_thread.join(timeout=2.0)
            print("StateManager: Monitoramento de estados parado.")
    
    def _monitor_state_thread(self, screenshot_queue) -> None:
        """
        Thread que monitora a fila de screenshots e identifica o estado atual.
        
        Args:
            screenshot_queue: Fila contendo os screenshots capturados
        """
        last_check_time = 0
        
        while self._running:
            current_time = time.time()
            
            # Verifica se é hora de processar um novo frame
            if current_time - last_check_time >= self.check_interval:
                # Tenta obter um screenshot da fila sem bloquear
                screenshot = None
                try:
                    if not screenshot_queue.empty():
                        screenshot = screenshot_queue.get_nowait()
                        # Importante: Marcar como concluído
                        screenshot_queue.task_done()
                except Exception as e:
                    if self.verbose:
                        print(f"Erro ao obter screenshot da fila: {e}")
                
                # Se conseguiu um screenshot, tenta detectar o estado
                if screenshot is not None:
                    self._detect_state(screenshot)
                
                last_check_time = current_time
            
            # Pausa pequena para não consumir CPU
            time.sleep(0.05)
    
    def _detect_state(self, screenshot: np.ndarray) -> None:
        """
        Detecta o estado atual baseado no screenshot.
        
        Args:
            screenshot: Imagem do screenshot atual (formato OpenCV/numpy)
        """
        # Converte para escala de cinza se não estiver
        if len(screenshot.shape) > 2 and screenshot.shape[2] == 3:
            gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        else:
            gray_screenshot = screenshot
        
        best_match_state = GameState.UNKNOWN
        best_match_confidence = 0.0
        
        # Verifica cada template de estado
        for state, template in self.state_templates.items():
            try:
                # Usa o template matcher para encontrar o template na imagem
                result = cv2.matchTemplate(gray_screenshot, template, cv2.TM_CCOEFF_NORMED)
                _, confidence, _, _ = cv2.minMaxLoc(result)
                
                if self.verbose:
                    print(f"Estado {state}: confiança {confidence:.4f}")
                
                # Se a confiança for maior que o limiar e melhor que o encontrado até agora
                if confidence > self.threshold and confidence > best_match_confidence:
                    best_match_confidence = confidence
                    best_match_state = state
            except Exception as e:
                print(f"❌ Erro ao processar template para estado {state}: {e}")
        
        # Atualiza o estado se necessário
        with self._lock:
            if best_match_state != self.current_state:
                self._previous_state = self.current_state
                self.current_state = best_match_state
                self._last_state_change_time = time.time()
                
                # Notifica sobre a mudança de estado
                self._notify_state_change(self._previous_state, self.current_state)
                
                if self.verbose or best_match_state != GameState.UNKNOWN:
                    print(f"Estado alterado: {self._previous_state} -> {self.current_state} (confiança: {best_match_confidence:.4f})")
    
    def get_current_state(self) -> GameState:
        """Retorna o estado atual do jogo"""
        with self._lock:
            return self.current_state
    
    def get_state_duration(self) -> float:
        """Retorna o tempo (em segundos) desde a última mudança de estado"""
        with self._lock:
            return time.time() - self._last_state_change_time
    
    def get_previous_state(self) -> GameState:
        """Retorna o estado anterior do jogo"""
        with self._lock:
            return self._previous_state
