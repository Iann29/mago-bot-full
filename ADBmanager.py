# /ADBmanager.py

import adbutils
from adbutils import AdbError, AdbDevice, AdbDeviceInfo
import time
import threading
import queue
from typing import Optional, List, Any, Callable

class ADBManager:
    """
    Gerencia a conexão com o servidor ADB e fornece acesso ao primeiro dispositivo 'device' encontrado.
    Inclui sistema de detecção proativa de desconexão do emulador.
    """
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 5037, 
                 socket_timeout: int = 10):
        self._client: Optional[adbutils.AdbClient] = None
        self._device: Optional[AdbDevice] = None
        self._target_serial: Optional[str] = None
        self._is_connected_flag: bool = False
        self._adb_host: str = host
        self._adb_port: int = port
        self._socket_timeout: int = socket_timeout
        
        # Monitoramento de conexão
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor: bool = False
        self._connection_callbacks: List[Callable] = []
        self._disconnect_callbacks: List[Callable] = []
        self._monitor_interval: float = 3.0  # Verificar a cada 3 segundos
        
        print("🤖 ADBManager: Instância criada.")

    def _run_with_timeout(self, func: Callable, timeout: int = 5, *args, **kwargs) -> tuple[bool, Any]:
        """Executa uma função com timeout.
        
        Args:
            func: A função a ser executada
            timeout: Tempo máximo de espera em segundos
            *args, **kwargs: Argumentos para a função
            
        Returns:
            Tupla (sucesso, resultado)
        """
        result_queue = queue.Queue()
        
        def worker():
            try:
                result = func(*args, **kwargs)
                result_queue.put((True, result))
            except Exception as e:
                result_queue.put((False, e))
        
        thread = threading.Thread(target=worker)
        thread.daemon = True  # Thread daemon para não bloquear encerramento
        thread.start()
        
        try:
            return result_queue.get(timeout=timeout)
        except queue.Empty:
            return (False, TimeoutError(f"Operação ADB atingiu o timeout de {timeout}s"))
    
    def connect_first_device(self) -> bool:
        """Tenta conectar ao servidor ADB e ao primeiro dispositivo 'device' encontrado."""
        self._is_connected_flag = False
        self._device = None
        self._target_serial = None

        print(f"🔌 ADB: Conectando ao servidor...")
        try:
            # Cria o cliente ADB com timeout
            success, result = self._run_with_timeout(
                lambda: adbutils.AdbClient(host=self._adb_host, port=self._adb_port, socket_timeout=self._socket_timeout),
                timeout=5
            )
            
            if not success:
                print(f"❌ ADB: Falha na conexão ao criar cliente: {result}")
                self._client = None
                return False
                
            self._client = result
            
            # Verifica a conexão com o servidor (com timeout)
            success, result = self._run_with_timeout(
                lambda: self._client.server_version(),
                timeout=5
            )
            
            if not success:
                print(f"❌ ADB: Falha ao verificar versão do servidor: {result}")
                self._client = None
                return False
                
            server_version = result
            print(f"🔌 ADB: Servidor conectado (v{server_version})")
        except Exception as e:
            print(f"❌ ADB: Falha na conexão: {e}")
            self._client = None
            return False

        try:
            # Lista dispositivos com timeout
            success, result = self._run_with_timeout(
                lambda: self._client.device_list(),
                timeout=5
            )
            
            if not success:
                print(f"❌ ADB: Falha ao listar dispositivos: {result}")
                return False
                
            devices_info: List[AdbDeviceInfo] = result
            selected_device_info: Optional[AdbDeviceInfo] = None

            print(f"🔍 ADB: {len(devices_info)} dispositivo(s) encontrado(s)")

            # Pega o PRIMEIRO dispositivo da lista, ignorando o estado
            if devices_info:
                selected_device_info = devices_info[0]
                print(f"✅ ADB: Selecionando {getattr(selected_device_info, 'serial', 'N/A')}")

            if not selected_device_info:
                print("❌ ADB: Nenhum dispositivo encontrado.")
                return False

            # Tenta obter o objeto AdbDevice para o dispositivo selecionado
            device_serial = getattr(selected_device_info, 'serial', None)
            if not device_serial:
                print("❌ ADB: Dispositivo sem identificador.")
                return False
                
            print(f"📱 ADB: Conectando ao dispositivo {device_serial}...")
            
            # Cria o objeto de dispositivo com timeout
            success, result = self._run_with_timeout(
                lambda: self._client.device(serial=device_serial),
                timeout=5
            )
            
            if not success:
                print(f"❌ ADB: Falha ao criar objeto de dispositivo: {result}")
                return False
                
            self._device = result
            
            # Verifica se o objeto foi criado corretamente
            if isinstance(self._device, AdbDevice):
                # Teste de conexão rápido para verificar se o dispositivo responde
                success, _ = self._run_with_timeout(
                    lambda: self._device.shell("echo test"),
                    timeout=3
                )
                
                if not success:
                    print(f"❌ ADB: Dispositivo não está respondendo")
                    self._device = None
                    return False
                    
                self._target_serial = device_serial
                self._is_connected_flag = True
                print(f"📱✨ ADB: Dispositivo '{self._target_serial}' conectado!")
                return True
            else:
                print(f"❌ ADB: Falha ao conectar ao dispositivo {device_serial}")
                self._device = None
                return False

        except Exception as e:
            print(f"⚠️ ADB: Erro inesperado: {e}")
            return False

    def get_device(self) -> Optional[AdbDevice]:
        """Retorna o objeto AdbDevice conectado, se houver."""
        if self._is_connected_flag and self._device:
            return self._device
        return None

    def get_target_serial(self) -> Optional[str]:
        """Retorna o serial do dispositivo conectado, se houver."""
        return self._target_serial if self._is_connected_flag else None

    def is_connected(self) -> bool:
        """Verifica se a flag de conexão está ativa e tenta uma verificação rápida no dispositivo."""
        # Verificamos primeiro a flag interna para otimizar
        if not (self._is_connected_flag and self._device is not None):
            return False
            
        # Tenta executar um comando leve no dispositivo com timeout
        try:
            success, _ = self._run_with_timeout(
                lambda: self._device.shell("echo test"),
                timeout=2  # Timeout curto para não bloquear
            )
            return success
        except Exception:
            # Qualquer erro indica que o dispositivo não está conectado
            self._is_connected_flag = False
            return False



    def register_connection_callback(self, callback: Callable) -> None:
        """Registra uma função callback chamada quando uma conexão for estabelecida."""
        if callback not in self._connection_callbacks:
            self._connection_callbacks.append(callback)
    
    def register_disconnect_callback(self, callback: Callable) -> None:
        """Registra uma função callback chamada quando uma desconexão for detectada."""
        if callback not in self._disconnect_callbacks:
            self._disconnect_callbacks.append(callback)
    
    def start_connection_monitoring(self) -> None:
        """Inicia o monitoramento da conexão ADB em uma thread separada."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            print("🔔⚠️ ADB Monitor: Monitoramento já está ativo.")
            return
            
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(target=self._connection_monitor_worker, daemon=True)
        self._monitor_thread.start()
        print("🔔✅ ADB Monitor: Monitoramento de conexão iniciado.")
    
    def stop_connection_monitoring(self) -> None:
        """Para o monitoramento da conexão ADB."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            return
            
        self._stop_monitor = True
        self._monitor_thread.join(timeout=2.0)  # Aguarda até 2 segundos para a thread encerrar
        if self._monitor_thread.is_alive():
            print("🔔⚠️ ADB Monitor: Thread de monitoramento não encerrou a tempo.")
        else:
            print("🔔⏹️ ADB Monitor: Monitoramento de conexão encerrado.")
    
    def _connection_monitor_worker(self) -> None:
        """Thread de trabalho que monitora continuamente o estado da conexão ADB."""
        was_connected = self.is_connected()
        
        # Se estiver conectado na inicialização, notifica os callbacks
        if was_connected:
            for callback in self._connection_callbacks:
                try:
                    callback(self._target_serial)
                except Exception as e:
                    print(f"🔔❌ ADB Monitor: Erro ao chamar callback de conexão: {e}")
        
        while not self._stop_monitor:
            try:
                # Verificação de estado atual
                is_connected_now = self.is_connected()
                
                # Detecta mudança de estado
                if is_connected_now != was_connected:
                    if is_connected_now:
                        print(f"🔔📱 ADB Monitor: Conexão detectada com '{self._target_serial}'")
                        # Notifica callbacks de conexão
                        for callback in self._connection_callbacks:
                            try:
                                callback(self._target_serial)
                            except Exception as e:
                                print(f"🔔❌ ADB Monitor: Erro ao chamar callback de conexão: {e}")
                    else:
                        print("🔔⛔ ADB Monitor: Desconexão detectada!")
                        # Notifica callbacks de desconexão
                        for callback in self._disconnect_callbacks:
                            try:
                                callback()
                            except Exception as e:
                                print(f"🔔❌ ADB Monitor: Erro ao chamar callback de desconexão: {e}")
                
                # Atualiza o estado anterior
                was_connected = is_connected_now
                
            except Exception as e:
                print(f"🔔⚠️ ADB Monitor: Erro durante monitoramento: {e}")
            
            # Pausa entre verificações
            time.sleep(self._monitor_interval)
        
        print("🔔🔇 ADB Monitor: Thread de monitoramento encerrada.")

# Adiciona um método find_and_select_device para compatibilidade com o código existente
def find_and_select_device():
    """Compatibilidade com código existente - chama connect_first_device()"""
    return adb_manager.connect_first_device()

# Cria uma instância singleton (única) da classe ADBManager
# Esta instância pode ser importada por outros módulos
adb_manager = ADBManager()

# Adicionado ao singleton para compatibilidade com código existente
adb_manager.find_and_select_device = find_and_select_device

# --- Como usar (Exemplo) ---
if __name__ == "__main__":
    print("--- Testando ADBManager Simplificado ---")
    # Usa o singleton em vez de criar uma nova instância
    if adb_manager.connect_first_device():
        print("\nTeste: Conexão bem-sucedida!")
        device = adb_manager.get_device()
        serial = adb_manager.get_target_serial()
        if device and serial:
            print(f"  Serial: {serial}")
            try:
                props = device.prop.list()
                print(f"  Propriedades obtidas (contagem: {len(props)})")
                model = device.prop.get('ro.product.model')
                print(f"  Modelo (ro.product.model): {model}")
            except Exception as e:
                print(f"  Erro ao obter propriedades: {e}")
        else:
            print("  Erro: Não foi possível obter o objeto device ou serial após conexão.")
    else:
        print("\nTeste: Falha ao conectar ao primeiro dispositivo 'device'.")

    print("--- Fim do Teste ---")