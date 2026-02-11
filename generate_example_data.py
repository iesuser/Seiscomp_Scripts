"""
Generate example earthquake data for testing and demonstration.
"""

import os
from datetime import datetime, timedelta
import random
import xml.etree.ElementTree as ET
from earthquake_data import EarthquakeEvent, EarthquakeXMLParser


def create_example_events() -> list:
    """
    Create example earthquake events for the Caucasus region.
    
    Returns:
        List of EarthquakeEvent objects
    """
    events = [
        EarthquakeEvent(
            event_id='example_001',
            latitude=41.5,
            longitude=44.0,
            depth=12.5,
            magnitude=3.5,
            year=2026,
            month=2,
            day=10,
            hour=14,
            minute=30,
            second=45,
            timezone='GMT',
            location_string='Central Caucasus Example Event',
            created_timestamp=int(datetime.now().timestamp())
        ),
        EarthquakeEvent(
            event_id='example_002',
            latitude=40.8,
            longitude=43.5,
            depth=18.0,
            magnitude=4.2,
            year=2026,
            month=2,
            day=9,
            hour=8,
            minute=15,
            second=20,
            timezone='GMT',
            location_string='South Caucasus Example Event',
            created_timestamp=int((datetime.now() - timedelta(days=1)).timestamp())
        ),
        EarthquakeEvent(
            event_id='example_003',
            latitude=42.3,
            longitude=45.5,
            depth=8.5,
            magnitude=2.8,
            year=2026,
            month=2,
            day=8,
            hour=22,
            minute=45,
            second=10,
            timezone='GMT',
            location_string='North Caucasus Example Event',
            created_timestamp=int((datetime.now() - timedelta(days=2)).timestamp())
        ),
        EarthquakeEvent(
            event_id='example_004',
            latitude=40.5,
            longitude=46.0,
            depth=15.0,
            magnitude=3.8,
            year=2026,
            month=2,
            day=7,
            hour=16,
            minute=20,
            second=30,
            timezone='GMT',
            location_string='Eastern Caucasus Example Event',
            created_timestamp=int((datetime.now() - timedelta(days=3)).timestamp())
        ),
    ]
    return events


def create_synthetic_catalog(num_events: int = 50, 
                            lat_range: tuple = (40.0, 43.0),
                            lon_range: tuple = (42.0, 47.0),
                            mag_range: tuple = (1.5, 5.0)) -> list:
    """
    Create a synthetic earthquake catalog with random events.
    
    Args:
        num_events: Number of events to generate
        lat_range: Latitude range (min, max)
        lon_range: Longitude range (min, max)
        mag_range: Magnitude range (min, max)
        
    Returns:
        List of EarthquakeEvent objects
    """
    events = []
    base_date = datetime(2026, 1, 1)
    
    for i in range(num_events):
        # Random time over 40 days
        random_days = random.randint(0, 40)
        random_seconds = random.randint(0, 86400)
        event_time = base_date + timedelta(days=random_days, seconds=random_seconds)
        
        event = EarthquakeEvent(
            event_id=f'synthetic_{i:04d}',
            latitude=random.uniform(lat_range[0], lat_range[1]),
            longitude=random.uniform(lon_range[0], lon_range[1]),
            depth=random.uniform(5, 100),  # 5-100 km depth
            magnitude=random.uniform(mag_range[0], mag_range[1]),
            year=event_time.year,
            month=event_time.month,
            day=event_time.day,
            hour=event_time.hour,
            minute=event_time.minute,
            second=event_time.second,
            timezone='GMT',
            location_string=f'Synthetic Event {i:04d}',
            created_timestamp=int(datetime.now().timestamp())
        )
        events.append(event)
    
    return events


def save_events_to_files(events: list, output_dir: str):
    """
    Save earthquake events to XML files.
    
    Args:
        events: List of EarthquakeEvent objects
        output_dir: Directory to save XML files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for event in events:
        filename = os.path.join(output_dir, f'{event.event_id}.xml')
        EarthquakeXMLParser.create_event_xml(event, filename)
        print(f"Created {filename}")


def create_example_dataset():
    """
    Create a complete example dataset with example events only.
    (Synthetic events are disabled - use real earthquake data instead)
    """
    # Create directories
    example_dir = '/home/giorgi-chakhnashvili/Desktop/shakemap/example_data'
    
    print("Generating example earthquake events...")
    example_events = create_example_events()
    save_events_to_files(example_events, os.path.join(example_dir, 'example_events'))
    
    print("\nExample dataset created successfully!")
    print("Note: Synthetic earthquake generation is disabled.")
    print("Use your real earthquake data instead!")
    return example_events


if __name__ == '__main__':
    create_example_dataset()
