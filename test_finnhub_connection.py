#!/usr/bin/env python3
"""
Test Finnhub API Connection
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import finnhub

# Load environment variables
load_dotenv()

def test_finnhub_connection():
    """Test Finnhub API connection"""
    print("🔍 Testing Finnhub API Connection...")

    # Check API key
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key or api_key == 'your_finnhub_api_key_here':
        print("❌ FINNHUB_API_KEY not set in .env file")
        print("   Please get your API key from https://finnhub.io/")
        return False

    try:
        # Initialize client
        client = finnhub.Client(api_key=api_key)
        print("✅ Finnhub client initialized")

        # Test basic API call - get quote for AAPL
        print("📡 Testing API call (AAPL quote)...")
        quote = client.quote('AAPL')

        if quote and 'c' in quote:
            print(f"✅ API call successful! AAPL price: ${quote['c']}")
            return True
        else:
            print("❌ API call failed - no data returned")
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_finnhub_connection()
    sys.exit(0 if success else 1)