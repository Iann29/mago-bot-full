# Análise do Problema de Travamento ao Fechar o Emulador

## Problema Relatado
O usuário relatou que ao abrir o emulador e fechá-lo rapidamente, o programa HayDay Bot fica sem responder.

## Causas Prováveis

### 1. Bloqueio na Thread de Captura

A causa mais provável do travamento é que a thread de captura (`capture_worker`) fica bloqueada ao tentar se comunicar com o emulador que foi fechado abruptamente.

Analisando o código, identificamos os seguintes pontos críticos:

#### Em `capture_worker` (main.py):
- A thread tenta continuamente capturar screenshots
- Existe um mecanismo para contar falhas consecutivas (máximo de 5)
- Porém, se uma operação ADB bloquear completamente, este contador pode não chegar a ser incrementado

#### Em `_take_screenshot_adb` (screenshotMain.py):
- Quando o método `screenshot()` ou `shell("screencap -p")` são chamados em um dispositivo ADB que foi desconectado, podem bloquear por um tempo indeterminado esperando resposta
- A implementação atual não tem timeout explícito para estas operações
- O erro só é capturado se a operação falhar por exceção, não se bloquear indefinidamente

### 2. Problemas no Encerramento da Aplicação

Quando o usuário fecha a aplicação, o método `on_closing` tenta parar a thread de captura, mas:

- A thread pode estar bloqueada em uma operação ADB e não verificar a flag `stop_capture_thread`
- O método `join` na thread tem um timeout de apenas 3 segundos
- Se a thread não encerrar nesse período, o programa continua e finaliza a UI, mas a thread bloqueada continua rodando em background

### 3. Gerenciamento de Recursos ADB

O `ADBManager` é um singleton que mantém a conexão com o servidor ADB e o dispositivo:

- Quando o emulador é fechado, os objetos ADB ainda existem, mas as operações com eles falham ou bloqueiam
- Não há um mecanismo para detectar proativamente que o emulador foi fechado e reinicializar os objetos de conexão

## Solução Recomendada

Para corrigir o problema, seria necessário:

1. Implementar timeouts em todas as operações ADB que possam bloquear
2. Adicionar mecanismos para detectar proativamente quando o emulador é fechado, em vez de apenas reagir a falhas
3. Melhorar o processo de encerramento para garantir que todas as threads sejam corretamente finalizadas
4. Adicionar um sistema de "watchdog" que possa encerrar threads bloqueadas após um tempo limite

O principal problema parece estar na natureza bloqueante das operações ADB quando o dispositivo está inacessível, o que faz com que a thread fique presa sem chance de verificar se deve encerrar.
