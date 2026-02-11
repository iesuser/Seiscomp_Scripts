# Earthquake ShakeMap Visualization System

A comprehensive Python system for processing, analyzing, and visualizing earthquake data from the Caucasus region using ShakeMaps.

## Features

- **Earthquake Data Processing**: Parse and process earthquake XML data
- **ShakeMap Generation**: Create both static and interactive earthquake intensity maps
- **Statistical Analysis**: Comprehensive analysis of earthquake catalogs
- **Visualization**: Multiple visualization types including magnitude distribution, depth analysis, and temporal patterns
- **Interactive Maps**: Folium-based interactive HTML maps with heatmaps
- **Batch Processing**: Process multiple earthquake events in batch
- **Example Data**: Includes example earthquake data and synthetic earthquake catalog generation

## System Architecture

```
shakemap/
├── earthquake_data.py        # Core earthquake data structures and parsing
├── shakemap_generator.py     # ShakeMap creation and visualization
├── analysis.py              # Statistical analysis module
├── main.py                  # Main entry point with CLI
├── generate_example_data.py # Example data generation
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── example_data/            # Generated example data (created on first run)
    ├── example_events/      # Example earthquake events
    └── synthetic_catalog/   # Synthetic earthquake catalog
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager
- ~500MB disk space

### Setup

1. Navigate to the shakemap directory:
```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
```

2. Run the automated setup script:
```bash
./setup.sh
```

This will:
- Create a Python virtual environment (required for Python 3.12+)
- Install all required dependencies
- Generate example earthquake data
- Create sample ShakeMaps
- Prepare the output directory

**Note**: The system uses a Python virtual environment (`venv/`) to isolate dependencies. See [VENV_GUIDE.md](VENV_GUIDE.md) for details.

## Usage

### Important: Activate Virtual Environment

Before using any commands, activate the Python virtual environment created during setup:

```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt. See [VENV_GUIDE.md](VENV_GUIDE.md) for more details.

### Quick Start - Generate Test ShakeMaps

```bash
python main.py -m test --create-example
```

This will:
- Create example earthquake dataset
- Generate ShakeMaps for each event
- Create comparison maps across all events
- Output files to `outputs/test_maps/`

### Batch Process Earthquake Files

```bash
python main.py -m batch -d /path/to/earthquake/files -o outputs/my_results
```

### OR Process Downloads

```bash
python main.py -m downloads
```

### Command-Line Options

```
usage: main.py [-h] [-m {test,batch,downloads}] [-d DIRECTORY] [-o OUTPUT] 
               [--create-example]

optional arguments:
  -h, --help            show this help message and exit
  -m {test,batch,downloads}, --mode {test,batch,downloads}
                        Processing mode: test, batch, or downloads
                        (default: test)
  -d DIRECTORY, --directory DIRECTORY
                        Directory containing earthquake XML files
  -o OUTPUT, --output OUTPUT
                        Output directory for generated ShakeMaps
                        (default: outputs)
  --create-example      Create example earthquake dataset
```

## Data Format

### Input XML Format

Earthquake events should be in the following XML format:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE earthquake SYSTEM "earthquake.dtd">
<earthquake 
    id="event_id"
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
    locstring="Location description"
    created="1770125698"/>
```

### Key Attributes
- **id**: Unique event identifier
- **lat**: Latitude in decimal degrees
- **lon**: Longitude in decimal degrees
- **depth**: Depth in kilometers
- **mag**: Magnitude (moment magnitude Mw recommended)
- **year, month, day, hour, minute, second**: Event time
- **timezone**: Time zone (typically "GMT")
- **locstring**: Location description
- **created**: Unix timestamp of when the event was recorded

## Modules

### earthquake_data.py
Core module for earthquake data handling:
- `EarthquakeEvent`: Data class representing an earthquake
- `EarthquakeXMLParser`: Parse and create earthquake XML files
- `calculate_distance()`: Haversine distance calculation
- `calculate_magnitude_at_distance()`: Attenuation model

### shakemap_generator.py
ShakeMap generation:
- `ShakeMapGenerator`: Main class for creating ShakeMaps
- `compare_earthquakes()`: Create comparison maps

**ShakeMap Types**:
1. **Static ShakeMap** (PNG): Contour maps with intensity coloring
2. **Interactive Map** (HTML): Folium-based with heatmap overlay

### analysis.py
Earthquake statistical analysis:
- `EarthquakeAnalysis`: Analysis class for earthquake catalogs
- Magnitude and depth distributions
- Temporal analysis
- Summary statistics and classifications

### main.py
Command-line interface and orchestration:
- Event file processing
- Batch operations
- Integration with all modules

### generate_example_data.py
Example data generation:
- `create_example_events()`: Pre-defined example events
- `create_synthetic_catalog()`: Generate random realistic events
- `save_events_to_files()`: Export events to XML

## Output Files

ShakeMaps are generated in the output directory with the following structure:

```
outputs/
└── event_id/
    ├── event_id_shakemap.png        # Static ShakeMap
    ├── event_id_interactive.html    # Interactive map
    └── event_id_comparison.html     # Comparison maps (if multiple events)
```

## Intensity Scale

The ShakeMaps use an intensity scale from I (Not felt) to X (Extreme):

| Level | Color | Description |
|-------|-------|-------------|
| I | White | Not felt |
| II-III | Light Blue | Weak |
| IV | Light Blue | Light |
| V | Cyan | Moderate |
| VI | Yellow | Strong |
| VII | Orange | Very strong |
| VIII-IX | Red | Severe-Violent |
| X | Dark Red | Extreme |

## Examples

### Example 1: Process All Downloaded ShakeMaps
```bash
source venv/bin/activate
python main.py -m downloads
```

### Example 2: Analyze Specific Earthquake Catalog
```bash
source venv/bin/activate
python main.py -m batch -d ~/Downloads/shakemaps/ies2026cjfc -o results/cjfc_analysis
```

### Example 3: Generate and Analyze Synthetic Catalog
```bash
source venv/bin/activate
python << 'EOF'
from generate_example_data import create_synthetic_catalog
from earthquake_data import EarthquakeXMLParser
from analysis import EarthquakeAnalysis

# Generate 100 synthetic events
events = create_synthetic_catalog(num_events=100)

# Analyze
analysis = EarthquakeAnalysis(events)
analysis.print_summary()
analysis.generate_all_plots('my_analysis')
EOF
```

## Advanced Usage

### Custom ShakeMap Parameters

```bash
source venv/bin/activate
python << 'EOF'
from earthquake_data import EarthquakeXMLParser
from shakemap_generator import ShakeMapGenerator

# Load event
event = EarthquakeXMLParser.parse_event_xml('event.xml')

# Create generator with custom grid spacing
generator = ShakeMapGenerator(event, grid_spacing=0.02)

# Define custom extent (wider area)
extent = (
    event.latitude - 5,
    event.latitude + 5,
    event.longitude - 5,
    event.longitude + 5
)

# Generate maps
generator.create_static_shakemap('shakemap.png', extent=extent)
generator.create_interactive_map('map.html', extent=extent)
EOF
```

## Dependencies

- **obspy**: Seismology data processing (optional, for advanced features)
- **numpy**: Numerical computations
- **matplotlib**: Plotting and visualization
- **scipy**: Scientific computing
- **folium**: Interactive maps
- **pandas**: Data manipulation
- **lxml**: XML processing
- **requests**: HTTP library

## Troubleshooting

### Issue: No XML files found
**Solution**: Use `--create-example` flag to generate example data

### Issue: Low-resolution output
**Solution**: Adjust `grid_spacing` parameter in `ShakeMapGenerator` (smaller = higher resolution, slower)

### Issue: Missing dependencies
**Solution**: Run `pip install -r requirements.txt`

### Issue: Memory error with large catalog
**Solution**: Process events in smaller batches or increase system memory

## Citation and References

- **ShakeMap**: USGS Earthquake Program - https://earthquake.usgs.gov/earthquakes/events/
- **Obspy**: Python framework for seismology - https://obspy.org/
- **Folium**: Python data visualization library - https://python-visualization.github.io/folium/

## Author

Created for Georgian Seismology Institute as part of earthquake data visualization and analysis system.

## License

This project is created for educational and research purposes.

## Support

For issues or questions about the shakemap system, please contact IT support at the seismology institute.
