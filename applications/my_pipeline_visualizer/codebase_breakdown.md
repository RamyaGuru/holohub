# Reusing the NATS Logger and Visualizer in Your Holoscan Applications

## 🎯 Overview

The NATS logger and visualizer from this application are designed to be reusable across different Holoscan applications. This guide explains what you need to copy and how to integrate these components into your own projects.

## 📦 Architecture Overview

The NATS logger system consists of three main components:

```
┌─────────────────────────────────────────────────────────────┐
│  Your Holoscan Application                                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │ Source   │─────→│ Process  │─────→│   Sink   │         │
│  │ Operator │      │ Operator │      │ Operator │         │
│  └──────────┘      └──────────┘      └──────────┘         │
│       │                  │                  │              │
│       └──────────────────┼──────────────────┘              │
│                          ↓                                  │
│              ┌───────────────────────┐                     │
│              │  NATS Logger          │                     │
│              │  (Data Logger)        │                     │
│              │  • Serializes tensors │                     │
│              │  • Publishes to NATS  │                     │
│              └───────────┬───────────┘                     │
└──────────────────────────┼─────────────────────────────────┘
                           ↓
                  ┌─────────────────┐
                  │  NATS Server    │
                  │  (Message Bus)  │
                  └────────┬────────┘
                           ↓
              ┌────────────────────────┐
              │  Web Visualizer        │
              │  • Subscribes to NATS  │
              │  • Deserializes data   │
              │  • Renders with Plotly │
              └────────────────────────┘
```

### Component Responsibilities

1. **NATS Logger (C++/Python)**: Intercepts Holoscan tensor data, serializes to FlatBuffers, publishes to NATS
2. **NATS Server (Docker)**: Message broker for real-time data streaming
3. **Visualizer (Python/Dash)**: Web interface that subscribes to NATS streams and renders data

---

## 🚀 Quick Start: Reusing in Your Application

### Two Scenarios: Development vs. Standalone

#### Scenario 1: Development Within Holohub (No Copying!)

If you're developing **within the Holohub repository**, the visualizer is truly shared:

```bash
# Terminal 1: NATS server (one for all apps)
cd applications/my_pipeline_visualizer
./start_nats_server.sh

# Terminal 2: Dynamic visualizer (works with ALL apps!)
cd applications/my_pipeline_visualizer/visualizer
PYTHONPATH=../../build/my_pipeline_visualizer/python/../flatbuffers:$PYTHONPATH \
    python3 visualizer_dynamic.py

# Terminal 3: Run ANY Holoscan app in Holohub
./holohub run your_app_1
# Or: ./holohub run your_app_2
# Or: ./holohub run medical_imaging_app
# etc.

# Browser: http://localhost:8050
# Enter your app's subject_prefix (e.g., "your_app_1")
# Click "Connect" → See your data!
```

**Key Insight**: The dynamic visualizer discovers streams automatically - no configuration needed! One visualizer instance works with all apps in your Holohub workspace.

#### Scenario 2: Standalone/Distributed Application (Copy Needed)

If you're creating a **standalone application** to distribute (Docker image, Python package, different machine), you need to copy the visualizer files into your application directory. See "Files You Need to Copy" section below.

---

## 📋 Understanding "Shared" vs. "Standalone"

### Development in Holohub = Truly Shared

When working **within Holohub**, think of the visualizer like a shared tool in a workshop:

```
Holohub Workshop:
├── Tool Cabinet (visualizer/) ← Everyone uses this
├── Workbench 1 (your_app_1/)  → Points to tool cabinet
├── Workbench 2 (your_app_2/)  → Points to tool cabinet
└── Workbench 3 (your_app_3/)  → Points to tool cabinet

No need to duplicate tools!
```

All apps publish to NATS, one visualizer subscribes to any/all of them.

### Standalone Application = Self-Contained

When creating a **distributable package**:

```
Standalone Package:
├── Your App
├── Visualizer (included)    ← Must include copy
└── All dependencies

Like a portable toolbox - must contain everything!
```

**When you need standalone**:
- 🐳 Docker deployment
- 📦 Pip/Conda package  
- 🚢 Shipping to different machines
- 📤 GitHub release as single artifact

**When shared works**:
- 🔧 Local development
- 🧪 Testing multiple apps
- 👥 Team sharing Holohub repo

---

## 📋 Files You Need to Copy (For Standalone Only)

If you're creating a **standalone/distributable application**, copy these files:

### Minimal Set (Core NATS Logger)

```
your_app/
├── cpp/
│   ├── nats_logger.cpp           # Core logger implementation
│   ├── nats_logger.hpp           # Logger header
│   ├── create_tensor.cpp         # Tensor serialization
│   └── create_tensor.hpp         # Tensor header
├── python/
│   ├── nats_logger_pybind.cpp    # Python bindings
│   └── pydoc.hpp                 # Documentation helper
└── schemas/
    ├── message.fbs               # FlatBuffers message schema
    └── tensor.fbs                # FlatBuffers tensor schema
```

### Optional (If Customizing Visualizer)

```
your_app/
└── visualizer/
    ├── visualizer_static.py      # Static (predefined) visualizer
    ├── visualizer_dynamic.py     # Dynamic (auto-discovery) visualizer
    ├── graph_components.py       # Plotly graph components
    ├── tensor_to_numpy.py        # FlatBuffers → NumPy deserializer
    ├── nats_async.py             # Async NATS client wrapper
    └── styles.py                 # Dash CSS styles
```

### Commands to Copy

```bash
# From holohub root
cd /home/rgurunathan/projects/holohub

# Create your app directory
mkdir -p applications/your_app/{cpp,python,schemas}

# Copy NATS logger core
cp applications/my_pipeline_visualizer/cpp/nats_logger.* applications/your_app/cpp/
cp applications/my_pipeline_visualizer/cpp/create_tensor.* applications/your_app/cpp/

# Copy Python bindings
cp applications/my_pipeline_visualizer/python/nats_logger_pybind.cpp applications/your_app/python/
cp applications/my_pipeline_visualizer/python/pydoc.hpp applications/your_app/python/

# Copy FlatBuffers schemas
cp -r applications/my_pipeline_visualizer/schemas/* applications/your_app/schemas/

# Optional: Copy visualizer (if customizing)
cp -r applications/my_pipeline_visualizer/visualizer applications/your_app/
```

---

## 💻 Using the NATS Logger in Your Application

### Python Example

```python
# your_app/python/your_app.py
from holoscan.core import Application, Operator, OperatorSpec
from holoscan.conditions import PeriodicCondition
from holoscan import as_tensor
import numpy as np

# Import NATS logger (will be built with your app)
from holohub.nats_logger import NatsLogger

class YourOperator(Operator):
    """Your custom operator - generates data."""
    
    def setup(self, spec: OperatorSpec):
        spec.output("out")
    
    def compute(self, op_input, op_output, context):
        # Your computation here
        # Example: Generate 2D heatmap data
        data = np.random.rand(64, 64).astype(np.float32)
        
        # Emit data (automatically logged by NATS logger!)
        op_output.emit(dict(result=as_tensor(data)), "out")

class YourApp(Application):
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.nats_url = "nats://0.0.0.0:4222"
        self.subject_prefix = "your_app"  # YOUR CUSTOM PREFIX
    
    def compose(self):
        # Setup NATS logging
        nats_logger = NatsLogger(
            self,
            name="nats_logger",
            nats_url=self.nats_url,
            subject_prefix=self.subject_prefix,
        )
        
        # Register the logger - now ALL operator I/O is automatically logged!
        self.add_data_logger(nats_logger)
        
        # Create your pipeline
        source = YourOperator(
            self,
            PeriodicCondition(self, recess_period=0.1),
            name="source",
        )
        
        # Add operators to flow (logging happens automatically)
        # No manual logging code needed!

if __name__ == "__main__":
    app = YourApp()
    app.run()
```

### C++ Example

```cpp
// your_app/src/main.cpp
#include <holoscan/holoscan.hpp>
#include "nats_logger.hpp"

class YourOperator : public holoscan::Operator {
 public:
  HOLOSCAN_OPERATOR_FORWARD_ARGS(YourOperator)

  void setup(OperatorSpec& spec) override {
    spec.output<holoscan::gxf::Entity>("out");
  }

  void compute(InputContext&, OutputContext& op_output, ExecutionContext&) override {
    // Your computation here
    std::vector<float> data(64 * 64);
    // ... fill data ...
    
    // Emit data (automatically logged!)
    auto tensor = /* create your tensor */;
    op_output.emit(tensor, "out");
  }
};

class YourApp : public holoscan::Application {
 public:
  void compose() override {
    // Create NATS logger
    auto nats_logger = make_resource<NatsLogger>(
        "nats_logger",
        Arg("nats_url", "nats://0.0.0.0:4222"),
        Arg("subject_prefix", "your_app")  // YOUR CUSTOM PREFIX
    );
    
    // Register logger - automatic logging!
    add_data_logger(nats_logger);
    
    // Create your pipeline
    auto source = make_operator<YourOperator>("source");
    // ... rest of your pipeline
  }
};

int main() {
  auto app = std::make_shared<YourApp>();
  app->run();
  return 0;
}
```

---

## 🔧 Configuration

### NATS Logger Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `nats_url` | string | NATS server address | `"nats://0.0.0.0:4222"` |
| `subject_prefix` | string | NATS subject prefix for streams | Required |
| `publish_rate` | float | Rate limit for publishing (Hz) | `60.0` |

### Subject Naming Convention

The NATS logger publishes to two subjects:

- **Data stream**: `{subject_prefix}.data`
- **Metadata stream**: `{subject_prefix}.metadata`

Example with `subject_prefix="my_app"`:
- Data: `my_app.data`
- Metadata: `my_app.metadata`

### YAML Configuration Example

```yaml
# your_app/config.yaml
application:
  nats_url: "nats://0.0.0.0:4222"
  subject_prefix: "your_app"
  publish_rate: 30.0  # 30 Hz
  disable_logger: false
```

---

## 🔄 Workflow Comparison

### Workflow A: Shared Visualizer (Holohub Development)

```bash
# Your project structure
holohub/
├── applications/
│   ├── my_pipeline_visualizer/
│   │   └── visualizer/              # ← Original location
│   │       └── visualizer_dynamic.py
│   └── my_new_app/
│       ├── python/
│       │   └── my_app.py            # Your code
│       └── CMakeLists.txt

# Build your app
$ ./holohub build my_new_app

# Run your app (Terminal 1)
$ ./holohub run my_new_app

# Run shared visualizer (Terminal 2)
$ cd applications/my_pipeline_visualizer/visualizer
$ python3 visualizer_dynamic.py

# Connect to "my_new_app" in browser ✅
```

**Pros**: No duplication, easy updates, simple  
**Cons**: Requires Holohub repo structure

---

### Workflow B: Standalone Application (Independent Distribution)

```bash
# Your standalone project structure
my_standalone_app/
├── src/
│   └── my_app.py
├── visualizer/                      # ← Copied from my_pipeline_visualizer
│   ├── visualizer_dynamic.py
│   ├── tensor_to_numpy.py
│   └── ...
├── nats_logger/                     # ← Copied
│   ├── cpp/
│   └── python/
├── setup.py
└── Dockerfile

# Build Docker image
$ docker build -t my_standalone_app .

# Run anywhere (doesn't need Holohub!)
$ docker run -p 8050:8050 my_standalone_app

# Or install as Python package
$ pip install ./my_standalone_app
$ my-app --visualize
```

**Pros**: Self-contained, distributable, portable  
**Cons**: Must maintain copy, duplicates code

---

### Workflow C: Best of Both (Python Package)

```bash
# Create reusable package (one-time)
holohub/python/holoscan_viz/
├── setup.py
├── holoscan_viz/
│   ├── __init__.py
│   ├── visualizer.py
│   └── tensor_utils.py

# Install in development mode
$ pip install -e holohub/python/holoscan_viz

# Now ANY app can use it
# my_app_1/my_app.py:
from holoscan_viz import DynamicVisualizer
viz = DynamicVisualizer()
viz.run()

# my_app_2/my_app.py:
from holoscan_viz import DynamicVisualizer  # Same import!
viz = DynamicVisualizer()
viz.run()
```

**Pros**: Reusable, no copying, updateable via pip  
**Cons**: Requires packaging setup (one-time effort)

---

## 🧭 Decision Guide: Which Approach Should I Use?

```
Start here: Are you working within the Holohub repository?
│
├─ YES → Use Workflow A (Shared Visualizer)
│   │     - Run visualizer from my_pipeline_visualizer/visualizer/
│   │     - No copying needed!
│   │     - Best for: Development, testing, prototyping
│   │
│   └─ Will you distribute this app?
│       │
│       ├─ NO → Stick with Workflow A ✅
│       │
│       └─ YES → Switch to Workflow B (Copy for distribution)
│                 - Copy visualizer to your app
│                 - Package as Docker/pip/etc.
│
└─ NO (Outside Holohub) → Use Workflow B (Standalone)
    │     - Copy all needed files
    │     - Self-contained application
    │     - Best for: Production, distribution
    │
    └─ Planning multiple standalone apps?
        │
        └─ YES → Consider Workflow C (Python Package)
                  - Create holoscan_viz package
                  - pip install once, import everywhere
                  - Best for: Multiple projects, long-term
```

**Quick Decision Matrix**:

| Your Situation | Best Approach | Copying Needed? |
|----------------|---------------|-----------------|
| Developing in Holohub | **Workflow A** (Shared) | ❌ No |
| Docker deployment | **Workflow B** (Standalone) | ✅ Yes |
| Multiple standalone apps | **Workflow C** (Package) | ❌ No (pip install) |
| Quick prototype | **Workflow A** (Shared) | ❌ No |
| Production system | **Workflow B** or **C** | Depends |

---

## 🎨 Visualizer Options

### Option 1: Dynamic Visualizer (Recommended)

**Use case**: Quick prototyping, multiple apps, runtime stream discovery

```bash
cd applications/my_pipeline_visualizer/visualizer
python3 visualizer_dynamic.py
```

**Features**:
- ✅ Auto-discovers available NATS streams
- ✅ Works with any app using the FlatBuffers schema
- ✅ No configuration needed
- ✅ Connect/disconnect at runtime

**Usage**:
1. Open http://localhost:8050
2. Enter your `subject_prefix` (e.g., "your_app")
3. Click "Connect"

### Option 2: Static Visualizer

**Use case**: Fixed dashboard, pre-configured views

```bash
cd applications/my_pipeline_visualizer/visualizer
python3 visualizer_static.py --ising  # For 2D data
```

**Features**:
- ✅ Pre-configured graphs
- ✅ Faster initial load
- ✅ Fixed layout

**Configuration**: Edit `visualizer_static.py` to set `_unique_ids` and graph layouts.

---

## 🔍 How Data Flows

### 1. In Your Application

```python
# Your operator emits data
data = np.random.rand(64, 64)
op_output.emit(dict(result=as_tensor(data)), "out")
```

### 2. NATS Logger Intercepts

The logger automatically:
1. Receives the tensor from Holoscan runtime
2. Extracts metadata (shape, dtype, strides)
3. Serializes to FlatBuffers format:

```
FlatBuffers Message {
    unique_id: "source.out"
    timestamp: 1234567890
    payload: Tensor {
        shape: [64, 64, 1]
        dtype: FLOAT32
        data: [raw bytes]
    }
}
```

4. Publishes to NATS: `your_app.data`

### 3. Visualizer Subscribes

```python
# In visualizer
message = await nats_client.request("your_app.data")
data = tensor_to_numpy(message.Payload())  # Deserialize
# data is now a NumPy array: (64, 64)

# Render based on dimensionality
if data.ndim >= 2:
    fig = px.imshow(data)  # Heatmap
else:
    fig = px.line(y=data)  # Line plot
```

---

## 📊 Supported Data Types

### Tensor Shapes

The visualizer automatically handles:

| Shape | Visualization | Example Use Case |
|-------|---------------|------------------|
| `(N,)` | Line plot | Time series, 1D signal |
| `(H, W)` | Heatmap | 2D spatial data, Ising model |
| `(H, W, 1)` | Heatmap (squeezed) | Single-channel image |
| `(H, W, 3)` | RGB image* | Color image |

*Note: RGB image support requires custom graph component.

### Data Types

Supported NumPy dtypes:
- `float32`, `float64`
- `int8`, `int16`, `int32`, `int64`
- `uint8`, `uint16`, `uint32`, `uint64`

---

## 🛠️ CMakeLists.txt Configuration

Your application needs to build the NATS logger and FlatBuffers schemas:

```cmake
# your_app/CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(your_app)

find_package(holoscan 2.0 REQUIRED CONFIG)

# FlatBuffers for serialization
find_package(Flatbuffers REQUIRED)

# NATS client library
find_package(nats REQUIRED)

# Build FlatBuffers schemas
set(FB_SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/schemas)
set(FB_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/flatbuffers)

add_custom_command(
    OUTPUT ${FB_OUTPUT_DIR}/message_generated.h ${FB_OUTPUT_DIR}/tensor_generated.h
    COMMAND flatc --cpp --python -o ${FB_OUTPUT_DIR}
            ${FB_SCHEMA_DIR}/message.fbs
            ${FB_SCHEMA_DIR}/tensor.fbs
    DEPENDS ${FB_SCHEMA_DIR}/message.fbs ${FB_SCHEMA_DIR}/tensor.fbs
    COMMENT "Generating FlatBuffers code"
)

# NATS Logger library
add_library(nats_logger SHARED
    cpp/nats_logger.cpp
    cpp/create_tensor.cpp
    ${FB_OUTPUT_DIR}/message_generated.h
    ${FB_OUTPUT_DIR}/tensor_generated.h
)

target_include_directories(nats_logger PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/cpp
    ${FB_OUTPUT_DIR}
)

target_link_libraries(nats_logger
    holoscan::core
    flatbuffers::flatbuffers
    nats
)

# Python bindings
pybind11_add_module(nats_logger_pybind
    python/nats_logger_pybind.cpp
)

target_link_libraries(nats_logger_pybind PRIVATE
    holoscan::core
    nats_logger
)

# Your application
add_executable(your_app
    src/main.cpp
)

target_link_libraries(your_app
    holoscan::core
    nats_logger
)
```

---

## 📝 metadata.json Configuration

```json
{
    "application": {
        "title": "Your Application",
        "version": "1.0",
        "inputFormats": [],
        "outputFormats": []
    },
    "resources": {
        "cpu": 1,
        "gpu": 0,
        "memory": "2Gi"
    },
    "modes": {
        "standard": {
            "description": "Run your application",
            "run": {
                "command": "python3 <holohub_app_source>/python/your_app.py",
                "workdir": "holohub_app_bin"
            }
        },
        "visualizer": {
            "description": "Run web visualizer",
            "run": {
                "command": "python3 <holohub_app_source>/visualizer/visualizer_dynamic.py",
                "env": {
                    "PYTHONPATH": "<holohub_app_bin>/../flatbuffers:<PYTHONPATH>"
                },
                "workdir": "holohub_app_source"
            }
        }
    }
}
```

---

## 🐛 Troubleshooting

### "NATS connection refused"

**Problem**: NATS server not running

**Solution**:
```bash
cd applications/my_pipeline_visualizer
./start_nats_server.sh
```

### "ModuleNotFoundError: No module named 'Message'"

**Problem**: FlatBuffers Python modules not in PYTHONPATH

**Solution**:
```bash
export PYTHONPATH=/path/to/build/your_app/../flatbuffers:$PYTHONPATH
```

Or use the `holohub run` command with the visualizer mode.

### "Data shows as 1D line plot instead of 2D heatmap"

**Problem**: Visualizer not detecting 2D data

**Solution**: Check tensor shape in your operator:
```python
# Ensure shape is (H, W) or (H, W, 1), not flattened
data = np.random.rand(64, 64)  # ✅ Good
# not: data = np.random.rand(64*64)  # ❌ Bad
```

### "No data appearing in visualizer"

**Checklist**:
1. ✅ NATS server running? (`docker ps | grep nats`)
2. ✅ Application running with logger enabled? (check `disable_logger: false`)
3. ✅ Correct subject prefix? (match `subject_prefix` in app and visualizer)
4. ✅ Firewall blocking port 4222?

---

## 🎯 Best Practices

### 1. Use Unique Subject Prefixes

```python
# Good: Unique per application
subject_prefix = "medical_imaging_app"
subject_prefix = "robotics_control_v2"

# Bad: Generic names cause conflicts
subject_prefix = "app"
subject_prefix = "test"
```

### 2. Rate Limit for Performance

```python
# For high-frequency data (>60Hz), set rate limit
nats_logger = NatsLogger(
    self,
    publish_rate=30.0,  # Limit to 30 Hz for visualization
    # ...
)
```

### 3. Disable Logger in Production

```yaml
# config.yaml
application:
  disable_logger: true  # No overhead when not needed
```

```python
# In your app
if not self.disable_logger:
    self.add_data_logger(nats_logger)
```

### 4. Reuse Infrastructure

- ✅ One NATS server for all apps
- ✅ One dynamic visualizer for all apps
- ✅ Share FlatBuffers schemas across projects

### 5. Version Your Schemas

```
schemas/
├── v1/
│   ├── message.fbs
│   └── tensor.fbs
└── v2/  # Future changes
    └── ...
```

---

## 🌟 Advanced: Make NATS Logger a Shared Operator

For the Holohub community, consider moving NATS logger to a shared location:

```bash
holohub/
├── operators/
│   └── nats_logger/               # ← Shared operator
│       ├── cpp/
│       ├── python/
│       ├── schemas/
│       └── CMakeLists.txt
└── applications/
    └── your_app/                  # ← Just reference it
        └── your_app.py
```

Then everyone can use:
```python
from holohub.operators.nats_logger import NatsLogger
```

---

## 📚 Related Documentation

- [NATS.io Documentation](https://docs.nats.io/)
- [FlatBuffers Documentation](https://google.github.io/flatbuffers/)
- [Holoscan SDK Documentation](https://docs.nvidia.com/holoscan/)
- [Plotly/Dash Documentation](https://dash.plotly.com/)

---

## 🤝 Contributing

If you improve the NATS logger or visualizer:

1. Test with multiple data types and shapes
2. Update this documentation
3. Consider making it a shared Holohub operator
4. Submit a pull request!

---

## 📄 License

This component follows the Holohub repository license.

---

**Questions or Issues?**

- Check existing Holohub applications for examples
- Review FlatBuffers schema definitions
- Test with the dynamic visualizer first (simplest setup)
- Monitor NATS traffic: `nats sub "your_app.>"`

Happy visualizing! 🎉

