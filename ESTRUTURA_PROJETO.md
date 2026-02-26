# Estrutura do Projeto MarmSoft

## 📁 Estrutura Ativa (Arquivos em Uso)

### Arquivos Principais
- **main.py** - Ponto de entrada da aplicação
- **main.spec** - Especificação do PyInstaller para compilação
- **config.json** - Configurações da aplicação
- **sessions.csv** - Registro de sessões clínicas
- **requirements.txt** - Dependências Python
- **LICENSE** - Licença do software

### Pastas Essenciais

#### `/Modules/`
Código principal da aplicação:
- **ui_manager.py** - Interface principal PyQt6
- **sensor_data.py** - Gerenciamento de dados dos sensores
- **clinical_manager.py** - Gerenciamento de pacientes e terapeutas
- **ble_manager.py** - Comunicação Bluetooth
- **goniometer_manager.py** - Gerenciamento do goniômetro
- **flex_calibrador.py** - Calibração de sensores flex
- **fsr_calibrador.py** - Calibração de sensores FSR
- **plot_manager.py** - Visualização de gráficos
- **tests.py** - Ferramentas de teste de sensores
- **mapeamento_sensores.py** - Mapeamento de sensores para articulações
- `/legacy/` - Versões antigas de interfaces (não utilizadas)

#### `/calibrations/`
Arquivos de calibração dos sensores:
- `/flex/` - Calibrações dos sensores flex (flex1 a flex8)
  - Formato: `calibration_flex<N>.csv`
- `/fsr/` - Calibrações dos sensores FSR (fsr1 a fsr4)
  - Formato: `calibration_fsr<N>.csv`

#### `/Pacientes/`
Dados dos pacientes:
- Arquivos individuais por paciente: `<ID>.csv`
- Dados de jogos: `<ID>_flybird.csv`
- **Exemplo**: P001.csv, P001_flybird.csv

#### `/Terapeutas/`
Cadastro de terapeutas:
- **therapists.csv** - Lista de terapeutas registrados

#### `/FlyBird/`
Jogo de reabilitação FlyBird:
- `/assets/` - Recursos visuais e sonoros
- `/data/` - Dados do jogo
- `/modules/` - Código do jogo
- **main_fb.py** - Entrada do jogo

#### `/assets/`
Recursos visuais da aplicação:
- **icon.png** - Ícone do software
- Outros recursos gráficos

#### `/data_tests/`
Armazenamento de dados de testes dos sensores

#### `/dist/`
Executável compilado:
- `/Marms/` - Pasta da aplicação distribuível
  - **Marms.exe** - Executável principal
  - `/_internal/` - Bibliotecas e recursos necessários

---

## 📦 Arquivos Movidos para `/Legacy/`

### Desenvolvimento e Documentação
- **bugs_e_melhorias.txt** - Lista de bugs e melhorias (histórico)
- **estrutura_projeto.txt** - Descrição antiga da estrutura
- **Readme.txt** - README antigo

### Código de Desenvolvimento
- `/tests/` - Scripts de teste isolados
  - force_clean.py
  - scale_realtime.py
  - teste_ui.py

### Dados de Desenvolvimento
- `/calibracao_fsr/` - Dados antigos de calibração FSR
- `/gravacoes_fsr/` - Gravações antigas de testes FSR
- `/data_tests/` - Testes antigos (agora recriado vazio para produção)
- `/Jogos/` - Biblioteca de jogos externos não utilizados

### Firmware e Hardware
- `/Firmware do ESP32/` - Código do microcontrolador ESP32
- `/Firmware_da_celula_de_carga/` - Código da célula de carga/balança

### Documentação
- `/Docs/` - Documentação antiga do projeto

### Build Temporário
- `/build/` - Arquivos temporários do PyInstaller

---

## 🎯 Arquivos de Calibração Utilizados

O software carrega calibrações do diretório `calibrations/`:

### Sensores Flex (8 sensores)
```
calibrations/flex/calibration_flex1.csv
calibrations/flex/calibration_flex2.csv
...
calibrations/flex/calibration_flex8.csv
```

### Sensores FSR (4 sensores)
```
calibrations/fsr/calibration_fsr1.csv
calibrations/fsr/calibration_fsr2.csv
calibrations/fsr/calibration_fsr3.csv
calibrations/fsr/calibration_fsr4.csv
```

**Formato dos arquivos:**
- CSV com cabeçalho
- Flex: Voltage,Angle (tensão em V, ângulo em graus)
- FSR: tensao,forca (tensão em V, força em N)
- Linha opcional de coeficientes polinomiais: `#COEFFICIENTS,c0,c1,c2,...`

---

## 🚀 Distribuição (pasta `/dist/Marms/`)

### Estrutura Copiada pelo PyInstaller:
✅ **Marms.exe** - Executável principal
✅ **_internal/** - Todas as dependências
  - Bibliotecas Python (numpy, PyQt6, pygame, etc.)
  - **config.json** - Configurações
  - **sessions.csv** - Sessões (se existir)
  - **/calibrations/** - Arquivos de calibração
  - **/Pacientes/** - Dados de exemplo
  - **/Terapeutas/** - Terapeuta de exemplo
  - **/FlyBird/** - Jogo completo
  - **/assets/** - Recursos visuais
  - **/Modules/** - Código Python
  - **/data_tests/** - Pasta para testes (vazia)

### Arquivos de Exemplo Incluídos:
- **Paciente**: Alex Martins (P001)
- **Terapeuta**: Dra. Maria Silva (CREFITO-12345)

---

## 📝 Notas Importantes

1. **Calibrações**: Os arquivos em `calibrations/` são essenciais para o funcionamento correto dos sensores
2. **Config.json**: Armazena configurações como tema, mapeamento de sensores, etc.
3. **Sessions.csv**: Histórico de sessões clínicas (mantido limitado a 20 últimas)
4. **Legacy**: Nada foi deletado, apenas movido para organização

## 🔄 Fluxo de Dados

```
ESP32 (BLE) → BLE Manager → Sensor Data → UI Manager → Visualização
                                ↓
                          Calibration Files
                                ↓
                          Valores Calibrados
                                ↓
                          Clinical Manager → Pacientes/Terapeutas
                                ↓
                          Sessions.csv / FlyBird
```
