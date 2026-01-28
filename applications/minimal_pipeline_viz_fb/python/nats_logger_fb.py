"""
FlatBuffers-based NATS Logger Operator

Requires build step to generate FlatBuffers Python modules.
"""

import time
import asyncio
from threading import Thread

import numpy as np
import nats
import flatbuffers
from holoscan.core import Operator, OperatorSpec

# FlatBuffers imports (generated code)
from Message import Message, CreateMessage, IOType
from Tensor import Tensor as TensorFB


class NatsLoggerFbOp(Operator):
    """
    NATS logger using FlatBuffers serialization.
    
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
        
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def compute(self, op_input, op_output, context):
        """Receive, serialize to FlatBuffers, publish, and pass through."""
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
                
                # Serialize with FlatBuffers
                builder = flatbuffers.Builder(1024)
                
                # Create tensor
                shape_fb = builder.CreateNumpyVector(np.array(np_data.shape, dtype=np.int64))
                data_fb = builder.CreateByteVector(np_data.tobytes())
                
                TensorFB.Start(builder)
                TensorFB.AddShape(builder, shape_fb)
                TensorFB.AddData(builder, data_fb)
                tensor_fb = TensorFB.End(builder)
                
                # Create message
                stream_id_fb = builder.CreateString(self.stream_id)
                timestamp = int(time.time() * 1e9)
                
                Message.Start(builder)
                Message.AddUniqueId(builder, stream_id_fb)
                Message.AddIoType(builder, IOType.IOType.kOutput)
                Message.AddAcquisitionTimestampNs(builder, timestamp)
                Message.AddTimestampNs(builder, timestamp)
                Message.AddPayloadType(builder, 0)  # Tensor
                Message.AddPayload(builder, tensor_fb)
                msg = Message.End(builder)
                
                builder.Finish(msg)
                
                # Publish
                asyncio.run_coroutine_threadsafe(
                    self.nc.publish(self.subject, builder.Output()),
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
