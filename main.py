# /main.py

import time
import threading
import queue
import sys # Para sair em caso de falha crítica
import tkinter as tk
from tkinter import ttk, messagebox
import os

# Adiciona a raiz do projeto ao PYTHONPATH para garantir importações corretas
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importações dos módulos do projeto
from ADBmanager import adb_manager # Importa o SINGLETON adb_manager
from screenVision.screenshotMain import Screenshotter, config as screenshot_config 
from adbutils import AdbDevice
from execution.template import run_test, find_template # Importa as funções do módulo de template
from execution.testnew import execute_masked_test # Importa a função do módulo testnew.py

# --- Configurações Lidas do JSON ---
TARGET_FPS = screenshot_config.get("target_fps", 1) # Pega do CFG, default 1

# --- Variáveis Globais (definidas no nível do módulo) ---
# Usar um tamanho maior pode ajudar a não perder frames se o processamento for lento
screenshot_queue = queue.Queue(maxsize=5) 
stop_capture_thread = False  # Flag para parar a thread
capture_thread = None        # A thread de captura que será inicializada

# --- Função da Thread de Captura ---
def capture_worker(fps, adb_device: AdbDevice): 
    """Função que roda em uma thread separada para capturar screenshots."""
    global stop_capture_thread
    
    # Inicializa o Screenshotter PASSANDO o device conectado
    # A instância do Screenshotter é LOCAL para esta thread
    screenshotter = Screenshotter(adb_device=adb_device) 
    
    capture_interval = 1.0 / fps
    last_capture_time = time.time()
    consecutive_failures = 0 # Contador de falhas consecutivas
    max_failures = 5 # Número máximo de falhas antes de parar a thread
    
    print(f"CAPTURE_THREAD: Iniciada, tentando capturar a ~{fps} FPS.")

    while not stop_capture_thread:
        # A conexão é estabelecida no início.
        # Se cair, o screenshotter.capture() deve lançar uma exceção,
        # que será tratada abaixo.
        # Removida a verificação adb_device.is_connected() e a tentativa de reconexão.

        # Tenta capturar e colocar na fila
        try:
            current_time = time.time()
            # Lógica para tentar manter o FPS alvo
            if current_time - last_capture_time >= capture_interval:
                time_before_capture = time.time() 
                
                # Tira screenshot (padrão OpenCV/BGR)
                screenshot = screenshotter.take_screenshot(use_pil=False) 
                
                time_after_capture = time.time() 
                capture_duration = time_after_capture - time_before_capture
                
                # Atualiza o tempo da última tentativa de captura
                last_capture_time = time_before_capture 

                if screenshot is not None:
                    consecutive_failures = 0 # Reseta contador de falhas
                    # Coloca na fila se tiver espaço, senão descarta a antiga
                    if screenshot_queue.full():
                        try: screenshot_queue.get_nowait() 
                        except queue.Empty: pass 
                    screenshot_queue.put(screenshot)
                    # print(f"CAPTURE_THREAD: Screenshot OK ({capture_duration:.3f}s). Fila: {screenshot_queue.qsize()}") # Debug
                else:
                    consecutive_failures += 1
                    print(f"CAPTURE_THREAD: Falha ao capturar screenshot ({capture_duration:.3f}s) ({consecutive_failures}/{max_failures}).")
                    if consecutive_failures >= max_failures:
                         print("CAPTURE_THREAD: Máximo de falhas de captura atingido. Encerrando thread.")
                         stop_capture_thread = True
                         break # Sai do loop
                    time.sleep(0.5) # Pausa curta após falha na captura

        except Exception as e:
            consecutive_failures += 1
            print(f"CAPTURE_THREAD: Erro inesperado ao capturar screenshot: {e} ({consecutive_failures}/{max_failures}).")
            if consecutive_failures >= max_failures:
                 print("CAPTURE_THREAD: Máximo de falhas de captura atingido. Encerrando thread.")
                 stop_capture_thread = True
                 break # Sai do loop
            time.sleep(0.5) # Pausa curta após falha na captura

        # Dormir para controlar o FPS e não usar 100% CPU
        sleep_time = max(0.01, capture_interval - (time.time() - last_capture_time)) # Garante um sleep mínimo
        time.sleep(sleep_time * 0.9) # Dorme 90% do tempo restante

    print("CAPTURE_THREAD: Encerrando...")

# --- Classe da Interface Gráfica ---
class HayDayTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HayDay Test Tool")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Variáveis de controle
        self.adb_manager_instance = None
        self.connected_device = None
        
        # Configurar a interface
        self.setup_ui()
        
        # Inicializar ADB ao abrir
        self.initialize_adb()
    
    def setup_ui(self):
        """Configura todos os elementos da interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="HayDay Test Tool", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        
        # Frame de status
        status_frame = ttk.LabelFrame(main_frame, text="Status da Conexão", padding=10)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(status_frame, text="Não conectado")
        self.status_label.pack(pady=5)
        
        self.device_label = ttk.Label(status_frame, text="Dispositivo: Nenhum")
        self.device_label.pack(pady=5)
        
        # Frame de captura
        capture_frame = ttk.LabelFrame(main_frame, text="Status da Captura", padding=10)
        capture_frame.pack(fill=tk.X, pady=10)
        
        self.capture_status_label = ttk.Label(capture_frame, text="Thread de captura: Inativa")
        self.capture_status_label.pack(side=tk.LEFT, padx=5)
        
        self.capture_fps_label = ttk.Label(capture_frame, text="FPS: --")
        self.capture_fps_label.pack(side=tk.RIGHT, padx=5)
        
        # Frame de ações
        actions_frame = ttk.LabelFrame(main_frame, text="Ações", padding=10)
        actions_frame.pack(fill=tk.X, pady=10)
        
        # Botão de conectar
        self.connect_button = ttk.Button(actions_frame, text="Conectar ADB", command=self.initialize_adb)
        self.connect_button.pack(fill=tk.X, pady=5)
        
        # Botão de executar teste de template
        self.test_button = ttk.Button(actions_frame, text="Executar Teste de Template", command=self.run_template_test)
        self.test_button.pack(fill=tk.X, pady=5)
        
        # Botão de executar teste com máscara
        self.masked_test_button = ttk.Button(actions_frame, text="Executar Teste com Máscara", command=self.run_masked_test)
        self.masked_test_button.pack(fill=tk.X, pady=5)
        
        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def log(self, message):
        """Adiciona uma mensagem à área de log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        
        # Evitar duplicação de mensagens específicas no console
        if "TESTE CONCLUÍDO" not in message:
            print(message)  # Também envia para o console
    
    def initialize_adb(self):
        """Inicializa e conecta ao ADB"""
        self.log("Inicializando conexão ADB...")
        
        # Desabilita os botões enquanto conecta
        self.connect_button.config(state="disabled")
        self.test_button.config(state="disabled")
        self.masked_test_button.config(state="disabled")
        
        try:
            # Reutiliza o singleton adb_manager em vez de criar uma nova instância
            global adb_manager
            
            if not adb_manager.is_connected():
                self.log("ADB não conectado. Tentando conectar...")
                if not adb_manager.connect_first_device():
                    self.log("❌ Falha ao conectar ao dispositivo ADB via Manager.")
                    self.status_label.config(text="Falha na conexão")
                    self.device_label.config(text="Dispositivo: Nenhum")
                    messagebox.showerror("Erro de Conexão", "Não foi possível conectar a nenhum dispositivo Android.")
                    self.connect_button.config(state="normal")
                    return False
            
            # Obtém o dispositivo conectado
            self.connected_device = adb_manager.get_device()
            if not self.connected_device:
                self.log("❌ ADBManager conectou, mas não retornou um objeto de dispositivo.")
                self.status_label.config(text="Falha na conexão")
                self.device_label.config(text="Dispositivo: Nenhum")
                messagebox.showerror("Erro de Conexão", "Não foi possível obter o objeto do dispositivo.")
                self.connect_button.config(state="normal")
                return False
            
            # Atualiza a interface
            device_serial = adb_manager.get_target_serial()
            self.log(f"✅ ADB conectado com sucesso ao dispositivo: {device_serial}")
            self.status_label.config(text="Conectado")
            self.device_label.config(text=f"Dispositivo: {device_serial}")
            
            # Habilita os botões de teste
            self.test_button.config(state="normal")
            self.masked_test_button.config(state="normal")
            self.connect_button.config(state="normal")
            
            # Atualiza o status da thread de captura
            if capture_thread and capture_thread.is_alive():
                self.capture_status_label.config(text="Thread de captura: Ativa")
                self.capture_fps_label.config(text=f"FPS: {TARGET_FPS}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Erro ao conectar: {e}")
            self.status_label.config(text="Erro")
            self.device_label.config(text="Dispositivo: Nenhum")
            messagebox.showerror("Erro", f"Erro ao conectar: {e}")
            self.connect_button.config(state="normal")
            return False
    
    def run_template_test(self):
        """Executa o teste de template do módulo template.py"""
        self.log("Iniciando teste de template...")
        
        # Desabilita o botão durante o teste
        self.test_button.config(state="disabled")
        
        # Executa o teste em uma thread separada para não travar a UI
        threading.Thread(target=self._run_test_thread, daemon=True).start()
    
    def _run_test_thread(self):
        """Função que roda o teste em thread separada"""
        try:
            # Usa o conteúdo existente da área de log
            
            # Executa a função run_test do módulo template.py em modo silencioso
            # (para evitar duplicação de mensagens no console)
            result = run_test(silent=True)
            
            # Atualiza a interface com o resultado
            if result:
                self.log("✅ TESTE CONCLUÍDO: Template encontrado com sucesso!")
            else:
                self.log("❌ TESTE CONCLUÍDO: Template não encontrado.")
        
        except Exception as e:
            self.log(f"❌ Erro durante o teste: {e}")
        
        finally:
            # Habilita o botão novamente
            self.root.after(0, lambda: self.test_button.config(state="normal"))

    def run_masked_test(self):
        """Executa o teste com máscara do módulo testnew.py"""
        # Verifica se está conectado
        if not self.connected_device:
            messagebox.showerror("Erro", "Não há dispositivo conectado! Conecte um dispositivo Android primeiro.")
            return
            
        self.log("Iniciando teste com máscara...")
        
        # Desabilita o botão durante o teste
        self.masked_test_button.config(state="disabled")
        
        # Executa o teste em uma thread separada para não travar a UI
        threading.Thread(target=self._run_masked_test_thread, daemon=True).start()
    
    def _run_masked_test_thread(self):
        """Função que roda o teste com máscara em thread separada"""
        try:
            # Executa a função execute_masked_test do módulo testnew.py
            result = execute_masked_test()
            
            # Atualiza a interface com o resultado
            if result:
                self.log("✅ TESTE COM MÁSCARA CONCLUÍDO: Template encontrado com sucesso!")
            else:
                self.log("❌ TESTE COM MÁSCARA CONCLUÍDO: Template não encontrado.")
        
        except Exception as e:
            self.log(f"❌ Erro durante o teste com máscara: {e}")
        
        finally:
            # Habilita o botão novamente
            self.root.after(0, lambda: self.masked_test_button.config(state="normal"))
            
    def update_capture_status(self):
        """Atualiza o status da captura na interface a cada segundo"""
        global capture_thread, screenshot_queue, TARGET_FPS
        
        try:
            if capture_thread and capture_thread.is_alive():
                self.capture_status_label.config(text="Thread de captura: Ativa")
                self.capture_fps_label.config(text=f"FPS: {TARGET_FPS} (Fila: {screenshot_queue.qsize()})")
            else:
                self.capture_status_label.config(text="Thread de captura: Inativa")
                self.capture_fps_label.config(text="FPS: --")
        except Exception as e:
            print(f"Erro ao atualizar status da captura: {e}")
            
        # Programa a próxima atualização
        self.root.after(1000, self.update_capture_status)

# --- Função Principal ---
def main():
    global capture_thread, stop_capture_thread
    
    print("--- Iniciando HayDay Test Tool ---")
    
    # Lê o FPS do config carregado pelo screenshotMain
    target_fps = screenshot_config.get("target_fps", 1)
    print(f"Configurações de Captura: FPS={target_fps} (do screenshotCFG.json)")
    
    try:
        # 1. Inicializa e conecta o ADBManager
        if not adb_manager.connect_first_device():
            print("Falha crítica ao conectar ao dispositivo ADB via Manager. Encerrando.")
            sys.exit(1)  # Encerra o script se não conectar

        # 2. Obtém o dispositivo conectado
        connected_device = adb_manager.get_device()
        if not connected_device:
            print("Falha crítica: ADBManager conectou, mas não retornou um objeto de dispositivo. Encerrando.")
            sys.exit(1)

        print(f"ADB conectado com sucesso ao dispositivo: {adb_manager.get_target_serial()}")

        # 3. Cria e inicia a thread de captura, passando o dispositivo
        capture_thread = threading.Thread(target=capture_worker, args=(target_fps, connected_device), daemon=True)
        capture_thread.start()
        print(f"Thread de captura iniciada (FPS={target_fps})")
    
        # 4. Cria a janela principal da interface gráfica
        root = tk.Tk()
        app = HayDayTestApp(root)
        
        # 5. Configura a atualização do status da captura a cada segundo
        app.update_capture_status()
        
        # Inicia o loop principal da interface gráfica
        root.mainloop()
        
    except KeyboardInterrupt:
        print("\nMAIN: Interrupção solicitada (Ctrl+C).")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        # Garante que a thread seja sinalizada para parar e espera por ela
        print("MAIN: Sinalizando para thread de captura parar...")
        stop_capture_thread = True
        
        if capture_thread and capture_thread.is_alive():
            print("MAIN: Aguardando a thread de captura encerrar...")
            capture_thread.join(timeout=3)  # Aumenta um pouco o timeout
            if capture_thread.is_alive():
                print("MAIN: Thread de captura não terminou a tempo.")
                
        print("MAIN: Programa encerrado.")

# --- Ponto de entrada ---
if __name__ == "__main__":
    main()