"""
Emission Calculator
===================
Calculates CO2 emissions from categorized transactions.

This module:
1. Loads emission factors from JSON database
2. Applies appropriate factors based on category
3. Calculates total emissions and breakdown
4. Compares to global benchmarks

No AI used here - pure mathematics.
"""

import json
from typing import Dict, List
from pathlib import Path


class EmissionCalculator:
    """
    Calculate carbon emissions from categorized transactions.
    
    How it works:
    - Each transaction category has emission factors
    - We apply these factors to transaction amounts
    - Sum up to get total footprint
    
    Example:
        Flight for $350 → ~800 kg CO2
        Uber for $20 → ~4.5 kg CO2
        Groceries for $100 → ~10 kg CO2
    """
    
    def __init__(self, factors_file: str = "emission_factors.json"):
        """
        Initialize calculator with emission factors database.
        
        Args:
            factors_file: Path to JSON file with emission factors
        """
        self.factors = self._load_factors(factors_file)
        print(f"✅ Loaded emission factors for {len(self.factors)} categories")
    
    def _load_factors(self, factors_file: str) -> Dict:
        """
        Load emission factors from JSON file.
        
        The JSON contains:
        - categories: CO2 factors for each spending type
        - keyword_hints: Not used in calculator (used by Claude)
        - benchmarks: Global/US averages for comparison
        """
        factors_path = Path(factors_file)
        
        if not factors_path.exists():
            raise FileNotFoundError(
                f"Emission factors file not found: {factors_file}\n"
                f"Make sure emission_factors.json is in the same directory."
            )
        
        with open(factors_path, 'r') as f:
            data = json.load(f)
        
        return data['categories']
    
    def calculate_transaction(self, 
                            category: str, 
                            amount: float,
                            description: str = "") -> float:
        """
        Calculate emissions for a single transaction.
        
        Logic varies by category:
        
        AIR TRAVEL:
            - If amount > $300: assume international (1600 kg)
            - Else: assume domestic (800 kg)
        
        GROUND TRANSPORT:
            - Estimate miles from cost: $20 ≈ 10 miles
            - Apply factor: 0.45 kg CO2 per mile
        
        FOOD/RESTAURANT:
            - Estimate meals: $50 ≈ 2 meals
            - Apply factor: 2.5 kg CO2 per meal
        
        GROCERIES:
            - Simple ratio: $1 ≈ 0.1 kg CO2
        
        ELECTRICITY/UTILITIES:
            - Estimate kWh: $100 ≈ 700 kWh
            - Apply factor: 0.385 kg per kWh
        
        GOODS (electronics, clothing, general):
            - Simple ratio: $1 ≈ 0.10-0.20 kg CO2
        
        Args:
            category: Transaction category (from Claude)
            amount: Dollar amount spent
            description: Transaction description (for context)
            
        Returns:
            Estimated CO2 emissions in kilograms
        """
        
        # --- AIR TRAVEL ---
        if category == "air_travel":
            # Use amount as proxy for flight distance
            # International flights are more expensive
            if amount > 300:
                # International flight average
                return self.factors['air_travel']['international_avg_kg']
            else:
                # Domestic flight average
                return self.factors['air_travel']['domestic_avg_kg']
        
        # --- GROUND TRANSPORT (Uber, Lyft, Gas) ---
        elif category == "ground_transport":
            # Estimate miles traveled: $2 per mile average
            avg_cost_per_mile = self.factors['ground_transport']['avg_cost_per_mile_usd']
            estimated_miles = amount / avg_cost_per_mile
            
            # Apply rideshare emission factor (includes driver's empty return trip)
            kg_per_mile = self.factors['ground_transport']['rideshare_per_mile_kg']
            return estimated_miles * kg_per_mile
        
        # --- RESTAURANT FOOD ---
        elif category == "food_restaurant":
            # Estimate number of meals: $25 per meal average
            avg_cost_per_meal = self.factors['food_restaurant']['avg_cost_per_meal_usd']
            estimated_meals = amount / avg_cost_per_meal
            
            # Apply meal emission factor
            kg_per_meal = self.factors['food_restaurant']['avg_meal_kg']
            return estimated_meals * kg_per_meal
        
        # --- GROCERIES ---
        elif category == "groceries":
            # Simple ratio: groceries have mixed carbon intensity
            kg_per_dollar = self.factors['groceries']['per_dollar_kg']
            return amount * kg_per_dollar
        
        # --- ELECTRICITY ---
        elif category == "electricity":
            # Estimate kWh from bill amount
            avg_kwh_per_dollar = self.factors['electricity']['avg_kwh_per_dollar']
            estimated_kwh = amount * avg_kwh_per_dollar
            
            # Apply grid emission factor (US average)
            kg_per_kwh = self.factors['electricity']['per_kwh_kg']
            return estimated_kwh * kg_per_kwh
        
        # --- NATURAL GAS ---
        elif category == "natural_gas":
            # Estimate therms from bill amount
            avg_therms_per_dollar = self.factors['natural_gas']['avg_therms_per_dollar']
            estimated_therms = amount * avg_therms_per_dollar
            
            # Apply gas emission factor
            kg_per_therm = self.factors['natural_gas']['per_therm_kg']
            return estimated_therms * kg_per_therm
        
        # --- ELECTRONICS ---
        elif category == "goods_electronics":
            kg_per_dollar = self.factors['goods_electronics']['per_dollar_kg']
            return amount * kg_per_dollar
        
        # --- CLOTHING ---
        elif category == "goods_clothing":
            kg_per_dollar = self.factors['goods_clothing']['per_dollar_kg']
            return amount * kg_per_dollar
        
        # --- GENERAL GOODS / OTHER ---
        else:
            # Default: use general goods factor
            kg_per_dollar = self.factors['goods_general']['per_dollar_kg']
            return amount * kg_per_dollar
    
    def calculate_total(self, categorized_transactions: List[Dict]) -> Dict:
        """
        Calculate total emissions and breakdown by category.
        
        Process:
        1. Calculate emissions for each transaction
        2. Group by category
        3. Calculate percentages
        4. Round for readability
        
        Args:
            categorized_transactions: List of dicts with 'category', 'amount', etc.
            
        Returns:
            {
                'total_emissions_kg': 1250.5,
                'total_emissions_tons': 1.25,
                'breakdown': {
                    'air_travel': {
                        'emissions_kg': 800.0,
                        'percentage': 64.0,
                        'count': 1,
                        'total_spent': 350.00,
                        'items': [...]
                    },
                    ...
                }
            }
        """
        print(f"\n🧮 Calculating emissions for {len(categorized_transactions)} transactions...")
        
        breakdown = {}
        total_emissions = 0.0
        
        # Process each transaction
        for transaction in categorized_transactions:
            category = transaction.get('category', 'other')
            amount = transaction['amount']
            description = transaction.get('description', '')
            
            # Calculate emissions for this transaction
            emissions = self.calculate_transaction(category, amount, description)
            total_emissions += emissions
            
            # Add to category breakdown
            if category not in breakdown:
                breakdown[category] = {
                    'emissions_kg': 0.0,
                    'count': 0,
                    'total_spent': 0.0,
                    'items': []
                }
            
            # Accumulate category totals
            breakdown[category]['emissions_kg'] += emissions
            breakdown[category]['count'] += 1
            breakdown[category]['total_spent'] += amount
            
            # Store individual item details
            breakdown[category]['items'].append({
                'description': description,
                'amount': amount,
                'emissions_kg': round(emissions, 2)
            })
        
        # Calculate percentages for each category
        for category in breakdown:
            breakdown[category]['percentage'] = round(
                (breakdown[category]['emissions_kg'] / total_emissions) * 100, 1
            )
            breakdown[category]['emissions_kg'] = round(
                breakdown[category]['emissions_kg'], 2
            )
            breakdown[category]['total_spent'] = round(
                breakdown[category]['total_spent'], 2
            )
        
        # Sort categories by emissions (highest first)
        breakdown = dict(
            sorted(breakdown.items(), 
                   key=lambda x: x[1]['emissions_kg'], 
                   reverse=True)
        )
        
        print(f"✅ Total emissions: {round(total_emissions, 2)} kg CO2e")
        
        return {
            'total_emissions_kg': round(total_emissions, 2),
            'total_emissions_tons': round(total_emissions / 1000, 3),
            'breakdown': breakdown
        }
    
    def get_benchmarks(self, total_emissions_kg: float, period_days: int = 30) -> Dict:
        """
        Compare user's emissions to global benchmarks.
        
        Benchmarks:
        - US Average: 16,000 kg/year (highest in developed world)
        - Global Average: 4,000 kg/year
        - Paris Agreement Target: 2,300 kg/year (to limit warming to 1.5°C)
        - European Average: 6,800 kg/year
        
        Args:
            total_emissions_kg: Total emissions for the period
            period_days: Number of days in the analyzed period
            
        Returns:
            {
                'us_average_annual_kg': 16000,
                'your_annual_projection_kg': 14600,
                'comparison': {
                    'vs_us_average': 91.3,
                    'vs_paris_target': 635.2
                }
            }
        """
        # Project to annual based on period length
        annual_projection = (total_emissions_kg / period_days) * 365
        
        # Load benchmark values from emission factors
        benchmarks_path = Path("emission_factors.json")
        with open(benchmarks_path, 'r') as f:
            data = json.load(f)
        benchmarks = data['benchmarks']
        
        return {
            'us_average_annual_kg': benchmarks['us_average_annual_kg'],
            'global_average_annual_kg': benchmarks['global_average_annual_kg'],
            'paris_target_annual_kg': benchmarks['paris_target_annual_kg'],
            'european_average_annual_kg': benchmarks['european_average_annual_kg'],
            'your_annual_projection_kg': round(annual_projection, 0),
            'comparison': {
                'vs_us_average': round((annual_projection / benchmarks['us_average_annual_kg']) * 100, 1),
                'vs_global_average': round((annual_projection / benchmarks['global_average_annual_kg']) * 100, 1),
                'vs_paris_target': round((annual_projection / benchmarks['paris_target_annual_kg']) * 100, 1)
            }
        }


# Example usage / testing
if __name__ == "__main__":
    """
    Test the calculator with sample categorized transactions.
    
    Run this file directly to test:
        python calculator.py
    """
    import json
    
    # Sample categorized transactions (as if from Claude)
    sample_transactions = [
        {
            'category': 'air_travel',
            'amount': 420.00,
            'description': 'Delta Airlines NYC-LAX'
        },
        {
            'category': 'ground_transport',
            'amount': 15.50,
            'description': 'Uber to office'
        },
        {
            'category': 'groceries',
            'amount': 85.30,
            'description': 'Whole Foods'
        },
        {
            'category': 'food_restaurant',
            'amount': 68.50,
            'description': 'The Cheesecake Factory'
        }
    ]
    
    # Create calculator
    calculator = EmissionCalculator()
    
    # Calculate emissions
    result = calculator.calculate_total(sample_transactions)
    
    # Get benchmarks
    benchmarks = calculator.get_benchmarks(result['total_emissions_kg'], period_days=30)
    
    # Print results
    print("\n📊 RESULTS:")
    print(json.dumps({**result, 'benchmarks': benchmarks}, indent=2))