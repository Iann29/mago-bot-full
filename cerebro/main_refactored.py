# /cerebro/main_refactored.py
# Versão refatorada e modular do arquivo main.py original

import sys

from cerebro.app import start_app_with_auth

def main():
    """Função principal de entrada do programa."""
    print("--- Iniciando HayDay Test Tool ---")
    
    try:
        # Inicia a aplicação com autenticação
        exit_code = start_app_with_auth()
        return exit_code
    except Exception as e:
        print(f"Erro crítico na aplicação: {e}")
        return 1

if __name__ == "__main__":
    # Executa a função principal e usa o código de saída retornado
    sys.exit(main())