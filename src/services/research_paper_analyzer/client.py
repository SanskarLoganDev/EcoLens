"""
Claude API Client with Vision Support
======================================
Enhanced version of the client that supports both text and vision API calls.

New additions:
- call_vision() method for analyzing images
- Support for base64 image input
- Separate cost tracking for vision API

Used by: vision_analyzer.py, summarizer.py
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
    Enhanced Claude API wrapper with Vision support.
    
    Supports:
    - Text-only API calls (for summarization)
    - Vision API calls (for chart/image analysis)
    - Cost tracking for both
    
    Usage:
        client = ClaudeClient()
        
        # Text call
        response = client.call(messages=[...])
        
        # Vision call
        response = client.call_vision(
            image_data=base64_encoded_image,
            prompt="Analyze this chart"
        )
    """
    
    # Pricing (as of December 2024)
    INPUT_COST_PER_1M = 3.00    # $3 per million input tokens
    OUTPUT_COST_PER_1M = 15.00  # $15 per million output tokens
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude API client.
        
        Args:
            api_key: Anthropic API key (or use CLAUDE_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Claude API key not found!\n"
                "Set CLAUDE_API_KEY environment variable"
            )
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4000
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.text_calls = 0
        self.vision_calls = 0
        
        print(f"✅ Claude API client initialized (with Vision support)")
    
    def call(self, 
            messages: List[Dict],
            system: Optional[str] = None,
            temperature: float = 1.0) -> Dict:
        """
        Make a standard text-only API call.
        
        This is the same as the carbon feature client.
        
        Args:
            messages: List of message dicts [{'role': 'user', 'content': '...'}]
            system: Optional system prompt
            temperature: Sampling temperature (0-1)
            
        Returns:
            {
                'content': "Claude's response",
                'usage': {'input_tokens': ..., 'output_tokens': ...}
            }
        """
        try:
            params = {
                'model': self.model,
                'max_tokens': self.max_tokens,
                'messages': messages,
                'temperature': temperature
            }
            
            if system:
                params['system'] = system
            
            print(f"🤖 Calling Claude API (text)...")
            
            response = self.client.messages.create(**params)
            
            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.text_calls += 1
            
            content = response.content[0].text
            
            print(f"✅ API call successful")
            print(f"   Input: {input_tokens} tokens, Output: {output_tokens} tokens")
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
    
    def call_vision(self,
                   image_data: str,
                   prompt: str,
                   temperature: float = 0.5) -> Dict:
        """
        Make a Vision API call to analyze an image.
        
        NEW METHOD for Feature 2!
        
        Args:
            image_data: Base64-encoded image string
            prompt: What to ask Claude about the image
            temperature: Sampling temperature (default 0.5 for analysis)
            
        Returns:
            {
                'content': "Claude's analysis of the image",
                'usage': {'input_tokens': ..., 'output_tokens': ...}
            }
            
        Example:
            response = client.call_vision(
                image_data="iVBORw0KGgoAAAANS...",  # base64
                prompt="Describe this chart and its key findings"
            )
        """
        try:
            # Build message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",  # or "image/jpeg"
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            print(f"👁️  Calling Claude Vision API...")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                temperature=temperature
            )
            
            # Track usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.vision_calls += 1
            
            content = response.content[0].text
            
            print(f"✅ Vision API call successful")
            print(f"   Input: {input_tokens} tokens, Output: {output_tokens} tokens")
            print(f"   Cost: ${self._calculate_call_cost(input_tokens, output_tokens):.4f}")
            
            return {
                'content': content,
                'usage': {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                }
            }
            
        except Exception as e:
            print(f"❌ Claude Vision API error: {e}")
            raise Exception(f"Vision API call failed: {e}")
    
    def _calculate_call_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of a single API call"""
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost
    
    def get_cost_estimate(self) -> Dict:
        """
        Get total cost estimate for all API calls.
        
        Enhanced to show text vs vision breakdown.
        """
        input_cost = (self.total_input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (self.total_output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost
        
        return {
            'total_calls': self.text_calls + self.vision_calls,
            'text_calls': self.text_calls,
            'vision_calls': self.vision_calls,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'input_cost_usd': round(input_cost, 4),
            'output_cost_usd': round(output_cost, 4),
            'total_cost_usd': round(total_cost, 4)
        }
    
    def reset_tracking(self):
        """Reset cost tracking counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.text_calls = 0
        self.vision_calls = 0
        print("🔄 Cost tracking reset")


# Example usage / testing
if __name__ == "__main__":
    """
    Test the client with both text and vision calls.
    """
    import json
    
    try:
        client = ClaudeClient()
        
        # Test 1: Text call
        print("\n" + "="*60)
        print("TEST 1: Standard text call")
        print("="*60)
        
        response = client.call(
            messages=[
                {
                    'role': 'user',
                    'content': 'Explain ocean acidification in one sentence.'
                }
            ],
            temperature=0.5
        )
        
        print("\n📝 Response:")
        print(response['content'])
        
        # Test 2: Vision call would need actual image
        # Skipping for now as it requires base64 image
        
        # Show cost
        print("\n" + "="*60)
        print("COST SUMMARY")
        print("="*60)
        cost_info = client.get_cost_estimate()
        print(json.dumps(cost_info, indent=2))
        
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nTo test, set your API key:")
        print("  export CLAUDE_API_KEY='your_key_here'")