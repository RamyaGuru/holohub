"""
JSON-based NATS Logger Operator - No build required!

This operator uses JSON serialization instead of FlatBuffers,
eliminating the need for schema compilation and PYTHONPATH setup.
"""

import json
import base64
import time
import asyncio
from threading import Thread

import numpy as np
import nats
from holoscan.core import Operator, OperatorSpec


class NatsLoggerJsonOp(Operator):
    """
    NATS logger using JSON serialization.
    
    Args:
        nats_url: NATS server URL
        subject: NATS subject to publish to
        stream_id: Unique identifier for this stream
    """
    
    def __init__(self, *args, nats_url="nats://0.0.0.0:4222", 
                 subject="data", stream_id="stream", **kwargs):
        super().__init__(*args, **kwargs)
        self.nats_url = nats_url
        self.subject = subject
        self.stream_id = stream_id
        self.nc = None
        self.loop = None
        self.thread = None
    
    def setup(self, spec: OperatorSpec):
        spec.input("in")
        spec.output("out")
    
    def start(self):
        """Initialize NATS connection."""
        self.loop = asyncio.new_event_loop()
        
        async def connect():
            self.nc = await nats.connect(self.nats_url)
            print(f"✓ NATS connected to {self.nats_url} on '{self.subject}'")
        
        self.loop.run_until_complete(connect())
        
        # Background thread for async operations
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def compute(self, op_input, op_output, context):
        """Receive, serialize to JSON, publish, and pass through."""
        data = op_input.receive("in")
        
        if data and self.nc:
            try:
                # Extract tensor
                if isinstance(data, dict):
                    tensor = next(iter(data.values()))
                else:
                    tensor = data
                
                # Convert to numpy
                np_data = np.asarray(tensor)
                
                # Serialize to JSON (simple!)
                msg = {
                    'unique_id': self.stream_id,
                    'timestamp_ns': int(time.time() * 1e9),
                    'io_type': 'output',
                    'tensor': {
                        'data': base64.b64encode(np_data.tobytes()).decode('utf-8'),
                        'shape': list(np_data.shape),
                        'dtype': str(np_data.dtype)
                    }
                }
                
                # Publish JSON
                asyncio.run_coroutine_threadsafe(
                    self.nc.publish(self.subject, json.dumps(msg).encode('utf-8')),
                    self.loop
                )
            except Exception as e:
                print(f"Error publishing: {e}")
        
        # Pass through unchanged
        op_output.emit(data, "out")
    
    def stop(self):
        """Clean up NATS connection."""
        if self.nc:
            async def close():
                await self.nc.close()
            asyncio.run_coroutine_threadsafe(close(), self.loop).result()
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        print("✓ NATS logger stopped")
