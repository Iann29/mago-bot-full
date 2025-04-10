# Atualizações do StateManager

## 2025-04-10: Criação do Sistema de Gerenciamento de Estados

### Componentes implementados:
1. **Classe GameState**: Enum para representar os diferentes estados do jogo
   - Atualmente implementado o estado MOBILE_HOME para a tela principal do jogo

2. **Classe StateManager**: Responsável por monitorar e gerenciar os estados do jogo
   - Utiliza a thread de captura existente para análise em tempo real
   - Faz o reconhecimento de imagens usando a classe TemplateMatcher existente
   - Sistema de callback para notificar sobre mudanças de estado

### Funcionalidades:
- **Detecção automática de estados**: Analisa cada screenshot capturado para determinar o estado atual
- **Monitoramento assíncrono**: Executa em uma thread separada para não afetar a performance da UI
- **Callbacks de mudança de estado**: Permite que outras partes do programa reajam às mudanças de estado
- **Controle de concorrência**: Utiliza locks para evitar condições de corrida

### Próximos passos:
- Adicionar mais estados conforme necessário
- Implementar ações específicas para cada estado
- Melhorar a performance de detecção com possível otimização
- Implementar testes para garantir a robustez do sistema

### Observações técnicas:
- Threshold de correspondência definido em 0.75, pode precisar de ajustes conforme a qualidade das imagens
- Intervalo de verificação padrão de 0.2s, balanceando performance e responsividade
- Utiliza o diretório `dataset/imageStates` para as imagens de referência
