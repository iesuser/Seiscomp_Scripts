"""
ShakeMap generation module for earthquake visualization and intensity mapping.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import folium
from folium.plugins import HeatMap, MarkerCluster
from typing import Tuple, List, Optional
from earthquake_data import EarthquakeEvent, calculate_distance, calculate_magnitude_at_distance


class ShakeMapGenerator:
    def create_combined_shakemap(self, output_path: str, extent: Optional[Tuple[float, float, float, float]] = None, figsize: Tuple[int, int] = (14, 10)):
        """
        Create a single HTML file containing:
        - Static ShakeMap PNG (embedded)
        - Interactive Folium map
        - Event info and legend
        """
        import io
        import base64
        # Generate intensity grid
        self.generate_intensity_grid(extent=extent)

        # --- 1. Create static PNG in memory ---
        fig, ax = plt.subplots(figsize=figsize)
        colors = ['#ffffff', '#afe5ff', '#def9ff', '#68c7ff', '#4ccbff', 
                 '#ffeb3b', '#ff9800', '#ff6f00', '#d50000', '#800000']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('shakemap', colors, N=n_bins)
        im = ax.contourf(self.grid_lons, self.grid_lats, self.intensity_grid, levels=20, cmap=cmap)
        ax.plot(self.event.longitude, self.event.latitude, 'r*', markersize=25, label='Epicenter', zorder=5, markeredgecolor='darkred', markeredgewidth=1.5)
        contours = ax.contour(self.grid_lons, self.grid_lats, self.intensity_grid, levels=10, colors='black', linewidths=0.5, alpha=0.3)
        ax.clabel(contours, inline=True, fontsize=8)
        ax.set_xlabel('Longitude (°)', fontsize=12)
        ax.set_ylabel('Latitude (°)', fontsize=12)
        ax.set_title(f'Earthquake ShakeMap - {self.event.event_id}\nMagnitude {self.event.magnitude:.2f} | Depth {self.event.depth} km | {self.event.get_datetime().strftime("%Y-%m-%d %H:%M:%S UTC")}', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left', fontsize=11)
        cbar = plt.colorbar(im, ax=ax, label='Ground Motion Intensity', pad=0.02)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        # --- 2. Create interactive map as HTML string ---
        import folium
        m = folium.Map(location=[self.event.latitude, self.event.longitude], zoom_start=8, tiles='OpenStreetMap')
        popup_text = (f"<b>Earthquake {self.event.event_id}</b><br>"
                     f"Magnitude: <b>{self.event.magnitude:.2f}</b><br>"
                     f"Depth: <b>{self.event.depth} km</b><br>"
                     f"Time: <b>{self.event.get_datetime().isoformat()}</b><br>"
                     f"Location: {self.event.location_string}")
        folium.Marker(location=[self.event.latitude, self.event.longitude], popup=popup_text, icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')).add_to(m)
        heat_data = []
        for i in range(len(self.grid_lats)):
            for j in range(len(self.grid_lons)):
                normalized_intensity = min(max(self.intensity_grid[i, j], 0) / 10.0, 1.0)
                if normalized_intensity > 0.02:
                    heat_data.append([self.grid_lats[i, j], self.grid_lons[i, j], normalized_intensity])
        from folium.plugins import HeatMap
        HeatMap(heat_data, radius=20, blur=30, max_zoom=1, gradient={0.0: 'blue', 0.2: 'cyan', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1.0: 'red'}).add_to(m)
        # Hide folium default title/legend, we'll add our own
        map_html = m.get_root().render()

        # --- 3. Build combined HTML ---
        legend_html = '''
        <div style="background: #fff; border: 2px solid #d50000; border-radius: 8px; padding: 10px; margin-bottom: 10px; width: 350px;">
        <b style="font-size:16px; color: #d50000;">Earthquake ShakeMap</b><br>
        <b>Event ID:</b> {event_id}<br>
        <b>Magnitude:</b> {mag:.2f}<br>
        <b>Depth:</b> {depth} km<br>
        <b>Time:</b> {time}<br>
        <b>Location:</b> {loc}<br>
        <hr style="margin: 8px 0;">
        <b>Intensity Scale:</b><br>
        <span style="background:#ffffff; border:1px solid #ccc; padding:2px 8px;">I</span>
        <span style="background:#afe5ff; border:1px solid #ccc; padding:2px 8px;">II</span>
        <span style="background:#def9ff; border:1px solid #ccc; padding:2px 8px;">III</span>
        <span style="background:#68c7ff; border:1px solid #ccc; padding:2px 8px;">IV</span>
        <span style="background:#4ccbff; border:1px solid #ccc; padding:2px 8px;">V</span>
        <span style="background:#ffeb3b; border:1px solid #ccc; padding:2px 8px;">VI</span>
        <span style="background:#ff9800; border:1px solid #ccc; padding:2px 8px;">VII</span>
        <span style="background:#ff6f00; border:1px solid #ccc; padding:2px 8px;">VIII</span>
        <span style="background:#d50000; border:1px solid #ccc; padding:2px 8px; color:#fff;">IX</span>
        <span style="background:#800000; border:1px solid #ccc; padding:2px 8px; color:#fff;">X</span>
        <br><i style="color: #666; font-size: 12px;">Red = Strong shaking | Blue = Weak shaking</i>
        </div>
        '''.format(event_id=self.event.event_id, mag=self.event.magnitude, depth=self.event.depth, time=self.event.get_datetime().strftime("%Y-%m-%d %H:%M:%S UTC"), loc=self.event.location_string)

        html = f"""
        <html><head><meta charset='utf-8'><title>ShakeMap {self.event.event_id}</title>
        <style>body {{ font-family: Arial, sans-serif; background: #f7f7f7; }}</style></head>
        <body>
        <center>
        {legend_html}
        <div style='margin: 20px 0;'><b>Static ShakeMap (PNG):</b><br>
        <img src='data:image/png;base64,{img_base64}' style='max-width:90vw; border:2px solid #333; border-radius:8px; box-shadow:0 2px 8px #888;'/></div>
        <div style='margin: 20px 0;'><b>Interactive Map:</b></div>
        <div style='width:90vw; max-width:1200px; min-height:600px; border:2px solid #333; border-radius:8px; box-shadow:0 2px 8px #888; overflow:hidden;'>
        {map_html}
        </div>
        </center>
        </body></html>
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Combined ShakeMap saved to {output_path}")
    
    # Intensity color mapping (similar to USGS ShakeMap)
    INTENSITY_COLORS = {
        'I': '#ffffff',        # Not felt
        'II': '#afe5ff',       # Weak
        'III': '#def9ff',      # Weak
        'IV': '#68c7ff',       # Light
        'V': '#4ccbff',        # Moderate
        'VI': '#ffeb3b',       # Strong
        'VII': '#ff9800',      # Very strong
        'VIII': '#ff6f00',     # Severe
        'IX': '#d50000',       # Violent
        'X': '#800000'         # Extreme
    }
    
    def __init__(self, event: EarthquakeEvent, grid_spacing: float = 0.1):
        """
        Initialize ShakeMap generator.
        
        Args:
            event: EarthquakeEvent object
            grid_spacing: Spacing of the calculation grid in degrees
        """
        self.event = event
        self.grid_spacing = grid_spacing
        self.grid_lats = None
        self.grid_lons = None
        self.intensity_grid = None
    
    def generate_intensity_grid(self, 
                               extent: Optional[Tuple[float, float, float, float]] = None,
                               depth_km: float = 10.0) -> np.ndarray:
        """
        Generate intensity grid around the epicenter with circular spread pattern.
        
        Args:
            extent: (min_lat, max_lat, min_lon, max_lon) or None to auto-calculate
            depth_km: Depth of the earthquake (if not in event)
            
        Returns:
            2D array of intensity values
        """
        # Auto-calculate extent based on magnitude if not provided
        if extent is None:
            # Felt radius increases with magnitude (roughly 10^(mag-1) km)
            felt_radius_km = max(10 ** (self.event.magnitude - 2), 20)
            # Convert to degrees (approximately 1 degree = 111 km)
            radius_degrees = felt_radius_km / 111.0
            
            min_lat = self.event.latitude - radius_degrees
            max_lat = self.event.latitude + radius_degrees
            min_lon = self.event.longitude - radius_degrees
            max_lon = self.event.longitude + radius_degrees
        else:
            min_lat, max_lat, min_lon, max_lon = extent
        
        # Create grid
        lats = np.arange(min_lat, max_lat, self.grid_spacing)
        lons = np.arange(min_lon, max_lon, self.grid_spacing)
        
        self.grid_lats, self.grid_lons = np.meshgrid(lats, lons)
        
        # Use depth if event doesn't have it
        depth = self.event.depth if self.event.depth > 0 else depth_km
        
        # Calculate intensity grid based on distance from epicenter
        self.intensity_grid = np.zeros_like(self.grid_lats)
        
        for i in range(len(lats)):
            for j in range(len(lons)):
                # Distance from epicenter in km
                epicenter_distance = calculate_distance(
                    self.event.latitude, self.event.longitude,
                    lats[i], lons[j]
                )
                
                # Hypocentral distance (includes depth)
                hypo_dist = np.sqrt(epicenter_distance ** 2 + depth ** 2)
                
                # Intensity calculation with proper exponential decay
                # Closer to epicenter = stronger shaking
                if hypo_dist < 1:
                    intensity = self.event.magnitude
                else:
                    # Proper attenuation model - intensity decreases with distance
                    intensity = self.event.magnitude - 1.5 * np.log10(hypo_dist)
                
                self.intensity_grid[i, j] = max(intensity, 0)
        
        return self.intensity_grid
    
    def create_static_shakemap(self, 
                              output_path: str,
                              extent: Optional[Tuple[float, float, float, float]] = None,
                              figsize: Tuple[int, int] = (14, 10)):
        """
        Create a static ShakeMap image.
        
        Args:
            output_path: Path to save the figure
            extent: (min_lat, max_lat, min_lon, max_lon)
                   If None, auto-calculated based on magnitude
            figsize: Figure size in inches
        """
        # Generate intensity grid (with auto extent if not provided)
        self.generate_intensity_grid(extent=extent)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Create custom colormap for intensity
        colors = ['#ffffff', '#afe5ff', '#def9ff', '#68c7ff', '#4ccbff', 
                 '#ffeb3b', '#ff9800', '#ff6f00', '#d50000', '#800000']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('shakemap', colors, N=n_bins)
        
        # Create contour map
        im = ax.contourf(self.grid_lons, self.grid_lats, self.intensity_grid, 
                         levels=20, cmap=cmap)
        
        # Mark epicenter with large red star
        ax.plot(self.event.longitude, self.event.latitude, 'r*', 
               markersize=25, label='Epicenter', zorder=5, markeredgecolor='darkred', 
               markeredgewidth=1.5)
        
        # Add contour lines for reference
        contours = ax.contour(self.grid_lons, self.grid_lats, self.intensity_grid,
                             levels=10, colors='black', linewidths=0.5, alpha=0.3)
        ax.clabel(contours, inline=True, fontsize=8)
        
        ax.set_xlabel('Longitude (°)', fontsize=12)
        ax.set_ylabel('Latitude (°)', fontsize=12)
        ax.set_title(f'Earthquake ShakeMap - {self.event.event_id}\n'
                    f'Magnitude {self.event.magnitude:.2f} | Depth {self.event.depth} km | '
                    f'{self.event.get_datetime().strftime("%Y-%m-%d %H:%M:%S UTC")}',
                    fontsize=13, fontweight='bold')
        
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left', fontsize=11)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Ground Motion Intensity', pad=0.02)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"ShakeMap saved to {output_path}")
        plt.close()
    
    def create_interactive_map(self, 
                               output_path: str,
                               extent: Optional[Tuple[float, float, float, float]] = None):
        """
        Create an interactive Folium map with heatmap overlay.
        
        Args:
            output_path: Path to save the HTML map
            extent: (min_lat, max_lat, min_lon, max_lon)
                   If None, auto-calculated based on magnitude
        """
        # Create base map centered on epicenter
        m = folium.Map(
            location=[self.event.latitude, self.event.longitude],
            zoom_start=8,
            tiles='OpenStreetMap'
        )
        
        # Generate intensity grid (with auto extent if not provided)
        self.generate_intensity_grid(extent=extent)
        
        # Add epicenter marker with event info
        popup_text = (
            f"<b>Earthquake {self.event.event_id}</b><br>"
            f"Magnitude: <b>{self.event.magnitude:.2f}</b><br>"
            f"Depth: <b>{self.event.depth} km</b><br>"
            f"Time: <b>{self.event.get_datetime().isoformat()}</b><br>"
            f"Location: {self.event.location_string}"
        )
        
        folium.Marker(
            location=[self.event.latitude, self.event.longitude],
            popup=popup_text,
            icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')
        ).add_to(m)
        
        # Create a list of points with intensity for heatmap
        heat_data = []
        for i in range(len(self.grid_lats)):
            for j in range(len(self.grid_lons)):
                # Normalize intensity for heatmap (0-1 scale)
                normalized_intensity = min(max(self.intensity_grid[i, j], 0) / 10.0, 1.0)
                if normalized_intensity > 0.02:  # Only include significant values
                    heat_data.append([
                        self.grid_lats[i, j],
                        self.grid_lons[i, j],
                        normalized_intensity
                    ])
        
        # Add heatmap layer
        HeatMap(heat_data, radius=20, blur=30, max_zoom=1, 
                gradient={0.0: 'blue', 0.2: 'cyan', 0.4: 'lime', 
                         0.6: 'yellow', 0.8: 'orange', 1.0: 'red'}).add_to(m)
        
        # Add title and legend
        title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 400px; height: 200px; 
                    background-color: white; border:3px solid #d50000; 
                    border-radius: 8px; z-index:9999; font-size:14px; 
                    padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <b style="font-size:16px; color: #d50000;">Earthquake ShakeMap</b><br>
        <hr style="margin: 8px 0;">
        <b>Event ID:</b> {}<br>
        <b>Magnitude:</b> {:.2f}<br>
        <b>Depth:</b> {} km<br>
        <b>Time:</b> {}<br>
        <b>Location:</b> {}<br>
        <br>
        <i style="color: #666; font-size: 12px;">
        Red = Strong shaking | Blue = Weak shaking
        </i>
        </div>
        '''.format(
            self.event.event_id,
            self.event.magnitude,
            self.event.depth,
            self.event.get_datetime().strftime("%Y-%m-%d %H:%M:%S UTC"),
            self.event.location_string
        )
        m.get_root().html.add_child(folium.Element(title_html))
        
        m.save(output_path)
        print(f"Interactive map saved to {output_path}")



def compare_earthquakes(events: List[EarthquakeEvent], output_path: str):
    """
    Create a comparison map of multiple earthquake events.
    
    Args:
        events: List of EarthquakeEvent objects
        output_path: Path to save the comparison map
    """
    if not events:
        return
    
    # Calculate center point
    center_lat = np.mean([e.latitude for e in events])
    center_lon = np.mean([e.longitude for e in events])
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add markers for each event
    for event in events:
        color = 'red' if event.magnitude > 5.0 else 'orange' if event.magnitude > 4.0 else 'green'
        
        folium.CircleMarker(
            location=[event.latitude, event.longitude],
            radius=max(5, event.magnitude * 2),
            popup=f"<b>Event {event.event_id}</b><br>"
                  f"Magnitude: {event.magnitude:.2f}<br>"
                  f"Depth: {event.depth} km<br>"
                  f"Time: {event.get_datetime().isoformat()}",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(m)
    
    m.save(output_path)
    print(f"Comparison map saved to {output_path}")
