# Resumo do Projeto HayDay Test Tool

## Visão Geral
Este projeto é uma ferramenta de automação e teste para o jogo HayDay em dispositivos Android. Utiliza técnicas de visão computacional para reconhecer elementos na tela do dispositivo, permitindo automatizar interações e testes.

## Arquitetura do Sistema

### Módulos Principais

1. **ADBManager (ADBmanager.py)**
   - Gerencia a conexão com dispositivos Android via ADB (Android Debug Bridge)
   - Implementa um design Singleton para garantir uma única instância de conexão ADB em todo o projeto
   - Responsável por encontrar, conectar e gerenciar dispositivos

2. **ScreenVision**
   - **screenshotMain.py**: Captura screenshots do dispositivo Android
   - **templateMatcher.py**: Utiliza OpenCV para encontrar templates (imagens de referência) na tela
   - **maskedTemplateMatcher.py**: Versão avançada do template matcher que suporta máscaras
   - **screenshotCFG.json**: Configuração centralizada para os parâmetros de captura e debug

3. **Execution**
   - **template.py**: Implementa testes práticos, como buscar templates específicos em screenshots
   - **testnew.py**: Implementa teste com máscaras para reconhecimento avançado de templates

4. **StateManager**
   - **stateManager.py**: Gerencia os estados do jogo baseado na detecção das imagens de referência
   - Utiliza a thread de captura existente para analisar os estados em tempo real
   - Sistema de callbacks para notificar mudanças de estado

5. **Interface Gráfica (main.py)**
   - Interface Tkinter para interação do usuário
   - Gerencia uma thread contínua de captura de screenshots 
   - Fornece funcionalidades para testar reconhecimento de templates
   - Exibe o estado atual do jogo detectado pelo StateManager

## Funcionalidades Principais

### Captura Contínua de Screenshots
- Sistema assíncrono que captura screenshots em intervalos regulares
- Configurado para trabalhar a um FPS específico (atualmente 1 fps)
- Executa em uma thread separada, permitindo que a interface continue responsiva

### Reconhecimento de Templates
- Busca imagens de referência (templates) dentro dos screenshots capturados
- Suporta regiões de interesse (ROI) para limitar a busca a áreas específicas
- Retorna posição e nível de confiança quando um template é encontrado
- Suporte para templates com máscaras para reconhecimento avançado

### Gerenciamento de Estados
- Detecção automática do estado atual do jogo baseado em imagens de referência
- Monitoramento contínuo em thread separada utilizando os screenshots capturados
- Sistema de notificação de mudanças de estado via callbacks
- Suporte para expansão com novos estados e ações específicas para cada estado

### Interface Gráfica
- Permite iniciar/parar a captura de screenshots
- Monitora o status da thread de captura
- Fornece botões para executar testes de reconhecimento específicos
- Exibe o estado atual do jogo e o tempo de permanência nesse estado

### Modo Debug
- Quando ativado, salva screenshots em um diretório configurável
- Facilita o desenvolvimento e a depuração do processo de reconhecimento

## Modificações Recentes

### Correções de Integração
1. **Refatoração do ADBManager**
   - Implementado o padrão Singleton para compartilhar a conexão ADB entre módulos
   - Adicionados métodos auxiliares para verificar o estado da conexão

2. **Integração da Interface Gráfica**
   - Adicionada uma interface Tkinter para facilitar o uso do sistema
   - Implementação de um sistema de atualização em tempo real para monitorar a thread de captura

3. **Melhorias na Estrutura de Threading**
   - Reorganização da lógica de threads para evitar bloqueios e condições de corrida
   - Implementação adequada de sinalizadores para encerramento limpo das threads

4. **Correções de Erro**
   - Resolvidos problemas de referência a variáveis globais
   - Corrigida a estrutura do código para evitar erros de lint e melhorar a legibilidade
   - Implementada verificação correta do estado do ADB antes da execução de operações críticas

5. **Melhorias no Screenshotter**
   - Modificado para utilizar a instância singleton do ADBManager quando necessário
   - Adicionado suporte para o modo debug que salva screenshots para análise

6. **Módulo de Template Matching Aprimorado**
   - Renomeado de test.py para template.py para melhor refletir sua funcionalidade
   - Criado arquivo de configuração separado (templateCFG.json) com propriedades independentes
   - Implementada visualização de bounding boxes nos resultados de reconhecimento
   - Reestruturado para expor uma API mais flexível com a função find_template()
   - Corrigido o problema de duplicação de logs usando um modo silencioso quando chamado por outros módulos

## Modificações Recentes

### Implementação do StateManager
1. **Novo Módulo de Gerenciamento de Estados**
   - Criado o módulo `stateManager` para detectar e monitorar estados do jogo
   - Implementado enumeração `GameState` para representar diferentes estados do jogo
   - Integração com o sistema de captura de screenshots existente

2. **Detecção Inteligente de Estados**
   - Utiliza template matching para identificar estados a partir de imagens de referência
   - Configuração ajustável de limiares de confiança e intervalos de verificação
   - Sistema robusto de notificação de mudanças via callbacks

3. **Integração com a Interface Gráfica**
   - Adicionado painel na interface para exibir o estado atual e tempo de permanência
   - Notificação visual no log quando ocorrem mudanças de estado
   - Gerenciamento limpo das threads e recursos ao fechar a aplicação

### Melhorias no Template Matching
1. **Implementação de Template Matching com Máscaras**
   - Criado `MaskedTemplateMatcher` para reconhecimento mais preciso com máscaras
   - Parâmetro `verbose` para controlar nível de detalhamento dos logs
   - Melhor tratamento de erros e feedback de resultados

2. **Refatoração do `testnew.py`**
   - Removida a execução direta do script
   - Implementada função `execute_masked_test()` para uso via interface gráfica
   - Integração com GUI através de nova opção na interface

## Próximos Passos Planejados
1. Expandir o conjunto de estados detectados com mais imagens de referência
2. Desenvolver sistema de ações automáticas baseadas no estado atual do jogo
3. Implementar máquina de estados para criar workflows de automação complexos
4. Melhorar a performance de detecção de estados com possibilidade de caching
5. Adicionar mecanismos para salvar e carregar configurações de estados personalizados
