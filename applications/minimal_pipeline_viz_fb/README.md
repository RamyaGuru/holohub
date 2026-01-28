# Minimal Pipeline Visualizer (FlatBuffers)

Streamlined version using **FlatBuffers** for performance with minimal complexity.

## Quick Start

### 1. Build FlatBuffers Schemas

```bash
cd /home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz_fb
mkdir build && cd build
cmake ..
make
```

### 2. Install Python Dependencies

```bash
pip install numpy holoscan-sdk nats-py dash plotly flatbuffers
```

### 3. Start NATS Server

```bash
# Terminal 1
docker run --network host nats:latest
```

### 4. Run Pipeline

```bash
# Terminal 2
export PYTHONPATH=/home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz_fb/build/flatbuffers:$PYTHONPATH
cd /home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz_fb
python3 python/ising_pipeline.py
```

### 5. Run Visualizer

```bash
# Terminal 3
export PYTHONPATH=/home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz_fb/build/flatbuffers:$PYTHONPATH
cd /home/rgurunathan/projects/holohub/applications/minimal_pipeline_viz_fb
python3 visualizer/visualizer_fb.py
```

### 6. Open Browser

Go to **http://localhost:8050** and click **Connect**

## What's Different?

### vs JSON Version (`minimal_pipeline_viz`)

| Aspect | JSON | FlatBuffers (this) |
|--------|------|-------------------|
| **Build step** | None | **Required** |
| **PYTHONPATH** | None | **Required** |
| **Message size** | 21 KB | 16.5 KB (~25% smaller) |
| **Speed** | 60 μs | 20 μs (~3× faster) |
| **Zero-copy** | No | Yes |

### vs Full Version (`my_pipeline_visualizer`)

| Aspect | Full | Minimal (this) |
|--------|------|----------------|
| **Files** | 30+ | 6 |
| **Logger** | Resource + Operator | Operator only |
| **Visualizer** | 7 files | 1 file |
| **Complexity** | High | Low |

## Architecture

```
IsingOp → NatsLoggerFbOp → SinkOp
            ↓
      (FlatBuffers over NATS)
            ↓
      visualizer_fb.py
```

## Files

```
minimal_pipeline_viz_fb/
├── CMakeLists.txt               # FlatBuffers build
├── schemas/
│   ├── message.fbs              # Message schema
│   └── tensor.fbs               # Tensor schema
├── python/
│   ├── nats_logger_fb.py        # FlatBuffers NATS logger operator
│   └── ising_pipeline.py        # Ising model pipeline
└── visualizer/
    └── visualizer_fb.py         # FlatBuffers visualizer
```

## Advantages

✅ **Faster** - 20 μs serialization vs 60 μs (JSON)  
✅ **Smaller** - 16.5 KB vs 21 KB messages  
✅ **Zero-copy** - Direct memory access in visualizer  
✅ **Still minimal** - Only 6 files vs 30+ in full version  

## Trade-offs

⚠️ **Requires build** - Must run CMake once  
⚠️ **Requires PYTHONPATH** - Must set environment variable  

## When to Use

**Use FlatBuffers version when:**
- Performance matters (>50 Hz)
- Message size matters
- Zero-copy is beneficial
- Production deployment

**Use JSON version when:**
- Prototyping/learning
- Ease of setup is priority
- Publishing <50 Hz

## Performance

At **20 Hz** on 64×64 float32 data:

- Message size: 16.5 KB
- Serialize time: 20 μs
- Deserialize time: 5 μs (zero-copy!)
- **Total overhead: 25 μs (0.05% of 50ms frame budget)**

## Customization

Same as JSON version - see `minimal_pipeline_viz/README.md`
