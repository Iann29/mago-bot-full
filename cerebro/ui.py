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
    
    # Dicionário de kits disponíveis e seus respectivos módulos
    KITS = {
        'Celeiro': 'kit_celeiro',
        'Terra': 'kit_terra',
        'Silo': 'kit_silo',
        'Serra': 'kit_serra',
        'Dinamite': 'kit_dinamite',
        'Machado': 'kit_machado',
        'Pá': 'kit_pa'
    }
    
    def __init__(self, root, user_data=None):
        """
        Inicializa a interface gráfica.
        
        Args:
            root: Elemento raiz do Tkinter
            user_data: Dados do usuário autenticado
        """
        self.root = root
        self.root.title("@magodohayday")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configurar tema escuro com cores nativas
        bg_color = "#2d2d2d"  # Cor de fundo escura
        fg_color = "#ffffff"  # Cor de texto clara
        accent_color = "#007acc"  # Cor de destaque (azul)
        frame_bg = "#333333"  # Cor de fundo para frames
        entry_bg = "#1e1e1e"  # Cor de fundo para entradas de texto
        
        # Configura cores para a janela principal
        self.root.configure(bg=bg_color)
        
        # Configura estilo para os widgets
        style = ttk.Style()
        
        # Configurações gerais
        style.configure(".", background=bg_color, foreground=fg_color)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        
        # Botões padronizados com o mesmo estilo do botão de destaque
        style.configure("TButton", background="#4cc9f0", foreground="#000000")
        style.map("TButton", 
                  background=[("active", "#80ed99"), ("pressed", "#57cc99")],
                  foreground=[("active", "#000000")])
        
        # LabelFrame com bordas mais suaves e cores escuras
        style.configure("TLabelframe", background=bg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Segoe UI", 9, "bold"))
        
        # Botão destacado com cores vibrantes
        style.configure("Accent.TButton", background="#4cc9f0", foreground="#000000")
        style.map("Accent.TButton", 
                  background=[("active", "#80ed99"), ("pressed", "#57cc99")],
                  foreground=[("active", "#000000")])
        
        # Configura cores para a área de texto do log
        self.log_colors = {
            "bg": entry_bg,
            "fg": fg_color,
            "select_bg": accent_color,
            "select_fg": "white"
        }
        
        # Variáveis de controle
        self.adb_manager_instance = None
        self.connected_device = None
        self.emulator_connection_lost = False
        
        # Flag para controlar se a interface está ativa
        self.ui_active = True
        self.after_ids = []  # Lista para armazenar os IDs de chamadas after()
        
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
        title_text = "@magodohayday"
        if self.html_id:
            # Extrai nome do usuário do html_id (exemplo: "screen-ian" -> "Ian")
            user_name = self.html_id.replace("screen-", "").capitalize()
            title_text += f" - {user_name}"
            
        # Header com título e logo
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(10, 20))
        
        # Título estilizado
        title_label = ttk.Label(header_frame, text=title_text, font=("Segoe UI", 20, "bold"))
        title_label.pack(pady=5)
        
        # Subtítulo
        subtitle = ttk.Label(header_frame, text="Bot de Automação", font=("Segoe UI", 12))
        subtitle.pack(pady=2)
        
        # Frame de status com visual melhorado
        status_frame = ttk.LabelFrame(main_frame, text="Status da Conexão", padding=15)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Layout de status com botão de verificação
        status_content_frame = ttk.Frame(status_frame)
        status_content_frame.pack(fill=tk.X, expand=True)
        
        # Coluna esquerda: Labels de status
        status_labels_frame = ttk.Frame(status_content_frame)
        status_labels_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.status_label = ttk.Label(status_labels_frame, text="Não conectado")
        self.status_label.pack(pady=5, anchor=tk.W)
        
        self.device_label = ttk.Label(status_labels_frame, text="Dispositivo: Nenhum")
        self.device_label.pack(pady=5, anchor=tk.W)
        
        # Coluna direita: Botão de verificação
        status_button_frame = ttk.Frame(status_content_frame)
        status_button_frame.pack(side=tk.RIGHT)
        
        self.check_status_button = ttk.Button(
            status_button_frame, 
            text="Verificar Status", 
            command=self.check_emulator_status
        )
        self.check_status_button.pack(padx=5, pady=10)
        
        # Frame de captura com visual melhorado
        capture_frame = ttk.LabelFrame(main_frame, text="Status da Captura", padding=15)
        capture_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.capture_status_label = ttk.Label(capture_frame, text="Thread de captura: Inativa")
        self.capture_status_label.pack(side=tk.LEFT, padx=5)
        
        self.capture_fps_label = ttk.Label(capture_frame, text="FPS: --")
        self.capture_fps_label.pack(side=tk.RIGHT, padx=5)
        
        # Frame de estado do jogo com visual melhorado
        state_frame = ttk.LabelFrame(main_frame, text="Estado do Jogo", padding=15)
        state_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.state_label = ttk.Label(state_frame, text="Estado atual: Desconhecido")
        self.state_label.pack(side=tk.LEFT, padx=5)
        
        self.state_time_label = ttk.Label(state_frame, text="Tempo no estado: 0s")
        self.state_time_label.pack(side=tk.RIGHT, padx=5)
        
        # Frame de status de transmissão com visual melhorado
        transmission_frame = ttk.LabelFrame(main_frame, text="Status da Transmissão", padding=15)
        transmission_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.transmission_status_label = ttk.Label(transmission_frame, text="Transmissão: Inativa", foreground="gray")
        self.transmission_status_label.pack(side=tk.LEFT, padx=5)
        
        # Frame de venda de kits com visual melhorado
        actions_frame = ttk.LabelFrame(main_frame, text="Botões de Venda de Kits", padding=15)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Frame para organizar os botões em grid
        buttons_grid = ttk.Frame(actions_frame)
        buttons_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Configurar o grid para 3 colunas
        num_cols = 3
        row, col = 0, 0
        
        # Adicionar botões para cada kit disponível
        for kit_name, module_name in self.KITS.items():
            button = ttk.Button(
                buttons_grid, 
                text=f"Kit {kit_name}", 
                command=lambda name=kit_name, module=module_name: self.run_kit(name, module)
            )
            button.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            # Avançar para a próxima posição no grid
            col += 1
            if col >= num_cols:
                col = 0
                row += 1
        
        # Configurar pesos das colunas para distribuição uniforme
        for i in range(num_cols):
            buttons_grid.columnconfigure(i, weight=1)
        
        # Espaçador para manter o layout equilibrado
        spacer_frame = ttk.Frame(main_frame, height=20)
        spacer_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Inicia o timer para atualizar a UI
        self.schedule_ui_update(self.update_capture_status, 1000)  # Atualiza a cada 1s
        self.schedule_ui_update(self.check_transmission_timeout, 2000)  # Verifica a cada 2s
        
        # Configura o callback no transmissor
        transmitter.set_transmission_callback(self.update_transmission_status)
        
        # Registra callback para mudanças de estado
        from cerebro.state import register_state_callback
        register_state_callback(self.on_state_change)
        self.log("🔔✅ Callback de estado registrado na UI")
    
    def log(self, message):
        """Registra mensagem no console em vez da interface"""
        print(message)
    
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
    
    def run_kit(self, kit_name, module_name):
        """Executa a venda do kit especificado"""
        if not self.connected_device:
            messagebox.showerror("Erro", "Nenhum dispositivo conectado!")
            return
            
        # Cria thread para não travar a UI
        kit_thread = threading.Thread(target=lambda: self._run_kit_thread(kit_name, module_name))
        kit_thread.daemon = True
        kit_thread.start()
    
    def _run_kit_thread(self, kit_name, module_name):
        """Função que executa a venda do kit em thread separada"""
        try:
            self.log(f"Iniciando venda do Kit {kit_name}...")
            
            # Importa dinamicamente o módulo do kit
            import importlib
            try:
                # Carrega o módulo do kit da pasta execution
                kit_module = importlib.import_module(f'execution.{module_name}')
                
                # Verifica se o módulo tem uma função run
                if hasattr(kit_module, 'run'):
                    result = kit_module.run()
                    if result:
                        self.log(f"✅ Kit {kit_name} vendido com sucesso!")
                        messagebox.showinfo("Venda de Kit", f"Kit {kit_name} vendido com sucesso!")
                    else:
                        self.log(f"⚠️ Kit {kit_name}: Operação finalizada")
                        messagebox.showinfo("Venda de Kit", f"Operação de venda do Kit {kit_name} finalizada.")
                else:
                    self.log(f"❌ Kit {kit_name}: Módulo não possui função 'run'")
                    messagebox.showwarning("Erro de Kit", f"O módulo do Kit {kit_name} não possui função 'run'")
            except Exception as e:
                self.log(f"❌ Erro ao carregar módulo do Kit {kit_name}: {e}")
                messagebox.showerror("Erro de Importação", f"Erro ao carregar módulo do Kit {kit_name}: {e}")
        except Exception as e:
            self.log(f"❌ ERRO ao executar Kit {kit_name}: {e}")
            messagebox.showerror("Erro na Venda", f"Ocorreu um erro: {e}")
    
    def schedule_ui_update(self, callback, delay_ms):
        """Agenda uma atualização de UI com segurança"""
        if self.ui_active:
            after_id = self.root.after(delay_ms, callback)
            self.after_ids.append(after_id)
            return after_id
        return None
        
    def update_capture_status(self):
        """Atualiza o status da captura na interface a cada segundo"""
        if not self.ui_active:
            return
            
        try:
            from cerebro.capture import capture_thread, stop_capture_thread
            
            if capture_thread and capture_thread.is_alive() and not stop_capture_thread:
                self.capture_status_label.config(text="Thread de captura: Ativa ✓", foreground="green")
                queue_size = screenshot_queue.qsize()
                self.capture_fps_label.config(text=f"Fila: {queue_size}")
            else:
                self.capture_status_label.config(text="Thread de captura: Inativa ✗", foreground="red")
                self.capture_fps_label.config(text="Fila: 0")
        except Exception as e:
            # Ignora erros se a interface já estiver sendo destruída
            pass
            
        # Reagenda para 1 segundo depois
        self.schedule_ui_update(self.update_capture_status, 1000)
    
    def on_state_change(self, previous_state, new_state):
        """Callback chamado quando o estado do jogo muda"""
        # Atualiza a interface na thread da UI
        self.root.after(0, lambda: self._update_state_ui(previous_state, new_state))
    
    def _update_state_ui(self, previous_state, new_state):
        """Atualiza a UI com a mudança de estado"""
        # Destacar visualmente a mudança de estado com formatação especial
        self.state_label.config(text=f"Estado atual: {new_state}")
        self.state_time_label.config(text="Tempo no estado: 0s")
        
        # Registra a mudança no console
        print(f"🔄 Estado alterado: {previous_state} → {new_state}")
    
    def update_transmission_status(self):
        """Atualiza o status da transmissão na GUI - chamado pelo transmitter"""
        # Ativado via callback com lock de thread
        if self.ui_active:
            try:
                self.root.after(0, self._update_transmission_ui)
            except Exception:
                # Ignora erros se a interface já estiver sendo destruída
                pass
    
    def _update_transmission_ui(self):
        """Atualiza a UI da transmissão (thread-safe)"""
        if not self.ui_active:
            return
            
        try:
            self.transmission_status_label.config(text="Transmissão: Ativa ✓", foreground="green")
            self.transmission_last_active = time.time()
        except Exception:
            # Ignora erros se a interface já estiver sendo destruída
            pass
    
    def check_transmission_timeout(self):
        """Verifica se a transmissão está inativa há mais de 2 segundos"""
        if not self.ui_active:
            return
            
        try:
            if hasattr(self, 'transmission_last_active'):
                if time.time() - self.transmission_last_active > 2.0:
                    self.transmission_status_label.config(text="Transmissão: Inativa", foreground="gray")
        except Exception:
            # Ignora erros se a interface já estiver sendo destruída
            pass
        
        # Reagenda verificação
        self.schedule_ui_update(self.check_transmission_timeout, 2000)
        
    def check_emulator_status(self):
        """Verifica o status do emulador quando o botão é clicado."""
        self.check_status_button.config(text="Verificando...", state="disabled")
        self.root.update_idletasks()  # Atualiza a UI imediatamente para mostrar o botão desabilitado
        
        try:
            # Verifica se o emulador está conectado
            is_connected = adb_manager.is_connected()
            
            if is_connected:
                device_serial = adb_manager.get_target_serial()
                self.status_label.config(text="Conectado ✓", foreground="green")
                self.device_label.config(text=f"Dispositivo: {device_serial}")
                
                # Atualiza o atributo connected_device
                self.connected_device = adb_manager.get_device()
                
                # Se estava marcado como desconectado antes, notifica reconexão
                if self.emulator_connection_lost:
                    self.emulator_connection_lost = False
                    self.log("📱✅ Emulador reconectado!")
                    try:
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)
                    except Exception:
                        pass
            else:
                self.status_label.config(text="Desconectado ✗", foreground="red")
                self.device_label.config(text="Dispositivo: Nenhum")
                self.connected_device = None
                
                # Se não estava marcado como desconectado antes, notifica desconexão
                if not self.emulator_connection_lost:
                    self.emulator_connection_lost = True
                    self.log("📱❌ Emulador desconectado!")
                    try:
                        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                    except Exception:
                        pass
            
            # Exibe um toast de resultado
            status_text = "conectado" if is_connected else "desconectado"
            self.log(f"🔍 Verificação de status: Emulador {status_text}")
        except Exception as e:
            self.log(f"❌ Erro ao verificar status: {e}")
            self.status_label.config(text="Erro ✗", foreground="red")
        finally:
            # Reativa o botão
            self.check_status_button.config(text="Verificar Status", state="normal")
    
    def on_close(self):
        """Chamado quando a interface está sendo fechada"""
        # Marca a UI como inativa para evitar atualizações futuras
        self.ui_active = False
        
        # Cancela todos os agendamentos pendentes
        for after_id in self.after_ids:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        
        # Limpa a lista de IDs
        self.after_ids.clear()

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
