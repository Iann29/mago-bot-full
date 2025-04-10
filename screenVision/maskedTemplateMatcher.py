# /screenVision/maskedTemplateMatcher.py

import cv2
import numpy as np
import os
from typing import Optional, Tuple, Dict, Union, List

class MaskedTemplateMatcher:
    """
    Realiza a busca por imagens de template com máscara dentro de uma imagem maior,
    usando OpenCV. A máscara permite ignorar partes específicas do template durante a busca.
    """

    def __init__(self, default_threshold: float = 0.9, verbose: bool = False):
        """
        Inicializa o MaskedTemplateMatcher.

        Args:
            default_threshold (float): O limiar de confiança padrão a ser usado
                                       se nenhum for especificado na busca.
                                       Para TM_CCORR_NORMED, geralmente valores altos (0.9+)
                                       funcionam melhor.
            verbose (bool): Se True, exibe mensagens de log detalhadas.
        """
        self.default_threshold = default_threshold
        self.verbose = verbose
        # Opcional: Cache de templates e máscaras para evitar I/O repetido
        # self._template_cache: Dict[str, np.ndarray] = {}
        # self._mask_cache: Dict[str, np.ndarray] = {}
        if self.verbose:
            print("MaskedTemplateMatcher inicializado.")

    def _load_template(self, template_path: str) -> Optional[np.ndarray]:
        """
        Carrega uma imagem de template do disco.

        Args:
            template_path (str): Caminho completo para o arquivo .png do template.

        Returns:
            Optional[np.ndarray]: O template carregado como um array NumPy (OpenCV)
                                  ou None se o carregamento falhar.
        """
        if not os.path.exists(template_path):
            if self.verbose:
                print(f"❌ MaskedTemplateMatcher: Template não encontrado: '{template_path}'")
            return None
            
        try:
            # Carrega em cores (BGR) pois para template com máscara isso geralmente
            # funciona melhor que grayscale
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                if self.verbose:
                    print(f"❌ MaskedTemplateMatcher: Falha ao carregar template: '{template_path}'")
                return None
            
            return template
        except Exception as e:
            if self.verbose:
                print(f"❌ MaskedTemplateMatcher: Erro ao carregar template: {e}")
            return None

    def _load_mask(self, mask_path: str) -> Optional[np.ndarray]:
        """
        Carrega uma imagem de máscara do disco.

        Args:
            mask_path (str): Caminho completo para o arquivo .png da máscara.

        Returns:
            Optional[np.ndarray]: A máscara carregada como um array NumPy (OpenCV)
                                  em escala de cinza ou None se o carregamento falhar.
        """
        if not os.path.exists(mask_path):
            if self.verbose:
                print(f"❌ MaskedTemplateMatcher: Máscara não encontrada: '{mask_path}'")
            return None
            
        try:
            # A máscara deve ser carregada em escala de cinza, conforme requisitos
            # do cv2.matchTemplate com máscara
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                if self.verbose:
                    print(f"❌ MaskedTemplateMatcher: Falha ao carregar máscara: '{mask_path}'")
                return None
            
            return mask
        except Exception as e:
            if self.verbose:
                print(f"❌ MaskedTemplateMatcher: Erro ao carregar máscara: {e}")
            return None

    def find_template(self, 
                      main_image: np.ndarray, 
                      template_path: str,
                      mask_path: str,
                      roi: Optional[Tuple[int, int, int, int]] = None, 
                      threshold: Optional[float] = None,
                      silent: bool = False
                     ) -> Optional[Dict[str, Union[bool, float, Tuple[int, int], List[int]]]]:
        """
        Procura por um template (.png) dentro da imagem principal, usando uma máscara.

        Args:
            main_image (np.ndarray): A imagem onde procurar (formato OpenCV BGR).
            template_path (str): O caminho para o arquivo .png do template.
            mask_path (str): O caminho para o arquivo .png da máscara.
            roi (Optional[Tuple[int, int, int, int]]): Região de Interesse (x, y, w, h) 
                                                       para limitar a busca na main_image.
            threshold (Optional[float]): Limiar de confiança (0.0 a 1.0). Se None, usa
                                         o default_threshold da classe.
            silent (bool): Se True, suprime mensagens de log.

        Returns:
            Optional[Dict]: Um dicionário com os detalhes da melhor correspondência encontrada
                           acima do limiar, ou None se nada for encontrado.
                           Exemplo: {'found': True, 'confidence': 0.95, 
                                     'position': (center_x, center_y), 
                                     'rectangle': [x_min, y_min, x_max, y_max]}
        """
        
        if main_image is None:
            if not silent:
                print("MaskedTemplateMatcher: Imagem principal é None.")
            return None

        # Carrega o template e a máscara
        template = self._load_template(template_path)
        if template is None:
            return None  # Erro já foi logado em _load_template
            
        mask = self._load_mask(mask_path)
        if mask is None:
            return None  # Erro já foi logado em _load_mask

        # Verifica se o template e a máscara têm as mesmas dimensões
        if template.shape[:2] != mask.shape[:2]:
            if not silent:
                print(f"❌ MaskedTemplateMatcher: Template ({template.shape[:2]}) e Máscara ({mask.shape[:2]}) têm dimensões diferentes!")
            return None

        # Define o limiar a ser usado
        current_threshold = threshold if threshold is not None else self.default_threshold

        # Define a área de busca (ROI ou imagem inteira)
        search_area = main_image
        offset_x, offset_y = 0, 0
        if roi:
            try:
                x, y, w, h = roi
                # Validação básica da ROI
                if x < 0 or y < 0 or w <= 0 or h <= 0 or \
                   x + w > main_image.shape[1] or y + h > main_image.shape[0]:
                    if not silent and self.verbose:
                        print(f"⚠️ MaskedTemplateMatcher: ROI inválida. Usando imagem inteira.")
                else:
                    search_area = main_image[y:y+h, x:x+w]
                    offset_x, offset_y = x, y
                    # Verifica se a ROI é maior que o template (necessário para matchTemplate)
                    if search_area.shape[0] < template.shape[0] or search_area.shape[1] < template.shape[1]:
                        if not silent and self.verbose:
                            print(f"⚠️ MaskedTemplateMatcher: ROI menor que o template. Usando imagem inteira.")
                        search_area = main_image
                        offset_x, offset_y = 0, 0

            except Exception as e_roi:
                if not silent and self.verbose:
                    print(f"⚠️ MaskedTemplateMatcher: Erro ao processar ROI. Usando imagem inteira.")
                search_area = main_image
                offset_x, offset_y = 0, 0
        
        # Garante que a área de busca ainda seja válida após o corte da ROI
        if search_area.shape[0] < template.shape[0] or search_area.shape[1] < template.shape[1]:
            if not silent and self.verbose:
                print(f"❌ MaskedTemplateMatcher: Área de busca menor que o template. Impossível comparar.")
            return None

        # Realiza o Template Matching com máscara
        try:
            # TM_CCORR_NORMED funciona melhor com máscaras em testes realizados
            result = cv2.matchTemplate(search_area, template, cv2.TM_CCORR_NORMED, mask=mask)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if not silent and self.verbose:
                print(f"MaskedTemplateMatcher: Confiança: {max_val:.4f}")

            # Verifica se a confiança máxima atingiu o limiar
            if max_val >= current_threshold:
                # Calcula as coordenadas da caixa delimitadora e do centro
                template_h, template_w = template.shape[:2]
                
                # Canto superior esquerdo na imagem *principal*
                top_left_x = max_loc[0] + offset_x
                top_left_y = max_loc[1] + offset_y
                
                # Canto inferior direito na imagem *principal*
                bottom_right_x = top_left_x + template_w
                bottom_right_y = top_left_y + template_h

                # Centro na imagem *principal*
                center_x = top_left_x + template_w // 2
                center_y = top_left_y + template_h // 2

                return {
                    'found': True,
                    'confidence': float(max_val),  # Converte para float padrão
                    'position': (center_x, center_y),
                    'rectangle': [top_left_x, top_left_y, bottom_right_x, bottom_right_y]  # [xmin, ymin, xmax, ymax]
                }
            else:
                # Encontrou algo, mas abaixo da confiança mínima
                if not silent and self.verbose:
                    print(f"MaskedTemplateMatcher: Template não encontrado (confiança {max_val:.4f} < {current_threshold}).")
                return None

        except Exception as e:
            if not silent and self.verbose:
                print(f"❌ MaskedTemplateMatcher: Erro durante matchTemplate: {e}")
            return None

# --- Bloco de Teste (Opcional) ---
if __name__ == "__main__":
    print("--- Testando MaskedTemplateMatcher ---")
    
    # Crie ou coloque uma imagem de teste, um template e uma máscara na mesma pasta
    # Exemplo: 'test_main_image.png', 'test_template.png' e 'test_mask.png'
    
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    # Para testar, use o caminho correto para suas imagens
    main_image_path = os.path.join(project_root, "dataset", "haydayBuildings", "screenshot.png") 
    template_path = os.path.join(project_root, "dataset", "haydayBuildings", "banca.png")
    mask_path = os.path.join(project_root, "dataset", "haydayBuildings", "bancamask.png")
    
    if not os.path.exists(main_image_path) or not os.path.exists(template_path) or not os.path.exists(mask_path):
        print(f"Erro: Verifique se os arquivos de teste existem nas localizações especificadas.")
    else:
        matcher = MaskedTemplateMatcher(default_threshold=0.8, verbose=True)
        
        # Carrega a imagem principal
        img_main = cv2.imread(main_image_path, cv2.IMREAD_COLOR)
        
        if img_main is not None:
            print(f"\nBuscando '{os.path.basename(template_path)}' na imagem inteira com máscara...")
            result = matcher.find_template(img_main, template_path, mask_path)
            
            if result:
                print(f"✅ Encontrado: Conf={result['confidence']:.4f}, Pos={result['position']}, Rect={result['rectangle']}")
                
                # Desenha o resultado para visualização
                debug_img = img_main.copy()
                r = result['rectangle']
                cv2.rectangle(debug_img, (r[0], r[1]), (r[2], r[3]), (0, 255, 0), 2)  # Retângulo em verde
                cv2.circle(debug_img, result['position'], 5, (0, 0, 255), -1)  # Centro em vermelho
                
                # Salva a imagem de resultado
                debug_path = os.path.join(project_root, "output_masked_test.png")
                cv2.imwrite(debug_path, debug_img)
                print(f"Imagem de debug salva em: {debug_path}")
            else:
                print("❌ Template não encontrado na imagem (ou abaixo do limiar).")
        else:
            print(f"Erro ao carregar a imagem principal de teste.")
