resumo: O código implementa um sistema completo para monitorar e visualizar dados de sensores flex conectados a um ESP32 via BLE, com funcionalidades de calibração e gamificação. A interface gráfica exibe dois gráficos lado a lado: um para as leituras de tensão dos sensores e outro para os ângulos correspondentes, calculados por interpolação com base em valores calibrados. Botões permitem pausar e retomar a coleta de dados, limpar os gráficos, ajustar a suavização do sinal por filtro passa-baixa, e realizar a calibração dos sensores. A calibração, configurada individualmente para cada sensor, define os valores correspondentes a zero e 90 graus, permitindo o cálculo de ângulos interpolados. Há também um módulo de gamificação, onde o usuário controla uma bolinha, que se movimenta verticalmente de acordo com o ângulo do sensor, para desviar de obstáculos. O sistema é modular, com componentes separados para gerenciamento de dados dos sensores, gráficos, interface gráfica, e jogo, garantindo escalabilidade para futuras melhorias, como a integração de novos dispositivos, como um goniômetro de alta precisão, para calibração mais precisa.




# Sistema de Monitoramento, Visualização e Gamificação com Sensores Flex

Este projeto implementa um sistema completo para monitorar, visualizar e gamificar dados provenientes de sensores flex conectados a um ESP32 via BLE. A solução é composta por módulos independentes que permitem fácil manutenção e escalabilidade, com funcionalidades que abrangem desde a calibração dos sensores até a utilização de dados em um jogo interativo.

## Estrutura do Projeto

```plaintext
19112024_Software_V2.2 - Gamificação/
├── Docs/
├── jogos/
│   └── FlyBird/
│       ├── assets/
│       │   ├── Background/ (Imagem de fundo do jogo)
│       │   ├── Bird/ (Sprites da animação do pássaro)
│       │   ├── Nuvens/ (Imagens decorativas das nuvens)
│       │   └── Woods/ (Obstáculos do jogo)
│       ├── data/ (Armazenamento de resultados e obstáculos)
│       ├── modules/ (Módulos do jogo)
│       └── main.py (Arquivo principal do jogo FlyBird)
├── Modules/ (Módulos do sistema principal)
├── main.py (Interface principal do sistema)
└── readme.md (Este arquivo)
```

## Funcionalidades Principais

### Monitoramento e Visualização de Dados
- **Sensores Flex**: Os sensores capturam tensões correspondentes ao movimento do dedo do usuário.
- **Filtragem de Dados**: Filtro passa-baixa ajustável para suavizar o sinal capturado.
- **Gráficos em Tempo Real**: Dois gráficos exibem tensões e ângulos correspondentes dos sensores em uma interface gráfica intuitiva.

### Calibração
- **Calibração Personalizada**: Cada sensor pode ser calibrado individualmente, com base nos valores de tensão e ângulo (0° a 90°).
- **Armazenamento de Calibração**: Dados de calibração são salvos em arquivos CSV para reutilização.

### Gamificação - FlyBird
O jogo "FlyBird" oferece um ambiente interativo para tornar o uso dos sensores mais motivador e divertido. 

#### Descrição do Jogo
- O jogador controla um pássaro animado, cuja posição vertical é determinada pelo ângulo capturado pelos sensores flex.
- O objetivo é desviar de obstáculos e alcançar a maior pontuação possível.
- Elementos como nuvens e madeira criam um ambiente dinâmico e visualmente atraente.

#### Mecânicas do Jogo
1. **Controle por Sensores**: A posição do pássaro é diretamente proporcional ao ângulo detectado pelo sensor flex.
2. **Obstáculos**: As posições dos troncos (woods) agora são definidas a partir de um mapa de posições pré-determinado em um arquivo CSV.
3. **Vida e Invencibilidade**: O pássaro possui vidas limitadas e fica invencível por alguns segundos após uma colisão.
4. **Pontuação**: A pontuação é calculada com base no número de obstáculos ultrapassados.

#### Funcionalidades Adicionais
- **Seleção de Jogador**: O jogador insere seu nome e escolhe qual dedo será utilizado durante a partida.
- **Armazenamento de Resultados**: Estatísticas como pontuação, amplitudes de movimento e nome do jogador são salvas em um arquivo CSV.
- **Gráficos Decorativos**: Elementos visuais como nuvens se movem em diferentes camadas para enriquecer a experiência do jogo.

#### Controles
- Use os sensores flex para movimentar o pássaro verticalmente.
- Teclas adicionais podem ser configuradas para movimentação ou depuração.

### Integração BLE
- O ESP32 é utilizado como intermediário para capturar os dados dos sensores e transmiti-los via BLE para o sistema.
- Notificações BLE permitem atualizações em tempo real.

## Tecnologias Utilizadas
- **Python**: Linguagem principal para desenvolvimento.
- **Pygame**: Para a criação do jogo "FlyBird".
- **Matplotlib**: Para geração de gráficos.
- **Tkinter**: Para a interface gráfica.
- **BLE (Bluetooth Low Energy)**: Conexão com sensores via ESP32.
- **Bibliotecas Científicas**: NumPy para cálculos de calibração.

## Como Executar
1. Certifique-se de ter o Python 3.10+ instalado.
2. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```
3. Conecte o ESP32 e execute o programa principal:
   ```bash
   python main.py
   ```
4. Para acessar o jogo, clique no botão "Jogos" na interface principal.

## Melhorias Futuras
- Integração com novos tipos de sensores e dispositivos.
- Criação de vídeos explicativos diretamente na interface de calibração.
- Melhoria na lógica de suavização para reduzir atrasos.
- Expansão do jogo para incluir novos desafios e modos.
