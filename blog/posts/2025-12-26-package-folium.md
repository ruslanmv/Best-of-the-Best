---
title: "Folium: Interactive Maps in Python — Practical Guide, Use Cases, and Alternatives"
date: 2025-12-26T09:00:00+00:00
last_modified_at: 2026-06-11T09:00:00+00:00
topic_kind: "package"
topic_id: "folium"
topic_version: 2
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
excerpt: "A practical guide to Folium for interactive Leaflet.js maps in Python: markers, choropleths, heatmaps, when to choose it over Plotly or pydeck, and how to publish maps from data pipelines."
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

## Why Folium matters

Every geospatial project hits the same wall: coordinates in a DataFrame and a stakeholder who wants to *see* them. Matplotlib gives you a static scatter plot nobody can zoom. A full web-mapping stack — Leaflet, a tile server, a JavaScript build — is a week of work for a ten-minute task.

Folium occupies exactly that gap. It is a thin, well-designed Python wrapper around [Leaflet.js](https://leafletjs.com/), the most battle-tested web mapping library in existence. You write Python; Folium emits a self-contained HTML file with all the Leaflet wiring done. The output pans, zooms, shows popups, and toggles layers — and it requires no server, no API key, and no JavaScript knowledge. Free OpenStreetMap and CartoDB tiles ship as defaults.

That "self-contained HTML file" property is the underrated part. A Folium map is an *artifact*: you can attach it to an email, drop it into an S3 bucket, commit it to a repo, or have a pipeline regenerate it nightly. Most mapping tools want to be applications. Folium is happy being a file, which makes it the most automation-friendly mapping tool in the Python ecosystem.

## Quick start

Folium is pure Python with light dependencies (Jinja2, branca, requests):

```bash
pip install folium
```

A complete, runnable map in under fifteen lines:

```python
import folium

m = folium.Map(location=[45.4642, 9.19], zoom_start=12, tiles="CartoDB positron")

folium.Marker(
    location=[45.4642, 9.19],
    popup=folium.Popup("<b>Milan</b><br>Duomo di Milano", max_width=200),
    tooltip="Click me",
    icon=folium.Icon(color="red", icon="info-sign"),
).add_to(m)

m.save("map.html")
```

Open `map.html` in any browser and you have a fully interactive Leaflet map. That is the entire workflow: build a `folium.Map`, call `.add_to(m)` on whatever you want drawn, save. Everything else in the library is a variation on this pattern.

## Map types and layers that matter

Folium has a long feature list, but four layer types cover roughly 95 percent of real work.

### Markers and popups

`folium.Marker` handles labeled points; `folium.CircleMarker` is the better choice when you have more than a handful, because it renders as a lightweight vector instead of an icon image. Popups accept arbitrary HTML, which is how you smuggle tables, links, and even small charts into a map:

```python
import folium

m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

stations = [
    ("King's Cross", 51.5308, -0.1238, 33_000_000),
    ("Waterloo", 51.5031, -0.1132, 41_000_000),
    ("Victoria", 51.4952, -0.1441, 36_000_000),
]

for name, lat, lon, riders in stations:
    folium.CircleMarker(
        location=[lat, lon],
        radius=riders / 4_000_000,
        color="#2b6cb0",
        fill=True,
        fill_opacity=0.7,
        popup=folium.Popup(f"<b>{name}</b><br>{riders:,} riders/yr", max_width=220),
    ).add_to(m)

m.fit_bounds([[51.49, -0.15], [51.54, -0.11]])
m.save("stations.html")
```

`fit_bounds` is worth memorizing — it removes the guesswork of picking `location` and `zoom_start` by hand.

### Choropleth

`folium.Choropleth` joins a pandas DataFrame to GeoJSON polygons and handles the color scale and legend for you. The only part people get wrong is `key_on`: it must point at the property inside each GeoJSON feature that matches your DataFrame's key column — usually `feature.id` or `feature.properties.<name>`.

```python
import folium
import pandas as pd

geo_url = ("https://raw.githubusercontent.com/python-visualization/"
           "folium/main/tests/data/world-countries.json")

data = pd.DataFrame({
    "iso": ["FRA", "DEU", "ITA", "ESP", "POL"],
    "value": [68, 84, 59, 48, 37],
})

m = folium.Map(location=[50, 10], zoom_start=4)
folium.Choropleth(
    geo_data=geo_url,            # remote GeoJSON; works offline with a local dict too
    data=data,
    columns=["iso", "value"],
    key_on="feature.id",
    fill_color="YlGnBu",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name="Population (millions)",
).add_to(m)
m.save("choropleth.html")
```

### Heatmaps and clusters (folium.plugins)

The `folium.plugins` module is where Leaflet's plugin ecosystem surfaces. The two you will actually use are `HeatMap` for density and `MarkerCluster` for keeping thousands of markers usable:

```python
import folium
from folium.plugins import HeatMap, MarkerCluster
import random

random.seed(7)
points = [[37.77 + random.gauss(0, 0.02),
           -122.42 + random.gauss(0, 0.02)] for _ in range(800)]

m = folium.Map(location=[37.77, -122.42], zoom_start=12)
HeatMap(points, radius=14, blur=18, min_opacity=0.3).add_to(m)

cluster = MarkerCluster(name="Incidents").add_to(m)
for lat, lon in points[:200]:
    folium.Marker([lat, lon]).add_to(cluster)

folium.LayerControl().add_to(m)
m.save("density.html")
```

`MarkerCluster` is not cosmetic — past a few hundred individual `Marker` objects, an unclustered map becomes sluggish, and clustering is the standard fix.

### GeoJSON layers

`folium.GeoJson` is the general-purpose escape hatch: any GeoJSON — routes, boundaries, buffers from shapely, output from geopandas — goes straight onto the map, with a `style_function` callback for per-feature styling and `GeoJsonTooltip` for hover info. When `Choropleth` feels too rigid (it often does), dropping down to `folium.GeoJson` with your own branca colormap gives you full control without leaving Python.

## Notebooks, export, and embedding

Folium has three output modes, and choosing the right one matters more than any styling decision.

**Inline in Jupyter.** A `folium.Map` object renders interactively as the last expression of a cell. This is the exploratory mode and where Folium shines during analysis. One caveat: every map is serialized into the notebook, so a dozen large maps will bloat the `.ipynb` file badly.

**Standalone HTML.** `m.save("map.html")` writes a single file that works anywhere a browser exists. `m.get_root().render()` gives you the same HTML as a string if you need to upload it or template it into something else.

**Embedded.** Because the output is plain HTML, an `<iframe>` drops a Folium map into a Jekyll post, a Sphinx site, a Flask response, or a Streamlit app (via the `streamlit-folium` package). I publish maps on this site exactly this way: the pipeline regenerates the HTML, the post iframes it, and the map updates without touching the article.

## When to use it

- **Exploratory geospatial analysis** in notebooks — the iteration loop from DataFrame to interactive map is seconds.
- **Automated reporting.** Cron job or pipeline produces `map.html`, ships it to a bucket or wiki. No server to maintain.
- **Sharing with non-technical audiences.** "Open this HTML file" is an instruction everyone can follow.
- **Small-to-medium datasets** — up to a few thousand vector features, or tens of thousands of points if you use `HeatMap` or `MarkerCluster`.
- **GeoJSON-centric workflows**, especially alongside geopandas — in fact `GeoDataFrame.explore()` returns a Folium map.

## When not to use it

- **Very large point datasets.** Leaflet renders SVG/DOM elements; 100k individual points will lock up the browser tab. This is a WebGL problem, and pydeck or kepler.gl solve it properly.
- **3D or GPU-accelerated visuals** — extrusions, hexbin towers, animated trips. Folium has no WebGL story at all.
- **Rich dashboard interactivity.** Folium is one-way: Python generates the map, and clicks in the browser do not flow back to Python. If you need "user clicks a region, charts update," you want Plotly Dash, ipyleaflet, or Streamlit with `streamlit-folium`.
- **Pixel-perfect custom design.** Beyond Leaflet's options you are writing custom JavaScript, at which point Folium is no longer saving you much.

## Integration with IBM watsonx.ai

A combination I keep returning to in client work: use a watsonx.ai LLM to extract structured geographic information from unstructured documents, then use Folium as the rendering layer. Field-service reports, news feeds, shipping manifests, and inspection logs all contain location mentions that a Granite or other foundation model on watsonx.ai can pull out as structured JSON — entity, place name, severity, date. Geocode the place names, and Folium turns the result into a shareable map artifact at the end of the pipeline. The LLM does language; Folium does presentation; neither pretends to do the other's job.

The glue is unremarkable, which is the point. Credentials stay in environment variables, never in code:

```python
import os, folium
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

creds = Credentials(url=os.environ["WATSONX_URL"], api_key=os.environ["WATSONX_APIKEY"])
model = ModelInference(model_id="ibm/granite-3-8b-instruct",
                       credentials=creds, project_id=os.environ["WATSONX_PROJECT_ID"])
# ...prompt the model to return [{"place": ..., "lat": ..., "lon": ..., "issue": ...}]
# then plot each extracted record:
m = folium.Map(location=[45.0, 9.0], zoom_start=6)
for rec in extracted_records:
    folium.Marker([rec["lat"], rec["lon"]], popup=rec["issue"]).add_to(m)
m.save("extracted_locations.html")
```

The same pattern works for model *outputs* rather than extractions: risk scores per region from a model deployed on watsonx.ai feed a `folium.Choropleth` directly, giving reviewers a spatial view of predictions instead of a CSV.

## Integration with IBM Watson Orchestrate

Watson Orchestrate is about automating multi-step business workflows, and Folium fits in as the final, human-facing step. A typical flow: an Orchestrate skill triggers on a schedule or event, calls a Python automation that pulls fresh data (open tickets by branch, delivery exceptions, sensor alerts), renders a Folium map to HTML, and publishes it — to SharePoint, Slack, email, or an internal portal. Because Folium's output is a static file with zero runtime dependencies, it survives every corporate delivery channel that would choke on a live dashboard. The map becomes a recurring report nobody has to remember to make: the workflow regenerates it, stakeholders get a link, and the "current state of the field" view is always at most one cycle old.

## Alternatives compared

| Tool | Rendering | Data size sweet spot | Interactivity | Best for |
|---|---|---|---|---|
| **Folium** | Leaflet.js (SVG/DOM) | Up to ~10k features | One-way; popups, layers, zoom | Reports, notebooks, standalone HTML artifacts |
| **Plotly** (`scatter_map`) | WebGL via plotly.js | 10k–100k points | Two-way in Dash; hover, select | Dashboards needing maps plus linked charts |
| **pydeck / kepler.gl** | deck.gl WebGL | 100k–millions of points | GPU layers, 3D, time playback | Big-data visual exploration, 3D urban analytics |
| **ipyleaflet** | Leaflet.js via Jupyter widgets | Similar to Folium | Two-way Python-JS in notebooks | Interactive notebook apps reacting to map events |
| **geopandas `.explore()`** | Folium under the hood | Same as Folium | Same as Folium | One-line maps straight from a GeoDataFrame |

My honest read: these tools are less interchangeable than the table suggests. Plotly's map traces earn their keep only when the map lives inside a dashboard with other linked figures — as a standalone map maker, Plotly is clumsier than Folium and its output is heavier. pydeck is genuinely in a different class for volume: plotting a million GPS pings is not a preference question, it is the only tool here that works. But its API is rougher and harder to make "boring and reliable" for a weekly report.

ipyleaflet deserves more attention than it gets. It wraps the same Leaflet but as a Jupyter widget, so map events flow back into Python — click handlers, draw tools, live layer updates. If your map needs to *respond*, ipyleaflet beats Folium decisively inside notebooks. Its weakness is exactly Folium's strength: the output is bound to a running kernel, so there is no email-able artifact.

And note that geopandas' `.explore()` *is* Folium — it constructs and returns a `folium.Map`. That tells you where the ecosystem has settled: for the default case of "show me this GeoDataFrame," Folium won. Start there; reach for the others when you hit a specific wall.

## Limitations

Be clear-eyed about three structural limits. First, **client-side rendering**: every feature is serialized into the HTML and drawn by the browser, so file size and frame rate degrade together as features grow — a 50 MB map HTML is a real failure mode I have shipped and regretted. Second, **the bridge is one-way**: Python writes JavaScript; nothing comes back. There is no callback when a user clicks a polygon, so any "interactive application" ambitions end at Leaflet's built-in behaviors. Third, **styling has a ceiling**: Leaflet's options go a long way, but custom controls or bespoke animations mean injecting raw JavaScript through Folium's element machinery, which is documented but unpleasant. When you find yourself doing a lot of that, the honest move is to write the Leaflet app directly.

## Final recommendation

Folium is the right default for interactive maps in Python, and I say that having used most of the alternatives in production. Its sweet spot — analysis to zoomable, shareable HTML map in ten lines with zero infrastructure — covers most geospatial visualization tasks in data work. The library is mature, the Leaflet foundation is rock solid, and the artifact-based output model composes beautifully with pipelines, LLM extraction workflows, and automation tools like Watson Orchestrate. Know its two hard edges — feature count and one-way interactivity — and switch to pydeck or ipyleaflet the moment you genuinely hit them, not before. For everything else: `pip install folium`, build the map, save the file, ship it.

## References

- Folium on GitHub: <https://github.com/python-visualization/folium>
- Folium documentation: <https://python-visualization.github.io/folium/>
- Leaflet.js: <https://leafletjs.com/>
- Folium on PyPI: <https://pypi.org/project/folium/>

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
