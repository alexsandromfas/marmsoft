# MarmSoft - Software de Reabilitação com Sensores

Sistema de reabilitação para mãos e membros superiores utilizando sensores flex, FSR, goniômetro e jogos terapêuticos.

## 🎮 Características

- **Monitoramento em Tempo Real**: Visualização de dados de sensores flex, FSR, goniômetro e célula de carga
- **Calibração de Sensores**: Sistema completo de calibração para sensores flex e FSR
- **Gestão Clínica**: Cadastro de pacientes, terapeutas e sessões clínicas
- **Jogos Terapêuticos**: FlyBird - jogo de reabilitação controlado por sensores
- **Conectividade Bluetooth**: Comunicação BLE com ESP32
- **Análise de Dados**: Gráficos e visualizações em tempo real

## 📋 Requisitos

- Python 3.13
- Windows 10/11 (testado em Windows 11)
- ESP32 com firmware específico (Bluetooth)
- Goniômetro Biometrics DataLITE (opcional)

## 🚀 Instalação

### Modo Desenvolvimento

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd marmsoft

# Crie ambiente virtual
python -m venv .venv

# Ative o ambiente virtual
.venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt

# Execute o software
python main.py
```

### Modo Distribuição

Execute o arquivo `Marms.exe` localizado em `dist/Marms/`

## 📁 Estrutura do Projeto

```
marmsoft/
├── main.py                 # Ponto de entrada da aplicação
├── main.spec              # Especificação PyInstaller
├── config.json            # Configurações
├── sessions.csv           # Registro de sessões
├── Modules/               # Código principal
├── calibrations/          # Arquivos de calibração
│   ├── flex/             # Sensores flex
│   └── fsr/              # Sensores FSR
├── Pacientes/            # Dados dos pacientes
├── Terapeutas/           # Cadastro de terapeutas
├── FlyBird/              # Jogo terapêutico
├── assets/               # Recursos visuais
├── data_tests/           # Dados de testes
├── dist/                 # Executável compilado
└── Legacy/               # Arquivos históricos
```

Ver [ESTRUTURA_PROJETO.md](ESTRUTURA_PROJETO.md) para detalhes completos.

## 🎯 Uso Básico

### 1. Iniciar Sessão Clínica
1. Abra o software
2. Na tela inicial, clique em "Nova Sessão" ou "Abrir Paciente"
3. Selecione ou cadastre um paciente
4. Inicie a sessão com terapeuta registrado

### 2. Conectar Sensores
1. Vá para "Config" → "Bluetooth"
2. Escaneie dispositivos
3. Conecte ao ESP32
4. Verifique leitura dos sensores em "Sensores"

### 3. Calibrar Sensores
1. Vá para "Calibração"
2. Selecione o sensor (flex1-8 ou fsr1-4)
3. Siga os passos de calibração
4. Salve a calibração

### 4. Mapear Articulações
1. Em "Config" → "Mapeamento de Sensores"
2. Associe cada articulação a um sensor
3. Salve o mapeamento

### 5. Jogar FlyBird
1. Com sensores conectados e calibrados
2. Vá para "Jogos" → "FlyBird"
3. Selecione a articulação a usar
4. Calibre os limites de movimento
5. Jogue!

## 🔧 Calibração

### Sensores Flex (Ângulo)
- Formato: Voltage, Angle
- Mínimo 3 pontos recomendado
- Ajuste polinomial de grau 2

### Sensores FSR (Força)
- Formato: tensao, forca
- Calibração com pesos conhecidos
- Ajuste linear ou polinomial

Os arquivos são salvos em:
- `calibrations/flex/calibration_<sensor>.csv`
- `calibrations/fsr/calibration_<sensor>.csv`

## 📊 Dados dos Pacientes

Cada paciente possui:
- Arquivo principal: `Pacientes/<ID>.csv`
- Dados de jogos: `Pacientes/<ID>_flybird.csv`
- Histórico em sessions.csv

## 🔨 Compilar Executável

```bash
# Certifique-se de estar no ambiente virtual ativado
pyinstaller main.spec --noconfirm
```

O executável será gerado em `dist/Marms/`

## 🐛 Solução de Problemas

### Software não inicia
- Verifique se todos os arquivos estão presentes
- Execute a partir da pasta raíz do projeto
- Verifique logs no terminal

### Sensores não conectam
- Verifique se o ESP32 está ligado
- Confirme que o Bluetooth está ativo
- Resete o ESP32 se necessário

### Erro de calibração
- Verifique se os arquivos em `calibrations/` existem
- Recalibre o sensor se necessário
- Formato do CSV deve estar correto

### Jogo não responde ao sensor
- Verifique se o sensor está mapeado para a articulação
- Confirme que o sensor está calibrado
- Calibre os limites de movimento no jogo

## 📝 Observações

- Antes de usar, calibre todos os sensores
- Mapeie os sensores para as articulações corretas
- Faça backup dos arquivos de calibração
- O histórico de sessões é limitado a 20 entradas

## 👥 Exemplo de Uso

O software vem com dados de exemplo:
- **Paciente**: Alex Martins (P001)
- **Terapeuta**: Dra. Maria Silva (CREFITO-12345)

Use-os para testar o sistema ou como modelo para novos cadastros.

## 📄 Licença

Ver arquivo LICENSE para detalhes.

## 🤝 Contribuindo

Este é um projeto de pesquisa. Para contribuições, entre em contato.

## 📞 Suporte

Para questões técnicas, consulte a documentação em `Legacy/Docs/` ou entre em contato com o desenvolvedor.

---

**Desenvolvido para Mestrado FEI - Pesquisa em Reabilitação**
