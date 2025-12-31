"""
Carbon Footprint Analyzer - Main Orchestrator
==============================================
Ties all components together into a complete pipeline.

Pipeline:
1. Parse CSV → transactions
2. Categorize with Claude → labeled transactions
3. Calculate emissions → emission breakdown
4. Get benchmarks → comparisons
5. Get coaching from Claude → recommendations
6. Return complete analysis

This is the main file you'll run!
"""

import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

# Import our components
from parser import TransactionParser
from calculator import EmissionCalculator
from client import ClaudeClient
from prompts import categorization_prompt, coaching_prompt


class CarbonAnalyzer:
    """
    Main carbon footprint analysis orchestrator.
    
    Usage:
        analyzer = CarbonAnalyzer()
        result = analyzer.analyze_file("transactions.csv")
        print(result)
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize analyzer with all components.
        
        Args:
            api_key: Claude API key (optional, uses env var if not provided)
        """
        print("\n🌱 Initializing Carbon Footprint Analyzer...")
        print("="*70)
        
        # Initialize components
        self.parser = TransactionParser()
        self.calculator = EmissionCalculator()
        self.claude = ClaudeClient(api_key=api_key)
        
        print("="*70)
        print("✅ All components ready!\n")
    
    def analyze_file(self, file_path: str, skip_coaching: bool = False) -> Dict:
        """
        Complete analysis pipeline for a transaction CSV file.
        
        Steps:
        1. Parse CSV
        2. Categorize with Claude AI
        3. Calculate emissions
        4. Get benchmarks
        5. Get coaching (optional)
        6. Save results
        
        Args:
            file_path: Path to transactions CSV
            skip_coaching: If True, skip AI coaching (saves money)
            
        Returns:
            Complete analysis dictionary
        """
        
        print("\n" + "="*70)
        print("STARTING CARBON FOOTPRINT ANALYSIS")
        print("="*70)
        
        # STEP 1: Parse CSV
        print("\n📄 STEP 1: Parsing transactions...")
        print("-"*70)
        transactions = self.parser.parse_csv(file_path)
        
        if not transactions:
            raise ValueError("No valid transactions found in CSV")
        
        summary = self.parser.get_summary()
        print(f"   Transactions: {summary['total_transactions']}")
        print(f"   Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"   Total spent: ${summary['total_amount']:.2f}")
        
        # STEP 2: Categorize with Claude
        print("\n🤖 STEP 2: Categorizing transactions with Claude AI...")
        print("-"*70)
        categorized = self._categorize_transactions(self.parser.to_dict_list())
        
        # STEP 3: Calculate emissions
        print("\n🧮 STEP 3: Calculating carbon emissions...")
        print("-"*70)
        emissions_result = self.calculator.calculate_total(categorized)
        
        # Print breakdown
        print(f"\n   📊 Emission Breakdown:")
        for category, data in emissions_result['breakdown'].items():
            print(f"      {category:20} {data['emissions_kg']:8.2f} kg ({data['percentage']:5.1f}%)")
        
        # STEP 4: Get benchmarks
        print("\n📊 STEP 4: Comparing to global benchmarks...")
        print("-"*70)
        period_days = self._calculate_period_days(transactions)
        benchmarks = self.calculator.get_benchmarks(
            emissions_result['total_emissions_kg'],
            period_days
        )
        
        print(f"   Your annual projection: {benchmarks['your_annual_projection_kg']:,} kg/year")
        print(f"   vs US Average ({benchmarks['us_average_annual_kg']:,} kg): {benchmarks['comparison']['vs_us_average']}%")
        print(f"   vs Paris Target ({benchmarks['paris_target_annual_kg']:,} kg): {benchmarks['comparison']['vs_paris_target']}%")
        
        # STEP 5: Get AI coaching (optional)
        coaching = None
        if not skip_coaching:
            print("\n💡 STEP 5: Generating personalized recommendations...")
            print("-"*70)
            coaching = self._get_coaching(emissions_result)
            
            print(f"\n   Generated {len(coaching['recommendations'])} recommendations:")
            for i, rec in enumerate(coaching['recommendations'][:3], 1):
                print(f"   {i}. {rec['action']}")
                print(f"      Savings: {rec['potential_savings_kg']} kg/year | Difficulty: {rec['difficulty']}")
        else:
            print("\n⏭️  STEP 5: Skipping coaching (as requested)")
        
        # STEP 6: Combine results
        print("\n✅ ANALYSIS COMPLETE!")
        print("="*70)
        
        result = {
            **emissions_result,
            'period_info': {
                'start_date': summary['date_range']['start'],
                'end_date': summary['date_range']['end'],
                'days': period_days,
                'transaction_count': summary['total_transactions'],
                'total_spent': summary['total_amount']
            },
            'benchmarks': benchmarks,
            'coaching': coaching,
            'analysis_date': datetime.now().isoformat(),
            'api_cost': self.claude.get_cost_estimate()
        }
        
        # STEP 7: Save results
        output_path = self._save_results(result, file_path)
        print(f"\n💾 Results saved to: {output_path}")
        
        # Print cost summary
        cost_info = self.claude.get_cost_estimate()
        print(f"\n💰 API Cost Summary:")
        print(f"   Total calls: {cost_info['total_calls']}")
        print(f"   Total cost: ${cost_info['total_cost_usd']:.4f}")
        
        return result
    
    def _categorize_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Use Claude AI to categorize transactions.
        
        Process:
        1. Generate categorization prompt
        2. Call Claude API
        3. Parse JSON response
        4. Handle errors gracefully
        
        Returns:
            Transactions with 'category' field added
        """
        
        # Generate prompt
        prompt = categorization_prompt(transactions)
        
        # Call Claude with low temperature (more consistent)
        response = self.claude.call(
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            temperature=0.3  # Low temp for consistent categorization
        )
        
        # Parse JSON response
        try:
            # Claude should return pure JSON
            result = json.loads(response['content'])
            categorized_list = result['categorized_transactions']
            
            print(f"   ✅ Categorized {len(categorized_list)} transactions")
            
            # Show category distribution
            categories = {}
            for t in categorized_list:
                cat = t.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"   📋 Category distribution:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                print(f"      {cat:20} {count:3} transactions")
            
            return categorized_list
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Warning: Claude returned invalid JSON")
            print(f"   Error: {e}")
            print(f"   Response preview: {response['content'][:200]}...")
            
            # Fallback: return transactions with 'other' category
            print(f"   Using fallback: categorizing all as 'other'")
            return [
                {**t, 'category': 'other', 'confidence': 'low'}
                for t in transactions
            ]
    
    def _get_coaching(self, emissions_result: Dict) -> Dict:
        """
        Get personalized coaching from Claude AI.
        
        Process:
        1. Generate coaching prompt with emission data
        2. Call Claude API
        3. Parse JSON recommendations
        4. Handle errors gracefully
        
        Returns:
            Coaching recommendations dictionary
        """
        
        # Generate prompt
        prompt = coaching_prompt(emissions_result)
        
        # Call Claude with higher temperature (more creative)
        response = self.claude.call(
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            temperature=0.7  # Higher temp for creative suggestions
        )
        
        # Parse JSON response
        try:
            coaching = json.loads(response['content'])
            return coaching
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Warning: Could not parse coaching response")
            print(f"   Error: {e}")
            
            # Fallback
            return {
                'recommendations': [],
                'overall_strategy': 'Unable to generate recommendations at this time.',
                'realistic_annual_target_kg': emissions_result['total_emissions_kg'] * 12
            }
    
    def _calculate_period_days(self, transactions: List) -> int:
        """Calculate number of days covered by transactions."""
        if not transactions:
            return 30
        
        dates = [t.date for t in transactions]
        return (max(dates) - min(dates)).days + 1
    
    def _save_results(self, result: Dict, original_file: str) -> str:
        """
        Save analysis results to JSON file.

        Creates filename based on original CSV:
            transactions.csv → carbon_analysis_transactions_2025-01-30.json

        Saves to: src/services/carbon/results/
        """
        # Create output filename
        original_name = Path(original_file).stem
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_name = f"carbon_analysis_{original_name}_{timestamp}.json"

        # Save in results folder within the carbon directory
        carbon_dir = Path(__file__).parent  # src/services/carbon
        results_dir = carbon_dir / "results"
        output_path = results_dir / output_name

        # Create results directory if needed
        results_dir.mkdir(exist_ok=True)

        # Save as formatted JSON
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        return str(output_path)


# Main execution
if __name__ == "__main__":
    """
    Run the analyzer on sample data.
    
    Usage:
        python analyzer.py
    
    Or with custom file:
        python analyzer.py your_transactions.csv
    """
    import sys
    
    # Get file path from command line or use default
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = "src/services/carbon/samples/sample_transactions_5.csv"
    
    print("\n" + "="*70)
    print("ECOLENS - CARBON FOOTPRINT ANALYZER")
    print("="*70)
    
    try:
        # Create analyzer
        print("\n📍 Step: Initializing analyzer...")
        analyzer = CarbonAnalyzer()

        # Run analysis
        print(f"\n📍 Step: Running analysis on {csv_file}...")
        result = analyzer.analyze_file(csv_file)

        # Print summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total Emissions: {result['total_emissions_kg']} kg CO2e")
        print(f"Annual Projection: {result['benchmarks']['your_annual_projection_kg']:,} kg/year")

        if result['coaching']:
            print(f"\nTop Recommendation:")
            top_rec = result['coaching']['recommendations'][0]
            print(f"  → {top_rec['action']}")
            print(f"  → Potential savings: {top_rec['potential_savings_kg']} kg/year")

        print("\n✅ Analysis complete! Check the results file for full details.")

    except FileNotFoundError as e:
        print(f"\n❌ FileNotFoundError: {e}")
        print(f"\n📍 Location: File lookup failed")
        print(f"   File attempted: {csv_file}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"\nUsage: python analyzer.py <path_to_csv>")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ValueError as e:
        print(f"\n❌ ValueError: {e}")
        print(f"\n📍 Location: Validation or initialization failed")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print(f"\n📍 Location: Missing required module")
        print("\nTip: Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Unexpected error ({type(e).__name__}): {e}")
        print(f"\n📍 Location: Error details below")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()