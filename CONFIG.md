# Earthquake ShakeMap System - Configuration Guide

## System Overview

The Earthquake ShakeMap System is designed to:
- **Parse** earthquake XML data from the Caucasus Seismic Institute
- **Generate** ShakeMap visualizations (static PNG and interactive HTML)
- **Analyze** earthquake catalogs with comprehensive statistics
- **Compare** multiple earthquake events across regions and time periods

## File Structure

```
shakemap/
├── earthquake_data.py           # Core data structures and XML parsing
├── shakemap_generator.py        # ShakeMap visualization engine
├── analysis.py                  # Statistical analysis and plotting
├── main.py                      # CLI interface and orchestration
├── generate_example_data.py     # Example data generation
├── examples.py                  # Usage examples
├── setup.sh                     # Automated setup script
├── requirements.txt             # Python dependencies
├── README.md                    # Full documentation
├── CONFIG.md                    # This file
└── example_data/
    ├── example_events/          # Pre-made example earthquakes
    └── synthetic_catalog/       # Synthetic earthquake data
```

## Installation Steps

### Option A: Automated Setup (Recommended)

```bash
cd /home/giorgi-chakhnashvili/Desktop/shakemap
chmod +x setup.sh
./setup.sh
```

### Option B: Manual Setup

1. **Install dependencies:**
```bash
pip3 install -r requirements.txt
```

2. **Create example data:**
```bash
python3 generate_example_data.py
```

3. **Generate test ShakeMaps:**
```bash
python3 main.py -m test --create-example
```

## Configuration Options

### ShakeMap Grid Resolution

In `shakemap_generator.py`, adjust the `grid_spacing` parameter:

```python
# Fine resolution (slower, higher quality)
generator = ShakeMapGenerator(event, grid_spacing=0.01)

# Medium resolution (balanced)
generator = ShakeMapGenerator(event, grid_spacing=0.05)

# Coarse resolution (faster, lower quality)
generator = ShakeMapGenerator(event, grid_spacing=0.1)
```

### Intensity Color Scheme

The `INTENSITY_COLORS` dictionary in `shakemap_generator.py` defines the color palette:

```python
INTENSITY_COLORS = {
    'I': '#ffffff',      # Not felt (White)
    'II': '#afe5ff',     # Weak (Light Blue)
    # ... etc
    'X': '#800000'       # Extreme (Dark Red)
}
```

### Depth Attenuation Model

In `earthquake_data.py`, the `calculate_magnitude_at_distance()` function uses:

$$M_{att} = M_0 - 0.5 \log_{10}(d)$$

Where:
- $M_{att}$ = Attenuated magnitude
- $M_0$ = Epicenter magnitude
- $d$ = Distance from epicenter (km)

Modify the coefficient (0.5) to adjust attenuation:
- **Lower values** = slower intensity decay (more felt ground motion)
- **Higher values** = faster intensity decay (less widespread shaking)

## Input Data Configuration

### Expected XML Format

Your earthquake XML files should follow this structure:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE earthquake SYSTEM "earthquake.dtd">
<earthquake 
    id="event_id"
    lat="latitude"
    lon="longitude"
    depth="depth_km"
    mag="magnitude"
    year="YYYY"
    month="MM"
    day="DD"
    hour="HH"
    minute="MM"
    second="SS"
    timezone="GMT"
    locstring="Location description"
    created="unix_timestamp"/>
```

### Attribute Details

| Attribute | Type | Range | Notes |
|-----------|------|-------|-------|
| id | String | - | Unique identifier |
| lat | Float | -90 to 90 | Latitude in decimal degrees |
| lon | Float | -180 to 180 | Longitude in decimal degrees |
| depth | Float | 0-700 | Depth in kilometers |
| mag | Float | 1-10 | Magnitude (Mw recommended) |
| year | Integer | 1900-2100 | Year |
| month | Integer | 1-12 | Month |
| day | Integer | 1-31 | Day |
| hour | Integer | 0-23 | Hour (24-h format) |
| minute | Integer | 0-59 | Minute |
| second | Float | 0-60 | Second |
| timezone | String | "GMT", "UTC" | Time zone |
| locstring | String | - | Human-readable location |
| created | Integer | - | Unix timestamp |

## Output Configuration

### Static Map (PNG) Settings

In `shakemap_generator.py`, modify `create_static_shakemap()`:

```python
# Change figure size
figsize=(16, 14)  # Default: (14, 10)

# Change DPI for resolution
plt.savefig(output_path, dpi=300, bbox_inches='tight')  # Default: dpi=150
```

### Interactive Map (HTML) Settings

In `shakemap_generator.py`, modify `create_interactive_map()`:

```python
# Change zoom level
zoom_start=8  # Default: 7

# Change base tiles
tiles='OpenStreetMap'  # Also try: 'Stamen Terrain', 'CartoDB positron'

# Adjust heatmap parameters
HeatMap(heat_data, radius=20, blur=30, max_zoom=1)
```

## Processing Modes

### Mode: test
Generates test ShakeMaps from example data.
```bash
python3 main.py -m test
```

### Mode: batch
Processes earthquake XML files from a directory.
```bash
python3 main.py -m batch -d /path/to/events -o results/
```

### Mode: downloads
Automatically processes files from your Downloads directory.
```bash
python3 main.py -m downloads
```

## Analysis Configuration

### Statistical Analysis

In `analysis.py`, customize analysis:

```python
from analysis import EarthquakeAnalysis

analyzer = EarthquakeAnalysis(events)

# Print summary
analyzer.print_summary()

# Generate all plots
analyzer.generate_all_plots(output_dir='my_analysis')

# Individual plots
analyzer.magnitude_distribution('mag_dist.png')
analyzer.depth_distribution('depth_dist.png')
analyzer.magnitude_vs_depth('mag_vs_depth.png')
analyzer.temporal_distribution('temporal.png')
```

### Earthquake Classifications

The analysis module categorizes events as:

**By Depth:**
- Shallow: < 70 km
- Intermediate: 70-300 km
- Deep: ≥ 300 km

**By Magnitude:**
- Micro: < 2.0
- Very Minor: 2.0-3.0
- Minor: 3.0-4.0
- Light: 4.0-5.0
- Moderate & Strong: ≥ 5.0

## Region-Specific Settings

### For Caucasus Region (default)

```python
batch_process_events(
    directory='/home/giorgi-chakhnashvili/Downloads/shakemaps',
    lat_range=(40.0, 43.0),
    lon_range=(42.0, 47.0)
)
```

### For Custom Region

Modify in `main.py` or `generate_example_data.py`:

```python
# Custom geographic extent
extent = (min_lat, max_lat, min_lon, max_lon)

# Example: Japan region
create_synthetic_catalog(
    num_events=100,
    lat_range=(30.0, 45.0),
    lon_range=(130.0, 145.0),
    mag_range=(1.5, 7.0)
)
```

## Performance Tuning

### For Large Catalogs (>1000 events)

```python
# Use coarser grid
generator = ShakeMapGenerator(event, grid_spacing=0.1)

# Reduce plot quality
plt.savefig(output_path, dpi=100)  # Instead of 150

# Process in batches
for event in events[batch_start:batch_end]:
    process_event(event)
```

### For High-Resolution Maps

```python
# Use finer grid
generator = ShakeMapGenerator(event, grid_spacing=0.01)

# Increase DPI
plt.savefig(output_path, dpi=300)

# Larger figure size
figsize=(20, 16)
```

## Troubleshooting Configuration

### Q: ShakeMaps look too blocky?
**A:** Decrease `grid_spacing`, increase figure `dpi`.

### Q: Processing takes too long?
**A:** Increase `grid_spacing`, decrease `dpi`, use coarser grid.

### Q: Colors don't match USGS ShakeMaps?
**A:** Adjust `INTENSITY_COLORS` dictionary or attenuation model parameters.

### Q: Interactive maps are too large?
**A:** Reduce precision of heat_data points or use lower zoom_start.

## Environmental Variables (Optional)

You can set these for persistent configuration:

```bash
# Set output directory
export SHAKEMAP_OUTPUT_DIR="/path/to/outputs"

# Set data directory
export SHAKEMAP_DATA_DIR="/path/to/events"

# Set log level
export SHAKEMAP_LOG_LEVEL="INFO"
```

## Advanced: Custom Intensity Models

Replace the attenuation function in `earthquake_data.py`:

```python
def calculate_magnitude_at_distance(epicenter_magnitude, distance_km):
    """Custom attenuation model"""
    if distance_km < 1:
        return epicenter_magnitude
    
    # Your custom model here
    attenuation = epicenter_magnitude - (0.3 * np.log10(distance_km + 1))
    return max(attenuation, 0)
```

## System Requirements

- **Python**: 3.7 or higher
- **RAM**: 2 GB minimum (4+ GB recommended for large catalogs)
- **Disk Space**: 500 MB for example data + outputs
- **CPU**: Multi-core processor recommended for batch processing

## Next Steps

1. Run the automated setup: `./setup.sh`
2. Check the generated outputs in `outputs/test_maps/`
3. Study the [README.md](README.md) for detailed documentation
4. Review [examples.py](examples.py) for usage patterns
5. Try batch processing your earthquake data
6. Customize the system for your specific needs

## Support

For technical issues:
1. Check [README.md](README.md) Troubleshooting section
2. Review log output for error messages
3. Verify XML format matches specification
4. Check Python version compatibility

---

**Last Updated**: February 2026
**Version**: 1.0
**Maintained by**: Georgian Seismology Institute
