"""
Example usage scripts for the Earthquake ShakeMap System.
"""

# EXAMPLE 1: Load and analyze a single earthquake event
def example_single_event():
    from shakemap.earthquake_data import EarthquakeXMLParser
    from shakemap.shakemap_generator import ShakeMapGenerator
    
    # Load earthquake event
    event = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_001.xml')
    
    print(f"Event: {event.event_id}")
    print(f"Magnitude: {event.magnitude}")
    print(f"Location: ({event.latitude}, {event.longitude})")
    print(f"Depth: {event.depth} km")
    
    # Generate ShakeMaps
    generator = ShakeMapGenerator(event)
    generator.create_static_shakemap('outputs/single_shakemap.png')
    generator.create_interactive_map('outputs/single_interactive_map.html')


# EXAMPLE 2: Batch process all example events
def example_batch_process():
    from pathlib import Path
    from shakemap.earthquake_data import EarthquakeXMLParser
    from shakemap.shakemap_generator import ShakeMapGenerator, compare_earthquakes
    
    # Load all example events
    events = []
    for xml_file in Path('example_data/example_events').glob('*.xml'):
        event = EarthquakeXMLParser.parse_event_xml(str(xml_file))
        events.append(event)
    
    print(f"Loaded {len(events)} events")
    
    # Generate individual ShakeMaps
    for event in events:
        generator = ShakeMapGenerator(event)
        generator.create_static_shakemap(f'outputs/{event.event_id}_map.png')
        generator.create_interactive_map(f'outputs/{event.event_id}_map.html')
    
    # Generate comparison map
    compare_earthquakes(events, 'outputs/batch_comparison.html')


# EXAMPLE 3: Statistical analysis of earthquake catalog
def example_statistics():
    from pathlib import Path
    from shakemap.earthquake_data import EarthquakeXMLParser
    from shakemap.analysis import EarthquakeAnalysis
    
    # Load all events
    events = []
    for xml_file in Path('example_data/example_events').glob('*.xml'):
        event = EarthquakeXMLParser.parse_event_xml(str(xml_file))
        events.append(event)
    
    # Analyze
    analyzer = EarthquakeAnalysis(events)
    analyzer.print_summary()
    analyzer.generate_all_plots('outputs/analysis')


# EXAMPLE 4: Generate synthetic earthquake catalog (DISABLED)
def example_synthetic_catalog():
    """
    Synthetic earthquake generation is disabled.
    Please use your real earthquake data instead!
    
    Location: /home/giorgi-chakhnashvili/Downloads/shakemaps/
    
    To process real earthquakes:
        python main.py -m downloads
    """
    print("\n" + "="*60)
    print("SYNTHETIC EARTHQUAKE GENERATION IS DISABLED")
    print("="*60)
    print("\nSynthetic data is not needed for your seismic institute.")
    print("You have real earthquake data available!")
    print("\nUse real earthquake data instead:")
    print("  - Location: ~/Downloads/shakemaps/")
    print("  - Command: python main.py -m downloads")
    print("\nFor analysis of real earthquakes, use examples 1, 2, and 3.")
    print("="*60 + "\n")


# EXAMPLE 5: Create custom earthquake event
def example_custom_event():
    from datetime import datetime
    from shakemap.earthquake_data import EarthquakeEvent, EarthquakeXMLParser
    from shakemap.shakemap_generator import ShakeMapGenerator
    
    # Create custom event
    event = EarthquakeEvent(
        event_id='custom_event_2026',
        latitude=41.5,
        longitude=44.0,
        depth=15.0,
        magnitude=4.5,
        year=2026,
        month=2,
        day=10,
        hour=12,
        minute=30,
        second=0,
        timezone='GMT',
        location_string='Custom Earthquake Event',
        created_timestamp=int(datetime.now().timestamp())
    )
    
    # Save to XML
    EarthquakeXMLParser.create_event_xml(event, 'outputs/custom_event.xml')
    
    # Generate ShakeMap
    generator = ShakeMapGenerator(event)
    generator.create_static_shakemap('outputs/custom_shakemap.png')
    generator.create_interactive_map('outputs/custom_interactive.html')


# EXAMPLE 6: Advanced ShakeMap customization
def example_advanced_shakemap():
    from shakemap.earthquake_data import EarthquakeXMLParser
    from shakemap.shakemap_generator import ShakeMapGenerator
    
    event = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_002.xml')
    
    # Create generator with finer grid
    generator = ShakeMapGenerator(event, grid_spacing=0.02)
    
    # Define custom extent (wider area)
    extent = (
        event.latitude - 5,
        event.latitude + 5,
        event.longitude - 5,
        event.longitude + 5
    )
    
    # Generate high-resolution maps
    generator.create_static_shakemap(
        'outputs/advanced_shakemap.png',
        extent=extent,
        figsize=(16, 12)
    )
    generator.create_interactive_map('outputs/advanced_interactive.html', extent=extent)


# EXAMPLE 7: Direct comparison of specific events
def example_specific_comparison():
    from shakemap.earthquake_data import EarthquakeXMLParser
    from shakemap.shakemap_generator import compare_earthquakes
    
    # Load specific events
    event1 = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_001.xml')
    event2 = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_002.xml')
    event3 = EarthquakeXMLParser.parse_event_xml('example_data/example_events/example_003.xml')
    
    # Compare
    compare_earthquakes([event1, event2, event3], 'outputs/specific_comparison.html')


if __name__ == '__main__':
    import sys
    
    examples = {
        '1': ('Single Event Analysis', example_single_event),
        '2': ('Batch Processing', example_batch_process),
        '3': ('Statistical Analysis', example_statistics),
        '4': ('Synthetic Catalog', example_synthetic_catalog),
        '5': ('Custom Event', example_custom_event),
        '6': ('Advanced ShakeMap', example_advanced_shakemap),
        '7': ('Specific Comparison', example_specific_comparison),
    }
    
    print("\nEarthquake ShakeMap System - Example Usage\n")
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}: {name}")
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        key = sys.argv[1]
        name, func = examples[key]
        print(f"\nRunning: {name}\n")
        func()
    else:
        print("\nUsage: python examples.py <number>")
        print("Example: python examples.py 1\n")
