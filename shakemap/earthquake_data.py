"""
Earthquake data processing utilities for seismic event analysis.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np


@dataclass
class EarthquakeEvent:
    """Data class representing a single earthquake event."""
    event_id: str
    latitude: float
    longitude: float
    depth: float  # in km
    magnitude: float
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    timezone: str
    location_string: str
    created_timestamp: int

    def get_datetime(self):
        """Convert event to datetime object."""
        return datetime(self.year, self.month, self.day, 
                       self.hour, self.minute, int(self.second))

    def to_dict(self) -> Dict:
        """Convert event to dictionary."""
        return {
            'id': self.event_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'depth': self.depth,
            'magnitude': self.magnitude,
            'datetime': self.get_datetime().isoformat(),
            'location': self.location_string
        }


class EarthquakeXMLParser:
    """Parser for earthquake XML files."""

    @staticmethod
    def parse_event_xml(xml_file_path: str) -> EarthquakeEvent:
        """
        Parse earthquake event from XML file.
        
        Args:
            xml_file_path: Path to the event.xml file
            
        Returns:
            EarthquakeEvent object
        """
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        if root.tag != 'earthquake':
            raise ValueError("Invalid XML format: root element must be 'earthquake'")
        
        attrs = root.attrib
        
        event = EarthquakeEvent(
            event_id=attrs.get('id', 'unknown'),
            latitude=float(attrs.get('lat', 0)),
            longitude=float(attrs.get('lon', 0)),
            depth=float(attrs.get('depth', 0)),
            magnitude=float(attrs.get('mag', 0)),
            year=int(attrs.get('year', 0)),
            month=int(attrs.get('month', 0)),
            day=int(attrs.get('day', 0)),
            hour=int(attrs.get('hour', 0)),
            minute=int(attrs.get('minute', 0)),
            second=float(attrs.get('second', 0)),
            timezone=attrs.get('timezone', 'GMT'),
            location_string=attrs.get('locstring', ''),
            created_timestamp=int(attrs.get('created', 0))
        )
        
        return event

    @staticmethod
    def create_event_xml(event: EarthquakeEvent, output_path: str) -> None:
        """
        Create an earthquake XML file from an EarthquakeEvent object.
        
        Args:
            event: EarthquakeEvent object
            output_path: Path where to save the XML file
        """
        earthquake_elem = ET.Element('earthquake')
        
        earthquake_elem.set('id', event.event_id)
        earthquake_elem.set('lat', str(event.latitude))
        earthquake_elem.set('lon', str(event.longitude))
        earthquake_elem.set('depth', str(event.depth))
        earthquake_elem.set('mag', str(event.magnitude))
        earthquake_elem.set('year', str(event.year))
        earthquake_elem.set('month', str(event.month))
        earthquake_elem.set('day', str(event.day))
        earthquake_elem.set('hour', str(event.hour))
        earthquake_elem.set('minute', str(event.minute))
        earthquake_elem.set('second', str(event.second))
        earthquake_elem.set('timezone', event.timezone)
        earthquake_elem.set('locstring', event.location_string)
        earthquake_elem.set('created', str(event.created_timestamp))
        
        tree = ET.ElementTree(earthquake_elem)
        tree.write(output_path, encoding='UTF-8', xml_declaration=True)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points on Earth using Haversine formula.
    
    Args:
        lat1, lon1: Reference point coordinates (degrees)
        lat2, lon2: Target point coordinates (degrees)
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


def calculate_magnitude_at_distance(epicenter_magnitude: float, distance_km: float) -> float:
    """
    Estimate shaking intensity at a given distance from epicenter using attenuation.
    
    Args:
        epicenter_magnitude: Magnitude at epicenter
        distance_km: Distance from epicenter in km
        
    Returns:
        Estimated magnitude/intensity at the given distance
    """
    if distance_km < 1:
        return epicenter_magnitude
    
    # Simplified attenuation model
    attenuation = epicenter_magnitude - (0.5 * np.log10(distance_km))
    return max(attenuation, 0)
