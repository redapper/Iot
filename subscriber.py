# prediction_subscriber.py

import paho.mqtt.client as mqtt
import json
import random
import pandas as pd
import pickle
import os

# --- MQTT Configuration ---
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "cStick/sensor_data"

#MQTT_BROKER = "test.mosquitto.org"
#MQTT_PORT = 1883
#MQTT_TOPIC = "esp32/cstick/data"
CLIENT_ID = f'Prediction_Unit_{random.randint(1000, 9999)}'

# --- Machine Learning Placeholder ---
def predict_fall_status(sensor_data):
    """
    Load the trained Random Forest model (modelo_RdF.pkl) and predict fall status
    from incoming sensor_data dict.
    Expected keys in sensor_data:
      - Distance, Pressure, HRV, Sugar level, SpO2, Accelerometer
    Returns one of the class labels: 0, 1, or 2.
    """
    # Lazy-load the model once and reuse
    global _rf_model
    if '_rf_model' not in globals() or _rf_model is None:
        model_path = os.path.join(os.path.dirname(__file__), 'modelo_RdF.pkl')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        with open(model_path, 'rb') as f:
            _rf_model = pickle.load(f)

    # Map possible payload keys to model feature names
    key_map = {
        # English expected
        'Distance': 'Distance',
        'Pressure': 'Pressure',
        'HRV': 'HRV',
        'Sugar level': 'Sugar level',
        'SpO2': 'SpO2',
        'Accelerometer': 'Accelerometer',
        # Portuguese variants
        'distancia_cm': 'Distance',
        'pressao': 'Pressure',
        'VFC': 'HRV',
        'nivel_acucar': 'Sugar level',
        'acelerometro': 'Accelerometer',
        # Common alternates
        'distance_cm': 'Distance',
        'sugar_level': 'Sugar level',
    }

    # Normalize incoming dict to expected feature names
    normalized = {}
    for incoming_key, value in sensor_data.items():
        target_key = key_map.get(incoming_key)
        if target_key:
            normalized[target_key] = value

    # Ensure the payload contains the required features after normalization
    required_features = ['Distance', 'Pressure', 'HRV', 'Sugar level', 'SpO2', 'Accelerometer']
    missing = [k for k in required_features if k not in normalized]
    if missing:
        raise KeyError(f"Missing required sensor keys: {missing}. Provided keys: {list(sensor_data.keys())}")

    # Convert categorical string pressure to numeric if needed
    # accepted strings: 'baixa','média','media','alta','low','medium','high'
    pressure = normalized['Pressure']
    if isinstance(pressure, str):
        p_str = pressure.strip().lower()
        mapping = {
            '0': 0, '1': 1, '2': 2,
            'baixa': 0, 'media': 1, 'média': 1, 'alta': 2,
            'small': 0, 'medium': 1, 'large': 2
        }
        if p_str in mapping:
            normalized['Pressure'] = mapping[p_str]
        else:
            raise ValueError(f"Unrecognized pressure value: {pressure}")

    # Build a single-row DataFrame in the expected feature order (using normalized keys)
    X_row = pd.DataFrame([[normalized[k] for k in required_features]], columns=required_features)

    # Predict class using the loaded Random Forest model
    pred = _rf_model.predict(X_row)
    return int(pred[0])




# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the broker."""
    if rc == 0:
        print("Subscriber Connected successfully to MQTT Broker.")
        # Subscribe to the topic upon successful connection
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Connection failed. Code: {rc}")

def on_message(client, userdata, msg):
    """Callback function for when a message is received."""
    try:
        # Decode and parse the JSON payload
        payload_str = msg.payload.decode('utf-8')
        sensor_data = json.loads(payload_str)
        
        print("\n--- NEW DATA RECEIVED ---")
        # Display the physiological data points
        print(f"Physiological Data: {sensor_data}")
        
        # Perform the fall prediction
        fall_status = predict_fall_status(sensor_data)
        
        # Human-friendly status message
        status_messages = {
            2: "2 Definite Fall. Help is on the way!",
            1: "1 Take a break, you tripped/might fall!",
            0: "0 No fall. Happy walking!"
        }
        print(f"*** Fall Prediction Result: {fall_status} ***")
        print(status_messages.get(fall_status, f"Unknown status: {fall_status}"))
        
    except Exception as e:
        print(f"Error processing message: {e}")

# Create an MQTT client instance
client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker and start the network loop
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever() # Blocks and listens for messages