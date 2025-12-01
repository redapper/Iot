#include <Arduino.h>

#include <WiFi.h>
#include <PubSubClient.h>
#include <FS.h>
#include <SPIFFS.h> 

// --- Configurações da Rede Wi-Fi ---
const char* ssid = "RNV_INTELBRAS";
const char* password = "42888024";

// --- Configurações do MQTT ---
const char* mqtt_server = "TEST.MOSQUITTO.ORG"; 
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/cstick/data";
const char* mqtt_client_id = "ESP32-CSV-Publisher";

// --- Variáveis Globais de Estado ---
WiFiClient espClient;
PubSubClient client(espClient);

// Variável global para o arquivo, permitindo manter o ponteiro de leitura
File dataFile; 
// Flag para garantir que o cabeçalho seja ignorado apenas na primeira vez
bool is_header_skipped = false;

// --- Funções de Conexão e Reconexão ---

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Tentando conexão MQTT...");
    if (client.connect(mqtt_client_id)) {
      Serial.println("conectado!");
    } else {
      Serial.print("Falha, rc=");
      Serial.print(client.state());
      Serial.println(" Tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

// --- Função Principal de Leitura e Publicação Linha a Linha ---

// --- Leitura e Envio ---

void read_and_publish_next_line() {
  // Se o arquivo não estiver aberto, abre usando SPIFFS
  if (!dataFile) {
    dataFile = SPIFFS.open("/cStick.csv", "r");
    if (!dataFile) {
      Serial.println("Falha ao abrir o arquivo cStick.csv no SPIFFS!");
      return;
    }
    Serial.println("Arquivo aberto com sucesso via SPIFFS.");
    is_header_skipped = false; 
  }

  // Pula o cabeçalho na primeira vez
  if (!is_header_skipped && dataFile.available()) {
    String header = dataFile.readStringUntil('\n'); 
    is_header_skipped = true;
    Serial.println("Cabeçalho ignorado.");
    return;
  }

  // Lê e processa a linha
  if (dataFile.available()) {
    String line = dataFile.readStringUntil('\n');
    line.trim(); // Remove espaços extras e quebras de linha

    if (line.length() > 0 && client.connected()) {
      
      // --- LÓGICA DE CONVERSÃO CSV PARA JSON ---
      
      // Definição das chaves 
      const char* chaves[] = {"distancia_cm", "pressao", "VFC", "nivel_acucar", "SpO2", "acelerometro", "decisao"};
      
      String json = "{"; // Inicia o objeto JSON
      int inicio = 0;
      int fim = -1;

      // Loop para pegar os 7 campos
      for (int i = 0; i < 7; i++) {
        fim = line.indexOf(',', inicio); // Procura a próxima vírgula
        
        String valor;
        if (fim == -1) {
          // Se não achar vírgula, é o último valor da linha
          valor = line.substring(inicio);
        } else {
          // Pega o trecho entre as vírgulas
          valor = line.substring(inicio, fim);
          inicio = fim + 1; // Atualiza o início para o próximo ciclo
        }
        
        // Adiciona ao JSON: "chave": valor
        // Nota: Assumindo que os valores são números, não levam aspas. 
        // Se fossem texto, precisaria ser: "\"" + valor + "\""
        json += "\"" + String(chaves[i]) + "\": " + valor;

        // Adiciona vírgula entre os campos, mas não após o último
        if (i < 6) {
          json += ", ";
        }
      }
      json += "}"; // Fecha o objeto JSON

      // --- FIM DA CONVERSÃO ---

      Serial.print("Publicando JSON: ");
      Serial.println(json);
      
      // Converte para char array para enviar
      char payload[512]; // Aumentei o buffer por segurança
      json.toCharArray(payload, sizeof(payload));
      
      if(client.publish(mqtt_topic, payload)) {
         Serial.println("-> Enviado MQTT com sucesso");
      }
    }
  } else {
    Serial.println("Fim do arquivo. Reiniciando leitura...");
    dataFile.close(); 
  }
}

// --- Setup e Loop ---

void setup() {
  Serial.begin(115200);
  delay(1000); // Dá um tempo para o serial estabilizar

  Serial.println("\n\n--- INICIANDO SISTEMA ---");
  
  // Tenta iniciar o SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("ERRO FATAL: Falha ao montar SPIFFS (mesmo com formatação).");
    return;
  }
  Serial.println("SPIFFS Montado.");

  // --- ROTINA DE DIAGNÓSTICO ---
  Serial.println("Listando arquivos na raiz:");
  File root = SPIFFS.open("/");
  File file = root.openNextFile();
  
  int totalFiles = 0;
  while(file){
      Serial.print("ARQUIVO ENCONTRADO: ");
      Serial.print(file.name());
      Serial.print(" | Tamanho: ");
      Serial.println(file.size());
      totalFiles++;
      file = root.openNextFile();
  }
  
  if(totalFiles == 0) {
      Serial.println("AVISO: Nenhum arquivo encontrado! O SPIFFS está vazio.");
      Serial.println("Provavelmente o SPIFFS.begin(true) formatou a memória.");
      
  } else {
      Serial.println("Validação concluída. Verificando cStick.csv específico...");
      // Verifica das duas formas (com e sem barra) para garantir
      if(SPIFFS.exists("/cStick.csv") || SPIFFS.exists("cStick.csv")) {
           Serial.println("SUCESSO FINAL: O arquivo alvo existe!");
      }
  }
  Serial.println("-------------------------");
  // -----------------------------

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  // 1. Manutenção da Conexão
  if (!client.connected()) {
    reconnect_mqtt(); // Garante que o Wi-Fi e MQTT estão conectados
  }
  client.loop(); // Processa mensagens pendentes do MQTT
  
  // 2. Leitura e Publicação
  read_and_publish_next_line();
  
  // 3. Atraso solicitado
  delay(2000); // 2 segundos de atraso entre o envio de cada linha
}
