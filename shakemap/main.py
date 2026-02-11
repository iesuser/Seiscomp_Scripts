"""
Main script for earthquake ShakeMap visualization and analysis.
"""

import os
import sys
import argparse
from pathlib import Path
from shakemap.earthquake_data import EarthquakeXMLParser, EarthquakeEvent
from shakemap.shakemap_generator import ShakeMapGenerator, compare_earthquakes
from generate_example_data import create_example_dataset


def process_event_file(event_file: str, output_dir: str):
    """
    Process a single earthquake event file and generate ShakeMaps.
    
    Args:
        event_file: Path to event.xml file
        output_dir: Directory to save outputs
    """
    print(f"\nProcessing event file: {event_file}")
    
    try:
        # Parse event
        event = EarthquakeXMLParser.parse_event_xml(event_file)
        print(f"Event ID: {event.event_id}")
        print(f"Magnitude: {event.magnitude}")
        print(f"Location: ({event.latitude:.4f}, {event.longitude:.4f})")
        print(f"Time: {event.get_datetime()}")

        # Create output directory for this event
        event_output_dir = os.path.join(output_dir, event.event_id)
        os.makedirs(event_output_dir, exist_ok=True)

        # Generate combined ShakeMap (HTML with embedded PNG and interactive map)
        combined_path = os.path.join(event_output_dir, f'{event.event_id}_combined_shakemap.html')
        generator = ShakeMapGenerator(event, grid_spacing=0.05)
        generator.create_combined_shakemap(combined_path)

        print(f"✓ Combined ShakeMap generated for {event.event_id}")
        return event
    except Exception as e:
        print(f"✗ Error processing {event_file}: {e}")
        return None


def batch_process_events(directory: str, pattern: str = '**/event.xml', output_dir: str = 'outputs'):
    """
    Process all earthquake events in a directory structure.
    
    Args:
        directory: Root directory to search for event files
        pattern: Glob pattern for finding event files
        output_dir: Directory to save outputs
    """
    print(f"Searching for earthquake files in {directory}")
    
    event_files = list(Path(directory).glob(pattern))
    print(f"Found {len(event_files)} event file(s)")
    
    if not event_files:
        print("No event files found. Creating example dataset...")
        create_example_dataset()
        event_files = list(Path('/home/giorgi-chakhnashvili/Desktop/shakemap/example_data').glob('**/*.xml'))
    
    os.makedirs(output_dir, exist_ok=True)
    
    events = []
    for event_file in event_files:
        event = process_event_file(str(event_file), output_dir)
        if event:
            events.append(event)
    
    # Create comparison map if multiple events
    if len(events) > 1:
        print("\nCreating comparison map of all events...")
        comparison_path = os.path.join(output_dir, 'comparison_map.html')
        compare_earthquakes(events, comparison_path)
    
    print(f"\n✓ Processing complete! Generated {len(events)} ShakeMaps")
    print(f"  Output directory: {output_dir}")
    
    return events


def process_from_downloads():
    """
    Process earthquake data from the user's Downloads directory.
    """
    base_dir = Path.home() / 'Downloads' / 'shakemaps'
    
    if base_dir.exists():
        print(f"Processing shakemaps from {base_dir}")
        events = batch_process_events(str(base_dir), output_dir='outputs/downloads_shakemaps')
    else:
        print(f"Downloads directory not found: {base_dir}")


def generate_test_maps():
    """
    Generate test ShakeMaps from example data.
    """
    print("=" * 60)
    print("GENERATING TEST SHAKEMAPS FROM EXAMPLE DATA")
    print("=" * 60)
    
    from generate_example_data import create_example_events
    
    events = create_example_events()
    os.makedirs('outputs/test_maps', exist_ok=True)
    
    for event in events:
        print(f"\nGenerating ShakeMap for {event.event_id}...")
        generator = ShakeMapGenerator(event, grid_spacing=0.05)
        
        extent = (
            event.latitude - 2,
            event.latitude + 2,
            event.longitude - 2,
            event.longitude + 2
        )
        
        static_path = f'outputs/test_maps/{event.event_id}_shakemap.png'
        interactive_path = f'outputs/test_maps/{event.event_id}_interactive.html'
        
        generator.create_static_shakemap(static_path, extent=extent)
        generator.create_interactive_map(interactive_path, extent=extent)
    
    # Generate comparison map
    comparison_path = 'outputs/test_maps/all_events_comparison.html'
    compare_earthquakes(events, comparison_path)
    
    print(f"\n✓ Test maps generated in 'outputs/test_maps/'")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Earthquake ShakeMap Generator - Visualization and analysis of seismic events'
    )
    
    parser.add_argument('-m', '--mode', 
                       choices=['test', 'batch', 'downloads'],
                       default='test',
                       help='Processing mode: test (example data), batch (directory), downloads (user downloads)')
    
    parser.add_argument('-d', '--directory',
                       help='Directory containing earthquake XML files (for batch mode)')
    
    parser.add_argument('-o', '--output',
                       default='outputs',
                       help='Output directory for generated ShakeMaps')
    
    parser.add_argument('--create-example',
                       action='store_true',
                       help='Create example earthquake dataset')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("EARTHQUAKE SHAKEMAP GENERATOR")
    print("=" * 60)
    
    if args.create_example:
        print("\nCreating example dataset...")
        create_example_dataset()
    
    if args.mode == 'test':
        generate_test_maps()
    elif args.mode == 'batch':
        if not args.directory:
            print("Error: --directory is required for batch mode")
            sys.exit(1)
        batch_process_events(args.directory, output_dir=args.output)
    elif args.mode == 'downloads':
        process_from_downloads()
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
