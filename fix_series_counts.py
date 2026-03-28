#!/usr/bin/env python3
"""Fix series counts based on story status"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.story_service import StoryService
from app.services.file_service import load_stories_data, save_stories_data

async def fix_series_counts():
    print("🔧 Fixing series counts based on status = Published...")
    
    data = await load_stories_data()
    stories = data.get("stories", {})
    series_data = data.get("series", {})
    
    print(f"\n📊 Found {len(series_data)} series")
    
    for series_name, series_info in series_data.items():
        total = 0
        published = 0
        for story_key in series_info.get("stories", []):
            if story_key in stories:
                total += 1
                if stories[story_key].get("status") == "Published":
                    published += 1
                    print(f"  ✅ {story_key} - Published")
                else:
                    print(f"  ❌ {story_key} - Not Published")
        
        print(f"\n📁 Series: {series_name}")
        print(f"   Total stories: {total}")
        print(f"   Published: {published}")
        
        series_info["total_stories"] = total
        series_info["published"] = published
    
    data["series"] = series_data
    await save_stories_data(data)
    
    print("\n✅ Series counts fixed successfully!")

if __name__ == "__main__":
    asyncio.run(fix_series_counts())