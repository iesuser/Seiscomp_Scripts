# Earthquake ShakeMap System - File Inventory & Architecture

## 📋 Complete File Listing

### 🐍 Python Scripts (Core Application)

| File | Purpose | Key Classes | Lines |
|------|---------|-------------|-------|
| **earthquake_data.py** | Core data structures and XML parsing | `EarthquakeEvent`, `EarthquakeXMLParser` | ~250 |
| **shakemap_generator.py** | ShakeMap visualization engine | `ShakeMapGenerator` | ~400 |
| **analysis.py** | Statistical analysis and plotting | `EarthquakeAnalysis` | ~350 |
| **main.py** | CLI interface and orchestration | - | ~300 |
| **generate_example_data.py** | Example data generation | - | ~200 |
| **examples.py** | Usage examples and tutorials | - | ~300 |

### 📄 Documentation Files

| File | Content | Audience |
|------|---------|----------|
| **README.md** | Complete system documentation | Developers & operators |
| **QUICKSTART.md** | 2-minute quick start guide | New users |
| **CONFIG.md** | Configuration and customization | Power users |
| **FILE_INVENTORY.md** | This file - system overview | Developers |

### ⚙️ Configuration & Setup

| File | Purpose |
|------|---------|
| **requirements.txt** | Python package dependencies |
| **setup.sh** | Automated installation script |

### 📊 Example Data

| Location | Files | Purpose |
|----------|-------|---------|
| `example_data/example_events/` | example_001.xml - example_004.xml | Pre-made earthquake examples |
| `example_data/synthetic_catalog/` | (generated at runtime) | Synthetic earthquake catalog |

---

## 🏗️ System Architecture

```
EARTHQUAKE SHAKEMAP SYSTEM
│
├─ Input Layer
│  ├─ XML Earthquake Files (your data)
│  └─ Example Data (example_data/)
│
├─ Data Processing Layer (earthquake_data.py)
│  ├─ EarthquakeXMLParser
│  ├─ EarthquakeEvent
│  ├─ Distance Calculations
│  └─ Attenuation Models
│
├─ Visualization Layer (shakemap_generator.py)
│  ├─ Static ShakeMaps (PNG/contours)
│  ├─ Interactive Maps (Folium/HTML)
│  └─ Comparison Maps (multiple events)
│
├─ Analysis Layer (analysis.py)
│  ├─ Statistical Calculations
│  ├─ Classification (shallow/deep, etc)
│  └─ Plot Generation
│
├─ Orchestration Layer (main.py)
│  ├─ CLI Interface
│  ├─ Batch Processing
│  └─ Mode Handlers (test/batch/downloads)
│
└─ Output Layer
   ├─ PNG ShakeMaps
   ├─ HTML Interactive Maps
   ├─ Analysis Plots
   └─ Summary Statistics
```

---

## 📚 Module Dependencies

```python
# External Dependencies (in requirements.txt)
obspy          # Seismology data processing
numpy          # Numerical computing
matplotlib     # Static visualization
scipy          # Scientific computing
folium         # Interactive maps
pandas         # Data manipulation
lxml           # XML processing
requests       # HTTP library

# Python Standard Library (no install needed)
xml.etree.ElementTree  # XML parsing
datetime               # Date/time handling
dataclasses           # Data structures
typing                # Type hints
argparse              # CLI argument parsing
os/pathlib            # File operations
numpy                 # Math operations
```

---

## 🔄 Data Flow

### Typical Processing Pipeline

```
1. Input XML Files
   ↓
2. EarthquakeXMLParser.parse_event_xml()
   ↓
3. EarthquakeEvent object(s) created
   ↓
4. ShakeMapGenerator.generate_intensity_grid()
   ↓
5. Parallel outputs:
   ├─ create_static_shakemap() → PNG
   ├─ create_interactive_map() → HTML
   └─ compare_earthquakes() → Comparison map
   ↓
6. Optional: EarthquakeAnalysis
   ├─ magnitude_distribution()
   ├─ depth_distribution()
   ├─ magnitude_vs_depth()
   └─ temporal_distribution()
   ↓
7. Output directory with all results
```

---

## 🎯 Main Functions & Classes

### earthquake_data.py

```python
class EarthquakeEvent:
    """Stores single earthquake information"""
    - event_id: str
    - latitude, longitude: float
    - depth, magnitude: float
    - year, month, day, hour, minute, second: int
    - get_datetime()
    - to_dict()

class EarthquakeXMLParser:
    - parse_event_xml(path) → EarthquakeEvent
    - create_event_xml(event, path) → None

def calculate_distance(lat1, lon1, lat2, lon2) → float
    """Haversine distance in km"""

def calculate_magnitude_at_distance(mag, dist) → float
    """Attenuation model"""
```

### shakemap_generator.py

```python
class ShakeMapGenerator:
    - __init__(event, grid_spacing)
    - generate_intensity_grid(extent) → numpy array
    - create_static_shakemap(path, extent)
    - create_interactive_map(path, extent)
    - INTENSITY_COLORS: dict

def compare_earthquakes(events, output_path)
    """Create comparison map of multiple events"""
```

### analysis.py

```python
class EarthquakeAnalysis:
    - __init__(events)
    - magnitude_statistics() → dict
    - depth_statistics() → dict
    - magnitude_distribution(path)
    - depth_distribution(path)
    - magnitude_vs_depth(path)
    - temporal_distribution(path)
    - print_summary()
    - generate_all_plots(dir)
```

### main.py

```python
def process_event_file(path, output_dir)
    """Process single Event XML"""

def batch_process_events(directory, pattern, output)
    """Process multiple events"""

def process_from_downloads()
    """Auto-process Downloads folder"""

def generate_test_maps()
    """Generate sample ShakeMaps"""

def main()
    """CLI entry point"""
    modes: test, batch, downloads
```

---

## 📊 Processing Modes

### Mode: test
- **Purpose**: Demonstration with example data
- **Command**: `python3 main.py -m test`
- **Output**: `outputs/test_maps/`
- **Use Case**: Verify system works, see example output

### Mode: batch
- **Purpose**: Process directory of earthquake files
- **Command**: `python3 main.py -m batch -d /path -o /output`
- **Output**: `outputs/` or custom directory
- **Use Case**: Process research data, institutional catalogs

### Mode: downloads
- **Purpose**: Auto-process Downloads folder
- **Command**: `python3 main.py -m downloads`
- **Output**: `outputs/downloads_shakemaps/`
- **Use Case**: Quick processing of downloaded events

---

## 🔌 Integration Points

### For IT Staff

**Use the CLI:**
```bash
python3 main.py -m batch -d /earthquake/data -o /tremor_maps
```

**Setup cron job for daily processing:**
```bash
0 2 * * * cd /shakemap && python3 main.py -m downloads >> logs/daily.log
```

### For Seismologists

**Use Python API:**
```python
from earthquake_data import EarthquakeXMLParser
from shakemap_generator import ShakeMapGenerator

event = EarthquakeXMLParser.parse_event_xml('event.xml')
generator = ShakeMapGenerator(event)
generator.create_static_shakemap('output.png')
```

### For Web Applications

**Generate HTML maps:**
```python
generator.create_interactive_map('earthquake.html')
# Embed HTML in your web application
```

---

## 💾 Output Structure

```
outputs/
├── test_maps/                    (test mode output)
│  ├── example_001_shakemap.png
│  ├── example_001_interactive.html
│  ├── example_002_shakemap.png
│  ├── example_002_interactive.html
│  └── all_events_comparison.html
│
├── downloads_shakemaps/          (downloads mode output)
│  ├── ies2026cjfc/
│  │  ├── ies2026cjfc_shakemap.png
│  │  └── ies2026cjfc_interactive.html
│  ├── ies2026bzmn/
│  │  ├── ies2026bzmn_shakemap.png
│  │  └── ies2026bzmn_interactive.html
│  └── comparison_map.html
│
└── batch_results/                (batch mode output)
   ├── event_id_1/
   ├── event_id_2/
   └── comparison_map.html
```

---

## 🎓 Learning Path

### Beginner
1. Read QUICKSTART.md (2 min)
2. Run `setup.sh` (5 min)
3. View generated maps in browser (2 min)
4. Total: ~10 minutes to see results

### Intermediate
1. Read README.md (20 min)
2. Study earthquake_data.py structure (10 min)
3. Run examples.py scripts (5 min)
4. Modify example data parameters (10 min)
5. Total: ~45 minutes to understand core

### Advanced
1. Read CONFIG.md (15 min)
2. Study all module code (30 min)
3. Customize attenuation models (20 min)
4. Implement custom analysis functions (30 min)
5. Integrate into existing systems (varies)

---

## 🚀 Deployment Checklist

- [ ] Python 3.7+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] setup.sh executed and completed
- [ ] Example ShakeMaps generated successfully
- [ ] Output directory created and populated
- [ ] HTML maps viewable in browser
- [ ] Read access to earthquake data files
- [ ] Write access to output directory
- [ ] Custom configuration completed (if needed)
- [ ] Backups of important earthquake data
- [ ] Documentation reviewed by team

---

## 📊 System Statistics

| Metric | Value |
|--------|-------|
| Total Python Code | ~1,400 lines |
| Total Documentation | ~2,000 lines |
| Number of Modules | 6 |
| Number of Classes | 4 |
| Number of Functions | 30+ |
| Example Earthquakes | 4 |
| Visualization Types | 3 (static, interactive, comparison) |
| Analysis Plots | 4 |
| Dependencies | 8 external packages |

---

## 🔧 Maintenance

### Regular Tasks
- Monitor output directory size
- Archive old ShakeMaps periodically
- Update example data as new events occur
- Review and update documentation

### Troubleshooting
- Check Python version compatibility
- Verify XML file format compliance
- Confirm file path permissions
- Review error logs for details

### Performance Optimization
- Adjust grid_spacing for balance
- Use batch processing for multiple events
- Consider database integration for catalog storage
- Cache generated maps for frequently accessed events

---

## 📞 Technical Support

### Quick Fixes
1. Missing dependencies → `pip install -r requirements.txt`
2. XML format issues → Validate against config/examples
3. Permission errors → Check file/directory permissions
4. Memory errors → Reduce grid_spacing or split batch

### Escalation
- For Python issues: Check Python documentation
- For seismology questions: Consult domain experts
- For system integration: Contact IT department

---

## 📝 Version History

**v1.0 (February 2026)**
- Initial release
- Core ShakeMap generation
- Interactive map support
- Statistical analysis module
- CLI interface
- Example data generation
- Full documentation

---

**Document Generated**: February 10, 2026
**System**: Earthquake ShakeMap v1.0
**Organization**: Georgian Seismology Institute
