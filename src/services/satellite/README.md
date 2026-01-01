# Satellite Environmental Monitor

An AI-powered satellite image analysis tool that detects and quantifies environmental changes using NASA GIBS satellite imagery and Claude Vision API.

## Features

- **Satellite Image Fetching**: Download before/after images from NASA GIBS (Global Imagery Browse Services)
- **Multiple Satellite Products**: Support for Landsat, Sentinel-2, MODIS, and VIIRS imagery
- **AI Vision Analysis**: Analyze satellite images using Claude's vision capabilities
- **Change Detection**: Quantify environmental changes (deforestation, ice melt, urban sprawl)
- **Carbon Emission Estimates**: Calculate CO2 emissions from forest loss
- **Multi-Format Reports**: Generate JSON, Markdown, and CSV reports
- **Cost Tracking**: Monitor Claude API usage and costs
- **Pre-defined Regions**: Quick analysis of known environmental hotspots
- **No API Key Required**: GIBS provides open-access satellite imagery

## Project Structure

```
satellite/
├── analyzer.py                    # Main orchestrator/entry point
├── satellite_fetcher.py           # NASA GIBS API integration
├── satellite_vision_analyzer.py   # Claude Vision analysis
├── change_detector.py             # Change quantification
├── report_generator.py            # Multi-format report generation
├── client.py                      # Claude API wrapper
├── prompts.py                     # AI prompts for analysis
├── satellite_config.py            # GIBS configuration and region presets
├── geo_utils.py                   # Geographic utilities
├── data/                          # Satellite images (auto-created)
│   ├── downloads/                 # Downloaded satellite images
│   └── cache/                     # API response cache
├── results/                       # Analysis reports (auto-created)
│   ├── *_analysis.json           # Complete analysis data
│   ├── *_report.md               # Human-readable summary
│   └── *_metrics.csv             # Spreadsheet-ready metrics
└── README.md
```

## Prerequisites

### Python Packages
```bash
pip install anthropic python-dotenv requests pillow
```

### API Keys

**Claude API Key** (Required)
- Get from: https://console.anthropic.com/
- Add to `.env` file in project root

**NASA GIBS** (No API Key Required!)
- GIBS provides open-access satellite imagery
- No registration or API key needed
- Imagery updated daily from multiple satellites

### Environment Variables

Create a `.env` file in the project root:
```
CLAUDE_API_KEY=your_claude_api_key_here
```

That's it! No NASA API key needed for GIBS.

## How to Run

### Basic Usage

From the project root directory:

```bash
python src/services/satellite/analyzer.py <region_or_options>
```

### Option 1: Analyze Pre-defined Region

```bash
# Analyze Amazon rainforest deforestation
python src/services/satellite/analyzer.py amazon_basin

# Analyze Greenland ice melt
python src/services/satellite/analyzer.py arctic_greenland

# Analyze Las Vegas urban sprawl
python src/services/satellite/analyzer.py las_vegas
```

### Option 2: Analyze Custom Location

```bash
python src/services/satellite/analyzer.py \
  --lat -3.0 \
  --lon -60.0 \
  --before 2024-01-01 \
  --after 2025-01-01 \
  --name "My Forest Site" \
  --type deforestation
```

### List Available Regions

```bash
python src/services/satellite/analyzer.py --list
```

## Available Pre-defined Regions

| Region Key | Location | Type | Recommended For |
|------------|----------|------|-----------------|
| `amazon_basin` | Amazon Rainforest, Brazil | Deforestation | Forest loss monitoring |
| `amazon_rondonia` | Rondônia, Brazil | Deforestation | Heavy deforestation area |
| `arctic_greenland` | Greenland Ice Sheet | Ice melt | Arctic monitoring |
| `las_vegas` | Las Vegas, Nevada | Urban sprawl | Desert urbanization |
| `dubai` | Dubai, UAE | Urban sprawl | Coastal development |
| `california_forests` | N. California | Fire damage | Wildfire impact |
| `congo_basin` | Congo Rainforest, DRC | Deforestation | Tropical forest |

## Analysis Types

- **deforestation**: Forest loss detection and carbon emission estimates
- **ice_melt**: Ice/snow coverage changes
- **urban_sprawl**: Urban development expansion
- **general**: General land cover change analysis

## Output

### Analysis Results

The tool generates three types of reports in the `results/` folder:

**1. JSON Report** (`*_analysis.json`)
- Complete analysis data
- Vision API responses
- All metrics and calculations
- API cost tracking

**2. Markdown Report** (`*_report.md`)
- Human-readable summary
- Key findings and metrics
- Environmental impact assessment
- Links to satellite images

**3. CSV Metrics** (`*_metrics.csv`)
- Spreadsheet-ready data
- Key metrics for comparison
- Good for tracking multiple locations

### Example Output Structure

```json
{
  "location": {
    "name": "Amazon Basin",
    "lat": -3.4653,
    "lon": -62.2159
  },
  "time_period": {
    "before": "2024-01-01",
    "after": "2025-01-01",
    "days_elapsed": 365
  },
  "changes": {
    "change_detected": true,
    "change_type": "deforestation",
    "severity": "high",
    "severity_score": 8,
    "metrics": {
      "forest_loss_km2": 22.2,
      "forest_loss_pct": 18.0,
      "carbon_emissions_tons": 4440
    }
  },
  "api_cost": {
    "total_cost_usd": 0.085
  }
}
```

## Troubleshooting

### "Claude API key not found!"
- Ensure `.env` file exists in project root
- Verify `CLAUDE_API_KEY` is set correctly
- No spaces around the `=` sign

### "GIBS API request failed"
- Check internet connection
- Verify coordinates are valid (lat: -90 to 90, lon: -180 to 180)
- GIBS might be temporarily down (check https://www.earthdata.nasa.gov/gibs)
- Some regions may not have recent imagery

### "No imagery available for date"
- GIBS may not have imagery for the exact date requested
- Try nearby dates (±1-3 days)
- Some satellite products have different temporal coverage:
  - Landsat: 16-day repeat cycle
  - Sentinel-2: 5-day repeat cycle
  - MODIS/VIIRS: Daily coverage
- Some locations have limited satellite coverage

### Import Errors
- Install required packages: `pip install anthropic python-dotenv requests pillow`
- Ensure Python 3.8+ is installed
- Run from project root directory

### "Invalid image from GIBS"
- GIBS returns XML errors when no data available
- Try a different date or satellite product (use `--layer` parameter)
- Check if the region has cloud-free imagery for that date

## API Costs

The analyzer uses Claude Sonnet 4. Typical costs per analysis:

- **Single location analysis**: $0.05 - $0.15
  - 2 vision API calls (before/after images)
  - 1 text API call (comparison analysis)
- **Batch analysis** (multiple locations): ~$0.10 per location

Costs are tracked and displayed after each analysis. Use caching to reduce costs for repeated analyses.

## Advanced Usage

### Custom Output Path

```bash
python src/services/satellite/analyzer.py amazon_basin --output my_analysis.json
```

### Select Satellite Product

You can specify which satellite product to use:

```bash
# Use Landsat (default, 30m resolution)
python src/services/satellite/analyzer.py amazon_basin --layer landsat

# Use Sentinel-2 (30m resolution, more frequent)
python src/services/satellite/analyzer.py amazon_basin --layer sentinel

# Use MODIS Terra (daily, 250m resolution)
python src/services/satellite/analyzer.py amazon_basin --layer modis_terra

# Use VIIRS (daily, 375m resolution)
python src/services/satellite/analyzer.py amazon_basin --layer viirs_day
```

**Available Layers:**
- `landsat` - HLS Landsat 8/9 (30m, 16-day repeat)
- `sentinel` - HLS Sentinel-2 (30m, 5-day repeat)
- `modis_terra` - MODIS Terra True Color (250m, daily)
- `modis_aqua` - MODIS Aqua True Color (250m, daily)
- `viirs_day` - VIIRS SNPP True Color (375m, daily)

### Programmatic Usage

```python
from analyzer import SatelliteAnalyzer

# Initialize
analyzer = SatelliteAnalyzer()

# Analyze region
result = analyzer.analyze_region('amazon_basin')

# Or analyze custom location
result = analyzer.analyze_location(
    lat=-3.0,
    lon=-60.0,
    before_date='2024-01-01',
    after_date='2025-01-01',
    location_name='My Site',
    analysis_type='deforestation'
)

# Access results
print(f"Forest loss: {result['changes']['metrics']['forest_loss_km2']} km²")
print(f"Carbon emissions: {result['changes']['metrics']['carbon_emissions_tons']} tons")
```

## Sample Commands

```bash
# Quick test with demo region
python src/services/satellite/analyzer.py amazon_basin

# Custom Amazon location with specific dates
python src/services/satellite/analyzer.py \
  --lat -3.4653 \
  --lon -62.2159 \
  --before 2023-06-01 \
  --after 2024-06-01 \
  --name "Amazon Monitoring Site" \
  --type deforestation

# Arctic ice monitoring
python src/services/satellite/analyzer.py arctic_greenland

# Urban development tracking
python src/services/satellite/analyzer.py \
  --lat 25.2048 \
  --lon 55.2708 \
  --before 2020-01-01 \
  --after 2024-01-01 \
  --name "Dubai Development" \
  --type urban_sprawl

# List all available pre-defined regions
python src/services/satellite/analyzer.py --list
```

## Notes

- First run will show the location of the loaded `.env` file
- Satellite images are cached in `data/downloads/` folder
- Results are saved with timestamps to prevent overwriting
- Images are organized by location name
- GIBS provides open-access imagery - no API key or registration required
- Multiple satellite products available (Landsat, Sentinel, MODIS, VIIRS)
- Imagery is updated daily from NASA's Earth observation satellites
- Default product is Landsat (HLS) at 30m resolution

## Error Handling

The tool includes comprehensive error handling with:
- Step-by-step progress indicators (Steps 1-5)
- Detailed error messages with troubleshooting tips
- Full tracebacks for debugging
- Graceful degradation (continues when possible)

If you encounter errors:
1. Read the error message and troubleshooting tips
2. Check the full traceback for details
3. Verify all prerequisites are met
4. Check API keys and internet connection
5. Report issues with full error output

## Contributing

When adding new regions to `satellite_config.py`:
- Include coordinates, type, and description
- Add recommended dates for best imagery
- Test coordinates work with NASA API
- Document in this README

## Data Sources

- **Satellite Imagery**: NASA GIBS (Global Imagery Browse Services)
  - Landsat 8/9 (HLS L30) - 30m resolution
  - Sentinel-2 (HLS S30) - 30m resolution
  - MODIS Terra/Aqua - 250m resolution
  - VIIRS SNPP - 375m resolution
- **AI Analysis**: Anthropic Claude Sonnet 4 Vision API
- **Carbon Estimates**: Based on IPCC forest biomass data

## About GIBS

NASA's Global Imagery Browse Services (GIBS) provides full-resolution satellite imagery from multiple NASA Earth observation missions. Benefits:

- **Open Access**: No API key or registration required
- **Daily Updates**: Fresh imagery from multiple satellites
- **Multiple Products**: Access to Landsat, Sentinel-2, MODIS, VIIRS
- **WMS/WMTS Standards**: Uses OGC web service protocols
- **High Performance**: Optimized for fast image delivery
- **Free**: Completely free for all users

Learn more: https://www.earthdata.nasa.gov/gibs
