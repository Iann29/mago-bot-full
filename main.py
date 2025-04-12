# /main.py

import time
import threading
import queue
import sys # Para sair em caso de falha crítica
import tkinter as tk
from tkinter import ttk, messagebox
import os
import winsound  # For playing sounds on Windows
from PIL import Image, ImageTk  # Para trabalhar com imagens e GIFs

# Importa o módulo de monitoramento ADB
from adb_monitor import setup_adb_monitor_in_app, cleanup_adb_monitor_on_exit

# Adiciona a raiz do projeto ao PYTHONPATH para garantir importações corretas
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importações do sistema de autenticação
from auth.login_ui import start_login_window

# Importações dos módulos do projeto
from ADBmanager import adb_manager # Importa o SINGLETON adb_manager
from screenVision.screenshotMain import Screenshotter, config as screenshot_config 
from screenVision.transmitter import transmitter # Importa o transmissor para VPS
from adbutils import AdbDevice
from execution.template import run_test, find_template # Importa as funções do módulo de template
from execution.testnew import execute_masked_test # Importa a função do módulo testnew.py
from stateManager import StateManager, GameState # Importa o gerenciador de estados

# --- Configurações Lidas do JSON ---
TARGET_FPS = screenshot_config.get("target_fps", 1) # Pega do CFG, default 1

# --- Variáveis Globais (definidas no nível do módulo) ---
# Usar um tamanho maior pode ajudar a não perder frames se o processamento for lento
screenshot_queue = queue.Queue(maxsize=5) 
stop_capture_thread = False  # Flag para parar a thread
capture_thread = None        # A thread de captura que será inicializada
state_manager = None         # Gerenciador de estados do jogo

# --- Função da Thread de Captura ---
def capture_worker(fps, adb_device: AdbDevice, username: str = None): 
    """Função que roda em uma thread separada para capturar screenshots."""
    global stop_capture_thread
    
    # Inicializa o Screenshotter PASSANDO o device conectado
    # A instância do Screenshotter é LOCAL para esta thread
    screenshotter = Screenshotter(adb_device=adb_device)
    
    # Configura o transmissor com o nome de usuário
    if username:
        transmitter.set_username(username)
        print(f"📡👤 Transmissor configurado para usuário: {username}")
    
    capture_interval = 1.0 / fps
    last_capture_time = time.time()
    consecutive_failures = 0 # Contador de falhas consecutivas
    max_failures = 5 # Número máximo de falhas antes de parar a thread
    
    print(f"📷▶️ CAPTURE_THREAD: Iniciada, capturando a ~{fps} FPS")

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
                
                # Tira screenshot (padrão OpenCV/BGR) e transmite para VPS
                screenshot = screenshotter.take_screenshot(use_pil=False, username=username, transmit=True)
                
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
                    print(f"📷⚠️ CAPTURE_THREAD: Falha na captura ({capture_duration:.3f}s) ({consecutive_failures}/{max_failures})")
                    if consecutive_failures >= max_failures:
                         print("📷❌ CAPTURE_THREAD: Máximo de falhas atingido. Encerrando thread")
                         stop_capture_thread = True
                         break # Sai do loop
                    time.sleep(0.5) # Pausa curta após falha na captura

        except Exception as e:
            consecutive_failures += 1
            print(f"📷⛔ CAPTURE_THREAD: Erro inesperado: {e} ({consecutive_failures}/{max_failures})")
            if consecutive_failures >= max_failures:
                 print("📷❌ CAPTURE_THREAD: Máximo de falhas atingido. Encerrando thread")
                 stop_capture_thread = True
                 break # Sai do loop
            time.sleep(0.5) # Pausa curta após falha na captura

        # Dormir para controlar o FPS e não usar 100% CPU
        sleep_time = max(0.01, capture_interval - (time.time() - last_capture_time)) # Garante um sleep mínimo
        time.sleep(sleep_time * 0.9) # Dorme 90% do tempo restante

    print("📷⏹️ CAPTURE_THREAD: Encerrando...")

# --- Classe da Interface Gráfica ---
class HayDayTestApp:
    def __init__(self, root, user_data=None):
        self.root = root
        self.root.title("HayDay Test Tool")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Variáveis de controle
        self.adb_manager_instance = None
        self.connected_device = None
        self.emulator_connection_lost = False
        
        # Dados do usuário autenticado
        self.user_data = user_data
        self.html_id = user_data.get("html_id") if user_data else None
        
        # Configurar a interface
        self.setup_ui()
        
        # Inicializar ADB ao abrir
        self.initialize_adb()
        
        # Registrar callbacks no ADBManager para detecção proativa
        adb_manager.register_connection_callback(self.on_emulator_connected)
        adb_manager.register_disconnect_callback(self.on_emulator_disconnected)
        
        # Iniciar monitoramento de conexão
        adb_manager.start_connection_monitoring()
    
    def setup_ui(self):
        """Configura todos os elementos da interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título com informação do usuário
        title_text = "HayDay Test Tool"
        if self.html_id:
            # Extrai nome do usuário do html_id (exemplo: "screen-ian" -> "Ian")
            user_name = self.html_id.replace("screen-", "").capitalize()
            title_text += f" - {user_name}"
            
        title_label = ttk.Label(main_frame, text=title_text, font=("Helvetica", 16, "bold"))
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
        
        # Frame de estado do jogo
        state_frame = ttk.LabelFrame(main_frame, text="Estado do Jogo", padding=10)
        state_frame.pack(fill=tk.X, pady=10)
        
        self.state_label = ttk.Label(state_frame, text="Estado atual: Desconhecido")
        self.state_label.pack(side=tk.LEFT, padx=5)
        
        self.state_time_label = ttk.Label(state_frame, text="Tempo no estado: 0s")
        self.state_time_label.pack(side=tk.RIGHT, padx=5)
        
        # Frame de status de transmissão
        transmission_frame = ttk.LabelFrame(main_frame, text="Status da Transmissão", padding=10)
        transmission_frame.pack(fill=tk.X, pady=10)
        
        self.transmission_status_label = ttk.Label(transmission_frame, text="Transmissão: Inativa", foreground="gray")
        self.transmission_status_label.pack(side=tk.LEFT, padx=5)
        
        self.transmission_indicator = ttk.Label(transmission_frame, text="⚪", font=("Helvetica", 12))
        self.transmission_indicator.pack(side=tk.RIGHT, padx=5)
        
        # Variáveis para controle da transmissão
        self.last_transmission_time = 0
        self.transmission_active = False
        
        # Frame de ações
        actions_frame = ttk.LabelFrame(main_frame, text="Ações", padding=10)
        actions_frame.pack(fill=tk.X, pady=10)
        
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
        self.log("📱🔌 Inicializando conexão ADB...")
        
        # Desabilita os botões enquanto conecta
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
                    
                    # Toca um som de alerta antes de mostrar o popup
                    try:
                        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                    except Exception as sound_error:
                        self.log(f"Erro ao reproduzir som: {sound_error}")
                    
                    # Exibe mensagem amigável informando que o emulador está fechado
                    messagebox.showerror("Emulador Fechado", "Teu emulador ta fechado pai!")
                    return False
            
            # Obtém o dispositivo conectado
            self.connected_device = adb_manager.get_device()
            if not self.connected_device:
                self.log("❌ ADBManager conectou, mas não retornou um objeto de dispositivo.")
                self.status_label.config(text="Falha na conexão")
                self.device_label.config(text="Dispositivo: Nenhum")
                
                # Toca um som de alerta antes de mostrar o popup
                try:
                    winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                except Exception as sound_error:
                    self.log(f"Erro ao reproduzir som: {sound_error}")
                
                messagebox.showerror("Erro de Conexão", "Não foi possível obter o objeto do dispositivo.")
                return False
            
            # Atualiza a interface
            device_serial = adb_manager.get_target_serial()
            # Removendo log duplicado - ADBManager já mostra essa mensagem
            self.status_label.config(text="Conectado")
            self.device_label.config(text=f"Dispositivo: {device_serial}")
            
            # Habilita os botões de teste
            self.test_button.config(state="normal")
            self.masked_test_button.config(state="normal")
            
            # Atualiza o status da thread de captura
            if capture_thread and capture_thread.is_alive():
                self.capture_status_label.config(text="Thread de captura: Ativa")
                self.capture_fps_label.config(text=f"FPS: {TARGET_FPS}")
                
            # Reset flag de perda de conexão
            self.emulator_connection_lost = False
            
            return True
            
        except Exception as e:
            self.log(f"❌ Erro ao conectar: {e}")
            self.status_label.config(text="Erro")
            self.device_label.config(text="Dispositivo: Nenhum")
            
            # Toca um som de alerta antes de mostrar o popup
            try:
                winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
            except Exception as sound_error:
                self.log(f"Erro ao reproduzir som: {sound_error}")
            
            # Mostra mensagem amigável caso seja um erro de conexão ADB
            if "adb" in str(e).lower() or "connection" in str(e).lower() or "device" in str(e).lower():
                messagebox.showerror("GÊnio", "Teu emulador ta fechado pai!")
            else:
                messagebox.showerror("Erro", f"Erro ao conectar: {e}")
                
            try:
                self.connect_button.config(state="normal")
            except:
                pass  # O botão pode não existir
                
            return False
            
    def on_emulator_connected(self, device_serial):
        """Callback chamado quando o emulador é conectado/reconectado."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return  # Janela foi fechada
            
        # Executa operações na thread do Tkinter
        self.root.after(0, lambda: self._handle_emulator_connected(device_serial))
    
    def _handle_emulator_connected(self, device_serial):
        """Manipula o evento de conexão do emulador na thread da interface gráfica."""
        if self.emulator_connection_lost:
            self.log(f"📱✅ Emulador reconectado! Serial: {device_serial}")
            self.status_label.config(text="Reconectado")
            self.device_label.config(text=f"Dispositivo: {device_serial}")
            
            # Habilita os botões
            self.test_button.config(state="normal")
            self.masked_test_button.config(state="normal")
            
            # Tenta reiniciar a thread de captura se não estiver rodando
            global capture_thread, stop_capture_thread
            if (not capture_thread or not capture_thread.is_alive()) and not stop_capture_thread:
                self.log("📱📷 Tentando reiniciar a thread de captura...")
                try:
                    # Obtém o dispositivo conectado novamente
                    self.connected_device = adb_manager.get_device()
                    if self.connected_device:
                        username = self.html_id if self.html_id else None
                        start_screenshot_capture(TARGET_FPS, self.connected_device, username=username)
                        self.capture_status_label.config(text="Thread de captura: Ativa")
                        self.capture_fps_label.config(text=f"FPS: {TARGET_FPS}")
                        self.log("📷✅ Thread de captura reiniciada!")
                except Exception as e:
                    self.log(f"❌ Erro ao reiniciar thread de captura: {e}")
            
            # Reset flag
            self.emulator_connection_lost = False
    
    def on_emulator_disconnected(self):
        """Callback chamado quando o emulador é desconectado."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return  # Janela foi fechada
            
        # Executa operações na thread do Tkinter
        self.root.after(0, self._handle_emulator_disconnected)
    
    def _handle_emulator_disconnected(self):
        """Manipula o evento de desconexão do emulador na thread da interface gráfica."""
        self.log("📱❌ Emulador desconectado!")
        self.status_label.config(text="Desconectado", foreground="red")
        self.device_label.config(text="Dispositivo: Nenhum")
        
        # Desabilita os botões
        self.test_button.config(state="disabled")
        self.masked_test_button.config(state="disabled")
        
        # Toca som de alerta
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
        except Exception as sound_error:
            self.log(f"Erro ao reproduzir som: {sound_error}")
        
        # Mostra popup informando que o emulador foi fechado
        try:
            # Verifica se o popup já está sendo exibido
            if not self.emulator_connection_lost:
                self.root.after(100, lambda: messagebox.showwarning("Emulador Fechado", 
                                                            "Emulador foi fechado ou desconectado!\n" +
                                                            "Reabra o emulador para continuar."))
        except Exception as e:
            self.log(f"Erro ao mostrar popup: {e}")
            
        # Define flag de perda de conexão
        self.emulator_connection_lost = True
    
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
        global capture_thread, screenshot_queue, TARGET_FPS, state_manager
        
        try:
            # Atualiza status da thread de captura
            if capture_thread and capture_thread.is_alive():
                self.capture_status_label.config(text="Thread de captura: Ativa")
                self.capture_fps_label.config(text=f"FPS: {TARGET_FPS} (Fila: {screenshot_queue.qsize()})")
            else:
                self.capture_status_label.config(text="Thread de captura: Inativa")
                self.capture_fps_label.config(text="FPS: --")
            
            # Atualiza informações do estado atual do jogo
            if state_manager is not None:
                current_state = state_manager.get_current_state()
                state_duration = state_manager.get_state_duration()
                
                # Atualiza as labels com informações do estado
                self.state_label.config(text=f"Estado atual: {current_state}")
                self.state_time_label.config(text=f"Tempo no estado: {state_duration:.1f}s")
        except Exception as e:
            print(f"Erro ao atualizar status: {e}")
            
        # Programa a próxima atualização
        self.root.after(1000, self.update_capture_status)
        
    def on_state_change(self, previous_state, new_state):
        """Callback chamado quando o estado do jogo muda"""
        self.log(f"⚡ Estado alterado: {previous_state} -> {new_state}")
        
    def update_transmission_status(self):
        """Atualiza o status da transmissão na GUI - chamado pelo transmitter"""
        if not hasattr(self, 'transmission_indicator'):
            return
            
        current_time = time.time()
        self.last_transmission_time = current_time
        
        if not self.transmission_active:
            self.transmission_active = True
            self.transmission_status_label.config(text="Transmissão: Ativa", foreground="green")
            self.transmission_indicator.config(text="🟢")  # Círculo verde
            
            # Programa a verificação de timeout após 2 segundos
            self.root.after(2000, self.check_transmission_timeout)
    
    def check_transmission_timeout(self):
        """Verifica se a transmissão está inativa há mais de 2 segundos"""
        current_time = time.time()
        if current_time - self.last_transmission_time > 2 and self.transmission_active:
            self.transmission_active = False
            self.transmission_status_label.config(text="Transmissão: Inativa", foreground="gray")
            self.transmission_indicator.config(text="⚪")  # Círculo cinza
        
        # Continua verificando enquanto o aplicativo estiver em execução
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(2000, self.check_transmission_timeout)

# Função para inicializar o gerenciador de estados
def initialize_state_manager():
    """Inicializa o gerenciador de estados e inicia o monitoramento"""
    global state_manager, screenshot_queue
    
    try:
        # Cria uma instância do StateManager com configurações ajustadas
        state_manager = StateManager(threshold=0.75, check_interval=0.2, verbose=False)
        
        # Inicia o monitoramento de estados usando a fila de screenshots existente
        if screenshot_queue is not None:
            state_manager.start_monitoring(screenshot_queue)
            print("🔔✅ StateManager inicializado e monitoramento iniciado.")
            return True
        else:
            print("❌ Erro: Fila de screenshots não inicializada. StateManager não pode ser inicializado.")
            return False
    except Exception as e:
        print(f"❌ Erro ao inicializar StateManager: {e}")
        return False
        
# Função para iniciar a captura de screenshots com username
def start_screenshot_capture(fps, device, username=None):
    """Inicia a captura de screenshots em thread separada."""
    global capture_thread, stop_capture_thread
    
    # Para a thread anterior se existir
    if capture_thread and capture_thread.is_alive():
        stop_capture_thread = True
        capture_thread.join(timeout=2.0)
        stop_capture_thread = False
    
    # Inicia nova thread
    capture_thread = threading.Thread(
        target=capture_worker,
        args=(fps, device, username),
        daemon=True
    )
    capture_thread.start()
    return capture_thread

# --- Função Principal ---
def show_emulator_closed_message():
    """Mostra uma mensagem amigável com GIF animado quando o emulador está fechado e toca um som."""
    # Toca o som de alerta antes de mostrar a mensagem
    try:
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
    except Exception as sound_error:
        print(f"Erro ao reproduzir som: {sound_error}")
    
    # Cria uma janela customizada para mostrar o GIF e a mensagem
    root = tk.Tk()
    root.title("GÊNIO")
    root.geometry("400x320")
    root.resizable(False, False)
    
    # Centraliza a janela na tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 400) // 2
    y = (screen_height - 320) // 2
    root.geometry(f"400x320+{x}+{y}")
    
    # Configura o estilo
    root.configure(bg="#f0f0f0")
    style = ttk.Style()
    style.configure("TButton", font=("Helvetica", 12))
    style.configure("TLabel", font=("Helvetica", 14), background="#f0f0f0")
    
    # Frame principal
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Carrega o GIF (verificamos se o arquivo existe)
    gif_path = os.path.join(project_root, "china.gif")
    if os.path.exists(gif_path):
        # Cria um objeto para armazenar os frames do GIF
        frames = []
        try:
            # Tenta carregar o GIF
            gif = Image.open(gif_path)
            # Extrai todos os frames
            try:
                while True:
                    frames.append(ImageTk.PhotoImage(gif.copy()))
                    gif.seek(len(frames)) # Vai para o próximo frame
            except EOFError:
                pass # Fim dos frames
                
            # Cria um label para exibir o GIF
            gif_label = ttk.Label(main_frame)
            gif_label.pack(pady=10)
            
            # Função para animar o GIF
            def update_frame(idx):
                frame = frames[idx]
                gif_label.configure(image=frame)
                root.after(100, update_frame, (idx + 1) % len(frames))
            
            # Inicia a animação
            if frames:
                root.after(0, update_frame, 0)
                
        except Exception as e:
            print(f"Erro ao carregar o GIF: {e}")
            # Usa um texto simples se o GIF não puder ser carregado
            ttk.Label(main_frame, text="[😱 GIF Indisponível]")\
                .pack(pady=20)
    else:
        # Se o arquivo não existir, mostra um texto alternativo
        ttk.Label(main_frame, text="[😱 GIF Indisponível]")\
            .pack(pady=20)
    
    # Adiciona a mensagem
    ttk.Label(main_frame, text="Teu emulador ta fechado pai!", 
               font=("Helvetica", 14, "bold"))\
        .pack(pady=10)
    ttk.Label(main_frame, text="Abra o emulador antes de iniciar o bot.")\
        .pack(pady=5)
    
    # Botão de fechar
    ttk.Button(main_frame, text="Entendi, vou abrir!", command=root.destroy)\
        .pack(pady=15)
    
    # Configura a janela para se fechar ao pressionar Esc ou Enter
    root.bind("<Escape>", lambda event: root.destroy())
    root.bind("<Return>", lambda event: root.destroy())
    
    # Coloca a janela em primeiro plano
    root.attributes("-topmost", True)
    root.update()
    root.attributes("-topmost", False)
    
    # Inicia o loop principal
    root.mainloop()

def main():
    global capture_thread, stop_capture_thread
    
    print("🌟--- Iniciando HayDay Test Tool ---🌟")
    
    # Autentica usuário pelo Supabase
    print("🔐 Iniciando autenticação...")
    user_data = start_login_window()
    
    # Verificar se o usuário foi autenticado
    if not user_data:
        print("❌ Autenticação falhou ou foi cancelada. Encerrando aplicação.")
        return
    
    print(f"✅ Usuário {user_data.get('username')} autenticado com sucesso!")
    
    # Lê o FPS do config carregado pelo screenshotMain
    target_fps = screenshot_config.get("target_fps", 1)
    print(f"⚙️ Configurações: FPS={target_fps} (do screenshotCFG.json)")
    
    try:
        # 1. Inicializa e conecta o ADBManager
        if not adb_manager.connect_first_device():
            print("🚨 Falha crítica ao conectar ao dispositivo. Encerrando.")
            # Mostra o popup com mensagem amigável antes de encerrar
            show_emulator_closed_message()
            return  # Usamos return em vez de sys.exit para um encerramento mais limpo

        # 2. Obtém o dispositivo conectado
        connected_device = adb_manager.get_device()
        if not connected_device:
            print("🚨 Falha crítica: Conexão OK, mas sem objeto de dispositivo. Encerrando.")
            # Mostra o popup com mensagem amigável antes de encerrar
            show_emulator_closed_message()
            return  # Usamos return em vez de sys.exit para um encerramento mais limpo

        # ADBManager já registra a conexão bem-sucedida, não precisamos duplicar

        # 3. Cria e inicia a thread de captura, passando o dispositivo e identificação do usuário
        username = user_data.get('username')
        html_id = user_data.get('html_id')  # Pega o html_id retornado pelo Supabase
        
        # Se não tiver html_id, usa o username como fallback
        screen_id = html_id if html_id else f"screen-{username}"
        print(f"💻📁 Identificador de tela para transmissão: {screen_id}")
        
        # Inicia a thread de captura com o identificador correto
        capture_thread = threading.Thread(target=capture_worker, args=(target_fps, connected_device, screen_id), daemon=True)
        capture_thread.start()
        print(f"📷✨ Thread de captura iniciada (FPS={target_fps})")
    
        # 4. Cria a janela principal da interface gráfica
        root = tk.Tk()
        app = HayDayTestApp(root, user_data)

        # Configura o monitoramento proativo do ADB
        setup_adb_monitor_in_app(app)        
        # Configura o monitoramento proativo do ADB
        setup_adb_monitor_in_app(app)
        
        # 5. Inicializa o gerenciador de estados
        if initialize_state_manager():
            # Registra o callback de mudança de estado
            state_manager.register_state_change_callback(app.on_state_change)
            print("🔔✅ Registro de callback de estado concluído.")
        
        # 6. Configura o callback de transmissão na GUI para indicar transmissões
        from screenVision.transmitter import transmitter
        transmitter.set_transmission_callback(app.update_transmission_status)
        
        # 7. Configura a atualização do status da captura e do estado a cada segundo
        app.update_capture_status()
        
        # Configura o fechamento da janela para usar nossa função on_closing
        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
        
        # Inicia o loop principal da interface gráfica
        root.mainloop()
        
    except KeyboardInterrupt:
        print("\nMAIN: Interrupção solicitada (Ctrl+C).")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        # Garante que a thread seja sinalizada para parar e espera por ela
        print("💻⛔ MAIN: Sinalizando para thread de captura parar...")
        stop_capture_thread = True
        
        # Para o monitoramento de estados
        if state_manager is not None:
            print("💻⏹️ MAIN: Parando monitoramento de estados...")
            state_manager.stop_monitoring()
        
        if capture_thread and capture_thread.is_alive():
            print("💻⏸️ MAIN: Aguardando a thread de captura encerrar...")
            capture_thread.join(timeout=3)  # Aumenta um pouco o timeout
            if capture_thread.is_alive():
                print("💻⚠️ MAIN: Thread de captura não terminou a tempo.")
                
        print("💻✨ MAIN: Programa encerrado.")

# Função chamada quando a janela principal é fechada
def on_closing(root):
    """Trata o fechamento da janela principal"""
    global stop_capture_thread, state_manager
    
    print("💻🔒 MAIN: Aplicativo está sendo fechado...")

    # Para o monitoramento de conexão ADB
    cleanup_adb_monitor_on_exit()
    
    # Para a thread de captura
    stop_capture_thread = True
    
    # Para o monitoramento de estados
    if state_manager is not None:
        print("💻⏹️ MAIN: Parando monitoramento de estados...")
        state_manager.stop_monitoring()
    
    # Destrói a janela e encerra o programa
    root.destroy()
    print("💻🚫 MAIN: Interface encerrada.")

# --- Ponto de entrada ---
if __name__ == "__main__":
    main()