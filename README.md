# IoT_IA — Detecção de Queda (cStick)

Este projeto realiza EDA, treinamento de modelos (Random Forest e Rede Neural) e integra publicação/assinatura MQTT para prever status de queda a partir de sensores.

## Estrutura
- `cStick.csv`: dataset principal.
- `data.ipynb`: EDA, pré-processamento, Z-Score e análises.
- `IA_model.ipynb`: treinamento e avaliação (RF e PyTorch NN); salva modelos.
- `publisher.py`: publica leituras do CSV via MQTT.
- `subscriber.py`: assina MQTT, carrega `modelo_RdF.pkl` e prediz o status de queda.
- `archive/`: materiais auxiliares.

## Requisitos
- Windows, PowerShell 5.1
- Python 3.12 (ajuste se usar versão diferente)

## Dependências Python
Instale no mesmo interpretador Python usado para rodar os scripts (veja o caminho no comando de execução). 

```powershell
# (Opcional) criar venv
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# Instalação das libs
pip install pandas seaborn matplotlib scikit-learn torch paho-mqtt
```

Se usar Jupyter dentro do VS Code:
```powershell
pip install notebook ipykernel
python -m ipykernel install --user --name iot_ia
```

## Broker MQTT (Mosquitto)
Você pode usar um broker local ou um público.

- Instalar Mosquitto no Windows (Chocolatey):
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
choco install mosquitto -y
net start mosquitto
```

- Instalação manual:
```powershell
"C:\\Program Files\\mosquitto\\mosquitto.exe" -v
# Abrir firewall (se necessário)
New-NetFirewallRule -DisplayName "Mosquitto MQTT 1883" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow
```

- Teste de conectividade ao broker local:
```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 1883
```

- Clientes mosquitto (opcional):
```powershell
"C:\\Program Files\\mosquitto\\mosquitto_sub.exe" -h 127.0.0.1 -t cStick/sensor_data -v
"C:\\Program Files\\mosquitto\\mosquitto_pub.exe" -h 127.0.0.1 -t cStick/sensor_data -m "hello"
```

## Treinamento de Modelos
Abra e execute `IA_model.ipynb` no kernel Python configurado. Ao final, os arquivos serão gerados:
- `modelo_RdF.pkl` (Random Forest)
- `modelo_nn.pkl` (state_dict da Rede Neural PyTorch)
- `scaler_nn.pkl` (scaler usado pela NN)

Certifique-se de que `modelo_RdF.pkl` esteja no mesmo diretório de `subscriber.py` para inferência.

## Execução — Assinante e Publicador
1) Assinante:
```powershell
"c:/path/to/subscriber.py"
```
Mensagens exibidas quando um payload chega:
- `2 Definite Fall. Help is on the way!`
- `1 Take a break, you tripped/might fall!`
- `0 No fall. Happy walking!`

1) Publicador (emite dados do `cStick.csv`):
```powershell
"c:/path/to/publisher.py"
```

Observações:
- `publisher.py` tenta conectar primeiro em `127.0.0.1:1883`.
- Alinhe `MQTT_BROKER`, `MQTT_PORT` e `MQTT_TOPIC` em ambos os scripts se usar um broker próprio.
  - Tópico do publisher: `cStick/sensor_data`
  - Tópico do subscriber (exemplo atual): `esp32/cstick/data` (ajuste para o mesmo tópico se necessário)

## EDA e Z-Score
Execute `data.ipynb` para:
- auditoria de dados (shape, dtypes, missing, describe)
- distribuição das classes com rótulos em português
- correlações e heatmaps
- boxplots por atributo
- criação de dataset padronizado com Z-Score e boxplots correspondentes

## Dicas de Troubleshooting
- Erro `ModuleNotFoundError: No module named 'paho'`: instale `paho-mqtt` no mesmo Python do comando.
- Erro `ConnectionRefusedError [WinError 10061]`: verifique se o broker está rodando; teste porta 1883; confira firewall.
- Tópico inválido: garanta que `publisher.py` e `subscriber.py` estão usando o mesmo `MQTT_TOPIC`.
- Feature mapping: o `subscriber.py` aceita chaves em português e inglês; pressão é normalizada para 0/1/2.
