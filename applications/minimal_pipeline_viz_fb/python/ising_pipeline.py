#!/usr/bin/env python3
"""
Minimal Ising Model Pipeline with FlatBuffers-based NATS Logger
"""

import numpy as np
from holoscan.core import Application, Operator, OperatorSpec
from holoscan.conditions import PeriodicCondition
from holoscan import as_tensor

from nats_logger_fb import NatsLoggerFbOp


class IsingOp(Operator):
    """2D Ising model operator."""
    
    def __init__(self, fragment, *args, size=64, temperature=2.5, **kwargs):
        super().__init__(fragment, *args, **kwargs)
        self.size = size
        self.temperature = temperature
        self.beta = 1.0 / temperature
        self.spins = np.random.choice([-1, 1], size=(size, size)).astype(np.float32)
        self.iteration = 0
    
    def setup(self, spec: OperatorSpec):
        spec.output("out")
    
    def compute(self, op_input, op_output, context):
        # Monte Carlo sweep
        for _ in range(5):
            self._sweep()
        
        # Normalize to [0, 1] for visualization
        spin_config = ((self.spins + 1.0) / 2.0).reshape(self.size, self.size, 1).astype(np.float32)
        
        if self.iteration % 20 == 0:
            mag = np.mean(self.spins)
            print(f"[Ising] Iter {self.iteration}: M={mag:+.3f}, T={self.temperature:.2f}")
        
        self.iteration += 1
        op_output.emit({"spins": as_tensor(spin_config)}, "out")
    
    def _sweep(self):
        """Metropolis algorithm."""
        for _ in range(self.size * self.size):
            i, j = np.random.randint(0, self.size, 2)
            spin = self.spins[i, j]
            
            neighbors = (
                self.spins[(i+1) % self.size, j] +
                self.spins[(i-1) % self.size, j] +
                self.spins[i, (j+1) % self.size] +
                self.spins[i, (j-1) % self.size]
            )
            
            delta_E = 2.0 * spin * neighbors
            
            if delta_E < 0 or np.random.random() < np.exp(-self.beta * delta_E):
                self.spins[i, j] *= -1


class SinkOp(Operator):
    """Terminal sink."""
    
    def setup(self, spec: OperatorSpec):
        spec.input("in")
    
    def compute(self, op_input, op_output, context):
        _ = op_input.receive("in")


class IsingApp(Application):
    """Ising model application with FlatBuffers NATS logger."""
    
    def __init__(self, nats_url="nats://0.0.0.0:4222", subject="ising.data", **kwargs):
        super().__init__(**kwargs)
        self.nats_url = nats_url
        self.subject = subject
    
    def compose(self):
        # Create operators
        ising = IsingOp(
            self,
            PeriodicCondition(self, recess_period=0.05),  # 20 Hz
            name="ising",
            size=64,
            temperature=2.5
        )
        
        logger = NatsLoggerFbOp(
            self,
            name="logger",
            nats_url=self.nats_url,
            subject=self.subject,
            stream_id="ising.out"
        )
        
        sink = SinkOp(self, name="sink")
        
        # Wire: ising -> logger -> sink
        self.add_flow(ising, logger, {("out", "in")})
        self.add_flow(logger, sink, {("out", "in")})


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ising Model Pipeline (FlatBuffers)")
    parser.add_argument("-u", "--nats_url", default="nats://0.0.0.0:4222", help="NATS URL")
    parser.add_argument("-s", "--subject", default="ising.data", help="NATS subject")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Ising Model Pipeline (FlatBuffers)")
    print("="*60)
    print(f"NATS URL: {args.nats_url}")
    print(f"Subject: {args.subject}")
    print("="*60 + "\n")
    
    app = IsingApp(nats_url=args.nats_url, subject=args.subject)
    app.run()
