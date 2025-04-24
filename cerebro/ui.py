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
        'Pá': 'kit_pa',
        'Add Cliente': 'addCliente',
        'Verificar Lucro': 'verificarLucro'
    }
    
    def __init__(self, root):
        """
        Inicializa a interface gráfica.
        
        Args:
            root: Elemento raiz do Tkinter
        """
        self.root = root
        self.root.title("HayDay Test Tool")
        self.root.geometry("700x860")
        self.root.resizable(True, True)
        
        # Configurar tema escuro com cores modernas
        self.configure_theme()
        
        # Variáveis de controle
        self.adb_manager_instance = None
        self.connected_device = None
        self.emulator_connection_lost = False
        
        # Flag para controlar se a interface está ativa
        self.ui_active = True
        self.after_ids = []  # Lista para armazenar os IDs de chamadas after()
        
        # Variáveis para a área de adicionar cliente
        self.client_tag_var = tk.StringVar()
        
        # Variável para controlar o modo Turbo
        self.turbo_mode = tk.BooleanVar(value=False)
        
        # Configurar a interface
        self.setup_ui()
        
        # Inicializar ADB ao abrir
        self.initialize_adb()
        
        # Registrar callbacks no ADBManager para detecção proativa
        adb_manager.register_connection_callback(self.on_emulator_connected)
        adb_manager.register_disconnect_callback(self.on_emulator_disconnected)
        
        # Iniciar monitoramento de conexão
        adb_manager.start_connection_monitoring()
    
    def configure_theme(self):
        """Configura o tema e as cores para a interface"""
        # Cores mais modernas e atraentes
        bg_color = "#1e1e2e"  # Fundo principal mais escuro
        fg_color = "#cdd6f4"  # Texto mais suave
        accent_color = "#89b4fa"  # Azul suave
        frame_bg = "#313244"  # Fundo para frames
        button_bg = "#89dceb"  # Cor vibrante para botões
        button_active = "#94e2d5"  # Cor quando botão está ativo
        switch_on = "#a6e3a1"  # Verde para o switch ativado
        
        # Configura cores para a janela principal
        self.root.configure(bg=bg_color)
        
        # Configura estilo para os widgets
        style = ttk.Style()
        
        # Configurações gerais
        style.configure(".", background=bg_color, foreground=fg_color)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        
        # Estilo específico para campos de entrada com texto ESCURO
        style.configure("TEntry", 
                       fieldbackground="white", 
                       foreground="#11111b",  # Texto escuro para contrastar com o fundo claro
                       insertcolor=accent_color)  # Cor do cursor de inserção de texto
        
        # Botões estilizados
        style.configure("TButton", background=button_bg, foreground="#11111b")
        style.map("TButton", 
                  background=[("active", button_active), ("pressed", "#74c7ec")],
                  foreground=[("active", "#181825")])
        
        # LabelFrame com bordas mais suaves e cores escuras
        style.configure("TLabelframe", background=bg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Segoe UI", 10, "bold"))
        
        # Botão destacado com cores vibrantes
        style.configure("Accent.TButton", background=button_bg, foreground="#11111b")
        style.map("Accent.TButton", 
                  background=[("active", button_active), ("pressed", "#74c7ec")],
                  foreground=[("active", "#181825")])
        
        # Estilo para o checkbutton do modo Turbo
        style.configure("Switch.TCheckbutton",
                        background=bg_color,
                        foreground=fg_color)
        style.map("Switch.TCheckbutton",
                 foreground=[("selected", switch_on)],
                 background=[("active", bg_color)])
    
    def setup_ui(self):
        """Configura todos os elementos da interface"""
        # Frame principal com padding
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header mais compacto com logo e título
        self.setup_header(main_frame)
        
        # Área de status em um único frame compacto
        self.setup_status_area(main_frame)
        
        # Frame de estado do jogo
        self.setup_game_state_area(main_frame)
        
        # Área para adicionar cliente
        self.setup_add_client_area(main_frame)
        
        # Área de ações para venda de kits
        self.setup_actions_area(main_frame)
        
        # Inicia o timer para atualizar a UI
        self.schedule_ui_update(self.update_state_time, 1000)  # Atualiza tempo de estado a cada 1s
        
        # Registra callback para mudanças de estado
        from cerebro.state import register_state_callback
        register_state_callback(self.on_state_change)
        self.log("🔔✅ Callback de estado registrado na UI")
    
    def setup_header(self, parent_frame):
        """Configuração do cabeçalho da aplicação"""
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Título e subtítulo em layout horizontal
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(pady=5)
        
        title_label = ttk.Label(title_frame, text="@magodohayday", font=("Segoe UI", 20, "bold"))
        title_label.pack(side=tk.LEFT, padx=(0, 10))
        
        subtitle = ttk.Label(title_frame, text="Bot de Automação", font=("Segoe UI", 12))
        subtitle.pack(side=tk.LEFT, padx=5, pady=8)
    
    def setup_status_area(self, parent_frame):
        """Configuração da área de status compacta"""
        status_frame = ttk.LabelFrame(parent_frame, text="Status do Sistema", padding=12)
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Grid para organizar status e botão
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Área de conexão
        conn_frame = ttk.Frame(status_grid)
        conn_frame.grid(row=0, column=0, sticky="w", padx=10)
        
        self.status_label = ttk.Label(conn_frame, text="Não conectado", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.device_label = ttk.Label(conn_frame, text="Dispositivo: Nenhum")
        self.device_label.pack(side=tk.LEFT)
        
        # Botão de verificar status à direita
        self.check_status_button = ttk.Button(
            status_grid, 
            text="Verificar Conexão", 
            command=self.check_emulator_status,
            style="Accent.TButton"
        )
        self.check_status_button.grid(row=0, column=1, sticky="e", padx=10)
        
        # Configurar pesos das colunas
        status_grid.columnconfigure(0, weight=1)
        status_grid.columnconfigure(1, weight=0)
    
    def setup_game_state_area(self, parent_frame):
        """Configuração da área de estado do jogo"""
        state_frame = ttk.LabelFrame(parent_frame, text="Estado do Jogo", padding=12)
        state_frame.pack(fill=tk.X, padx=10, pady=10)
        
        state_grid = ttk.Frame(state_frame)
        state_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        self.state_label = ttk.Label(state_grid, text="Estado atual: Desconhecido", font=("Segoe UI", 9, "bold"))
        self.state_label.grid(row=0, column=0, sticky="w", padx=10)
        
        self.state_time_label = ttk.Label(state_grid, text="Tempo no estado: 0s")
        self.state_time_label.grid(row=0, column=1, sticky="e", padx=10)
        
        # Configurar pesos das colunas
        state_grid.columnconfigure(0, weight=1)
        state_grid.columnconfigure(1, weight=0)
    
    def setup_add_client_area(self, parent_frame):
        """Configura a área para adicionar cliente na interface principal"""
        client_frame = ttk.LabelFrame(parent_frame, text="Adicionar Cliente", padding=12)
        client_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame interno para organização
        inner_frame = ttk.Frame(client_frame)
        inner_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Label de instrução
        instruction_label = ttk.Label(inner_frame, text="Tag do cliente:", font=("Segoe UI", 10))
        instruction_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Campo de texto para a tag
        tag_entry = ttk.Entry(inner_frame, textvariable=self.client_tag_var, width=30)
        tag_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Botão de adicionar
        add_button = ttk.Button(
            inner_frame, 
            text="Adicionar", 
            command=self.add_client,
            style="Accent.TButton",
            width=15
        )
        add_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)
        
        # Configurar pesos das colunas
        inner_frame.columnconfigure(0, weight=0)  # Label não precisa expandir
        inner_frame.columnconfigure(1, weight=1)  # Campo de texto expande
        inner_frame.columnconfigure(2, weight=0)  # Botão não precisa expandir
    
    def setup_actions_area(self, parent_frame):
        """Configuração da área de botões de ação"""
        actions_frame = ttk.LabelFrame(parent_frame, text="Botões de Venda de Kits", padding=12)
        actions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame para o botão Turbo
        turbo_frame = ttk.Frame(actions_frame)
        turbo_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        # Label para o Turbo
        turbo_label = ttk.Label(turbo_frame, text="Turbo:", font=("Segoe UI", 10, "bold"))
        turbo_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # Botão de alternância para o Turbo
        self.turbo_switch = ttk.Checkbutton(
            turbo_frame, 
            text="ON/OFF",
            variable=self.turbo_mode,
            onvalue=True,
            offvalue=False,
            style="Switch.TCheckbutton"
        )
        self.turbo_switch.pack(side=tk.LEFT)
        
        # Grid melhorado para botões
        buttons_grid = ttk.Frame(actions_frame)
        buttons_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configurar o grid para 3 colunas
        num_cols = 3
        row, col = 0, 0
        
        # Adicionar botões para cada kit disponível com visual melhorado
        for kit_name, module_name in self.KITS.items():
            # Pula o 'Add Cliente' e 'Verificar Lucro' que serão tratados separadamente
            if kit_name == "Add Cliente" or kit_name == "Verificar Lucro":
                continue
                
            button_frame = ttk.Frame(buttons_grid, padding=5)
            button_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            button = ttk.Button(
                button_frame, 
                text=f"Kit {kit_name}", 
                command=lambda name=kit_name, module=module_name: self.run_kit(name, module),
                style="TButton"
            )
            button.pack(fill=tk.BOTH, expand=True, ipady=8)
            
            # Avançar para a próxima posição no grid
            col += 1
            if col >= num_cols:
                col = 0
                row += 1
        
        # Configurar pesos das colunas e linhas para distribuição uniforme
        for i in range(num_cols):
            buttons_grid.columnconfigure(i, weight=1)
        
        for i in range(row + 1):
            buttons_grid.rowconfigure(i, weight=1)
            
        # Adicionar o botão "Verificar lucro de conta" em um frame separado
        verify_profit_frame = ttk.LabelFrame(parent_frame, text="Verificação de Lucro", padding=12)
        verify_profit_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame interno para o botão
        inner_frame = ttk.Frame(verify_profit_frame)
        inner_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Botão de verificar lucro com estilo destacado
        profit_button = ttk.Button(
            inner_frame, 
            text="Verificar Lucro de Conta", 
            command=lambda: self.run_kit("Verificar Lucro", self.KITS["Verificar Lucro"]),
            style="Accent.TButton",
            width=25
        )
        profit_button.pack(pady=10)
    
    def add_client(self):
        """Função para adicionar cliente a partir da interface integrada"""
        customer_id = self.client_tag_var.get().strip()
        if not customer_id:
            messagebox.showwarning("Aviso", "Por favor, digite uma tag válida!")
            return
        
        # Obtém o módulo de adicionar cliente
        module_name = self.KITS["Add Cliente"]
        
        # Inicia a thread para adicionar o cliente
        if not self.connected_device:
            messagebox.showerror("Erro", "Nenhum dispositivo conectado!")
            return
            
        kit_thread = threading.Thread(
            target=lambda: self._run_kit_thread("Add Cliente", module_name, customer_id)
        )
        kit_thread.daemon = True
        kit_thread.start()
        
        # Limpa o campo de texto após iniciar o processo
        self.client_tag_var.set("")
    
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
            
            self.status_label.config(text="Conectado ✓", foreground="#a6e3a1")  # Verde
            self.device_label.config(text=f"Dispositivo: {device_serial}")
            
            print(f"📱🔌 Inicializando conexão ADB...")
            return True
        else:
            self.status_label.config(text="Não conectado ✗", foreground="#f38ba8")  # Vermelho
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
        self.status_label.config(text="Conectado ✓", foreground="#a6e3a1")  # Verde
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
        self.status_label.config(text="Desconectado ✗", foreground="#f38ba8")  # Vermelho
        self.device_label.config(text="Dispositivo: Nenhum")
        
        # Mostra popup uma única vez se a conexão foi perdida
        message = "A conexão com o emulador foi perdida. Verifique se o emulador está em execução."
        messagebox.showwarning("Conexão Perdida", message)
    
    def run_kit(self, kit_name, module_name):
        """Executa a venda do kit especificado"""
        if not self.connected_device:
            messagebox.showerror("Erro", "Nenhum dispositivo conectado!")
            return
        
        # Inicia a thread para executar o kit
        kit_thread = threading.Thread(target=lambda: self._run_kit_thread(kit_name, module_name))
        kit_thread.daemon = True
        kit_thread.start()
    
    def _run_kit_thread(self, kit_name, module_name, customer_id=None):
        """Função que executa a venda do kit ou operação em thread separada"""
        try:
            # Mensagem apropriada dependendo da operação
            if kit_name == "Add Cliente":
                self.log(f"Iniciando adição de cliente com tag: {customer_id}...")
            else:
                self.log(f"Iniciando venda do Kit {kit_name}...")
            
            # Verificar se o modo Turbo está ativado para os kits compatíveis
            if hasattr(self, 'turbo_mode') and self.turbo_mode.get():
                # Kit Terra no modo Turbo
                if kit_name == "Terra":
                    try:
                        # Tenta importar e executar diretamente o módulo turbo
                        import execution.turbo.terraturbo as turbo_module
                        self.log(f"Modo TURBO ativado para o Kit {kit_name}!")
                        result = turbo_module.run()
                        
                        # Mensagens de resultado
                        if result:
                            self.log(f"✅ Kit {kit_name} (TURBO) vendido com sucesso!")
                            messagebox.showinfo("Venda de Kit", f"Kit {kit_name} vendido com sucesso no modo TURBO!")
                        else:
                            self.log(f"⚠️ Kit {kit_name} (TURBO): Operação finalizada")
                            messagebox.showinfo("Venda de Kit", f"Operação de venda do Kit {kit_name} (TURBO) finalizada.")
                        return
                    except Exception as e:
                        self.log(f"❌ Erro no modo TURBO: {e} - Continuando com modo normal")
                
                # Kit Celeiro no modo Turbo
                elif kit_name == "Celeiro":
                    try:
                        # Tenta importar e executar diretamente o módulo turbo
                        import execution.turbo.celeiroturbo as turbo_module
                        self.log(f"Modo TURBO ativado para o Kit {kit_name}!")
                        result = turbo_module.run()
                        
                        # Mensagens de resultado
                        if result:
                            self.log(f"✅ Kit {kit_name} (TURBO) vendido com sucesso!")
                            messagebox.showinfo("Venda de Kit", f"Kit {kit_name} vendido com sucesso no modo TURBO!")
                        else:
                            self.log(f"⚠️ Kit {kit_name} (TURBO): Operação finalizada")
                            messagebox.showinfo("Venda de Kit", f"Operação de venda do Kit {kit_name} (TURBO) finalizada.")
                        return
                    except Exception as e:
                        self.log(f"❌ Erro no modo TURBO: {e} - Continuando com modo normal")
            
            # Importa dinamicamente o módulo (fluxo normal)
            import importlib
            try:
                # Carrega o módulo da pasta execution
                kit_module = importlib.import_module(f'execution.{module_name}')
                
                # Verifica se o módulo tem uma função run
                if hasattr(kit_module, 'run'):
                    # Executa com parâmetro adicional se for adição de cliente
                    if kit_name == "Add Cliente" and customer_id:
                        result = kit_module.run(customer_id)
                    else:
                        result = kit_module.run()
                    
                    # Mensagens de resultado apropriadas
                    if result:
                        if kit_name == "Add Cliente":
                            self.log(f"✅ Cliente {customer_id} adicionado com sucesso!")
                            messagebox.showinfo("Sucesso", f"Cliente com tag {customer_id} adicionado com sucesso!")
                        else:
                            self.log(f"✅ Kit {kit_name} vendido com sucesso!")
                            messagebox.showinfo("Venda de Kit", f"Kit {kit_name} vendido com sucesso!")
                    else:
                        if kit_name == "Add Cliente":
                            self.log(f"⚠️ Adição de cliente {customer_id}: operação finalizada sem sucesso")
                            messagebox.showinfo("Resultado", f"Operação de adição do cliente finalizada sem sucesso.")
                        else:
                            self.log(f"⚠️ Kit {kit_name}: Operação finalizada")
                            messagebox.showinfo("Venda de Kit", f"Operação de venda do Kit {kit_name} finalizada.")
                else:
                    self.log(f"❌ Módulo {module_name}: não possui função 'run'")
                    messagebox.showwarning("Erro de Módulo", f"O módulo '{module_name}' não possui função 'run'")
            except Exception as e:
                self.log(f"❌ Erro ao carregar módulo {module_name}: {e}")
                messagebox.showerror("Erro de Importação", f"Erro ao carregar módulo '{module_name}': {e}")
        except Exception as e:
            self.log(f"❌ ERRO ao executar operação {kit_name}: {e}")
            messagebox.showerror("Erro na Operação", f"Ocorreu um erro: {e}")
    
    def schedule_ui_update(self, callback, delay_ms):
        """Agenda uma atualização de UI com segurança"""
        if self.ui_active:
            after_id = self.root.after(delay_ms, callback)
            self.after_ids.append(after_id)
            return after_id
        return None
    
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
    
    def update_state_time(self):
        """Atualiza o tempo desde a última mudança de estado"""
        if not self.ui_active:
            return
        
        try:
            # Importa o state_manager para obter o tempo no estado atual
            from cerebro.state import state_manager
            
            if state_manager:
                # Obtém o tempo em segundos desde a última mudança de estado
                duration = state_manager.get_state_duration()
                
                # Formata o tempo (pode ser formatado em minutos/horas se necessário)
                duration_str = f"{int(duration)}s"
                
                # Atualiza o texto na interface
                self.state_time_label.config(text=f"Tempo no estado: {duration_str}")
        except Exception:
            # Ignora erros se a interface já estiver sendo destruída
            pass
        
        # Reagenda a atualização
        self.schedule_ui_update(self.update_state_time, 1000)
        
    def check_emulator_status(self):
        """Verifica o status do emulador quando o botão é clicado."""
        self.check_status_button.config(text="Verificando...", state="disabled")
        self.root.update_idletasks()  # Atualiza a UI imediatamente para mostrar o botão desabilitado
        
        try:
            # Verifica se o emulador está conectado
            is_connected = adb_manager.is_connected()
            
            if is_connected:
                device_serial = adb_manager.get_target_serial()
                self.status_label.config(text="Conectado ✓", foreground="#a6e3a1")  # Verde
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
                self.status_label.config(text="Desconectado ✗", foreground="#f38ba8")  # Vermelho
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
            
            # Exibe log de resultado
            status_text = "conectado" if is_connected else "desconectado"
            self.log(f"🔍 Verificação de status: Emulador {status_text}")
        except Exception as e:
            self.log(f"❌ Erro ao verificar status: {e}")
            self.status_label.config(text="Erro ✗", foreground="#f38ba8")  # Vermelho
        finally:
            # Reativa o botão
            self.check_status_button.config(text="Verificar Conexão", state="normal")
    
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