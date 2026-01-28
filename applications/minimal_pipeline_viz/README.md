# Minimal Pipeline Visualizer

A simple example of a Holoscan pipeline that generates data (Ising model simulation), logs it to NATS using JSON serialization, and visualizes it in real-time through a web interface.

## What This Does

This application demonstrates:
- **Data Generation**: Runs a 2D Ising model physics simulation
- **NATS Logging**: Publishes simulation data to a NATS message broker using JSON
- **Real-time Visualization**: Displays the evolving spin configuration in a web dashboard

**Key Features:**
- ✅ No build step required - pure Python
- ✅ YAML configuration for easy parameter tuning
- ✅ JSON serialization (human-readable, easy to debug)
- ✅ Real-time updates at 20 Hz

## How to Run

### Prerequisites
- Docker (for NATS server)
- Python 3.8+

### Steps

**1. Build the application (one-time setup):**
```bash
cd /home/rgurunathan/projects/holohub
./holohub build minimal_pipeline_viz
```

**2. Start NATS server (Terminal 1):**
```bash
cd /home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz
./start_nats.sh
```

**3. Run the pipeline (Terminal 2):**
```bash
cd /home/rgurunathan/projects/holohub
./holohub run minimal_pipeline_viz
```

**4. Run the visualizer (Terminal 3):**
```bash
cd /home/rgurunathan/projects/holohub
./holohub run minimal_pipeline_viz visualizer
```

**5. Open your browser:**
- Navigate to `http://localhost:8050`
- Click the **Connect** button

You should see the Ising model visualization updating in real-time!

## Configuration

Edit `config.yaml` to customize the simulation:

```yaml
ising:
  lattice_size: 64          # Grid size (NxN)
  temperature: 2.5          # T < 2.27: ordered, T > 2.27: disordered
  sweeps_per_frame: 5       # Monte Carlo iterations per update

pipeline:
  frequency: 20             # Update rate in Hz

nats:
  url: "nats://0.0.0.0:4222"
  subject: "ising.data"
```

## Architecture

```
IsingOp → NatsLoggerJsonOp → SinkOp
            ↓
         (JSON over NATS)
            ↓
      visualizer_json.py
```

The pipeline generates Ising model data, logs it to NATS as JSON, and a separate visualizer application subscribes to the NATS stream to display the data.
