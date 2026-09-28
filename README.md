# Civic Deserts

Where do people live far from the services they depend on? This project joins open population and settlement data with mapped amenities to rank South African areas by people per amenity, and to flag dense places with few or none.

## Question

Which areas have the most people per clinic, school, bank branch and police station, and how does that change once age structure is taken into account?

## Data

| Dataset | Source | Use |
|---|---|---|
| HDX HAPI baseline population | https://data.humdata.org/dataset/hdx-hapi-population (API: `hapi.humdata.org/api/v2/geography-infrastructure/baseline-population`) | Population by admin area, gender and age range (UNFPA baseline) |
| South Africa Populated Places (OSM export) | https://data.humdata.org/dataset/hotosm_zaf_populated_places | Named settlements and their locations |
| South Africa Points of Interest (OSM export) | https://data.humdata.org/organization/hot | Amenities: health, education, finance, safety |

Raw files go in `data/raw/` and are not committed. HAPI needs a free app identifier, stored in `.env` as `HAPI_APP_IDENTIFIER`.

## Method

1. Profile the three sources: HAPI admin2 coverage for South Africa, population tag completeness in the OSM places.
2. Fix the unit of analysis (HAPI admin2 or hex grid) and assign places and amenities to it.
3. Build amenity classes and compute people per amenity, overall and by age band.
4. Rank and map the results, then build the Streamlit app.

## Structure

```
data/
  raw/         Downloads exactly as received
  interim/     Cleaned and joined intermediates
  processed/   Final analysis tables
notebooks/     Exploration and profiling
src/           Reusable pipeline code
app/           Streamlit app
outputs/
  figures/     Exported charts and maps
docs/          Notes, data dictionary, methodology
```

## Status

Setup. No data loaded yet.

## Limitations to keep in view

- OSM completeness varies by area. A low amenity count can mean unmapped, not absent.
- The OSM population tag is unlikely to be filled for most places.
- Admin-level counts hide within-area distance and access effects.

## Licences and attribution

- OpenStreetMap data: ODbL, credit OpenStreetMap contributors and HOT.
- HAPI and UNFPA population data: follow the licence stated on each HDX dataset page.
