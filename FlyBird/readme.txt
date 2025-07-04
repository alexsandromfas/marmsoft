game/
├── Assets/
│   ├── Background/
│   │   └── background.png
│   ├── Bird/
│   │   ├── bird_1.png
│   │   ├── bird_2.png
│   │   └── ...
│   ├── Nuvens/
│   │   ├── cloud_1.png
│   │   ├── cloud_2.png
│   │   └── ...
│   ├── Woods/
│   │   ├── wood_1.png
│   │   ├── wood_2.png
│   │   └── ...
│   └── ...
├── core/
│   ├── __init__.py
│   ├── config.py         # Configurações globais
│   ├── game_manager.py   # Lógica principal do jogo
│   └── utils.py          # Funções utilitárias gerais
├── entities/
│   ├── __init__.py
│   ├── bird.py           # Classe do pássaro
│   ├── cloud.py          # Classe das nuvens
│   ├── wood.py           # Classe dos troncos
│   └── ...
├── screens/
│   ├── __init__.py
│   ├── game_over.py      # Tela de "Game Over"
│   └── main_screen.py    # Tela principal
├── main.py               # Arquivo principal para rodar o jogo
└── README.md             # Documentação do projeto
