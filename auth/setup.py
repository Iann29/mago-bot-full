"""
Setup script for initializing the Supabase database for HayDay Bot authentication.
This script creates the necessary tables and inserts the predefined users.
"""

import os
import sys
import argparse
import requests

# Adiciona a raiz do projeto ao PYTHONPATH para garantir importações corretas
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from auth.supabase_auth import SupabaseAuth
from auth.config import SUPABASE_URL, SUPABASE_KEY


def setup_database():
    """
    Verificar a conexão com o Supabase e testar a estrutura do banco de dados.
    
    Returns:
        bool: True se a verificação foi bem-sucedida, False caso contrário
    """
    print("Inicializando setup de autenticação do Supabase...")
    
    # Verificar se URL e chave do Supabase estão configuradas
    if SUPABASE_URL == "https://YOUR_SUPABASE_PROJECT_URL.supabase.co" or SUPABASE_KEY == "YOUR_SUPABASE_API_KEY":
        print("Erro: URL e chave do Supabase não foram configuradas.")
        print("Por favor, atualize o arquivo auth/config.py com suas credenciais do Supabase.")
        return False
    
    # Inicializar o manipulador de autenticação do Supabase
    auth_handler = SupabaseAuth(SUPABASE_URL, SUPABASE_KEY)
    
    # Verificar conexão testando busca por um usuário
    print("\nTestando conexão com o Supabase...")
    
    endpoint = f"{SUPABASE_URL}/rest/v1/users"
    headers = auth_handler.headers
    params = {"limit": 1}
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        print(f"Resposta do Supabase (código {response.status_code}):")
        print(response.text)
        
        if response.status_code == 200:
            print("\n✓ Conexão com Supabase estabelecida com sucesso!")
            
            # Verificar resultado para entender a estrutura da resposta
            result = response.json()
            print(f"\nEstrutura da resposta: {type(result)}")
            
            if isinstance(result, list):
                if result:
                    print(f"\nExemplo de registro encontrado:")
                    for key, value in result[0].items():
                        print(f"  {key}: {value}")
                    return True
                else:
                    print("\nNenhum registro encontrado na tabela. Verifique se existem usuários registrados.")
                    print("Considere executar o SQL fornecido para criar os usuários.")
            else:
                print(f"\nEstrutura inesperada de resposta: {result}")
                print("Verifique a estrutura da tabela no Supabase.")
        else:
            print(f"\n⚠️ Erro ao acessar a tabela: {response.text}")
            print("Verifique se a tabela 'users' existe ou se as permissões estão corretas.")
            print("\nLembre-se de executar o SQL fornecido para criar as tabelas e usuários.")
    except Exception as e:
        print(f"\n⚠️ Erro ao conectar: {str(e)}")
        return False
    
    print("\nObs: Os seguintes usuários devem existir na tabela:")
    print("Username: ian | Password: abacaxi | HTML ID: screen-ian")
    print("Username: matheus | Password: morango | HTML ID: screen-matheus")
    print("Username: andi | Password: banana | HTML ID: screen-andi")
    print("Username: giovani | Password: laranja | HTML ID: screen-giovani")
    print("Username: julio | Password: uva | HTML ID: screen-julio")
    print("Username: pedro | Password: manga | HTML ID: screen-pedro")
    print("Username: vini | Password: kiwi | HTML ID: screen-vini")
    print("Username: dumbdummy | Password: melancia | HTML ID: screen-dumbdummy")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Supabase authentication for HayDay Bot")
    parser.add_argument("--force", action="store_true", help="Force recreation of tables")
    args = parser.parse_args()
    
    success = setup_database()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
