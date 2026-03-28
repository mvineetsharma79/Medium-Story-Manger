#!/usr/bin/env python3
"""
Test script for Medium Stats
"""
import os
from datetime import datetime, timedelta

# Set credentials
os.environ['MEDIUM_SID'] = '1:F6kf77r5PKDcd4x+6srlbABmWXOTStI5FecXdpFZsVV1bvT4GkfkKnAZ/P/7Xrkk'
os.environ['MEDIUM_UID'] = '6a63927f9b83'

try:
    from medium_stats.scraper import StatGrabberUser
    print("✅ medium-stats library loaded successfully")
    
    end = datetime.now()
    start = end - timedelta(days=30)
    
    print(f"📅 Fetching stats from {start.date()} to {end.date()}")
    
    grabber = StatGrabberUser(
        'mvineetsharma',
        sid=os.environ['MEDIUM_SID'],
        uid=os.environ['MEDIUM_UID'],
        start=start,
        stop=end
    )
    
    print("📊 Fetching summary stats...")
    stats = grabber.get_summary_stats()
    
    print(f"\n✅ Found {len(stats)} stories in the last 30 days")
    print("\n📖 Recent stories:")
    print("-" * 80)
    
    for i, s in enumerate(stats[:5]):
        title = s.get('title', 'Unknown')
        reads = s.get('reads', 0)
        claps = s.get('upvotes', 0) or s.get('claps', 0)
        views = s.get('views', 0)
        print(f"{i+1}. {title[:60]}")
        print(f"   Reads: {reads}, Claps: {claps}, Views: {views}")
        print()
    
    if stats:
        print(f"\n📈 Total stats for last 30 days:")
        total_reads = sum(s.get('reads', 0) for s in stats)
        total_claps = sum(s.get('upvotes', 0) or s.get('claps', 0) for s in stats)
        total_views = sum(s.get('views', 0) for s in stats)
        print(f"   Total Reads: {total_reads}")
        print(f"   Total Claps: {total_claps}")
        print(f"   Total Views: {total_views}")
    
except ImportError as e:
    print(f"❌ medium-stats library not installed: {e}")
    print("   Run: pip install medium-stats")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()