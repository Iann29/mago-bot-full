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
   - **screenshotCFG.json**: Configuração centralizada para os parâmetros de captura e debug

3. **Execution**
   - **test.py**: Implementa testes práticos, como buscar templates específicos em screenshots

4. **Interface Gráfica (main.py)**
   - Interface Tkinter para interação do usuário
   - Gerencia uma thread contínua de captura de screenshots 
   - Fornece funcionalidades para testar reconhecimento de templates

## Funcionalidades Principais

### Captura Contínua de Screenshots
- Sistema assíncrono que captura screenshots em intervalos regulares
- Configurado para trabalhar a um FPS específico (atualmente 1 fps)
- Executa em uma thread separada, permitindo que a interface continue responsiva

### Reconhecimento de Templates
- Busca imagens de referência (templates) dentro dos screenshots capturados
- Suporta regiões de interesse (ROI) para limitar a busca a áreas específicas
- Retorna posição e nível de confiança quando um template é encontrado

### Interface Gráfica
- Permite iniciar/parar a captura de screenshots
- Monitora o status da thread de captura
- Fornece botões para executar testes de reconhecimento específicos

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

## Próximos Passos Planejados
1. Implementar mais testes de reconhecimento para diferentes elementos do jogo
2. Desenvolver sistema de ações que possa interagir com os elementos reconhecidos
3. Expandir a interface gráfica com mais opções de configuração e controle
4. Melhorar a documentação de uso da API find_template
5. Implementar suporte para sequências de reconhecimento de múltiplos templates
