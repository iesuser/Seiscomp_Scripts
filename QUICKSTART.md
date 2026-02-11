# Earthquake ShakeMap System - Quick Start Guide

## 🚀 Get Started in 2 Minutes

### Step 1: Install & Setup (1 minute)
```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
chmod +x setup.sh
./setup.sh
```

This script will:
- ✓ Create a Python virtual environment
- ✓ Check your Python installation
- ✓ Install all required packages
- ✓ Create example earthquake data
- ✓ Generate sample ShakeMaps
- ✓ Create output directory

### Step 2: Activate Virtual Environment & View Results (1 minute)

After setup completes, activate the virtual environment:
```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
source venv/bin/activate     # Note: Do this every time you use the system
```

Open these files in your browser:

```
outputs/test_maps/
├── example_001_interactive.html   ← Open this! (Interactive map)
├── example_001_shakemap.png       ← Static map
├── example_002_interactive.html
├── example_002_shakemap.png
├── example_003_interactive.html
├── example_003_shakemap.png
├── example_004_interactive.html
├── example_004_shakemap.png
└── all_events_comparison.html     ← Compare all events
```

---

## 📊 What is a ShakeMap?

A ShakeMap visualizes earthquake ground motion intensity across a region. The color scale shows:

- **White/Blue**: Weak shaking (Magnitude I-IV)
- **Yellow/Orange**: Moderate-strong shaking (Magnitude V-VII)
- **Red/Dark Red**: Severe-extreme shaking (Magnitude VIII-X)

---

## 🎯 Common Tasks

### Task 1: Process Your Downloaded Earthquakes
```bash
source venv/bin/activate
python main.py -m downloads
```
This automatically finds and processes all earthquakes in your Downloads folder.

### Task 2: Process a Specific Event
```bash
source venv/bin/activate
python main.py -m batch -d /home/giorgi-chakhnashvili/Downloads/shakemaps/ies2026cjfc
```

### Task 3: Analyze a Catalog
```bash
source venv/bin/activate
python examples.py 3
```
This generates magnitude, depth, and temporal analysis plots.

### Task 4: Create Custom Earthquake
```bash
source venv/bin/activate
python examples.py 5
```
Generate ShakeMaps for a custom earthquake event.

---

## 📁 System Components

### Core Modules

**earthquake_data.py** - Data handling
- Reads/writes XML earthquake files
- Stores earthquake information
- Calculates distances and attenuation

**shakemap_generator.py** - Visualization
- Creates PNG ShakeMaps
- Generates interactive HTML maps
- Compares multiple events

**analysis.py** - Statistics
- Magnitude/depth analysis
- Temporal distribution
- Catalog statistics

**main.py** - Command-line interface
- Batch processing
- Orchestrates all modules
- Generates reports

---

## 💾 Data Format

Your earthquake XML files should look like:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE earthquake SYSTEM "earthquake.dtd">
<earthquake 
    id="ies2026cjfc"
    lat="41.074"
    lon="43.8527"
    depth="10.5"
    mag="3.5"
    year="2026"
    month="2"
    day="10"
    hour="14"
    minute="30"
    second="45"
    timezone="GMT"
    locstring="Central Caucasus"
    created="1770125698"/>
```

**Key attributes:**
- `lat`, `lon`: Epicenter location (decimal degrees)
- `depth`: Earthquake depth in kilometers
- `mag`: Magnitude (moment magnitude Mw preferred)
- Other fields: Date and time of the event

---

## 🔧 Examples

### Example 1: Quick ShakeMap
```python
source venv/bin/activate
python -c "
from earthquake_data import EarthquakeXMLParser
from shakemap_generator import ShakeMapGenerator

# Load event
event = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_001.xml')

# Create ShakeMap
generator = ShakeMapGenerator(event)
generator.create_static_shakemap('my_shakemap.png')
generator.create_interactive_map('my_map.html')
"
```

### Example 2: Batch Analysis
```bash
source venv/bin/activate
python << 'EOF'
from pathlib import Path
from earthquake_data import EarthquakeXMLParser
from analysis import EarthquakeAnalysis

# Load all events
events = [
    EarthquakeXMLParser.parse_event_xml(f) 
    for f in Path('example_data/example_events').glob('*.xml')
]

# Analyze
analyzer = EarthquakeAnalysis(events)
analyzer.print_summary()
analyzer.generate_all_plots()
EOF
```

### Example 3: Custom Event
```python
source venv/bin/activate
python << 'EOF'
from earthquake_data import EarthquakeEvent, EarthquakeXMLParser
from datetime import datetime

# Create event
event = EarthquakeEvent(
    event_id='my_event_2026',
    latitude=41.5,
    longitude=44.0,
    depth=15.0,
    magnitude=4.5,
    year=2026, month=2, day=10,
    hour=12, minute=30, second=0,
    timezone='GMT',
    location_string='My Location',
    created_timestamp=int(datetime.now().timestamp())
)

# Save & visualize
EarthquakeXMLParser.create_event_xml(event, 'my_event.xml')
# ... then use ShakeMapGenerator
EOF
```

---

## 📊 Output Examples

### Static ShakeMap (PNG)
- High-quality contour map
- Shows intensity colors
- Plots epicenter location
- Perfect for reports and presentations

### Interactive Map (HTML)
- Click-enabled map
- Heatmap overlay
- Event information popup
- Zoom and pan controls

### Comparison Map
- Multiple earthquakes on one map
- Size shows magnitude
- Color shows intensity
- Easy event comparison

### Analysis Plots
- Magnitude distribution
- Depth distribution
- Magnitude vs depth
- Temporal patterns

---

## ⚙️ Configuration

### Adjust Map Resolution
In code:
```bash
source venv/bin/activate
python << 'EOF'
from earthquake_data import EarthquakeXMLParser
from shakemap_generator import ShakeMapGenerator

event = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_001.xml')

# Fine resolution (slower, better quality)
generator = ShakeMapGenerator(event, grid_spacing=0.02)

# Fast resolution (quicker, lower quality)
generator = ShakeMapGenerator(event, grid_spacing=0.1)
EOF
```

### Change Colors
Edit `INTENSITY_COLORS` in `shakemap_generator.py` to customize the color palette.

### Custom Extent
```bash
source venv/bin/activate
python << 'EOF'
# Define map boundaries
extent = (min_lat, max_lat, min_lon, max_lon)
generator.create_static_shakemap('map.png', extent=extent)
EOF
```

---

## 🐛 Troubleshooting

### Problem: "No module named 'obspy'"
**Solution:** Run `pip3 install -r requirements.txt`

### Problem: "No event files found"
**Solution:** Use `--create-example` flag or provide correct directory path

### Problem: ShakeMaps take too long to generate
**Solution:** Increase `grid_spacing` (0.05 → 0.1) or reduce `dpi` (150 → 100)

### Problem: Map looks blocky/low resolution
**Solution:** Decrease `grid_spacing` (0.1 → 0.02) or increase `dpi` (150 → 300)

---

## 📚 Learn More

- **README.md** - Full documentation
- **CONFIG.md** - Configuration guide
- **examples.py** - More usage examples

---

## 📞 Support

If you encounter issues:
1. Check the error message for hints
2. Review the README.md troubleshooting section
3. Verify your XML files are properly formatted
4. Ensure Python 3.7+ is installed

---

## 🎓 What Next?

1. Run the interactive maps in your browser
2. Explore the analysis.py examples
3. Try processing your own earthquake data
4. Customize the color schemes and settings
5. Integrate into your seismology workflow

---

**Happy mapping! 🗺️⚡**

*Earthquake ShakeMap System v1.0*
*Georgian Seismology Institute*
