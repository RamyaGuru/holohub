#!/usr/bin/env python3
"""
Minimal Ising Model Pipeline with JSON-based NATS Logger

No build required! Just install Python packages and run.
"""

import os
import numpy as np
import yaml
from holoscan.core import Application, Operator, OperatorSpec
from holoscan.conditions import PeriodicCondition
from holoscan import as_tensor

from nats_logger_json import NatsLoggerJsonOp


class IsingOp(Operator):
    """2D Ising model operator."""
    
    def __init__(self, fragment, *args, size=64, temperature=2.5, sweeps_per_frame=5, **kwargs):
        super().__init__(fragment, *args, **kwargs)
        self.size = size
        self.temperature = temperature
        self.sweeps_per_frame = sweeps_per_frame
        self.beta = 1.0 / temperature
        self.spins = np.random.choice([-1, 1], size=(size, size)).astype(np.float32)
        self.iteration = 0
    
    def setup(self, spec: OperatorSpec):
        spec.output("out")
    
    def compute(self, op_input, op_output, context):
        # Monte Carlo sweep
        for _ in range(self.sweeps_per_frame):
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
    """Minimal Ising model application with JSON NATS logger."""
    
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
    
    def compose(self):
        # Extract config
        ising_cfg = self.config['ising']
        nats_cfg = self.config['nats']
        pipeline_cfg = self.config['pipeline']
        
        # Create operators
        ising = IsingOp(
            self,
            PeriodicCondition(self, recess_period=1.0/pipeline_cfg['frequency']),
            name="ising",
            size=ising_cfg['lattice_size'],
            temperature=ising_cfg['temperature'],
            sweeps_per_frame=ising_cfg['sweeps_per_frame']
        )
        
        logger = NatsLoggerJsonOp(
            self,
            name="logger",
            nats_url=nats_cfg['url'],
            subject=nats_cfg['subject'],
            stream_id="ising.out"
        )
        
        sink = SinkOp(self, name="sink")
        
        # Wire: ising -> logger -> sink
        self.add_flow(ising, logger, {("out", "in")})
        self.add_flow(logger, sink, {("out", "in")})


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Minimal Ising Model Pipeline (JSON)")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()
    
    # Load config
    config_path = args.config
    if not os.path.isabs(config_path):
        # If relative path, look in application directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(script_dir), config_path)
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("\n" + "="*60)
    print("Ising Model Pipeline (JSON - No Build Required!)")
    print("="*60)
    print(f"Config: {config_path}")
    print(f"Lattice size: {config['ising']['lattice_size']}")
    print(f"Temperature: {config['ising']['temperature']}")
    print(f"Sweeps/frame: {config['ising']['sweeps_per_frame']}")
    print(f"Frequency: {config['pipeline']['frequency']} Hz")
    print(f"NATS URL: {config['nats']['url']}")
    print(f"Subject: {config['nats']['subject']}")
    print("="*60 + "\n")
    
    app = IsingApp(config=config)
    app.run()
