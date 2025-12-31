"""
Claude API Client
=================
Wrapper for Anthropic's Claude API with cost tracking.

This module:
1. Handles authentication with API key
2. Makes API calls to Claude
3. Tracks token usage and costs
4. Provides cost estimates

Used for:
- Transaction categorization
- Personalized coaching advice
"""

import os
from typing import Dict, List, Optional
from anthropic import Anthropic
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
# find_dotenv() automatically searches up the directory tree for .env
# This is the standard, professional way to handle .env files
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"✅ Loaded .env from: {dotenv_path}")
else:
    # Fallback: try loading from current working directory
    load_dotenv()  # This will silently fail if .env doesn't exist


class ClaudeClient:
    """
    Wrapper for Claude API with built-in cost tracking.
    
    Usage:
        client = ClaudeClient()
        response = client.call(messages=[...])
        cost = client.get_cost_estimate()
    """
    
    # Claude Sonnet 4 pricing (as of December 2025)
    # These are per MILLION tokens
    INPUT_COST_PER_1M = 3.00   # $3 per million input tokens
    OUTPUT_COST_PER_1M = 15.00  # $15 per million output tokens
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API client.
        
        Args:
            api_key: Anthropic API key (or use CLAUDE_API_KEY env variable)
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Claude API key not found!\n"
                "Either:\n"
                "  1. Pass api_key parameter, or\n"
                "  2. Set CLAUDE_API_KEY environment variable\n"
                "\n"
                "Get your API key from: https://console.anthropic.com/"
            )
        
        # Initialize Anthropic client
        self.client = Anthropic(api_key=self.api_key)
        
        # Default model (Sonnet 4 - good balance of cost/quality)
        self.model = "claude-sonnet-4-20250514"
        
        # Maximum tokens Claude can generate
        self.max_tokens = 4000
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        
        print(f"✅ Claude API client initialized")
        print(f"   Model: {self.model}")
        print(f"   Max tokens: {self.max_tokens}")
    
    def call(self, 
            messages: List[Dict],
            system: Optional[str] = None,
            temperature: float = 1.0) -> Dict:
        """
        Make a call to Claude API.
        
        Args:
            messages: List of message dicts
                Example: [
                    {'role': 'user', 'content': 'Hello Claude!'}
                ]
            
            system: Optional system prompt (instructions for Claude)
                Example: "You are a helpful assistant that..."
            
            temperature: Sampling temperature (0-1)
                - 0.0 = deterministic (same input → same output)
                - 1.0 = creative (more variation)
                Use lower for categorization, higher for coaching
        
        Returns:
            {
                'content': "Claude's response text",
                'usage': {
                    'input_tokens': 150,
                    'output_tokens': 300
                }
            }
        """
        try:
            # Build API call parameters
            params = {
                'model': self.model,
                'max_tokens': self.max_tokens,
                'messages': messages,
                'temperature': temperature
            }
            
            # Add system prompt if provided
            if system:
                params['system'] = system
            
            print(f"\n🤖 Calling Claude API...")
            print(f"   Temperature: {temperature}")
            if system:
                print(f"   System prompt: {system[:50]}...")
            
            # Make the API call
            response = self.client.messages.create(**params)
            
            # Extract usage information
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Update cost tracking
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.call_count += 1
            
            # Extract response text
            content = response.content[0].text
            
            print(f"✅ API call successful")
            print(f"   Input tokens: {input_tokens}")
            print(f"   Output tokens: {output_tokens}")
            print(f"   Cost: ${self._calculate_call_cost(input_tokens, output_tokens):.4f}")
            
            return {
                'content': content,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                }
            }
            
        except Exception as e:
            print(f"❌ Claude API error: {e}")
            raise Exception(f"Claude API call failed: {e}")
    
    def _calculate_call_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost of a single API call.
        
        Formula:
            cost = (input_tokens / 1M * $3) + (output_tokens / 1M * $15)
        """
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost
    
    def get_cost_estimate(self) -> Dict:
        """
        Get total cost estimate based on all API calls.
        
        Returns:
            {
                'total_calls': 5,
                'total_input_tokens': 2500,
                'total_output_tokens': 1800,
                'input_cost_usd': 0.0075,
                'output_cost_usd': 0.027,
                'total_cost_usd': 0.0345
            }
        """
        input_cost = (self.total_input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (self.total_output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost
        
        return {
            'total_calls': self.call_count,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'input_cost_usd': round(input_cost, 4),
            'output_cost_usd': round(output_cost, 4),
            'total_cost_usd': round(total_cost, 4)
        }
    
    def reset_tracking(self):
        """Reset cost tracking counters."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        print("🔄 Cost tracking reset")


# Example usage / testing
if __name__ == "__main__":
    """
    Test the Claude client with a simple call.
    
    Run this file directly to test:
        python client.py
    
    Note: Requires CLAUDE_API_KEY environment variable
    """
    import json
    
    # Create client
    try:
        client = ClaudeClient()
        
        # Test call
        response = client.call(
            messages=[
                {
                    'role': 'user',
                    'content': 'Say hello in exactly 5 words.'
                }
            ],
            temperature=0.5
        )
        
        print("\n📝 Claude's response:")
        print(response['content'])
        
        # Show cost
        print("\n💰 Total cost:")
        cost_info = client.get_cost_estimate()
        print(json.dumps(cost_info, indent=2))
        
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nTo test this, set your API key:")
        print("  export CLAUDE_API_KEY='your_key_here'")