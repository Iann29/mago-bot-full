# /cerebro/ui.py
# Módulo para a interface gráfica do aplicativo

import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
import threading
import winsound
from PIL import Image, ImageTk
from typing import Optional, Dict, Any, Callable

from ADBmanager import adb_manager
from screenVision.transmitter import transmitter
from stateManager import GameState
from execution.template import run_test, find_template
from execution.testnew import execute_masked_test
from cerebro.capture import screenshot_queue

class HayDayTestApp:
    """Classe principal da interface gráfica do aplicativo."""
    
    def __init__(self, root, user_data=None):
        """
        Inicializa a interface gráfica.
        
        Args:
            root: Elemento raiz do Tkinter
            user_data: Dados do usuário autenticado
        """
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
        
        # Frame de ações/testes
        actions_frame = ttk.LabelFrame(main_frame, text="Ações e Testes", padding=10)
        actions_frame.pack(fill=tk.X, pady=10)
        
        # Botões de teste
        test_button = ttk.Button(actions_frame, text="Executar Teste de Template", command=self.run_template_test)
        test_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        masked_test_button = ttk.Button(actions_frame, text="Teste com Máscara", command=self.run_masked_test)
        masked_test_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log de Eventos", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, width=60, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Inicia o timer para atualizar a UI
        self.update_capture_status()
        self.check_transmission_timeout()
        
        # Configura o callback no transmissor
        transmitter.set_transmission_callback(self.update_transmission_status)
    
    def log(self, message):
        """Adiciona uma mensagem à área de log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)  # Rola para o final
    
    def initialize_adb(self):
        """Inicializa e conecta ao ADB"""
        # Usa a instância singleton existente
        self.adb_manager_instance = adb_manager
        
        # Tenta conectar
        if self.adb_manager_instance.connect_first_device():
            # Obtém o dispositivo e o serial
            self.connected_device = self.adb_manager_instance.get_device()
            device_serial = self.adb_manager_instance.get_target_serial()
            
            self.status_label.config(text="Conectado ✓", foreground="green")
            self.device_label.config(text=f"Dispositivo: {device_serial}")
            
            print(f"📱🔌 Inicializando conexão ADB...")
            return True
        else:
            self.status_label.config(text="Não conectado ✗", foreground="red")
            self.device_label.config(text="Dispositivo: Nenhum")
            return False
    
    def on_emulator_connected(self, device_serial):
        """Callback chamado quando o emulador é conectado/reconectado."""
        # Agenda para execução na thread da interface
        self.root.after(0, lambda: self._handle_emulator_connected(device_serial))
    
    def _handle_emulator_connected(self, device_serial):
        """Manipula o evento de conexão do emulador na thread da interface gráfica."""
        # Atualiza a interface para refletir a conexão
        self.emulator_connection_lost = False
        self.status_label.config(text="Conectado ✓", foreground="green")
        self.device_label.config(text=f"Dispositivo: {device_serial}")
        
        # Obtém a referência ao dispositivo
        self.connected_device = self.adb_manager_instance.get_device()
    
    def on_emulator_disconnected(self):
        """Callback chamado quando o emulador é desconectado."""
        # Agenda para execução na thread da interface
        self.root.after(0, self._handle_emulator_disconnected)
    
    def _handle_emulator_disconnected(self):
        """Manipula o evento de desconexão do emulador na thread da interface gráfica."""
        # Toca um som e atualiza a UI
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
        except Exception:
            pass  # Ignora erros de som
            
        self.emulator_connection_lost = True
        self.connected_device = None
        self.status_label.config(text="Desconectado ✗", foreground="red")
        self.device_label.config(text="Dispositivo: Nenhum")
        
        # Mostra popup uma única vez se a conexão foi perdida
        message = "A conexão com o emulador foi perdida. Verifique se o emulador está em execução."
        messagebox.showwarning("Conexão Perdida", message)
    
    def run_template_test(self):
        """Executa o teste de template do módulo template.py"""
        if not self.connected_device:
            messagebox.showerror("Erro", "Nenhum dispositivo conectado!")
            return
            
        # Cria thread para não travar a UI
        test_thread = threading.Thread(target=self._run_test_thread)
        test_thread.daemon = True
        test_thread.start()
    
    def _run_test_thread(self):
        """Função que roda o teste em thread separada"""
        try:
            self.log("Iniciando teste de template...")
            result = run_test()
            if result:
                self.log("✅ TESTE CONCLUÍDO: Template encontrado com sucesso!")
                messagebox.showinfo("Resultado do Teste", "Template encontrado com sucesso!")
            else:
                self.log("❌ TESTE CONCLUÍDO: Template NÃO encontrado!")
                messagebox.showinfo("Resultado do Teste", "Template NÃO encontrado!")
        except Exception as e:
            self.log(f"❌ ERRO no teste: {e}")
            messagebox.showerror("Erro no Teste", f"Ocorreu um erro: {e}")
    
    def run_masked_test(self):
        """Executa o teste com máscara do módulo testnew.py"""
        if not self.connected_device:
            messagebox.showerror("Erro", "Nenhum dispositivo conectado!")
            return
            
        # Cria thread para não travar a UI
        test_thread = threading.Thread(target=self._run_masked_test_thread)
        test_thread.daemon = True
        test_thread.start()
    
    def _run_masked_test_thread(self):
        """Função que roda o teste com máscara em thread separada"""
        try:
            self.log("Iniciando teste com máscara...")
            result = execute_masked_test()
            if result:
                self.log("✅ TESTE COM MÁSCARA CONCLUÍDO: Template encontrado com sucesso!")
                messagebox.showinfo("Resultado do Teste", "Template encontrado com sucesso!")
            else:
                self.log("❌ TESTE COM MÁSCARA CONCLUÍDO: Template NÃO encontrado!")
                messagebox.showinfo("Resultado do Teste", "Template NÃO encontrado!")
        except Exception as e:
            self.log(f"❌ ERRO no teste com máscara: {e}")
            messagebox.showerror("Erro no Teste", f"Ocorreu um erro: {e}")
    
    def update_capture_status(self):
        """Atualiza o status da captura na interface a cada segundo"""
        from cerebro.capture import capture_thread, stop_capture_thread
        
        if capture_thread and capture_thread.is_alive() and not stop_capture_thread:
            self.capture_status_label.config(text="Thread de captura: Ativa ✓", foreground="green")
            queue_size = screenshot_queue.qsize()
            self.capture_fps_label.config(text=f"Fila: {queue_size}")
        else:
            self.capture_status_label.config(text="Thread de captura: Inativa ✗", foreground="red")
            self.capture_fps_label.config(text="Fila: 0")
            
        # Reagenda para 1 segundo depois
        self.root.after(1000, self.update_capture_status)
    
    def on_state_change(self, previous_state, new_state):
        """Callback chamado quando o estado do jogo muda"""
        # Atualiza a interface na thread da UI
        self.root.after(0, lambda: self._update_state_ui(previous_state, new_state))
    
    def _update_state_ui(self, previous_state, new_state):
        """Atualiza a UI com a mudança de estado"""
        self.state_label.config(text=f"Estado atual: {new_state}")
        self.state_time_label.config(text="Tempo no estado: 0s")
        
        # Log da mudança
        self.log(f"Estado alterado: {previous_state} -> {new_state}")
    
    def update_transmission_status(self):
        """Atualiza o status da transmissão na GUI - chamado pelo transmitter"""
        # Ativado via callback com lock de thread
        self.root.after(0, self._update_transmission_ui)
    
    def _update_transmission_ui(self):
        """Atualiza a UI da transmissão (thread-safe)"""
        self.transmission_status_label.config(text="Transmissão: Ativa ✓", foreground="green")
        self.transmission_last_active = time.time()
    
    def check_transmission_timeout(self):
        """Verifica se a transmissão está inativa há mais de 2 segundos"""
        if hasattr(self, 'transmission_last_active'):
            if time.time() - self.transmission_last_active > 2.0:
                self.transmission_status_label.config(text="Transmissão: Inativa", foreground="gray")
        
        # Reagenda verificação
        self.root.after(2000, self.check_transmission_timeout)

def show_emulator_closed_message():
    """
    Mostra uma mensagem amigável com GIF animado quando o emulador está fechado e toca um som.
    
    Returns:
        bool: Se o usuário quer continuar ou não
    """
    # Tenta tocar um som para chamar atenção
    try:
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
    except Exception:
        pass  # Ignora erros de som
    
    # Cria janela de mensagem customizada
    message_window = tk.Toplevel()
    message_window.title("Emulador não Detectado")
    message_window.geometry("450x400")
    message_window.resizable(False, False)
    message_window.grab_set()  # Faz janela modal
    
    # Centraliza na tela
    window_width = 450
    window_height = 400
    screen_width = message_window.winfo_screenwidth()
    screen_height = message_window.winfo_screenheight()
    position_x = int((screen_width - window_width) / 2)
    position_y = int((screen_height - window_height) / 2)
    message_window.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
    
    # Verifica se existe o arquivo do GIF
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gif_path = os.path.join(project_root, "assets", "emulator_error.gif")
    
    # Frame principal com padding
    main_frame = ttk.Frame(message_window, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Título
    title_label = ttk.Label(main_frame, text="Emulador Não Encontrado", font=("Helvetica", 16, "bold"))
    title_label.pack(pady=(0, 15))
    
    # Função para animar o GIF se existir, caso contrário mostra texto
    if os.path.exists(gif_path):
        # Carrega todas as frames do GIF
        gif = Image.open(gif_path)
        frames = []
        try:
            while True:
                frames.append(ImageTk.PhotoImage(gif.copy()))
                gif.seek(len(frames))  # Avança para o próximo frame
        except EOFError:
            pass  # Fim do GIF
        
        # Label para mostrar o GIF
        gif_label = ttk.Label(main_frame)
        gif_label.pack(pady=10)
        
        def update_frame(index):
            frame = frames[index]
            gif_label.configure(image=frame)
            # Lógica para loop do GIF
            next_index = (index + 1) % len(frames)
            # Agenda próximo frame (ajuste o tempo conforme necessário, 100 = 0.1s)
            message_window.after(100, update_frame, next_index)
        
        # Inicia a animação do GIF
        if frames:
            update_frame(0)
    else:
        # Texto alternativo se o GIF não existir
        info_text = "O emulador precisa estar aberto para o funcionamento da ferramenta."
        info_label = ttk.Label(main_frame, text=info_text, font=("Helvetica", 12), wraplength=350)
        info_label.pack(pady=30)
    
    # Mensagem de instruções
    message_text = """
    Por favor, verifique se:
    
    1. O emulador está aberto e funcionando
    2. A conexão ADB está ativa (adb devices)
    3. O jogo HayDay está instalado
    
    Deseja tentar novamente?
    """
    message_label = ttk.Label(main_frame, text=message_text, justify="left", wraplength=380)
    message_label.pack(pady=10)
    
    # Variável para armazenar a resposta
    result = {"continue": False}
    
    # Função para fechar a janela com resposta
    def on_button_click(continue_execution):
        result["continue"] = continue_execution
        message_window.destroy()
    
    # Frame para botões
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=15)
    
    # Botões
    retry_button = ttk.Button(button_frame, text="Tentar Novamente", command=lambda: on_button_click(True))
    retry_button.pack(side=tk.LEFT, padx=10)
    
    exit_button = ttk.Button(button_frame, text="Sair", command=lambda: on_button_click(False))
    exit_button.pack(side=tk.LEFT, padx=10)
    
    # Espera a resposta
    message_window.wait_window()
    
    return result["continue"]
