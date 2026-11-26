# What if the Alqueva dam failed?

*[Versão em português](README.pt.md)*

A 2D hydraulic simulation of a hypothetical scenario: the Alqueva and Pedrógão dams in southern Portugal fail, and the flood wave runs down the Guadiana river to the sea. I followed it for 24 hours with HEC-RAS 7.0.2, ArcGIS Pro 3.6 and Python, using open data only.

> **Note: this is a hypothetical scenario, made for study and as a portfolio piece.** It is not an emergency plan and does not replace the External Emergency Plan (PEExt) for the Alqueva dam, which is the official document. I used the PEExt only as a reference to validate the model.

![Video preview](docs/media/previsao.gif)

- 2D video (1 min 54 s, 1080p): [`docs/media/b1_rotura_alqueva_2d.mp4`](docs/media/b1_rotura_alqueva_2d.mp4)
- 3D animation in ArcGIS Pro (46 s, 720p): [`docs/media/b1_rotura_alqueva_3d.mp4`](docs/media/b1_rotura_alqueva_3d.mp4)
- Project page: https://gustavosanta-star.github.io/rotura-alqueva/?lang=en
- [Technical report](docs/relatorio_tecnico.md) (in Portuguese) and [flyer (PDF)](docs/media/flyer_b1.pdf)

## In numbers

| | |
|---|---|
| Peak discharge downstream of Alqueva | ~210 000 m³/s |
| Area flooded by the wave | 22 631 ha |
| Area with extreme hazard (h·v > 4 m²/s) | 10 351 ha |
| Residents in the flooded area (Portugal + Spain) | ~28 800 |
| Wave arrival | Pedrógão 0 h 42 · Mértola 4 h 18 · Alcoutim 7 h 12 · Vila Real de Santo António 11 h 30 |

## Maps

| Maximum depth | Hazard (h·v) | Arrival time | Exposure |
|---|---|---|---|
| ![](docs/media/B1_1_profundidade.jpg) | ![](docs/media/B1_2_perigosidade.jpg) | ![](docs/media/B1_3_chegada.jpg) | ![](docs/media/B1_4_exposicao.jpg) |

The map labels are in Portuguese.

## How it was done

1. Terrain: DGT LiDAR (2 m → 10 m) in the valley; CNIG DTM in Spain; SRTM from 2000 for the reservoir beds (before the reservoirs were filled); a schematic channel in the estuary.
2. HEC-RAS 2D model:
   - reservoir and valley as two 2D areas, with a 100 m mesh refined to 50 m in the canyon;
   - Manning roughness from COS 2025 (the Portuguese land cover map);
   - breaches at Alqueva and Pedrógão (Pedrógão fails in cascade, 29 min later).
3. Validation:
   - the PEExt hydrograph (for km 5) applied just downstream of the dam, with the dam failure switched off;
   - water levels within ±3 m up to km 55;
   - the limitations downstream of Pulo do Lobo are documented.
4. Scenario B1: 56 h of simulation, with maps every 10 min.
5. Products (ArcGIS Pro + Python):
   - depth, hazard, arrival and exposure maps (INE BGRI 2021, JRC 2021 grid, Spanish Catastro);
   - a 2D video generated in code;
   - a 3D animation in ArcGIS Pro;
   - a flyer.

The details, the validation tables and the limitations are in the [technical report](docs/relatorio_tecnico.md) (in Portuguese).

## Main limitations
- Downstream of Pulo do Lobo, the wave arrives 1.4 to 2 times later than in the PEExt. These times cannot be used as warning times.
- Water levels are overestimated downstream of Pulo do Lobo (the gorge is narrower than the mesh).
- The river mouth has a fixed level (2 m), and the flooded area is underestimated in the salt marshes, which run up against the model boundary.
- Exposure assumes population is spread evenly within each census subsection or 100 m cell (residents, not the population actually present).

## Structure

```
scripts/        Python (ArcGIS Pro/arcpy and plain Python), numbered in run order
  00–05         study area, open data download, terrain, elevation-volume curve
  06–12         dams, HEC-RAS results, COS → Manning, comparison with the PEExt
  13–15         B1 products, exposure (PT and ES), A3 layouts
  16–22         3D scene data, 2-minute frames, 2D video, 3D animation
  23            A4 flyer
  kit/          bathymetry, reference lines and HEC-RAS input files
  util/         GeoTIFF read/write and UTM projection without GDAL
docs/           technical report, web page (GitHub Pages) and media
```

Script names and comments are in Portuguese. The data (several GB) and the HEC-RAS model are not in the repository; they can be downloaded from the sources listed in the report. In the scripts, replace `C:\caminho\para\rotura-alqueva` with your project folder.

## Data sources
DGT (LiDAR DTM, COS 2025) · CNIG (5 m DTM) · NASA/USGS (SRTM) · INE (BGRI and 2021 Census) · JRC/Eurostat (Census Population Grid 2021) · Dirección General del Catastro (INSPIRE) · ANEPC (Alqueva PEExt, used as a reference). Each source has its own licence and attribution terms.

## Licence
- Code: [MIT](LICENSE).
- Text, maps, video and images: CC BY 4.0, with attribution to Gustavo Santa.

---
Gustavo Santa · Geospatial engineering · [gustavosanta-star.github.io](https://gustavosanta-star.github.io) · ORCID [0009-0008-4266-0732](https://orcid.org/0009-0008-4266-0732)

<sub>Personal project, made outside my professional work, using open data only.</sub>
