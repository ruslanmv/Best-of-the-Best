---
title: "Folium: Create Interactive Leaflet.js Maps in Python"
date: 2025-12-26T09:00:00+00:00
last_modified_at: 2025-12-26T09:00:00+00:00
topic_kind: "package"
topic_id: "folium"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - folium
  - python
  - data-visualization
  - geospatial
  - leaflet
  - interactive-maps
  - gis
excerpt: "A practical guide to Folium, the Python library for creating interactive Leaflet.js maps with markers, choropleth layers, and heatmaps."
header:
  overlay_image: /assets/images/2025-12-26-package-folium/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-26-package-folium/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Folium is a Python library that makes it easy to create interactive maps powered by Leaflet.js. It lets you generate rich map visualizations directly from Python, combining the data-processing capabilities of the Python ecosystem with the interactive mapping features of Leaflet. Maps are rendered as HTML, making them easy to embed in Jupyter notebooks, web pages, or dashboards. In this post, you will learn how to install Folium, create maps with markers and popups, build choropleth maps, and generate heatmaps.

## Overview

Folium bridges Python and Leaflet.js to provide:

- **Interactive tile maps** -- pan, zoom, and explore maps with multiple tile layer options (OpenStreetMap, CartoDB, Stamen, and more)
- **Markers and popups** -- place markers with customizable icons and HTML-rich popups
- **GeoJSON and choropleth support** -- overlay GeoJSON data and create choropleth maps linked to pandas DataFrames
- **Heatmaps** -- visualize point density using the `HeatMap` plugin
- **Layer control** -- toggle multiple layers on and off within a single map
- **HTML output** -- save maps as standalone HTML files or display inline in Jupyter notebooks

Common use cases include geographic data visualization, spatial analysis reporting, location-based dashboards, and exploratory data analysis of geospatial datasets.

## Getting Started

Install Folium using pip:

```bash
pip install folium
```

Here is a minimal example that creates a map centered on the United States with a marker:

```python
import folium

# Create a map centered on the US
m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)

# Add a marker with a popup
folium.Marker(
    location=[40.7128, -74.0060],
    popup="New York City",
    tooltip="Click for details",
    icon=folium.Icon(color="blue", icon="info-sign"),
).add_to(m)

# Save to HTML
m.save("map.html")
```

In a Jupyter notebook, simply place `m` as the last expression in a cell to render the map inline.

## Core Concepts

### Tile Layers

Folium supports several built-in tile providers. You can switch the map style by changing the `tiles` parameter:

```python
import folium

# CartoDB Positron (clean, light style)
m = folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles="CartoDB positron")

# You can also add multiple tile layers with layer control
folium.TileLayer("OpenStreetMap").add_to(m)
folium.TileLayer("CartoDB dark_matter").add_to(m)
folium.LayerControl().add_to(m)

m.save("paris_tiles.html")
```

### Markers and Popups

Folium provides several marker types for different use cases:

```python
import folium

m = folium.Map(location=[51.5074, -0.1278], zoom_start=13)

# Standard marker with HTML popup
folium.Marker(
    location=[51.5074, -0.1278],
    popup=folium.Popup("<b>London</b><br>Population: 8.9M", max_width=200),
    icon=folium.Icon(color="red", icon="star"),
).add_to(m)

# Circle marker with radius in pixels
folium.CircleMarker(
    location=[51.5155, -0.1415],
    radius=15,
    color="green",
    fill=True,
    fill_opacity=0.6,
    popup="Oxford Circus",
).add_to(m)

# Circle with radius in meters
folium.Circle(
    location=[51.5033, -0.1196],
    radius=500,
    color="blue",
    fill=True,
    popup="Westminster area (500m radius)",
).add_to(m)

m.save("london_markers.html")
```

## Practical Examples

### Example 1: Choropleth Map

Choropleth maps shade regions based on a data variable. Folium makes this straightforward with GeoJSON data and a pandas DataFrame:

```python
import folium
import pandas as pd

# Create a map
m = folium.Map(location=[48.0, 2.0], zoom_start=5)

# Sample data: country codes and values
data = pd.DataFrame({
    "country": ["FRA", "DEU", "ITA", "ESP", "GBR"],
    "value": [65, 83, 60, 47, 67],
})

# Create the choropleth layer
folium.Choropleth(
    geo_data="https://raw.githubusercontent.com/python-visualization/folium/main/tests/data/world-countries.json",
    data=data,
    columns=["country", "value"],
    key_on="feature.id",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Population (millions)",
).add_to(m)

m.save("choropleth.html")
```

### Example 2: Heatmap with folium.plugins

Use the `HeatMap` plugin to visualize point density on a map:

```python
import folium
from folium.plugins import HeatMap
import numpy as np

# Create a base map
m = folium.Map(location=[37.7749, -122.4194], zoom_start=12)

# Generate sample data: random points around San Francisco
np.random.seed(42)
n_points = 500
lats = 37.7749 + np.random.randn(n_points) * 0.02
lons = -122.4194 + np.random.randn(n_points) * 0.02
weights = np.random.uniform(0.2, 1.0, n_points)

# Create the heat data as a list of [lat, lon, weight]
heat_data = list(zip(lats, lons, weights))

# Add the heatmap layer
HeatMap(
    heat_data,
    min_opacity=0.3,
    radius=15,
    blur=20,
    max_zoom=13,
).add_to(m)

m.save("heatmap.html")
```

## Best Practices

- **Choose appropriate tile layers** -- use `CartoDB positron` for clean presentations and `OpenStreetMap` for detailed street-level maps.
- **Use `FeatureGroup` for layer management** -- group related markers into a `FeatureGroup` and add `LayerControl()` so users can toggle layers on and off.
- **Keep popup content concise** -- use `folium.Popup` with `max_width` to prevent oversized popups. HTML formatting works inside popups.
- **Save large maps to HTML** -- for maps with many markers, save to an HTML file rather than rendering inline in a notebook to avoid performance issues.
- **Use `MarkerCluster` for dense point data** -- the `folium.plugins.MarkerCluster` plugin groups nearby markers at lower zoom levels, improving readability and performance.

## Conclusion

Folium provides an accessible way to create interactive maps in Python without writing JavaScript. Its integration with Leaflet.js gives you access to a rich set of mapping features, from simple markers to choropleth maps and heatmaps. Whether you are building a quick geographic visualization in a Jupyter notebook or an interactive dashboard, Folium handles the rendering while you focus on the data.

Resources:

- [Folium Official Documentation](https://python-visualization.github.io/folium/)
- [Folium GitHub Repository](https://github.com/python-visualization/folium)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
