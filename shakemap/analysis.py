"""
Earthquake data analysis and statistics module.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List
from datetime import datetime
from shakemap.earthquake_data import EarthquakeEvent


class EarthquakeAnalysis:
    """Analyze and visualize earthquake data."""
    
    def __init__(self, events: List[EarthquakeEvent]):
        """
        Initialize analysis module.
        
        Args:
            events: List of EarthquakeEvent objects
        """
        self.events = events
    
    def magnitude_statistics(self) -> dict:
        """
        Calculate magnitude statistics.
        
        Returns:
            Dictionary with magnitude statistics
        """
        magnitudes = [e.magnitude for e in self.events]
        
        return {
            'count': len(magnitudes),
            'mean': np.mean(magnitudes),
            'median': np.median(magnitudes),
            'std': np.std(magnitudes),
            'min': np.min(magnitudes),
            'max': np.max(magnitudes)
        }
    
    def depth_statistics(self) -> dict:
        """
        Calculate depth statistics.
        
        Returns:
            Dictionary with depth statistics
        """
        depths = [e.depth for e in self.events]
        
        return {
            'count': len(depths),
            'mean': np.mean(depths),
            'median': np.median(depths),
            'std': np.std(depths),
            'min': np.min(depths),
            'max': np.max(depths)
        }
    
    def magnitude_distribution(self, output_path: str = 'magnitude_distribution.png'):
        """
        Plot magnitude distribution.
        
        Args:
            output_path: Path to save the plot
        """
        magnitudes = [e.magnitude for e in self.events]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        ax1.hist(magnitudes, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
        ax1.set_xlabel('Magnitude', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('Magnitude Distribution Histogram', fontsize=13, fontweight='bold')
        ax1.grid(alpha=0.3)
        
        # Cumulative
        sorted_mags = sorted(magnitudes)
        cumulative = np.arange(1, len(sorted_mags) + 1)
        ax2.plot(sorted_mags, cumulative, marker='o', linestyle='-', linewidth=2)
        ax2.set_xlabel('Magnitude', fontsize=12)
        ax2.set_ylabel('Cumulative Count', fontsize=12)
        ax2.set_title('Cumulative Magnitude Distribution', fontsize=13, fontweight='bold')
        ax2.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Magnitude distribution plot saved to {output_path}")
        plt.close()
    
    def depth_distribution(self, output_path: str = 'depth_distribution.png'):
        """
        Plot depth distribution.
        
        Args:
            output_path: Path to save the plot
        """
        depths = [e.depth for e in self.events]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(depths, bins=15, color='coral', edgecolor='black', alpha=0.7)
        ax.set_xlabel('Depth (km)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Earthquake Depth Distribution', fontsize=13, fontweight='bold')
        ax.grid(alpha=0.3)
        
        # Add statistics
        stats = self.depth_statistics()
        stats_text = f"Mean: {stats['mean']:.1f} km\nMedian: {stats['median']:.1f} km\nMax: {stats['max']:.1f} km"
        ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, 
               fontsize=11, verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Depth distribution plot saved to {output_path}")
        plt.close()
    
    def magnitude_vs_depth(self, output_path: str = 'magnitude_vs_depth.png'):
        """
        Create scatter plot of magnitude vs depth.
        
        Args:
            output_path: Path to save the plot
        """
        magnitudes = [e.magnitude for e in self.events]
        depths = [e.depth for e in self.events]
        
        fig, ax = plt.subplots(figsize=(10, 7))
        
        scatter = ax.scatter(magnitudes, depths, s=100, alpha=0.6, c=magnitudes, 
                            cmap='viridis', edgecolors='black', linewidth=0.5)
        
        ax.set_xlabel('Magnitude', fontsize=12)
        ax.set_ylabel('Depth (km)', fontsize=12)
        ax.set_title('Magnitude vs Depth', fontsize=13, fontweight='bold')
        ax.invert_yaxis()  # Deeper earthquakes at bottom
        ax.grid(alpha=0.3)
        
        cbar = plt.colorbar(scatter, ax=ax, label='Magnitude')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Magnitude vs depth plot saved to {output_path}")
        plt.close()
    
    def temporal_distribution(self, output_path: str = 'temporal_distribution.png'):
        """
        Plot temporal distribution of earthquakes.
        
        Args:
            output_path: Path to save the plot
        """
        dates = [e.get_datetime() for e in self.events]
        magnitudes = [e.magnitude for e in self.events]
        
        # Sort by date
        sorted_data = sorted(zip(dates, magnitudes))
        dates, magnitudes = zip(*sorted_data)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        ax.scatter(dates, magnitudes, s=100, alpha=0.6, c=magnitudes, 
                  cmap='plasma', edgecolors='black', linewidth=0.5)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Magnitude', fontsize=12)
        ax.set_title('Temporal Distribution of Earthquakes', fontsize=13, fontweight='bold')
        ax.grid(alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Temporal distribution plot saved to {output_path}")
        plt.close()
    
    def print_summary(self):
        """Print summary statistics."""
        mag_stats = self.magnitude_statistics()
        depth_stats = self.depth_statistics()
        
        print("\n" + "=" * 60)
        print("EARTHQUAKE STATISTICS SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Events: {len(self.events)}")
        
        print("\nMAGNITUDE STATISTICS:")
        print(f"  Mean:     {mag_stats['mean']:.2f}")
        print(f"  Median:   {mag_stats['median']:.2f}")
        print(f"  Std Dev:  {mag_stats['std']:.2f}")
        print(f"  Range:    {mag_stats['min']:.2f} - {mag_stats['max']:.2f}")
        
        print("\nDEPTH STATISTICS:")
        print(f"  Mean:     {depth_stats['mean']:.2f} km")
        print(f"  Median:   {depth_stats['median']:.2f} km")
        print(f"  Std Dev:  {depth_stats['std']:.2f} km")
        print(f"  Range:    {depth_stats['min']:.2f} - {depth_stats['max']:.2f} km")
        
        # Magnitude classification
        shallow = sum(1 for e in self.events if e.depth < 70)
        intermediate = sum(1 for e in self.events if 70 <= e.depth < 300)
        deep = sum(1 for e in self.events if e.depth >= 300)
        
        print("\nDEPTH CLASSIFICATION:")
        print(f"  Shallow (<70 km):        {shallow} events")
        print(f"  Intermediate (70-300 km): {intermediate} events")
        print(f"  Deep (≥300 km):          {deep} events")
        
        # Magnitude classification
        micro = sum(1 for e in self.events if e.magnitude < 2.0)
        very_minor = sum(1 for e in self.events if 2.0 <= e.magnitude < 3.0)
        minor = sum(1 for e in self.events if 3.0 <= e.magnitude < 4.0)
        light = sum(1 for e in self.events if 4.0 <= e.magnitude < 5.0)
        moderate = sum(1 for e in self.events if e.magnitude >= 5.0)
        
        print("\nMAGNITUDE CLASSIFICATION:")
        print(f"  Micro (<2.0):              {micro} events")
        print(f"  Very Minor (2.0-3.0):     {very_minor} events")
        print(f"  Minor (3.0-4.0):          {minor} events")
        print(f"  Light (4.0-5.0):          {light} events")
        print(f"  Moderate & Strong (≥5.0): {moderate} events")
        
        print("=" * 60 + "\n")
    
    def generate_all_plots(self, output_dir: str = 'analysis_plots'):
        """
        Generate all analysis plots.
        
        Args:
            output_dir: Directory to save plots
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        self.magnitude_distribution(os.path.join(output_dir, 'magnitude_distribution.png'))
        self.depth_distribution(os.path.join(output_dir, 'depth_distribution.png'))
        self.magnitude_vs_depth(os.path.join(output_dir, 'magnitude_vs_depth.png'))
        self.temporal_distribution(os.path.join(output_dir, 'temporal_distribution.png'))
        
        print(f"\n✓ All plots saved to {output_dir}")
