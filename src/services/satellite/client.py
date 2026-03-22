"""
Satellite Client - Claude API Wrapper
======================================
Enhanced Claude API client specifically for satellite image analysis.

Features:
- Vision API for satellite imagery
- Text API for change analysis
- Cost tracking per analysis
- Caching support

Used by: vision_comparator.py, change_detector.py
"""

import os
import json
import re
from typing import Dict, Optional
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv, find_dotenv

# Load environment variables
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"✅ Loaded .env from: {dotenv_path}")
else:
    load_dotenv()


def strip_markdown_json(text: str) -> str:
    """Strip markdown code blocks from JSON response."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()


class SatelliteClient:
    """
    Claude API client optimized for satellite image analysis.

    Usage:
        client = SatelliteClient()
        result = client.analyze_image(image_base64="...", prompt="...")
    """

    INPUT_COST_PER_1M = 3.00
    OUTPUT_COST_PER_1M = 15.00

    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Claude API key not found!\n"
                "Set CLAUDE_API_KEY environment variable or pass api_key parameter"
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4000

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.vision_calls = 0
        self.text_calls = 0

        # Caching
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(__file__).parent / "data" / "cache"
        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"✅ Satellite Client initialized (Vision API enabled)")
        if cache_enabled:
            print(f"   Cache: Enabled ({self.cache_dir})")

    def analyze_image(self,
                      image_base64: str,
                      prompt: str,
                      temperature: float = 0.5,
                      use_cache: bool = True) -> Dict:
        """
        Analyze a satellite image using Claude Vision API.

        Returns:
            {
                'content': "Claude's analysis (JSON string)",
                'parsed': {...},
                'usage': {'input_tokens': ..., 'output_tokens': ...},
                'from_cache': True/False
            }
        """

        # Check cache first
        if self.cache_enabled and use_cache:
            cache_key = self._get_cache_key(image_base64, prompt)
            cached = self._load_from_cache(cache_key)
            if cached:
                print(f"   ✓ Loaded from cache (saved API call)")
                return {**cached, 'from_cache': True}

        try:
            print(f"   🤖 Calling Claude Vision API...")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                temperature=temperature
            )

            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.vision_calls += 1

            parsed = None
            try:
                parsed = json.loads(strip_markdown_json(content))
            except json.JSONDecodeError:
                print(f"   ⚠️  Response not valid JSON, returning as text")

            result = {
                'content': content,
                'parsed': parsed,
                'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens},
                'from_cache': False
            }

            if self.cache_enabled:
                self._save_to_cache(cache_key, result)

            cost = self._calculate_call_cost(input_tokens, output_tokens)
            print(f"   ✓ Vision analysis complete")
            print(f"      Tokens: {input_tokens} in, {output_tokens} out")
            print(f"      Cost: ${cost:.4f}")

            return result

        except Exception as e:
            print(f"   ❌ Vision API error: {e}")
            raise Exception(f"Vision API call failed: {e}")

    def analyze_text(self,
                     prompt: str,
                     temperature: float = 0.7,
                     system: Optional[str] = None) -> Dict:
        """Text-only API call for comparisons and summaries."""

        try:
            print(f"   🤖 Calling Claude Text API...")

            params = {
                'model': self.model,
                'max_tokens': self.max_tokens,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature
            }
            if system:
                params['system'] = system

            response = self.client.messages.create(**params)
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.text_calls += 1

            parsed = None
            try:
                parsed = json.loads(strip_markdown_json(content))
            except json.JSONDecodeError:
                pass

            cost = self._calculate_call_cost(input_tokens, output_tokens)
            print(f"   ✓ Text analysis complete")
            print(f"      Tokens: {input_tokens} in, {output_tokens} out")
            print(f"      Cost: ${cost:.4f}")

            return {
                'content': content,
                'parsed': parsed,
                'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens}
            }

        except Exception as e:
            print(f"   ❌ Text API error: {e}")
            raise Exception(f"Text API call failed: {e}")

    def get_cost_summary(self) -> Dict:
        input_cost = (self.total_input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (self.total_output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost
        return {
            'total_calls': self.vision_calls + self.text_calls,
            'vision_calls': self.vision_calls,
            'text_calls': self.text_calls,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'input_cost_usd': round(input_cost, 4),
            'output_cost_usd': round(output_cost, 4),
            'total_cost_usd': round(total_cost, 4),
            'breakdown': {
                'vision_estimate': round(self.vision_calls * 0.005, 4),
                'text_estimate': round(self.text_calls * 0.02, 4)
            }
        }

    def reset_tracking(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.vision_calls = 0
        self.text_calls = 0
        print("🔄 Cost tracking reset")

    def _calculate_call_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost

    def _get_cache_key(self, image_base64: str, prompt: str) -> str:
        import hashlib
        combined = image_base64[:1000] + prompt
        return hashlib.md5(combined.encode()).hexdigest()

    def _save_to_cache(self, cache_key: str, result: Dict):
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_data = {
                'content': result['content'],
                'parsed': result['parsed'],
                'usage': result['usage']
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"   ⚠️  Cache save failed: {e}")

    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"   ⚠️  Cache load failed: {e}")
            return None

    def clear_cache(self):
        if not self.cache_enabled:
            print("Cache not enabled")
            return
        cache_files = list(self.cache_dir.glob("*.json"))
        for f in cache_files:
            f.unlink()
        print(f"🗑️  Cleared {len(cache_files)} cached responses")
