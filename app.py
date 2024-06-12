from collections import Counter
from flask import Flask, send_file, jsonify, make_response
import requests
from flask_cors import CORS
import matplotlib.pyplot as plt
import matplotlib
import io
import threading
import pandas as pd

matplotlib.use('Agg')

app = Flask(__name__)
CORS(app)

api_lock = threading.Lock()

THINGSPEAK_API_URL = 'https://api.thingspeak.com/channels/2566728/feeds.json'

def fetch_data():
    try:
        with api_lock:
            response = requests.get(THINGSPEAK_API_URL)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            data = response.json()
            return data['feeds']
    except requests.RequestException as e:
        app.logger.error(f"Error fetching data: {e}")
        return []

def prepare_data(feeds):
    times = [feed['created_at'] for feed in feeds]
    values = [int(feed['field1']) for feed in feeds]
    return pd.DataFrame({'time': times, 'value': values})

@app.route('/api/graph1')
def get_graph1():
    feeds = fetch_data()
    if not feeds:
        return "Error fetching data", 500

    df = prepare_data(feeds)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    daily_data = df.resample('D').mean()

    dates = daily_data.index.strftime('%Y-%m-%d').tolist()
    mean_values = daily_data['value'].tolist()

    plt.figure(figsize=(10, 6))
    plt.plot(dates, mean_values, marker='o', linestyle='-')
    plt.title('Média do sensor de gás lido no dia')
    plt.xlabel('Data')
    plt.ylabel('Valor do sensor de gás')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    
    response = make_response(send_file(img_bytes, mimetype='image/png'))
    response.headers['Cache-Control'] = 'no-cache'
    
    return response

@app.route('/api/graph2')
def get_graph2():
    feeds = fetch_data()
    if not feeds:
        return "Error fetching data", 500

    values = [int(feed['field1']) for feed in feeds]
    value_counts = Counter(values)
    labels = list(value_counts.keys())
    counts = list(value_counts.values())
    
    colors = ['red' if value > 150 else 'blue' for value in labels]

    plt.figure(figsize=(10, 6))
    plt.bar(labels, counts, color=colors)
    plt.title('Leituras realizadas no sensor de gás')
    plt.xlabel('Valor lido')
    plt.ylabel('Quantidade')
    plt.grid(True)
    plt.tight_layout()

    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    
    response = make_response(send_file(img_bytes, mimetype='image/png'))
    response.headers['Cache-Control'] = 'no-cache'
    
    return response

@app.route('/api/max_value')
def get_max_value():
    feeds = fetch_data()
    if not feeds:
        return "Error fetching data", 500

    values = [int(feed['field1']) for feed in feeds]
    max_value = max(values)
    total_values = len(values)

    return jsonify({
        'max_value': max_value,
        'total_values': total_values
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0')