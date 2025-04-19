"""
# Fluxo de Funcionamento do Kit Terra

O diagrama abaixo mostra o fluxo completo da execução do Kit Terra, desde o início até a conclusão, incluindo a verificação e coleta de caixas vendidas.

```mermaid
flowchart TD
    Start([Iniciar Kit Terra]) --> RegisterCallback{Registrar callback\nde estado}
    RegisterCallback --> GetCurrentState[Obter estado atual do jogo]
    
    GetCurrentState --> CheckState{Verificar estado\ndo jogo}
    
    %% Diferentes estados e suas ações
    CheckState -- jogo_aberto --> SearchRoadside[Buscar banca\ncom máscara]
    CheckState -- book_interface --> CloseBook[Fechar interface\ndo livro]
    CheckState -- menu_add_client --> CloseMenu[Fechar menu\nde cliente]
    CheckState -- item_shop_list --> CloseList[Fechar lista\nde itens]
    CheckState -- fazenda_cliente --> ReturnHome[Voltar para\nfazenda principal]
    CheckState -- inside_shop --> ShopActions[Executar ações\nna loja]
    
    %% Fluxo após ações em diferentes estados
    SearchRoadside --> WaitForStateChange[Aguardar mudança\nde estado]
    CloseBook --> SearchRoadside
    CloseMenu --> CloseBook
    CloseList --> WaitForStateChange
    ReturnHome --> CheckBookOrMain[Verificar se voltou\npara o livro ou\nfazenda principal]
    
    WaitForStateChange --> CheckNewState{Estado\nmudou?}
    CheckNewState -- Sim --> CheckIfShop{Novo estado\né a loja?}
    CheckNewState -- Não --> CheckState
    
    CheckIfShop -- Sim --> ShopActions
    CheckIfShop -- Não --> CheckState
    
    %% Ações na loja
    ShopActions --> ScanEmptyBoxes[Verificar caixas]
    
    %% Lógica de verificação das caixas
    ScanEmptyBoxes --> CheckEachBox[Verificar cada\ncaixa individualmente]
    
    CheckEachBox --> CheckIfSold{Caixa\nvendida?}
    
    CheckIfSold -- Sim --> CollectCoins[Coletar moedas\nda caixa]
    CheckIfSold -- Não --> CheckIfEmpty{Caixa\nvazia?}
    
    CollectCoins --> MarkAsEmpty[Marcar como\ncaixa vazia]
    CheckIfEmpty -- Sim --> MarkAsEmpty
    CheckIfEmpty -- Não --> MarkAsOccupied[Marcar como\ncaixa ocupada]
    
    MarkAsEmpty --> NextBox{Próxima\ncaixa?}
    MarkAsOccupied --> NextBox
    
    NextBox -- Sim --> CheckEachBox
    NextBox -- Não --> RemoveCallback[Remover callback\nde estado]
    
    RemoveCallback --> FinishKitTerra([Kit Terra\nconcluído])
    
    %% Tratamento de erros
    subgraph "Tratamento de Erros"
        Error([Erro detectado]) --> RemoveCallbackError[Remover callback\nde estado]
        RemoveCallbackError --> ReturnError([Retornar erro])
    end
    
    %% Monitoramento de estado durante a execução
    subgraph "Monitoramento Contínuo de Estado"
        StateCallback[Callback de\nmudança de estado] --> CheckTutorial{Tutorial\ndetectado?}
        CheckTutorial -- Sim --> RestartExecution[Reiniciar execução]
        CheckTutorial -- Não --> UpdateStateInfo[Atualizar informações\nde estado]
    end
```

## Explicação do Fluxo

1. **Inicialização**:
   - O Kit Terra inicia e registra um callback para monitorar mudanças de estado
   - Obtém o estado atual do jogo

2. **Navegação entre Estados**:
   - Dependendo do estado atual, executa ações específicas:
     - Na fazenda principal (jogo_aberto): Busca pela banca
     - Na interface do livro (book_interface): Fecha o livro e busca pela banca
     - No menu de cliente (menu_add_client): Fecha o menu, fecha o livro e busca pela banca
     - Na lista de itens (item_shop_list): Fecha a lista
     - Na fazenda de cliente (fazenda_cliente): Volta para a fazenda principal

3. **Verificação de Caixas na Loja**:
   - Quando chega à loja (inside_shop), verifica cada caixa individualmente
   - Para cada caixa:
     - Primeiro verifica se está vendida
     - Se estiver vendida, coleta as moedas automaticamente
     - Se não estiver vendida, verifica se está vazia
     - Cria uma lista das caixas vazias (incluindo as que foram coletadas)

4. **Finalização**:
   - Remove o callback de estado
   - Conclui a execução do Kit Terra

5. **Monitoramento Contínuo**:
   - Durante toda a execução, monitora mudanças de estado
   - Se detectar o tutorial de colheita, reinicia a execução
"""

# Fluxo de Funcionamento do Kit Terra

O diagrama abaixo mostra o fluxo completo da execução do Kit Terra, desde o início até a conclusão, incluindo a verificação e coleta de caixas vendidas.

```mermaid
flowchart TD
    Start([Iniciar Kit Terra]) --> RegisterCallback{Registrar callback\nde estado}
    RegisterCallback --> GetCurrentState[Obter estado atual do jogo]
    
    GetCurrentState --> CheckState{Verificar estado\ndo jogo}
    
    %% Diferentes estados e suas ações
    CheckState -- jogo_aberto --> SearchRoadside[Buscar banca\ncom máscara]
    CheckState -- book_interface --> CloseBook[Fechar interface\ndo livro]
    CheckState -- menu_add_client --> CloseMenu[Fechar menu\nde cliente]
    CheckState -- item_shop_list --> CloseList[Fechar lista\nde itens]
    CheckState -- fazenda_cliente --> ReturnHome[Voltar para\nfazenda principal]
    CheckState -- inside_shop --> ShopActions[Executar ações\nna loja]
    
    %% Fluxo após ações em diferentes estados
    SearchRoadside --> WaitForStateChange[Aguardar mudança\nde estado]
    CloseBook --> SearchRoadside
    CloseMenu --> CloseBook
    CloseList --> WaitForStateChange
    ReturnHome --> CheckBookOrMain[Verificar se voltou\npara o livro ou\nfazenda principal]
    
    WaitForStateChange --> CheckNewState{Estado\nmudou?}
    CheckNewState -- Sim --> CheckIfShop{Novo estado\né a loja?}
    CheckNewState -- Não --> CheckState
    
    CheckIfShop -- Sim --> ShopActions
    CheckIfShop -- Não --> CheckState
    
    %% Ações na loja
    ShopActions --> ScanEmptyBoxes[Verificar caixas]
    
    %% Lógica de verificação das caixas
    ScanEmptyBoxes --> CheckEachBox[Verificar cada\ncaixa individualmente]
    
    CheckEachBox --> CheckIfSold{Caixa\nvendida?}
    
    CheckIfSold -- Sim --> CollectCoins[Coletar moedas\nda caixa]
    CheckIfSold -- Não --> CheckIfEmpty{Caixa\nvazia?}
    
    CollectCoins --> MarkAsEmpty[Marcar como\ncaixa vazia]
    CheckIfEmpty -- Sim --> MarkAsEmpty
    CheckIfEmpty -- Não --> MarkAsOccupied[Marcar como\ncaixa ocupada]
    
    MarkAsEmpty --> NextBox{Próxima\ncaixa?}
    MarkAsOccupied --> NextBox
    
    NextBox -- Sim --> CheckEachBox
    NextBox -- Não --> RemoveCallback[Remover callback\nde estado]
    
    RemoveCallback --> FinishKitTerra([Kit Terra\nconcluído])
    
    %% Tratamento de erros
    subgraph "Tratamento de Erros"
        Error([Erro detectado]) --> RemoveCallbackError[Remover callback\nde estado]
        RemoveCallbackError --> ReturnError([Retornar erro])
    end
    
    %% Monitoramento de estado durante a execução
    subgraph "Monitoramento Contínuo de Estado"
        StateCallback[Callback de\nmudança de estado] --> CheckTutorial{Tutorial\ndetectado?}
        CheckTutorial -- Sim --> RestartExecution[Reiniciar execução]
        CheckTutorial -- Não --> UpdateStateInfo[Atualizar informações\nde estado]
    end
```

## Explicação do Fluxo

1. **Inicialização**:
   - O Kit Terra inicia e registra um callback para monitorar mudanças de estado
   - Obtém o estado atual do jogo

2. **Navegação entre Estados**:
   - Dependendo do estado atual, executa ações específicas:
     - Na fazenda principal (jogo_aberto): Busca pela banca
     - Na interface do livro (book_interface): Fecha o livro e busca pela banca
     - No menu de cliente (menu_add_client): Fecha o menu, fecha o livro e busca pela banca
     - Na lista de itens (item_shop_list): Fecha a lista
     - Na fazenda de cliente (fazenda_cliente): Volta para a fazenda principal

3. **Verificação de Caixas na Loja**:
   - Quando chega à loja (inside_shop), verifica cada caixa individualmente
   - Para cada caixa:
     - Primeiro verifica se está vendida
     - Se estiver vendida, coleta as moedas automaticamente
     - Se não estiver vendida, verifica se está vazia
     - Cria uma lista das caixas vazias (incluindo as que foram coletadas)

4. **Finalização**:
   - Remove o callback de estado
   - Conclui a execução do Kit Terra

5. **Monitoramento Contínuo**:
   - Durante toda a execução, monitora mudanças de estado
   - Se detectar o tutorial de colheita, reinicia a execução
