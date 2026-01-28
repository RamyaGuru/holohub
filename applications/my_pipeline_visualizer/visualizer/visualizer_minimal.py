#!/usr/bin/env python3
"""
Minimal Pipeline Visualizer - ~130 lines

Demonstrates the MINIMUM needed for visualization:
- Uses existing nats_async.py (it's actually good!)
- Inlines all UI components (no graph_components.py)
- Inlines styles (no styles.py)
- Simple recreate strategy (no complex Patch updates)
- Single file for easy understanding

Usage:
    python3 visualizer_minimal.py
"""

import numpy as np
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, ctx, set_props
from dash.exceptions import PreventUpdate
from nats_async import NatsAsync
import pipeline_visualization.flatbuffers.Message as Message
import pipeline_visualization.flatbuffers.Tensor as Tensor

# Simple FlatBuffers to numpy conversion (inlined from tensor_to_numpy.py)
def fb_to_numpy(payload):
    """Convert FlatBuffers tensor to numpy array."""
    tensor = Tensor.Tensor()
    tensor.Init(payload.Bytes, payload.Pos)
    
    # Get dtype
    code = tensor.Dtype().Code()
    bits = tensor.Dtype().Bits()
    dtype_map = {0: f'i{bits//8}', 1: f'u{bits//8}', 2: f'f{bits//8}'}
    dtype = np.dtype(dtype_map.get(code, 'f4'))
    
    # Get data and reshape
    data = tensor.DataAsNumpy().view(dtype)
    shape = tuple(int(d) for d in tensor.ShapeAsNumpy())
    return data.reshape(shape)

# Global data store
data_store = {}
nats_client = None

app = Dash(__name__)

# Simple inline layout (no separate file needed)
app.layout = html.Div([
    html.H1("Pipeline Visualizer - Minimal", style={'textAlign': 'center'}),
    
    # Connection controls
    html.Div([
        html.Label("NATS Subject: "),
        dcc.Input(id='subject', value='nats_demo', type='text'),
        html.Button('Connect', id='connect-btn', n_clicks=0, 
                   style={'marginLeft': '10px', 'padding': '5px 15px'}),
    ], style={'padding': '20px', 'background': '#f0f0f0'}),
    
    # Graphs container
    html.Div(id='graphs-container'),
    
    # Update interval (200ms)
    dcc.Interval(id='interval', interval=200, n_intervals=0),
])

@app.callback(
    Input('subject', 'value'),
    Input('connect-btn', 'n_clicks'),
)
def handle_connection(subject, n_clicks):
    """Connect/disconnect from NATS."""
    if ctx.triggered_id == 'connect-btn':
        if n_clicks % 2 == 1:
            # Connect
            nats_client.subscribe(f"{subject}.data")
            set_props('subject', {'disabled': True})
            set_props('connect-btn', {'children': 'Disconnect'})
        else:
            # Disconnect
            nats_client.unsubscribe(f"{subject}.data")
            data_store.clear()
            set_props('subject', {'disabled': False})
            set_props('connect-btn', {'children': 'Connect'})

@app.callback(
    Output('graphs-container', 'children'),
    Input('interval', 'n_intervals'),
    Input('subject', 'value'),
    prevent_initial_call=True,
)
def update_graphs(n, subject):
    """Fetch messages and update graphs (simple recreate, no Patch complexity)."""
    if nats_client is None:
        raise PreventUpdate
    
    # Process all pending messages
    while True:
        msg_data = nats_client.get_message(f"{subject}.data")
        if msg_data is None:
            break
        
        # Parse FlatBuffers
        fb_msg = Message.Message.GetRootAs(msg_data, 0)
        stream_id = fb_msg.UniqueId().decode()
        
        # Convert to numpy
        try:
            np_data = fb_to_numpy(fb_msg.Payload())
        except Exception as e:
            print(f"Error converting tensor: {e}")
            continue
        
        # Store
        data_store[stream_id] = {
            'data': np_data,
            'timestamp': fb_msg.TimestampNs(),
            'io_type': 'Output' if fb_msg.IoType() == 1 else 'Input'
        }
    
    # Recreate all graphs (simple, no complex patching!)
    if not data_store:
        return html.Div("Waiting for data...", style={'padding': '20px'})
    
    graphs = []
    for stream_id, info in data_store.items():
        data = info['data']
        
        # Create appropriate plot
        if data.ndim >= 2 and data.shape[0] > 1 and data.shape[1] > 1:
            # 2D heatmap
            if data.ndim == 3 and data.shape[2] == 1:
                data = data.squeeze(axis=2)
            fig = px.imshow(data, color_continuous_scale='RdBu_r', aspect='equal')
        else:
            # 1D line plot
            fig = px.line(y=data.flatten())
        
        # Create graph card
        graphs.append(html.Div([
            html.H3(stream_id, style={'margin': '0 0 10px 0'}),
            html.P(f"Type: {info['io_type']} | Time: {info['timestamp']}", 
                   style={'fontSize': '12px', 'color': '#666'}),
            dcc.Graph(figure=fig, style={'height': '300px'}),
        ], style={
            'border': '1px solid #ddd',
            'borderRadius': '5px',
            'padding': '15px',
            'margin': '10px',
            'background': 'white'
        }))
    
    return graphs

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize NATS (reuse the good abstraction!)
    nats_client = NatsAsync(host="0.0.0.0:4222")
    
    # Run app
    app.run(debug=False, host='0.0.0.0', port=8050)
