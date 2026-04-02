#!/usr/bin/env python3
"""
Test script for Medium Stats Fetcher - Dumps Complete Response JSON
"""

import asyncio
import sys
import os
import json

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.medium_stats_fetcher import MediumStatsFetcher

async def test():
    """Test the Medium stats fetcher and dump complete JSON response"""
    
    print("\n" + "="*80)
    print(" MEDIUM STATS FETCHER - RAW JSON DUMP")
    print("="*80 + "\n")
    
    # Initialize fetcher
    print("🔧 Initializing MediumStatsFetcher...")
    fetcher = MediumStatsFetcher()
    
    # Check authentication
    if not fetcher.is_authenticated():
        print("\n❌ NOT AUTHENTICATED")
        print("\nPlease follow these steps:")
        print("  1. Close your browser completely")
        print("  2. Open Chrome or Firefox")
        print("  3. Go to https://medium.com")
        print("  4. Log into your Medium account")
        print("  5. Keep the browser open")
        print("  6. Run this script again")
        return False
    
    print("\n✅ AUTHENTICATION SUCCESSFUL!")
    print(f"🍪 Cookies found: {list(fetcher.cookies.keys())}")
    
    # Test URL
    test_url = "https://medium.com/@mvineetsharma/github-copilot-the-ai-powered-development-ecosystem-1ff02f7934c8"
    
    print("\n" + "="*80)
    print(f"📝 TEST URL: {test_url}")
    print("="*80)
    
    print("\n⏰ Waiting 6 seconds to avoid rate limiting...")
    
    # Fetch stats
    stats = await fetcher.fetch_post_stats(test_url)
    
    if stats:
        print("\n" + "="*80)
        print("✅ RAW JSON RESPONSE FROM MEDIUM API")
        print("="*80)
        
        # Dump complete JSON response
        print(json.dumps(stats, indent=2, default=str))
        
        print("\n" + "="*80)
        print("📊 PARSED STATISTICS SUMMARY")
        print("="*80)
        print(f"\n📅 Period: {stats['period']['start']} → {stats['period']['end']}")
        
        print(f"\n📖 READS:")
        print(f"   Total Reads: {stats['totals']['total_reads']:,}")
        print(f"   Member Reads: {stats['totals']['member_reads']:,}")
        print(f"   Non-member Reads: {stats['totals']['nonmember_reads']:,}")
        
        print(f"\n👁️ VIEWS:")
        print(f"   Total Views: {stats['totals']['total_views']:,}")
        print(f"   Member Views: {stats['totals']['member_views']:,}")
        print(f"   Non-member Views: {stats['totals']['nonmember_views']:,}")
        
        print(f"\n💬 ENGAGEMENT:")
        print(f"   Claps: {stats['totals']['claps']:,}")
        print(f"   Replies: {stats['totals']['replies']:,}")
        print(f"   Highlights: {stats['totals']['highlights']:,}")
        print(f"   New Followers: {stats['totals']['new_followers']:,}")
        
        print(f"\n📊 RATIOS:")
        print(f"   Read Ratio: {stats['totals']['read_ratio']}%")
        print(f"   Member Read %: {stats['totals']['member_read_percentage']}%")
        
        print(f"\n📆 Daily Breakdown: {len(stats['daily_breakdown'])} days")
        
        # Optionally save JSON to file
        with open("medium_stats_response.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, default=str)
        print(f"\n💾 Full JSON response saved to: medium_stats_response.json")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80 + "\n")
        return True
    else:
        print("\n❌ FAILED TO FETCH STATS")
        return False

async def test_raw_response():
    """Test and dump the raw GraphQL response before parsing"""
    
    import requests
    import time
    
    print("\n" + "="*80)
    print(" RAW GRAPHQL RESPONSE DUMP")
    print("="*80 + "\n")
    
    fetcher = MediumStatsFetcher()
    
    if not fetcher.is_authenticated():
        print("❌ Not authenticated")
        return False
    
    test_url = "https://medium.com/@mvineetsharma/github-copilot-the-ai-powered-development-ecosystem-1ff02f7934c8"
    post_id = fetcher.extract_post_id_from_url(test_url)
    
    print(f"📝 Post ID: {post_id}")
    print(f"🔗 URL: {test_url}")
    
    # Create session
    session = requests.Session()
    for name, value in fetcher.cookies.items():
        session.cookies.set(name, value, domain=".medium.com", path="/")
    
    url = "https://medium.com/_/graphql"
    payload = fetcher._get_graphql_payload(post_id)
    headers = fetcher._get_headers(post_id)
    
    print("\n📤 REQUEST DETAILS:")
    print(f"   URL: {url}")
    print(f"   Headers: {json.dumps(headers, indent=2)}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    print("\n⏰ Waiting 6 seconds...")
    time.sleep(6)
    
    print("\n🚀 Sending request...")
    response = session.post(url, headers=headers, json=payload, timeout=30)
    
    print(f"\n📥 RESPONSE STATUS: {response.status_code}")
    
    if response.status_code == 200:
        raw_data = response.json()
        
        print("\n" + "="*80)
        print(" RAW GRAPHQL RESPONSE JSON")
        print("="*80)
        print(json.dumps(raw_data, indent=2))
        
        # Save raw response
        with open("raw_graphql_response.json", "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2)
        print(f"\n💾 Raw response saved to: raw_graphql_response.json")
        
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    import sys
    
    # Choose which test to run
    if "--raw" in sys.argv or "-r" in sys.argv:
        asyncio.run(test_raw_response())
    else:
        asyncio.run(test())