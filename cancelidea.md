# Proposta de Implementação: Botão de Cancelamento para Kits

## Análise da Situação Atual

Após uma análise completa do código, identifiquei que atualmente não há um mecanismo centralizado para cancelar operações de kits em execução. A arquitetura atual possui os seguintes componentes relevantes:

1. **Interface Gráfica (UI)** - Gerenciada pela classe `HayDayTestApp` em `cerebro/ui.py`
2. **Execução de Kits** - Feita em threads separadas via `_run_kit_thread()` na UI
3. **Kit Manager** - Framework centralizado em `cerebro/kit_manager.py` que realiza operações genéricas
4. **Scripts de Kits** - Implementações específicas como `execution/kit_terra.py`
5. **Gerenciamento de Threads** - Através do `thread_terminator.py`

## Proposta de Solução

A proposta consiste em três partes principais:

1. **Mecanismo de sinalização** - Flag global que indica cancelamento
2. **Botão na UI** - Interface para acionar o cancelamento
3. **Pontos de verificação** - Locais no código onde verificar o sinal de cancelamento

### 1. Mecanismo de Sinalização Global

Implementar um mecanismo de sinalização através de uma flag compartilhada que pode ser acessada por todos os componentes envolvidos.

```python
# cerebro/kit_cancellation.py (novo arquivo)

import threading

# Flag global para controle de cancelamento
_cancel_requested = False
_cancel_lock = threading.Lock()

def request_cancel():
    """Solicita o cancelamento da operação atual de kit"""
    global _cancel_requested
    with _cancel_lock:
        _cancel_requested = True
    return True

def is_cancel_requested():
    """Verifica se o cancelamento foi solicitado"""
    global _cancel_requested
    with _cancel_lock:
        return _cancel_requested

def reset_cancel_flag():
    """Reseta a flag de cancelamento para uma nova operação"""
    global _cancel_requested
    with _cancel_lock:
        _cancel_requested = False
    return True
```

### 2. Integração na Interface Gráfica

Adicionar um botão de cancelamento na UI que só ficará ativo durante a execução de um kit:

```python
# Em cerebro/ui.py (HayDayTestApp)

# Adicionar à função setup_actions_area() ou em função própria:
def setup_cancel_button(self, parent_frame):
    """Configura o botão de cancelamento de operação"""
    
    self.cancel_frame = ttk.Frame(parent_frame)
    self.cancel_frame.pack(fill=tk.X, pady=10)
    
    self.cancel_button = ttk.Button(
        self.cancel_frame,
        text="⚠️ Cancelar Operação",
        command=self.cancel_current_operation,
        style="Danger.TButton",  # Novo estilo a ser criado
        state=tk.DISABLED  # Inicialmente desabilitado
    )
    self.cancel_button.pack(pady=5)
    
def cancel_current_operation(self):
    """Cancela a operação de kit em execução"""
    from cerebro.kit_cancellation import request_cancel
    
    response = messagebox.askyesno(
        "Confirmar Cancelamento", 
        "Deseja realmente cancelar a operação em andamento?\n\nNota: A operação será interrompida no próximo ponto seguro."
    )
    
    if response:
        # Solicitar cancelamento
        request_cancel()
        self.log("⚠️ Solicitação de cancelamento enviada. Aguardando interrupção da operação...")
```

### 3. Atualização do Gerenciador de Kit

Modificar o `kit_manager.py` para verificar a flag de cancelamento em pontos estratégicos:

```python
# Em cerebro/kit_manager.py

# Importar no início do arquivo
from cerebro.kit_cancellation import is_cancel_requested, reset_cancel_flag

# Adicionar verificação no início do process_kit
def process_kit(kit_config: Dict[str, Any], empty_boxes: List[int]) -> bool:
    """Processa um kit completo, com suporte a cancelamento"""
    
    # Reseta a flag de cancelamento no início da operação
    reset_cancel_flag()
    
    # ... código existente ...
    
    # Em pontos estratégicos, verificar se o cancelamento foi solicitado
    for item_config in kit_config.get("items", []):
        
        # Verificar cancelamento
        if is_cancel_requested():
            print(f"{Colors.YELLOW}[KIT MANAGER] AVISO:{Colors.RESET} Operação cancelada pelo usuário")
            return False
            
        # ... código existente ...
```

### 4. Integração nos Scripts de Kit

Adicionar verificações de cancelamento nos scripts específicos de kit, como `kit_terra.py`:

```python
# Em execution/kit_terra.py

# Importar no início do arquivo
from cerebro.kit_cancellation import is_cancel_requested, reset_cancel_flag

def run() -> bool:
    """Executa o kit terra completo com suporte a cancelamento"""
    
    # Reseta a flag de cancelamento no início
    reset_cancel_flag()
    
    # ... código existente ...
    
    # Verificar em pontos estratégicos
    for state_name, state_config in states.items():
        
        # Verificar cancelamento
        if is_cancel_requested():
            print(f"{Colors.YELLOW}[TERRA] AVISO:{Colors.RESET} Operação cancelada pelo usuário")
            unregister_state_callback(on_state_change_during_execution)
            return False
            
        # ... código existente ...
```

### 5. Atualização do Fluxo de Execução na UI

Modificar o método que inicia a execução dos kits para habilitar/desabilitar o botão de cancelamento:

```python
# Em cerebro/ui.py

def _run_kit_thread(self, kit_name, module_name, customer_id=None):
    """Função que executa a venda do kit ou operação em thread separada"""
    try:
        # Ativar botão de cancelamento
        self.root.after(0, lambda: self.cancel_button.config(state=tk.NORMAL))
        
        # ... código existente ...
        
    finally:
        # Desativar botão de cancelamento ao final
        self.root.after(0, lambda: self.cancel_button.config(state=tk.DISABLED))
        
        # Resetar flag de cancelamento (redundante, mas mais seguro)
        from cerebro.kit_cancellation import reset_cancel_flag
        reset_cancel_flag()
```

## Implementação do Estilo Visual Distinto

Adicionaremos um estilo visual específico para o botão de cancelamento:

```python
# Em cerebro/ui.py, método configure_theme

# Estilo de botão de perigo para cancelamento
style.configure("Danger.TButton", 
                background="#f38ba8",     # Vermelho
                foreground="#11111b")     # Texto escuro
style.map("Danger.TButton", 
         background=[("active", "#f5c2e7"), ("pressed", "#eba0ac")],
         foreground=[("active", "#181825")])
```

## Considerações Adicionais

1. **Segurança e Robustez**:
   - O sistema de cancelamento é projetado para ser não-intrusivo
   - O cancelamento ocorre apenas em "pontos seguros" para evitar estados inconsistentes
   - Múltiplos pontos de verificação garantem resposta rápida ao cancelamento

2. **Experiência do Usuário**:
   - Feedback visual claro (botão vermelho)
   - Confirmação antes do cancelamento
   - Feedback informando que o cancelamento está em andamento

3. **Extensibilidade**:
   - O design é modular e pode ser facilmente expandido para outros kits
   - O mesmo mecanismo pode ser usado para outras operações longas

## Benefícios da Implementação

1. **Maior Controle** - Permite ao usuário interromper operações que estão demorando muito
2. **Prevenção de Erros** - Evita esperar até o fim para corrigir problemas detectados
3. **Melhor Experiência** - Aumenta a sensação de controle do usuário sobre o sistema
4. **Robustez** - Evita que operações problemáticas bloqueiem o sistema indefinidamente

## Próximos Passos

1. Implementar o módulo `kit_cancellation.py`
2. Atualizar a UI para incluir o botão de cancelamento
3. Modificar `kit_manager.py` para verificar a flag de cancelamento
4. Integrar a verificação de cancelamento nos scripts de kit individuais
5. Testar exaustivamente para garantir que o cancelamento funcione em todos os cenários
