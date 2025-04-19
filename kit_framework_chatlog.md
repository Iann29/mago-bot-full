# Chatlog do Framework de Gerenciamento de Kits

## Objetivo do Framework

Criar um sistema modular para gerenciar a venda de kits no HayDay com as seguintes características:
- Separar a lógica genérica de preenchimento de caixas (framework) da configuração específica de cada kit
- Reaproveitar ao máximo o código existente
- Criar um sistema flexível que possa ser usado para diferentes kits

## Definição de um Kit

Um kit no HayDay é um conjunto de 3 tipos diferentes de itens, totalizando 89 itens, distribuídos em 9 caixas:
- Primeira caixa: 9 unidades do primeiro item
- Demais caixas: 10 unidades de cada item (3 caixas para cada tipo de item)

Exemplo do Kit Terra:
- **Estacas**: 29 unidades (9 + 10 + 10) - Caixas 1, 2 e 3
- **Marretas**: 30 unidades (10 + 10 + 10) - Caixas 4, 5 e 6
- **Escrituras**: 30 unidades (10 + 10 + 10) - Caixas 7, 8 e 9

## Fluxo de Preenchimento das Caixas

1. Clicar na caixa vazia
2. Aguardar 50ms
3. Clicar na posição (140, 231) para abrir o menu de itens
4. Buscar e identificar o item correto no ROI: [170, 146, 174, 208]
5. Clicar no item para selecioná-lo
6. Verificar a quantidade no ROI: [363, 156, 122, 43]
   - Se for a primeira caixa: ajustar para 9 unidades
   - Para as demais: ajustar para 10 unidades
   - Botão para diminuir: (378, 173)
   - Botão para aumentar: (466, 172)
7. Clicar em preço máximo: (401, 242)
8. Clicar em vender: (419, 354)
9. Passar para a próxima caixa vazia

## Funções Existentes a Serem Reutilizadas

- `cerebro/emulatorInteractFunction.py`: Funções para interação com o emulador
  - `click(x, y, duration)`: Realizar cliques
  - `wait(seconds)`: Aguardar tempo específico
  - Outras funções úteis já implementadas

- `screenVision/templateMatcher.py`: Para reconhecimento de imagens
  - Busca de templates na tela
  - Identificação de quantidades

## Estrutura Proposta

1. **Framework Principal** (`cerebro/kit_manager.py`):
   - Função `fill_box(box_index, item_config)`: Para preencher uma caixa específica
   - Função `identify_item(roi, template_path)`: Para identificar um item na tela
   - Função `adjust_quantity(target_quantity)`: Para ajustar a quantidade do item
   - Função `process_kit(kit_config)`: Para processar um kit completo

2. **Configuração de Kit** (`execution/kit_terra_items.json`):
   - Definição dos itens: caminhos das imagens dos templates
   - Quantidades por caixa
   - Mapeamento de itens para caixas

3. **Integração com o Kit Terra** (`execution/kit_terra.py`):
   - Após verificar caixas vazias, chamar o framework para preenchimento

## Pontos de Atenção

- Garantir tratamento de erro robusto para cada etapa
- Verificar se o item foi corretamente selecionado antes de prosseguir
- Implementar verificação de estado após cada ação importante
- Caixas ocupadas: pular para a próxima caixa disponível sem alterar o fluxo dos itens
- Sistema deve ser flexível para diferentes kits com diferentes itens

## Próximos Passos

1. Criar o arquivo `cerebro/kit_manager.py` com as funções principais
2. Criar o exemplo de configuração para o Kit Terra
3. Modificar o `execution/kit_terra.py` para usar o novo framework
4. Testar o fluxo completo com o Kit Terra
