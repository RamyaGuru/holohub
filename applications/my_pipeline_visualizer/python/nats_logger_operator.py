"""
SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Minimal NATS Logger Operator - Python version
"""

import numpy as np
from holoscan.core import Operator, OperatorSpec
from holoscan import as_tensor
import nats
import asyncio
import flatbuffers
from threading import Thread
import time

# Import FlatBuffers generated code
from Message import Message, CreateMessage, IOType
from Tensor import Tensor as TensorFB


class NatsLoggerOp(Operator):
    """
    Minimal NATS logger operator - pass-through with logging.
    
    Args:
        nats_url: NATS server URL (default: "nats://0.0.0.0:4222")
        subject: NATS subject to publish to (default: "data")
        stream_id: Unique identifier for this stream (default: "stream")
    
    Example:
        logger = NatsLoggerOp(
            self,
            name="logger",
            nats_url="nats://0.0.0.0:4222",
            subject="my_app.data",
            stream_id="source.out"
        )
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
        """Initialize NATS connection in separate thread."""
        self.loop = asyncio.new_event_loop()
        
        async def connect():
            self.nc = await nats.connect(self.nats_url)
            print(f"NATS logger connected to {self.nats_url} on subject '{self.subject}'")
        
        self.loop.run_until_complete(connect())
        
        # Keep event loop running in background thread
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        """Background thread to run asyncio event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def compute(self, op_input, op_output, context):
        """Receive, log, and pass through data."""
        # Receive data
        data = op_input.receive("in")
        
        # Publish to NATS (async, non-blocking)
        if data and self.nc:
            try:
                # Extract first tensor
                if isinstance(data, dict):
                    tensor = next(iter(data.values()))
                else:
                    tensor = data
                
                # Convert to numpy
                if hasattr(tensor, 'data'):
                    np_data = np.array(tensor, copy=False)
                else:
                    np_data = np.array(tensor)
                
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
                
                # Publish (schedule in event loop)
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
        
        print("NATS logger stopped")


# ============================================================================
# Example Usage
# ============================================================================

from holoscan.core import Application
from holoscan.conditions import PeriodicCondition


class SourceOp(Operator):
    """Example source operator."""
    
    def setup(self, spec: OperatorSpec):
        spec.output("out")
    
    def compute(self, op_input, op_output, context):
        # Generate data
        data = np.random.rand(64, 64).astype(np.float32)
        op_output.emit({"data": as_tensor(data)}, "out")


class ProcessOp(Operator):
    """Example processing operator."""
    
    def setup(self, spec: OperatorSpec):
        spec.input("in")
        spec.output("out")
    
    def compute(self, op_input, op_output, context):
        data = op_input.receive("in")
        # Process data...
        op_output.emit(data, "out")


# ============================================================================
# COMPARISON: Different approaches
# ============================================================================

class AppWithOperator(Application):
    """Example using operator-based logging."""
    
    def compose(self):
        source = SourceOp(
            self,
            PeriodicCondition(self, recess_period=0.5),
            name="source"
        )
        process = ProcessOp(self, name="process")
        
        # Insert logger operators
        logger1 = NatsLoggerOp(
            self,
            name="logger1",
            nats_url="nats://0.0.0.0:4222",
            subject="my_app.data",
            stream_id="source.out"
        )
        
        logger2 = NatsLoggerOp(
            self,
            name="logger2",
            nats_url="nats://0.0.0.0:4222",
            subject="my_app.data",
            stream_id="process.out"
        )
        
        # Wire pipeline
        self.add_flow(source, logger1)
        self.add_flow(logger1, process)
        self.add_flow(process, logger2)


def make_logger(app, name, stream_id, 
                nats_url="nats://0.0.0.0:4222",
                subject="data"):
    """Helper function to create logger with fewer arguments."""
    return NatsLoggerOp(
        app,
        name=name,
        nats_url=nats_url,
        subject=subject,
        stream_id=stream_id
    )


class AppWithHelper(Application):
    """Example using helper function (cleaner code)."""
    
    def compose(self):
        source = SourceOp(
            self,
            PeriodicCondition(self, recess_period=0.5),
            name="source"
        )
        process = ProcessOp(self, name="process")
        
        # Simpler with helper
        log1 = make_logger(self, "log1", "source.out")
        log2 = make_logger(self, "log2", "process.out")
        
        self.add_flow(source, log1)
        self.add_flow(log1, process)
        self.add_flow(process, log2)


if __name__ == "__main__":
    app = AppWithHelper()
    app.run()
