# Guia Detalhado do Sistema do Kit Terra

## Introdução

O Kit Terra é um sistema automatizado que ajuda a gerenciar as operações relacionadas à terra e à fazenda dentro do jogo HayDay. Este documento explica em detalhes como o sistema funciona, com foco nas funções principais e no fluxo de ações, de forma simples e fácil de entender para pessoas que não são programadoras.

## O que o Kit Terra faz?

O Kit Terra é projetado para automatizar tarefas repetitivas, como:
- Localizar a banca na sua fazenda
- Verificar quais caixas estão vazias
- Ajudar a preencher essas caixas com produtos para venda

## Como está estruturado o sistema

O sistema do Kit Terra é composto por dois arquivos principais:

1. **kit_terra.py**: Contém todo o código que executa as ações do sistema
2. **kit_terraCFG.json**: Contém as configurações e definições de como o sistema deve se comportar

Vamos entender cada um deles em detalhe:

## kit_terra.py - O cérebro do sistema

Este arquivo contém todas as funções que fazem o Kit Terra funcionar. Vamos explicar cada função importante:

### 1. load_config()

Esta função é responsável por carregar as configurações do arquivo JSON. É como se ela lesse o "manual de instruções" do sistema para saber o que fazer.

**O que ela faz:**
- Lê o arquivo kit_terraCFG.json
- Carrega todas as configurações necessárias
- Informa ao usuário que a configuração foi carregada

### 2. on_state_change_during_execution()

Esta função monitora as mudanças de estado durante a execução. Pense nela como um "vigilante" que fica atento para saber em qual parte do jogo você está.

**O que ela faz:**
- Detecta quando o estado do jogo muda
- Registra o novo estado
- Se detectar o tutorial de colheita, reinicia a execução
- Informa o usuário sobre a mudança de estado

### 3. scan_empty_boxes()

Esta é uma função muito importante que verifica quais caixas da loja estão vazias e também identifica caixas vendidas para coletar moedas automaticamente.

**O que ela faz:**
- Tira uma "foto" da tela atual do jogo
- Verifica cada caixa individualmente
- Para cada caixa, primeiro verifica se está vendida:
  - Se encontrar uma caixa vendida, clica nela para coletar as moedas automaticamente
  - Após coletar as moedas, considera a caixa como vazia
- Se a caixa não estiver vendida, verifica se está vazia
- Compara cada caixa com imagens de "caixa vendida" e "caixa vazia"
- Cria uma lista com os números das caixas vazias (incluindo as que foram coletadas)
- Informa quais caixas estão vazias, quais estão ocupadas e quais estavam vendidas

### 4. execute_action()

Esta função é como um "intérprete" que executa diferentes tipos de ações com base nas instruções recebidas.

**O que ela faz:**
- Lê o tipo de ação a ser executada (clique, espera, busca de imagem, etc.)
- Obtém os parâmetros necessários para aquela ação
- Executa a ação solicitada
- Retorna se a ação foi bem-sucedida ou não

### 5. search_template()

Esta função busca uma imagem específica na tela do jogo.

**O que ela faz:**
- Tira uma "foto" da tela atual
- Procura por uma imagem específica dentro dessa foto
- Se encontrar, clica naquele ponto
- Tenta várias vezes, se necessário
- Informa o resultado da busca (encontrado ou não)

### 6. run()

Esta é a função principal que controla todo o fluxo do Kit Terra.

**O que ela faz:**
- Registra um monitor para acompanhar mudanças de estado
- Carrega a configuração
- Define a sequência de estados a serem seguidos
- Executa as ações para cada estado
- Verifica caixas vazias
- Se reinicia quando necessário
- Informa o resultado final da operação

## kit_terraCFG.json - O manual de instruções

Este arquivo contém todas as configurações que o Kit Terra precisa para funcionar. Ele é organizado da seguinte forma:

### 1. Seção "states" (estados)

Define diferentes estados do jogo e quais ações realizar em cada um deles:

- **jogo_aberto**: Quando o jogo está na tela principal
  - Busca pela banca (usando uma imagem dela)
  - Espera um pouco após encontrá-la

- **inside_shop**: Quando está dentro da loja/banca
  - Verifica quais caixas estão vazias

- **book_interface**: Quando está na interface do livro
  - Clica para fechar o livro
  - Busca pela banca novamente
  - Espera um pouco

- **menu_add_client**: Quando aparece o menu para adicionar cliente
  - Fecha esse menu
  - Fecha a interface do livro
  - Busca pela banca novamente
  - Espera um pouco

- **item_shop_list**: Quando aparece a lista de itens da loja
  - Fecha essa lista
  - Espera um pouco

- **fazenda_cliente**: Quando está visitando a fazenda de outro jogador
  - Clica para voltar à fazenda principal
  - Espera um pouco
  - Verifica se voltou para a tela principal ou para o livro

### 2. Seção "box_positions"

Define as coordenadas (posição na tela) de cada uma das 10 caixas da loja. Isso permite que o sistema saiba exatamente onde clicar para interagir com cada caixa.

### 3. Seção "box_detection"

Contém informações para detectar caixas vazias:

- **individual_roi**: Define a área específica de cada caixa para verificação
- **full_area_roi**: Define a área completa que contém todas as caixas

## Como o sistema funciona na prática

1. **Inicialização**: 
   - O sistema carrega as configurações do arquivo JSON
   - Registra um monitor para detectar mudanças de estado

2. **Localização da banca**:
   - Procura pela imagem da banca na tela
   - Clica na banca quando a encontra

3. **Verificação de caixas vazias**:
   - Depois de entrar na banca, verifica quais caixas estão vazias
   - Cria uma lista com os números das caixas vazias

4. **Navegação entre estados**:
   - O sistema sabe lidar com diferentes situações do jogo
   - Se aparecer o menu do livro, ele fecha e volta para a banca
   - Se estiver na fazenda de outro jogador, volta para a fazenda principal

5. **Tratamento de erros**:
   - Se encontrar o tutorial de colheita, reinicia a execução
   - Se não conseguir concluir uma ação após várias tentativas, informa o erro

## Resumo

O Kit Terra é um sistema inteligente que ajuda a gerenciar a banca/loja no jogo HayDay, automatizando tarefas repetitivas. Ele usa reconhecimento de imagem para identificar elementos na tela e executar ações como cliques e esperas de acordo com o estado atual do jogo.

O arquivo kit_terra.py contém as funções que fazem o sistema funcionar, enquanto o arquivo kit_terraCFG.json define as configurações, como posições de clique e imagens a serem procuradas.

Este sistema foi projetado para ser eficiente e capaz de lidar com diferentes situações que podem ocorrer durante o jogo, como popups, menus inesperados e mudanças de estado.
