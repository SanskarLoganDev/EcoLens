# Carbon Footprint Analyzer

An AI-powered carbon footprint analysis tool that categorizes financial transactions and provides personalized recommendations for reducing carbon emissions.

## Overview

This tool analyzes your spending patterns from CSV transaction files, calculates associated carbon emissions, and provides actionable recommendations using Claude AI to help you reduce your environmental impact.

### Key Features

- 📊 **Transaction Categorization**: Automatically categorizes transactions using Claude AI
- 🌍 **Emission Calculation**: Calculates CO2 emissions for each spending category
- 📈 **Benchmarking**: Compares your footprint against US/global averages and Paris Agreement targets
- 💡 **AI Coaching**: Generates personalized recommendations for reducing emissions
- 📁 **Detailed Reports**: Exports comprehensive JSON analysis reports

## Project Structure

```
carbon/
├── README.md                      # This file
├── analyzer.py                    # Main orchestrator - runs the complete pipeline
├── parser.py                      # CSV transaction parser with validation
├── calculator.py                  # Emission calculation engine
├── client.py                      # Claude API client wrapper
├── prompts.py                     # AI prompt templates
├── emission_factors.json          # CO2 emission factors database
├── samples/                       # Sample transaction CSV files
│   ├── sample_transactions.csv
│   └── sample_transactions_5.csv
└── results/                       # Generated analysis reports (auto-created)
    └── carbon_analysis_*.json
```

### Module Breakdown

#### **analyzer.py** - Main Pipeline
The orchestrator that ties everything together:
1. Parses CSV transactions
2. Categorizes with Claude AI
3. Calculates emissions
4. Generates benchmarks
5. Provides AI coaching
6. Saves results

#### **parser.py** - Transaction Parser
Reads and validates CSV files:
- Supports multiple encodings (UTF-8, Latin-1, etc.)
- Validates required columns (date, description, amount)
- Cleans and normalizes data
- Converts to structured Transaction objects

#### **calculator.py** - Emission Calculator
Calculates CO2 emissions:
- Loads emission factors from JSON database
- Applies category-specific calculations
- Generates emission breakdowns
- Provides global benchmarks

#### **client.py** - Claude API Client
Handles AI interactions:
- Manages Claude API authentication
- Tracks token usage and costs
- Provides cost estimates
- Handles API errors gracefully

#### **prompts.py** - Prompt Templates
Pre-written prompts for AI:
- Transaction categorization prompt
- Personalized coaching prompt
- JSON output format specifications

#### **emission_factors.json** - Emission Database
Contains CO2 factors for categories:
- Air travel, ground transport
- Food (restaurants, groceries)
- Utilities (electricity, natural gas)
- Goods (electronics, clothing, general)

## Setup

### Prerequisites

- Python 3.8+
- Anthropic API key (Claude)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Required packages:
   - `anthropic` - Claude API client
   - `pandas` - CSV data processing
   - `pydantic` - Data validation
   - `python-dotenv` - Environment variable management

2. **Set up API key:**

   Create a `.env` file in the project root:
   ```bash
   CLAUDE_API_KEY="your-api-key-here"
   ```

   Get your API key from: https://console.anthropic.com/

## Usage

### Basic Usage

Run the analyzer with the sample data:

```bash
# From project root
python src/services/carbon/analyzer.py
```

This will analyze the default sample CSV file.

### Custom CSV File

Analyze your own transaction file:

```bash
python src/services/carbon/analyzer.py path/to/your/transactions.csv
```

### CSV File Format

Your CSV must have these columns:

```csv
date,description,amount
2025-01-15,Delta Airlines,420.00
2025-01-16,Starbucks,6.50
2025-01-17,Whole Foods,85.30
```

**Required columns:**
- `date` - Transaction date (flexible formats: YYYY-MM-DD, MM/DD/YYYY, etc.)
- `description` - Merchant/transaction description
- `amount` - Transaction amount in dollars (must be positive)

### Output

The analyzer generates a comprehensive JSON report in `src/services/carbon/results/`:

```
carbon_analysis_sample_transactions_2025-12-31_14-30-45.json
```

**Report includes:**
- Total emissions (kg CO2e)
- Category breakdown with percentages
- Individual transaction details
- Benchmark comparisons (US average, Paris target)
- 5 personalized recommendations
- API cost summary

## Example Output

```
======================================================================
ECOLENS - CARBON FOOTPRINT ANALYZER
======================================================================

🌱 Initializing Carbon Footprint Analyzer...
======================================================================
✅ Loaded .env from: E:\...\EcoLens\.env
✅ Loaded emission factors for 9 categories
✅ Claude API client initialized
   Model: claude-sonnet-4-20250514
   Max tokens: 4000
======================================================================
✅ All components ready!

📄 STEP 1: Parsing transactions...
----------------------------------------------------------------------
   Transactions: 17
   Date range: 2025-01-01 to 2025-01-31
   Total spent: $1,856.30

🤖 STEP 2: Categorizing transactions with Claude AI...
----------------------------------------------------------------------
   ✅ Categorized 17 transactions
   📋 Category distribution:
      air_travel           3 transactions
      ground_transport     4 transactions
      ...

🧮 STEP 3: Calculating carbon emissions...
----------------------------------------------------------------------
   📊 Emission Breakdown:
      air_travel          3200.00 kg ( 88.1%)
      electricity          336.88 kg (  9.3%)
      ground_transport      31.68 kg (  0.9%)
      ...

📊 STEP 4: Comparing to global benchmarks...
----------------------------------------------------------------------
   Your annual projection: 43,609 kg/year
   vs US Average (16,000 kg): +173%
   vs Paris Target (2,300 kg): +1,796%

💡 STEP 5: Generating personalized recommendations...
----------------------------------------------------------------------
   Generated 5 recommendations:
   1. Replace short domestic flights with train travel
      Savings: 1600 kg/year | Difficulty: medium
   2. Switch to renewable energy plan
      Savings: 2000 kg/year | Difficulty: easy
   ...

✅ ANALYSIS COMPLETE!
======================================================================

💾 Results saved to: src/services/carbon/results/carbon_analysis_...json

💰 API Cost Summary:
   Total calls: 2
   Total cost: $0.0316
```

## Emission Categories

The analyzer recognizes these categories:

| Category | Examples | Emission Factor |
|----------|----------|----------------|
| **air_travel** | Delta, United, Southwest | ~4kg CO2/$ |
| **ground_transport** | Uber, Lyft, Gas stations | ~0.225kg CO2/$ |
| **food_restaurant** | Starbucks, Chipotle | ~0.3kg CO2/$ |
| **groceries** | Whole Foods, Safeway | ~0.1kg CO2/$ |
| **electricity** | PG&E, Duke Energy | ~2.7kg CO2/$ |
| **natural_gas** | Gas utilities | ~5.3kg CO2/$ |
| **goods_electronics** | Apple, Best Buy | ~0.4kg CO2/$ |
| **goods_clothing** | Nordstrom, H&M | ~0.6kg CO2/$ |
| **goods_general** | Target, Walmart | ~0.3kg CO2/$ |

## Testing Individual Components

### Test the Parser

```bash
python src/services/carbon/parser.py
```

Tests CSV parsing with the default sample file.

### Test the Calculator

```bash
python src/services/carbon/calculator.py
```

Tests emission calculations with sample data.

### Test the Claude Client

```bash
python src/services/carbon/client.py
```

Tests Claude API connection (requires API key).

### Test Prompt Templates

```bash
python src/services/carbon/prompts.py
```

Shows generated prompts for categorization and coaching.

## Configuration

### Emission Factors

Edit `emission_factors.json` to customize emission factors for your region or update with latest data.

### API Settings

Modify in `client.py`:
- `model` - Claude model to use (default: claude-sonnet-4)
- `max_tokens` - Maximum response length (default: 4000)
- Temperature settings in `analyzer.py`:
  - Categorization: 0.3 (consistent)
  - Coaching: 0.7 (creative)

## Cost Estimates

Typical API costs (Claude Sonnet 4):
- Input: $3 per million tokens
- Output: $15 per million tokens

**Per analysis (17 transactions):**
- Categorization: ~$0.01
- Coaching: ~$0.02
- **Total: ~$0.03** per analysis

## Troubleshooting

### "CSV file not found"
- Ensure file path is correct
- Use forward slashes in paths: `src/services/carbon/file.csv`
- Check file exists with `ls` or `dir`

### "Claude API key not found"
- Verify `.env` file exists in project root
- Check no spaces around `=`: `CLAUDE_API_KEY="key"`
- Ensure `python-dotenv` is installed

### "Empty recommendations list"
- Check API key is valid
- Review Claude API response in console
- Check `results/*.json` for error messages
- Verify internet connection

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Activate virtual environment if using one

## Benchmarks

**Global Context:**
- **US Average**: 16,000 kg CO2/year per person
- **Global Average**: 4,000 kg CO2/year per person
- **Paris Agreement Target**: 2,300 kg CO2/year (to limit warming to 1.5°C)

## Contributing

To add new emission categories:

1. Update `emission_factors.json` with new category and factor
2. Add category to `prompts.py` categorization list
3. Update this README with new category info

## License

This project is part of the EcoLens carbon tracking platform.

## Support

For issues or questions, please check:
- Error messages in console (detailed traceback provided)
- `results/*.json` files for analysis details
- API cost summary to track usage
