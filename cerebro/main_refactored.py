# /cerebro/main_refactored.py
# Versão refatorada e modular do arquivo main.py original

import sys

# Remove import for start_app_with_auth
# from cerebro.app import start_app_with_auth 
# Import run_main_app directly
from cerebro.app import run_main_app, cleanup_app 

def main():
    """Função principal de entrada do programa."""
    print("--- Iniciando HayDay Test Tool ---")
    
    exit_code = 1 # Default exit code in case of error before running app
    try:
        # Call run_main_app directly, skipping authentication
        # exit_code = start_app_with_auth()
        exit_code = run_main_app() # Pass no user data
    except Exception as e:
        print(f"Erro crítico na aplicação: {e}")
        exit_code = 1 # Ensure error code is set
    finally:
        # Ensure cleanup happens even if run_main_app crashes
        cleanup_app()
        
    return exit_code

if __name__ == "__main__":
    # Executa a função principal e usa o código de saída retornado
    sys.exit(main())