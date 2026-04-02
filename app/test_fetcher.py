#!/usr/bin/env python3
import asyncio
from app.services.medium_stats_fetcher import MediumStatsFetcher

async def test():
    fetcher = MediumStatsFetcher()
    
    if not fetcher.is_authenticated():
        print("❌ Not authenticated. Please:")
        print("   1. Close your browser")
        print("   2. Log into Medium in your browser")
        print("   3. Keep browser open")
        print("   4. Run this script again")
        return
    
    print("✅ Authenticated!")
    print(f"🍪 Cookies: {list(fetcher.cookies.keys())}")
    
    # Test with a story URL
    test_url = "https://medium.com/@mvineetsharma/github-copilot-the-ai-powered-development-ecosystem-1ff02f7934c8"
    print(f"\n📝 Testing with URL: {test_url}")
    
    stats = await fetcher.fetch_post_stats(test_url)
    
    if stats:
        print(f"\n✅ Stats fetched successfully!")
        print(f"   📖 Reads: {stats['totals']['total_reads']}")
        print(f"   👁️ Views: {stats['totals']['total_views']}")
        print(f"   👏 Claps: {stats['totals']['claps']}")
        print(f"   💬 Replies: {stats['totals']['replies']}")
        print(f"   📊 Read Ratio: {stats['totals']['read_ratio']}%")
        print(f"   👑 Member Reads: {stats['totals']['member_reads']}")
        print(f"   🌐 Non-member Reads: {stats['totals']['nonmember_reads']}")
    else:
        print("❌ Failed to fetch stats")

if __name__ == "__main__":
    asyncio.run(test())