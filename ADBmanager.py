# /ADBmanager.py

import adbutils
from adbutils import AdbError, AdbDevice, AdbDeviceInfo
import time
from typing import Optional, List

class ADBManager:
    """
    Gerencia a conexão com o servidor ADB e fornece acesso ao primeiro dispositivo 'device' encontrado.
    Versão simplificada.
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
        print("ADBManager: Instância criada (versão simplificada).")

    def connect_first_device(self) -> bool:
        """Tenta conectar ao servidor ADB e ao primeiro dispositivo 'device' encontrado."""
        self._is_connected_flag = False
        self._device = None
        self._target_serial = None

        print(f"ADBManager: Conectando ao servidor ADB em {self._adb_host}:{self._adb_port}...")
        try:
            # Tenta criar o cliente adb (CORRIGIDO: AdbClient)
            self._client = adbutils.AdbClient(host=self._adb_host, port=self._adb_port, socket_timeout=self._socket_timeout)
            # Verifica a conexão com o servidor
            server_version = self._client.server_version()
            print(f"ADBManager: Conectado ao servidor ADB (Versão: {server_version}).")
        except Exception as e:
            print(f"ADBManager: Falha ao conectar/verificar servidor ADB: {e}")
            self._client = None
            return False

        print("ADBManager: Listando dispositivos...")
        try:
            devices_info: List[AdbDeviceInfo] = self._client.device_list()
            selected_device_info: Optional[AdbDeviceInfo] = None

            print(f"ADBManager: Dispositivos brutos encontrados: {[(getattr(d, 'serial', 'N/A'), getattr(d, 'state', 'Sem Estado')) for d in devices_info]}")

            # Pega o PRIMEIRO dispositivo da lista, ignorando o estado
            if devices_info:
                selected_device_info = devices_info[0]
                print(f"ADBManager: Selecionando o primeiro dispositivo encontrado: {getattr(selected_device_info, 'serial', 'N/A')}")
            # Removido o loop que procurava por d_info.state == 'device'
            # Removida a verificação 'hasattr(d_info, 'state')'

            if not selected_device_info:
                print("ADBManager: Nenhum dispositivo encontrado na lista.")
                return False

            # Tenta obter o objeto AdbDevice para o dispositivo selecionado
            device_serial = getattr(selected_device_info, 'serial', None)
            if not device_serial:
                print("ADBManager: Erro - Dispositivo selecionado não possui atributo 'serial'.")
                return False
                
            print(f"ADBManager: Tentando obter objeto AdbDevice para {device_serial}...")
            try:
                self._device = self._client.device(serial=device_serial)
                # Verifica se o objeto foi criado corretamente (opcional, mas bom)
                if isinstance(self._device, AdbDevice):
                    self._target_serial = device_serial
                    self._is_connected_flag = True
                    print(f"ADBManager: Conexão estabelecida com sucesso para '{self._target_serial}'.")
                    return True
                else:
                    print(f"ADBManager: Falha ao obter objeto AdbDevice válido para {device_serial}.")
                    self._device = None
                    return False
            except AdbError as connect_err:
                print(f"ADBManager: Erro ADB ao obter AdbDevice para {device_serial}: {connect_err}")
                self._device = None
                return False
            except Exception as connect_e:
                print(f"ADBManager: Erro inesperado ao obter AdbDevice para {device_serial}: {connect_e}")
                self._device = None
                return False

        except AdbError as list_err:
            print(f"ADBManager: Erro ADB ao listar dispositivos: {list_err}")
            return False
        except AttributeError as ae:
             # Captura o erro específico se ainda ocorrer ao acessar 'state'
             print(f"ADBManager: ERRO DE ATRIBUTO ('{ae}') ao processar lista de dispositivos. Verifique a versão do adbutils ou a saída do ADB.")
             # Imprime infos para debug
             try: print(f"ADBManager: Informações brutas dos dispositivos: {devices_info}")
             except: print("ADBManager: Não foi possível imprimir informações brutas dos dispositivos.")
             return False
        except Exception as list_e:
            print(f"ADBManager: Erro inesperado ao listar/processar dispositivos: {list_e}")
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
        """Verifica se a flag de conexão está ativa (não faz verificação real no dispositivo)."""
        # Nota: Esta verificação é simples, baseada no sucesso da última tentativa de conexão.
        # Uma verificação mais robusta poderia tentar um comando leve no self._device.
        return self._is_connected_flag and self._device is not None

# Cria uma instância singleton (única) da classe ADBManager
# Esta instância pode ser importada por outros módulos
adb_manager = ADBManager()

# Adiciona um método find_and_select_device para compatibilidade com o código existente
def find_and_select_device():
    """Compatibilidade com código existente - chama connect_first_device()"""
    return adb_manager.connect_first_device()

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