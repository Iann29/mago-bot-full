"""
Script de teste para verificar se os comandos ADB funcionam diretamente.
"""
import time
import adbutils

print("== Teste de conexão ADB e cliques ==")

try:
    # Conecta ao servidor ADB
    print("Conectando ao servidor ADB...")
    adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
    print(f"Versão do servidor ADB: {adb.server_version()}")
    
    # Lista dispositivos
    print("\nDispositivos conectados:")
    device_list = adb.device_list()
    for i, d in enumerate(device_list):
        print(f"{i+1}. {d.serial}")
    
    if not device_list:
        print("Nenhum dispositivo encontrado!")
        exit(1)
    
    # Seleciona o primeiro dispositivo
    device = device_list[0]
    print(f"\nUsando dispositivo: {device.serial}")
    
    # Obtém informações sobre o dispositivo
    info = device.info
    print(f"Modelo: {info.get('model', 'Desconhecido')}")
    print(f"Fabricante: {info.get('manufacturer', 'Desconhecido')}")
    
    # Tenta obter o tamanho da tela
    try:
        wm_size = device.shell("wm size").strip()
        print(f"Tamanho da tela: {wm_size}")
    except Exception as e:
        print(f"Erro ao obter tamanho da tela: {e}")
    
    # Teste de clique usando diferentes métodos
    print("\n== Teste de cliques ==")
    
    # Método 1: input tap (shell command)
    print("\nMétodo 1: Shell command 'input tap'")
    print("Clicando na posição (300, 300)...")
    result = device.shell("input tap 300 300")
    print(f"Resultado: {result or 'Comando executado'}")
    time.sleep(1)
    
    # Método 2: usando o método click do adbutils
    print("\nMétodo 2: Usando device.click() do adbutils")
    print("Clicando na posição (400, 400)...")
    try:
        device.click(400, 400)
        print("Click executado via device.click()")
    except Exception as e:
        print(f"Erro ao executar device.click(): {e}")
    time.sleep(1)
    
    # Teste adicional com shell e events diretamente
    print("\nMétodo 3: Teste com sendevent diretamente")
    print("Tentando enviar eventos de toque diretamente...")
    try:
        # Este método pode variar dependendo do dispositivo
        device.shell("sendevent /dev/input/event1 3 57 14")
        device.shell("sendevent /dev/input/event1 3 53 500") # X position
        device.shell("sendevent /dev/input/event1 3 54 500") # Y position
        device.shell("sendevent /dev/input/event1 3 58 50")  # Pressure
        device.shell("sendevent /dev/input/event1 0 0 0")    # Sync
        device.shell("sendevent /dev/input/event1 3 57 4294967295")
        device.shell("sendevent /dev/input/event1 0 0 0")    # Sync
        print("Eventos enviados via sendevent")
    except Exception as e:
        print(f"Erro ao enviar eventos: {e}")
    
    print("\nTeste concluído. Verifique se algum dos métodos funcionou no emulador.")
    
except Exception as e:
    print(f"Erro durante o teste: {e}")
