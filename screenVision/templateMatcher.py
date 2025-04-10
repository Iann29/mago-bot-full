# /screenVision/templateMatcher.py

import cv2
import numpy as np
import os
from typing import Optional, Tuple, Dict, Union, List

class TemplateMatcher:
    """
    Realiza a busca por imagens de template dentro de uma imagem maior,
    usando OpenCV.
    """

    def __init__(self, default_threshold: float = 0.8):
        """
        Inicializa o TemplateMatcher.

        Args:
            default_threshold (float): O limiar de confiança padrão a ser usado 
                                       se nenhum for especificado na busca.
        """
        self.default_threshold = default_threshold
        # Opcional: Cache de templates carregados para evitar I/O repetido
        # self._template_cache: Dict[str, np.ndarray] = {} 
        print("🔍✨ TemplateMatcher inicializado.")

    def _load_template(self, template_path: str) -> Optional[np.ndarray]:
        """
        Carrega uma imagem de template do disco. 
        (Pode adicionar lógica de cache aqui se desejar).

        Args:
            template_path (str): Caminho completo para o arquivo .png do template.

        Returns:
            Optional[np.ndarray]: O template carregado como um array NumPy (OpenCV)
                                  ou None se o carregamento falhar.
        """
        # --- Lógica de Cache (Opcional) ---
        # if template_path in self._template_cache:
        #     return self._template_cache[template_path]
        
        if not os.path.exists(template_path):
            print(f"❌ TemplateMatcher: Arquivo de template não encontrado em '{template_path}'")
            return None
            
        try:
            # Carrega a imagem com cores
            template = cv2.imread(template_path, cv2.IMREAD_COLOR) 
            if template is None:
                print(f"❌ TemplateMatcher: OpenCV não conseguiu carregar o template '{template_path}' (arquivo inválido ou formato não suportado?)")
                return None
            
            # --- Lógica de Cache (Opcional) ---
            # self._template_cache[template_path] = template
            
            return template
        except Exception as e:
            print(f"❌ TemplateMatcher: Erro inesperado ao carregar template '{template_path}': {e}")
            return None

    def find_template(self, 
                      main_image: np.ndarray, 
                      template_path: str, 
                      roi: Optional[Tuple[int, int, int, int]] = None, 
                      threshold: Optional[float] = None
                     ) -> Optional[Dict[str, Union[bool, float, Tuple[int, int], List[int]]]]:
        """
        Procura por um template (.png) dentro da imagem principal.

        Args:
            main_image (np.ndarray): A imagem onde procurar (formato OpenCV BGR ou Grayscale).
            template_path (str): O caminho para o arquivo .png do template.
            roi (Optional[Tuple[int, int, int, int]]): Região de Interesse (x, y, w, h) 
                                                       para limitar a busca na main_image.
            threshold (Optional[float]): Limiar de confiança (0.0 a 1.0). Se None, usa
                                         o default_threshold da classe.

        Returns:
            Optional[Dict]: Um dicionário com os detalhes da melhor correspondência encontrada
                           acima do limiar, ou None se nada for encontrado.
                           Exemplo: {'found': True, 'confidence': 0.95, 
                                     'position': (center_x, center_y), 
                                     'rectangle': [x_min, y_min, x_max, y_max]}
        """
        
        if main_image is None:
            # print("TemplateMatcher: Imagem principal é None.") # Log opcional
            return None

        # Carrega o template
        template = self._load_template(template_path)
        if template is None:
            return None # Erro já foi logado em _load_template

        # Define o limiar a ser usado
        current_threshold = threshold if threshold is not None else self.default_threshold

        # Usa a imagem principal com suas cores originais
        if len(main_image.shape) == 3: # Se for colorida (BGR)
            main_img = main_image
        elif len(main_image.shape) == 2: # Se for grayscale, converte para BGR
            main_img = cv2.cvtColor(main_image, cv2.COLOR_GRAY2BGR)
        else:
             print("❌ TemplateMatcher: Formato de imagem principal inválido.")
             return None

        # Define a área de busca (ROI ou imagem inteira)
        search_area = main_img
        offset_x, offset_y = 0, 0
        if roi:
            try:
                x, y, w, h = roi
                img_height, img_width = main_img.shape[:2]
                
                # Verifica se a ROI está completamente fora da imagem
                if (x >= img_width or y >= img_height or 
                    x + w <= 0 or y + h <= 0 or 
                    w <= 0 or h <= 0):
                    print(f"⚠️ TemplateMatcher: ROI {roi} está completamente fora da imagem {main_img.shape[:2]}. Buscando na imagem inteira.")
                    search_area = main_img
                    offset_x, offset_y = 0, 0
                else:
                    # Ajusta a ROI para manter dentro dos limites da imagem (clipping)
                    # Ajusta coordenada x se estiver fora dos limites
                    if x < 0:
                        # Reduz a largura e ajusta o offset
                        w += x  # x é negativo, então na verdade diminui w
                        offset_x = 0  # Coordenada inicial ajustada para 0
                        x = 0  # Define x como 0 para o recorte
                    else:
                        offset_x = x  # Mantém o offset original
                    
                    # Garante que não ultrapasse a largura da imagem
                    if x + w > img_width:
                        w = img_width - x
                    
                    # Ajusta coordenada y se estiver fora dos limites
                    if y < 0:
                        # Reduz a altura e ajusta o offset
                        h += y  # y é negativo, então na verdade diminui h
                        offset_y = 0  # Coordenada inicial ajustada para 0
                        y = 0  # Define y como 0 para o recorte
                    else:
                        offset_y = y  # Mantém o offset original
                    
                    # Garante que não ultrapasse a altura da imagem
                    if y + h > img_height:
                        h = img_height - y
                    
                    # Log para debug quando a ROI foi ajustada
                    if roi != (x, y, w, h):
                        print(f"🔍📍 TemplateMatcher: ROI ajustada de {roi} para {(x, y, w, h)}")
                    
                    # Recorta a região ajustada
                    search_area = main_img[y:y+h, x:x+w]
                    
                    # Verifica se a ROI é maior que o template (necessário para matchTemplate)
                    if search_area.shape[0] < template.shape[0] or search_area.shape[1] < template.shape[1]:
                        print(f"⚠️ TemplateMatcher: ROI ajustada {(x, y, w, h)} é menor que o template {template.shape}. Buscando na imagem inteira.")
                        search_area = main_img
                        offset_x, offset_y = 0, 0

            except Exception as e_roi:
                print(f"⚠️ TemplateMatcher: Erro ao processar ROI {roi}: {e_roi}. Buscando na imagem inteira.")
                search_area = main_img
                offset_x, offset_y = 0, 0
        
        # Garante que a área de busca ainda seja válida após o corte da ROI
        if search_area.shape[0] < template.shape[0] or search_area.shape[1] < template.shape[1]:
             print(f"❌ TemplateMatcher: Área de busca final ({search_area.shape}) é menor que o template ({template.shape}). Impossível comparar.")
             return None

        # Realiza o Template Matching
        try:
            result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # Verifica se a confiança máxima atingiu o limiar
            if max_val >= current_threshold:
                # Calcula as coordenadas da caixa delimitadora e do centro
                template_h, template_w = template.shape[:2] # Pegar shape do template grayscale
                
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
                    'confidence': float(max_val), # Converte para float padrão
                    'position': (center_x, center_y),
                    'rectangle': [top_left_x, top_left_y, bottom_right_x, bottom_right_y] # [xmin, ymin, xmax, ymax]
                }
            else:
                # Encontrou algo, mas abaixo da confiança mínima
                # print(f"Debug: Template '{os.path.basename(template_path)}' encontrado com confiança {max_val:.4f} (abaixo do limiar {current_threshold}).") # Log opcional
                return None

        except Exception as e:
            print(f"❌ TemplateMatcher: Erro durante cv2.matchTemplate para '{template_path}': {e}")
            return None

# --- Bloco de Teste (Opcional, remova se não precisar) ---
if __name__ == "__main__":
    print("--- Testando TemplateMatcher ---")

    # Crie ou coloque uma imagem de teste e um template na mesma pasta
    # Exemplo: 'test_main_image.png' e 'test_template.png'
    
    main_image_path = "test_main_image.png" # Substitua pelo nome da sua imagem principal de teste
    template_path = "test_template.png"   # Substitua pelo nome do seu template de teste

    if not os.path.exists(main_image_path) or not os.path.exists(template_path):
        print(f"Erro: Crie os arquivos '{main_image_path}' e '{template_path}' para testar.")
    else:
        matcher = TemplateMatcher(default_threshold=0.7) # Usando threshold de 70% para teste
        
        # Carrega a imagem principal (exemplo como BGR)
        img_main_bgr = cv2.imread(main_image_path, cv2.IMREAD_COLOR) 
        
        if img_main_bgr is not None:
            print(f"\nBuscando '{os.path.basename(template_path)}' na imagem inteira...")
            result_full = matcher.find_template(img_main_bgr, template_path)
            if result_full:
                 print(f"✅ Encontrado na imagem inteira: Conf={result_full['confidence']:.2f}, Pos={result_full['position']}, Rect={result_full['rectangle']}")
            else:
                 print("❌ Não encontrado na imagem inteira (ou abaixo do limiar).")

            # Exemplo de busca com ROI (ajuste as coordenadas da ROI!)
            test_roi = (100, 50, 200, 150) # Exemplo: (x, y, largura, altura)
            print(f"\nBuscando '{os.path.basename(template_path)}' na ROI {test_roi}...")
            result_roi = matcher.find_template(img_main_bgr, template_path, roi=test_roi)
            if result_roi:
                 print(f"✅ Encontrado na ROI: Conf={result_roi['confidence']:.2f}, Pos={result_roi['position']}, Rect={result_roi['rectangle']}")
                 # Desenha a ROI e o resultado para visualização
                 x, y, w, h = test_roi
                 cv2.rectangle(img_main_bgr, (x,y), (x+w, y+h), (255, 0, 0), 2) # Desenha ROI em azul
                 r = result_roi['rectangle']
                 cv2.rectangle(img_main_bgr, (r[0], r[1]), (r[2], r[3]), (0, 255, 0), 2) # Desenha resultado em verde
                 cv2.imshow("Teste com ROI", img_main_bgr)
                 cv2.waitKey(0)
                 cv2.destroyAllWindows()
            else:
                 print("❌ Não encontrado na ROI (ou abaixo do limiar).")
        else:
            print(f"Erro ao carregar a imagem principal de teste: {main_image_path}")