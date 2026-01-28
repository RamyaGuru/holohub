#!/usr/bin/env python3
"""
Minimal Visualizer with JSON Deserialization

No build required! Pure Python with standard libraries.
"""

import json
import base64
import asyncio
from threading import Thread

import numpy as np
import nats
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# Simple NATS subscriber
class NatsSubscriber:
    def __init__(self, nats_url="nats://localhost:4222"):
        self.nats_url = nats_url
        self.nc = None
        self.messages = {}
        self.loop = None
        self.thread = None
    
    def start(self):
        self.loop = asyncio.new_event_loop()
        
        async def connect():
            self.nc = await nats.connect(self.nats_url)
            print(f"✓ Connected to NATS at {self.nats_url}")
        
        self.loop.run_until_complete(connect())
        
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def subscribe(self, subject):
        async def sub():
            async def message_handler(msg):
                try:
                    # Deserialize JSON
                    data = json.loads(msg.data.decode('utf-8'))
                    
                    # Decode tensor
                    tensor_data = base64.b64decode(data['tensor']['data'])
                    array = np.frombuffer(tensor_data, dtype=data['tensor']['dtype'])
                    array = array.reshape(data['tensor']['shape'])
                    
                    # Store
                    self.messages[data['unique_id']] = {
                        'data': array,
                        'timestamp': data['timestamp_ns']
                    }
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            await self.nc.subscribe(subject, cb=message_handler)
            print(f"✓ Subscribed to {subject}")
        
        asyncio.run_coroutine_threadsafe(sub(), self.loop)
    
    def get_data(self):
        return self.messages.copy()


# Create Dash app
app = Dash(__name__)
nats_sub = None

app.layout = html.Div([
    html.H1("Minimal Ising Visualizer (JSON)", style={'textAlign': 'center'}),
    
    html.Div([
        html.Label("NATS Subject: "),
        dcc.Input(id='subject', value='ising.data', type='text'),
        html.Button('Connect', id='connect-btn', n_clicks=0,
                   style={'marginLeft': '10px', 'padding': '5px 15px'}),
    ], style={'padding': '20px', 'background': '#f0f0f0'}),
    
    html.Div(id='status', style={'padding': '10px', 'textAlign': 'center'}),
    html.Div(id='graph-container'),
    
    dcc.Interval(id='interval', interval=200, n_intervals=0)
])

@app.callback(
    Output('status', 'children'),
    Input('connect-btn', 'n_clicks'),
    Input('subject', 'value'),
    prevent_initial_call=True
)
def connect(n_clicks, subject):
    global nats_sub
    if n_clicks > 0 and nats_sub:
        nats_sub.subscribe(subject)
        return f"✓ Connected to {subject}"
    return "Click Connect"

@app.callback(
    Output('graph-container', 'children'),
    Input('interval', 'n_intervals')
)
def update_graph(n):
    if not nats_sub:
        return html.Div("Waiting...", style={'padding': '20px'})
    
    data_dict = nats_sub.get_data()
    if not data_dict:
        return html.Div("No data yet...", style={'padding': '20px'})
    
    graphs = []
    for stream_id, info in data_dict.items():
        data = info['data']
        
        # Create heatmap for 2D data
        if data.ndim >= 2:
            if data.ndim == 3 and data.shape[2] == 1:
                data = data.squeeze(axis=2)
            fig = px.imshow(data, color_continuous_scale='RdBu_r', aspect='equal')
        else:
            fig = px.line(y=data.flatten())
        
        graphs.append(html.Div([
            html.H3(stream_id),
            html.P(f"Time: {info['timestamp']}", style={'fontSize': '11px'}),
            dcc.Graph(figure=fig, style={'height': '400px'})
        ], style={
            'border': '1px solid #ddd',
            'borderRadius': '5px',
            'padding': '15px',
            'margin': '10px',
            'background': 'white'
        }))
    
    return graphs


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Minimal Visualizer (JSON - No Build Required!)")
    print("="*60)
    print("Starting at http://localhost:8050")
    print("="*60 + "\n")
    
    nats_sub = NatsSubscriber()
    nats_sub.start()
    
    app.run(debug=False, host='0.0.0.0', port=8050)
