"""
Claude Prompt Templates
========================
Pre-written prompts for Claude API calls.

This module contains:
1. Categorization prompt - classify transactions
2. Coaching prompt - generate reduction advice

Good prompts are:
- Clear and specific
- Include examples
- Specify output format (JSON)
- Give context/constraints
"""

from typing import List, Dict


def categorization_prompt(transactions: List[Dict]) -> str:
    """
    Generate prompt for transaction categorization.
    
    This prompt asks Claude to:
    1. Look at transaction descriptions
    2. Categorize each one
    3. Return structured JSON
    4. Include confidence level
    
    Args:
        transactions: List of dicts with 'description' and 'amount'
    
    Returns:
        Formatted prompt string for Claude
    """
    
    # Format transactions for the prompt
    # Example: "- Delta Airlines ($420.00)"
    transactions_text = "\n".join([
        f"- {t['description']} (${t['amount']:.2f})"
        for t in transactions
    ])
    
    # Build the prompt
    # Note: We're very explicit about what we want
    prompt = f"""You are an expert at categorizing financial transactions for carbon footprint analysis.

AVAILABLE CATEGORIES:
- air_travel: Flights, airlines (Delta, United, Southwest, etc.)
- ground_transport: Uber, Lyft, taxis, gas stations (Shell, Chevron, etc.)
- food_restaurant: Restaurants, cafes, fast food (Starbucks, Chipotle, etc.)
- groceries: Grocery stores (Whole Foods, Safeway, Trader Joe's, etc.)
- electricity: Utility bills, power companies (PG&E, Duke Energy, etc.)
- natural_gas: Gas utilities, heating bills
- goods_electronics: Electronics stores (Amazon, Best Buy, Apple Store, etc.)
- goods_clothing: Clothing stores (Nordstrom, Gap, H&M, etc.)
- goods_general: Other purchases (Target, Walmart, general merchandise)

TRANSACTIONS TO CATEGORIZE:
{transactions_text}

INSTRUCTIONS:
1. Categorize each transaction based on the merchant/description
2. Use your best judgment for unclear cases
3. Return ONLY valid JSON (no markdown, no explanations)
4. Include confidence level: high/medium/low

REQUIRED JSON FORMAT:
{{
  "categorized_transactions": [
    {{
      "description": "exact original description",
      "amount": exact_amount,
      "category": "chosen_category",
      "confidence": "high/medium/low",
      "reasoning": "brief 1-sentence explanation"
    }}
  ]
}}

Remember: Return ONLY the JSON object, nothing else."""
    
    return prompt


def coaching_prompt(analysis_result: Dict) -> str:
    """
    Generate prompt for personalized coaching.
    
    This prompt asks Claude to:
    1. Analyze the user's emission breakdown
    2. Identify highest-impact areas
    3. Generate specific, actionable advice
    4. Estimate potential savings
    5. Return structured JSON
    
    Args:
        analysis_result: Complete emission analysis with breakdown
    
    Returns:
        Formatted prompt string for Claude
    """
    
    # Extract key information
    total_kg = analysis_result['total_emissions_kg']
    breakdown = analysis_result['breakdown']
    
    # Find top 3 emission sources
    top_categories = sorted(
        breakdown.items(),
        key=lambda x: x[1]['emissions_kg'],
        reverse=True
    )[:3]
    
    # Format top categories for the prompt
    top_text = "\n".join([
        f"- {cat}: {data['emissions_kg']} kg CO2 ({data['percentage']}% of total)"
        for cat, data in top_categories
    ])
    
    # Build the prompt
    prompt = f"""You are an expert environmental coach helping someone reduce their carbon footprint.

CURRENT SITUATION:
- Total monthly emissions: {total_kg} kg CO2
- Projected annual emissions: {total_kg * 12} kg CO2
- Top emission sources:
{top_text}

GLOBAL CONTEXT:
- US Average: 16,000 kg CO2/year
- Global Average: 4,000 kg CO2/year
- Paris Agreement Target: 2,300 kg CO2/year (to limit warming to 1.5°C)

YOUR TASK:
Generate 5 specific, actionable recommendations to reduce emissions.

REQUIREMENTS FOR EACH RECOMMENDATION:
1. Focus on highest-impact categories first
2. Provide CONCRETE actions (not vague like "use less")
3. Estimate realistic annual CO2 savings in kg
4. Rate difficulty: easy/medium/hard
5. Suggest implementation timeline
6. Explain WHY it works

EXAMPLES OF GOOD RECOMMENDATIONS:
✓ "Replace domestic flights under 500 miles with train travel"
✓ "Carpool to work 3 days/week or use public transit"
✓ "Reduce meat consumption to 3 meals/week (currently ~7)"
✓ "Switch to a renewable energy plan from your utility"

EXAMPLES OF BAD RECOMMENDATIONS:
✗ "Be more environmentally conscious" (too vague)
✗ "Stop flying forever" (unrealistic)
✗ "Move to a different country" (impractical)

REQUIRED JSON FORMAT:
{{
  "recommendations": [
    {{
      "action": "specific action to take",
      "category": "which emission category this addresses",
      "potential_savings_kg": annual_kg_saved,
      "difficulty": "easy/medium/hard",
      "timeline": "how long to implement",
      "explanation": "why this works and how to do it"
    }}
  ],
  "overall_strategy": "2-3 sentence summary of recommended approach",
  "realistic_annual_target_kg": achievable_annual_target_number
}}

Return ONLY the JSON object, nothing else."""
    
    return prompt


# Example usage / testing
if __name__ == "__main__":
    """
    Test the prompt templates.
    
    Run this file directly to see prompts:
        python prompts.py
    """
    
    # Sample transactions
    sample_transactions = [
        {'description': 'DELTA AIR 006-123456', 'amount': 420.00},
        {'description': 'UBER *TRIP', 'amount': 15.50},
        {'description': 'WHOLE FOODS MKT', 'amount': 85.30}
    ]
    
    # Sample analysis result
    sample_analysis = {
        'total_emissions_kg': 908.7,
        'breakdown': {
            'air_travel': {
                'emissions_kg': 800.0,
                'percentage': 88.0
            },
            'ground_transport': {
                'emissions_kg': 6.7,
                'percentage': 1.0
            },
            'groceries': {
                'emissions_kg': 8.5,
                'percentage': 1.0
            }
        }
    }
    
    print("="*70)
    print("CATEGORIZATION PROMPT")
    print("="*70)
    print(categorization_prompt(sample_transactions))
    
    print("\n\n")
    
    print("="*70)
    print("COACHING PROMPT")
    print("="*70)
    print(coaching_prompt(sample_analysis))