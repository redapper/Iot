import paho.mqtt.client as mqtt
import time
import json
import random
import threading
import pandas as pd

# --- MQTT Configuration ---
# Use your local Mosquitto address or a public test broker
MQTT_BROKER = "127.0.0.1" 
MQTT_PORT = 1883
MQTT_TOPIC = "cStick/sensor_data" 
CLIENT_ID = f'cStick_Publisher_{random.randint(1000, 9999)}'
QOS_LEVEL = 1

# --- Publishing Configuration ---
# The period between publishing each row (in seconds)
PUBLISH_PERIOD_SECONDS = 5 

# Load the CSV file
try:
    df = pd.read_csv("cStick.csv")
    # Mapping for the 'Pressure' column based on the paper's descriptions (Table 3)
    # Assuming 0, 1, 2 correspond to Small, Medium, Large respectively based on the data context
    PRESSURE_MAP = {0: "Small", 1: "Medium", 2: "Large"}
    df['Pressure'] = df['Pressure'].astype(int).map(PRESSURE_MAP)
    print("Data loaded from cStick.csv.")
except FileNotFoundError:
    print("Error: cStick.csv not found. Please ensure the file is in the same directory.")
    exit()
except Exception as e:
    print(f"Error processing cStick.csv: {e}")
    exit()


# --- Publisher Thread Class ---
class PublisherThread(threading.Thread):
    def __init__(self, client, dataframe, topic, period):
        threading.Thread.__init__(self)
        self.client = client
        self.df = dataframe
        self.topic = topic
        self.period = period
        self.stop_event = threading.Event()

    def run(self):
        """Main publishing loop that iterates through CSV rows."""
        print(f"\nPublisher thread started. Publishing period: {self.period} seconds.")
        
        # Loop through the rows indefinitely (or stop when stop_event is set)
        while not self.stop_event.is_set():
            for index, row in self.df.iterrows():
                if self.stop_event.is_set():
                    break
                
                # Prepare the data payload
                data = {
                    "timestamp": time.time(),
                    "distancia_cm": row["Distance"],
                    "pressao": row["Pressure"], # Now mapped to string
                    "VFC": row["HRV"],
                    "nivel_acucar": row["Sugar level"], # Note the column name from CSV
                    "SpO2": row["SpO2"],
                    "acelerometro": row["Accelerometer"] # Assuming this is the 'g' value
                }
                
                # Convert to JSON string
                payload = json.dumps(data)
                
                # Publish the message
                self.client.publish(self.topic, payload, qos=QOS_LEVEL)
                print(f"[{index}/{len(self.df)}] Published: {payload}")
                
                # Pause for the configurable period
                time.sleep(self.period)
            
            # If the end of the file is reached, start over (simulating continuous monitoring)
            print("\n--- End of CSV data reached. Looping data over. ---\n")

    def stop(self):
        self.stop_event.set()


# --- MQTT Client Setup ---
def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the broker."""
    if rc == 0:
        print("Publisher connected successfully to MQTT Broker.")
    else:
        print(f"Connection failed. Code: {rc}")

client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect

# Connect to the broker with retry and optional fallback
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start() # Start a non-blocking network loop
except Exception as e:
    print(f"Failed to connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT} -> {e}")
    print("Tip: Ensure a broker is running locally (e.g., Mosquitto).\n"
          "Alternatively, set a public broker like 'test.mosquitto.org'.")
    # Optional fallback to public test broker
    fallback_broker = "test.mosquitto.org"
    try:
        print(f"Attempting fallback broker: {fallback_broker}:{MQTT_PORT}")
        client.connect(fallback_broker, MQTT_PORT, 60)
        client.loop_start()
        MQTT_BROKER = fallback_broker
        print("Connected to fallback public broker.")
    except Exception as e2:
        print(f"Fallback broker connection failed: {e2}")
        raise

# --- Main Execution ---
try:
    # Initialize and start the publishing thread
    publisher_thread = PublisherThread(
        client, 
        df, 
        MQTT_TOPIC, 
        PUBLISH_PERIOD_SECONDS
    )
    publisher_thread.start()

    # Keep the main thread alive (and MQTT loop running) until interruption
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\nPublisher script interrupted by user (Ctrl+C).")
except Exception as e:
    print(f"\n\nAn unexpected error occurred: {e}")
finally:
    # Clean up both the thread and the MQTT client
    if 'publisher_thread' in locals() and publisher_thread.is_alive():
        publisher_thread.stop()
        publisher_thread.join() # Wait for the thread to finish
        print("Publisher thread gracefully stopped.")
        
    client.loop_stop()
    client.disconnect()
    print("MQTT Client disconnected.")