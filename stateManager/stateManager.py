# stateManager/stateManager.py

import os
import cv2
import time
import json
import threading
import numpy as np
from enum import Enum, auto
from typing import Dict, Optional, List, Tuple, Callable, Any, Union

# Importando o template matcher existente para aproveitar o código
from screenVision.templateMatcher import TemplateMatcher

# Definição do estado desconhecido como string constante
UNKNOWN_STATE = "unknown"

class StateConfig:
    """
    Classe para armazenar a configuração de um estado do jogo
    """
    def __init__(self, 
                 state_id: str,
                 display_name: str,
                 image_path: str,
                 roi: List[int] = None,
                 confidence: float = 0.75,
                 use_mask: bool = False,
                 priority: List[str] = None):
        self.state_id = state_id
        self.display_name = display_name
        self.image_path = image_path
        self.roi = roi if roi else [0, 0, 0, 0]  # x, y, largura, altura
        self.confidence = confidence
        self.use_mask = use_mask
        self.priority = priority if priority else []
        self.mask_path = None
        
        # Se usar máscara, cria o caminho para o arquivo de máscara
        if use_mask:
            # Separa o nome do arquivo e extensão
            base_path, ext = os.path.splitext(image_path)
            self.mask_path = f"{base_path}mask{ext}"
            
    def __str__(self):
        return self.display_name

class StateManager:
    """
    Gerenciador de estados que monitora screenshots para identificar
    em qual estado o jogo se encontra baseado em imagens de referência.
    """
    
    def __init__(self, 
                 config_file: str = None,
                 check_interval: float = 0.2,
                 verbose: bool = False):
        """
        Inicializa o gerenciador de estados.
        
        Args:
            config_file: Caminho para o arquivo de configuração JSON dos estados
            check_interval: Intervalo em segundos para verificação de estados
            verbose: Se True, imprime mensagens de debug detalhadas
        """
        # Obtém o diretório do projeto
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define o arquivo de configuração padrão se não for fornecido
        if config_file is None:
            self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statesCFG.json")
        else:
            self.config_file = config_file
        
        # Verifica se o arquivo de configuração existe
        if not os.path.exists(self.config_file):
            raise ValueError(f"Arquivo de configuração não encontrado: {self.config_file}")
            
        # Configurações
        self.check_interval = check_interval
        self.verbose = verbose
        
        # Estado atual e anterior
        self.current_state = UNKNOWN_STATE
        self._previous_state = UNKNOWN_STATE
        self._last_state_change_time = time.time()
        
        # Dicionário de configurações de estados
        self.state_configs: Dict[str, StateConfig] = {}
        
        # Dicionário de templates carregados
        self.templates: Dict[str, Dict[str, Any]] = {}
        
        # Carrega a configuração dos estados
        self._load_state_configs()
        
        # Carrega os templates
        self._load_templates()
        
        # Instancia o template matcher para uso na detecção
        self.template_matcher = TemplateMatcher()
        
        # Configurações para thread
        self._running = False
        self._state_thread = None
        self._lock = threading.Lock()
        
        # Callbacks
        self._state_change_callbacks: List[Callable[[str, str], None]] = []
        
        if self.verbose:
            print(f"🔔✨ StateManager inicializado. {len(self.templates)} templates de estado carregados.")
    
    def _load_state_configs(self) -> None:
        """Carrega a configuração dos estados a partir do arquivo JSON"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            if 'states' not in config_data:
                raise ValueError(f"Arquivo de configuração inválido: Chave 'states' não encontrada em {self.config_file}")
                
            # Carrega cada estado definido no arquivo JSON
            for state_id, state_config in config_data['states'].items():
                try:
                    # Cria uma configuração de estado a partir dos dados do JSON
                    self.state_configs[state_id] = StateConfig(
                        state_id=state_id,
                        display_name=state_config.get('display_name', state_id),
                        image_path=state_config.get('image_path', ''),
                        roi=state_config.get('roi', [0, 0, 0, 0]),
                        confidence=state_config.get('confidence', 0.75),
                        use_mask=state_config.get('use_mask', False),
                        priority=state_config.get('priority', [])
                    )
                    
                    if self.verbose:
                        print(f"🔔📄 Configuração carregada para estado {state_id}: {self.state_configs[state_id].display_name}")
                        
                except Exception as e:
                    print(f"❌ Erro ao processar configuração para estado {state_id}: {e}")
                    
        except Exception as e:
            print(f"❌ Erro ao carregar arquivo de configuração {self.config_file}: {e}")
            raise
            
    def _load_templates(self) -> None:
        """Carrega as imagens de templates para cada estado"""
        for state_id, config in self.state_configs.items():
            # Caminho absoluto para o arquivo de template
            image_path = os.path.join(self.project_root, config.image_path)
            
            if os.path.exists(image_path):
                try:
                    # Carrega o template colorido para permitir máscaras
                    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
                    
                    if template is not None:
                        # Salva o template no dicionário
                        self.templates[state_id] = {
                            'template': template,
                            'mask': None,  # Será preenchido abaixo se usar máscara
                            'config': config
                        }
                        
                        # Se usar máscara, carrega a imagem da máscara
                        if config.use_mask and config.mask_path:
                            mask_path = os.path.join(self.project_root, config.mask_path)
                            if os.path.exists(mask_path):
                                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                                if mask is not None:
                                    self.templates[state_id]['mask'] = mask
                                    if self.verbose:
                                        print(f"🔔🎭 Máscara carregada para estado {state_id}: {mask_path}")
                                else:
                                    print(f"❌ Erro ao carregar máscara para estado {state_id}: {mask_path}")
                            else:
                                print(f"⚠️ Arquivo de máscara não encontrado para estado {state_id}: {mask_path}")
                        
                        if self.verbose:
                            print(f"🔔🖼️ Template carregado para estado {state_id}: {image_path}")
                    else:
                        print(f"❌ Erro ao carregar template para estado {state_id}: {image_path}")
                        
                except Exception as e:
                    print(f"❌ Erro ao processar template para estado {state_id}: {e}")
            else:
                print(f"❌ Arquivo de template não encontrado para estado {state_id}: {image_path}")
    
    def register_state_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Registra uma função de callback que será chamada quando o estado mudar.
        
        Args:
            callback: Função que recebe o estado anterior (state_id) e o novo estado como parâmetros
        """
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)
    
    def unregister_state_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """Remove um callback de mudança de estado"""
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
    
    def _notify_state_change(self, previous_state: str, new_state: str) -> None:
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
            print("🔔⚠️ StateManager já está em execução.")
            return
        
        self._running = True
        self._state_thread = threading.Thread(
            target=self._monitor_state_thread,
            args=(screenshot_queue,),
            daemon=True
        )
        self._state_thread.start()
        print("🔔✨ StateManager: Monitoramento de estados iniciado.")
    
    def stop_monitoring(self) -> None:
        """Para o monitoramento de estados"""
        self._running = False
        if self._state_thread and self._state_thread.is_alive():
            self._state_thread.join(timeout=2.0)
            print("🔔⏹️ StateManager: Monitoramento de estados parado.")
    
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
        Detecta o estado atual baseado no screenshot usando o TemplateMatch,
        ROIs específicos, máscaras e sistema de prioridades.
        
        Args:
            screenshot: Imagem do screenshot atual (formato OpenCV/numpy)
        """
        # Mantém o screenshot original para visualização e debugging
        original_screenshot = screenshot.copy()
        
        # Dicionário para armazenar matches encontrados
        matches = {}
        
        # Para cada template configurado
        for state_id, template_data in self.templates.items():
            config = template_data['config']
            template = template_data['template']
            mask = template_data['mask']  # Pode ser None
            
            try:
                # Cria o ROI a partir da configuração
                roi = None
                if config.roi and (config.roi[2] > 0 and config.roi[3] > 0):  # Se largura e altura forem > 0
                    roi = tuple(config.roi)  # (x, y, largura, altura)
                
                # Determina o threshold específico para este estado
                threshold = config.confidence
                
                # Usa o template matcher com os parâmetros configurados
                match_result = None
                
                # Se tiver uma máscara, usa o método com máscara
                if config.use_mask and mask is not None:
                    # Para usar máscara, precisa criar um arquivo temporário ou usar o OpenCV diretamente
                    # Aqui, usamos o OpenCV diretamente
                    # Primeiro, preparamos a região de interesse se especificado
                    search_area = screenshot
                    offset_x, offset_y = 0, 0
                    
                    if roi:
                        x, y, w, h = roi
                        if x >= 0 and y >= 0 and w > 0 and h > 0:
                            # Verifica se a ROI está dentro dos limites da imagem
                            if x < screenshot.shape[1] and y < screenshot.shape[0]:
                                # Ajusta a ROI se ela exceder os limites da imagem
                                w = min(w, screenshot.shape[1] - x)
                                h = min(h, screenshot.shape[0] - y)
                                
                                # Recorta a área de interesse
                                search_area = screenshot[y:y+h, x:x+w]
                                offset_x, offset_y = x, y
                    
                    # Verifica se as dimensões são adequadas
                    if search_area.shape[0] >= template.shape[0] and search_area.shape[1] >= template.shape[1]:
                        # Aplica template matching com máscara
                        result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED, mask=mask)
                        _, confidence, _, match_loc = cv2.minMaxLoc(result)
                        
                        if confidence >= threshold:
                            # Calcula as coordenadas considerando o offset
                            top_left_x = match_loc[0] + offset_x
                            top_left_y = match_loc[1] + offset_y
                            
                            bottom_right_x = top_left_x + template.shape[1]
                            bottom_right_y = top_left_y + template.shape[0]
                            
                            center_x = top_left_x + template.shape[1] // 2
                            center_y = top_left_y + template.shape[0] // 2
                            
                            match_result = {
                                'found': True,
                                'confidence': float(confidence),
                                'position': (center_x, center_y),
                                'rectangle': [top_left_x, top_left_y, bottom_right_x, bottom_right_y]
                            }
                else:
                    # Usa o TemplateMatcher para templates normais
                    match_result = self.template_matcher.find_template(
                        main_image=screenshot,
                        template_path=os.path.join(self.project_root, config.image_path),
                        roi=roi,
                        threshold=threshold
                    )
                
                if match_result and match_result.get('found', False):
                    matches[state_id] = {
                        'confidence': match_result['confidence'],
                        'config': config
                    }
                    
                    if self.verbose:
                        print(f"Estado {state_id}: confiança {match_result['confidence']:.4f}")
            except Exception as e:
                print(f"❌ Erro ao processar template para estado {state_id}: {e}")
        
        # Determina o melhor estado considerando prioridades
        best_state = self._determine_best_state(matches)
        
        # Atualiza o estado se necessário
        with self._lock:
            if best_state != self.current_state:
                self._previous_state = self.current_state
                self.current_state = best_state
                self._last_state_change_time = time.time()
                
                # Notifica sobre a mudança de estado
                self._notify_state_change(self._previous_state, self.current_state)
                
                # Nome para exibir do estado atual
                display_name = self.state_configs.get(best_state, StateConfig(best_state, best_state, "")).display_name
                prev_display_name = self.state_configs.get(self._previous_state, StateConfig(self._previous_state, self._previous_state, "")).display_name
                
                if self.verbose or best_state != UNKNOWN_STATE:
                    confidence_str = ""
                    if best_state != UNKNOWN_STATE and best_state in matches:
                        confidence_str = f" (confiança: {matches[best_state]['confidence']:.4f})"
                    print(f"🔔🔁 Estado alterado: {prev_display_name} -> {display_name}{confidence_str}")
    
    def _determine_best_state(self, matches: Dict[str, Dict]) -> str:
        """
        Determina o melhor estado com base nas correspondências encontradas e prioridades.
        
        Args:
            matches: Dicionário com os matches encontrados para cada estado
            
        Returns:
            ID do melhor estado ou UNKNOWN_STATE se nenhum for encontrado
        """
        if not matches:
            return UNKNOWN_STATE
            
        # Lista de estados detectados ordenados por confiança
        detected_states = sorted(matches.keys(), key=lambda s: matches[s]['confidence'], reverse=True)
        
        # Verifica sistema de prioridades
        # Para cada estado detectado, verifica se ele tem prioridade sobre os outros
        for state_id in detected_states:
            config = matches[state_id]['config']
            
            # Verifica se este estado tem prioridade sobre algum outro estado detectado
            has_priority = True
            
            # Se não tem prioridades definidas, usa apenas a confiança
            if not config.priority:
                return detected_states[0]  # Retorna o estado com maior confiança
            
            # Verifica se todos os estados de prioridade foram detectados
            for priority_state in config.priority:
                if priority_state in detected_states:
                    has_priority = False
                    break
            
            # Se tem prioridade sobre todos os outros estados detectados, é o vencedor
            if has_priority:
                return state_id
        
        # Se chegou aqui, retorna o estado com maior confiança
        return detected_states[0]
    
    def get_current_state(self) -> str:
        """Retorna o estado atual do jogo (ID do estado)"""
        with self._lock:
            return self.current_state
    
    def get_current_state_display_name(self) -> str:
        """Retorna o nome para exibição do estado atual do jogo"""
        with self._lock:
            if self.current_state in self.state_configs:
                return self.state_configs[self.current_state].display_name
            return self.current_state.replace('_', ' ').title()
    
    def get_state_duration(self) -> float:
        """Retorna o tempo (em segundos) desde a última mudança de estado"""
        with self._lock:
            return time.time() - self._last_state_change_time
    
    def get_previous_state(self) -> str:
        """Retorna o estado anterior do jogo (ID do estado)"""
        with self._lock:
            return self._previous_state
    
    def get_previous_state_display_name(self) -> str:
        """Retorna o nome para exibição do estado anterior do jogo"""
        with self._lock:
            if self._previous_state in self.state_configs:
                return self.state_configs[self._previous_state].display_name
            return self._previous_state.replace('_', ' ').title()
