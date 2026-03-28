from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import re

from app.services.file_service import (
    load_stories_data, save_stories_data,
    get_calendar_md_path, get_calendar_json_path,
    parse_series_number
)
from app.models import CalendarEntry, CalendarResponse

class CalendarService:
    @staticmethod
    async def generate_calendar() -> Tuple[List[Dict], Dict[str, Any]]:
        """Generate publishing calendar"""
        data = await load_stories_data()
        settings = data.get("calendar_settings", {})
        
        stories_per_week = settings.get("stories_per_week", 3)
        start_date = datetime.strptime(
            settings.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            "%Y-%m-%d"
        )
        preferred_days = settings.get("preferred_publish_days", ["Monday", "Tuesday", "Wednesday", "Thursday"])
        
        day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        preferred_weekdays = [day_map[d] for d in preferred_days if d in day_map]
        if not preferred_weekdays:
            preferred_weekdays = [0, 1, 2, 3]
        
        # Gather unpublished stories
        unpublished = []
        for story_key, story in data["stories"].items():
            if story.get("published_date") is None and story.get("status") != "Archived":
                part_number = parse_series_number(story.get("name", ""))
                unpublished.append({
                    "key": story_key,
                    "name": story.get("name", ""),
                    "series": story.get("series"),
                    "part": part_number,
                    "folder": story.get("folder", ""),
                    "rel_path": story.get("rel_path", ""),
                    "read_time": story.get("read_time", 25)
                })
        
        # Group by series and sort by part number
        series_groups = defaultdict(list)
        for story in unpublished:
            series_groups[story["series"]].append(story)
        
        for series_name, stories in series_groups.items():
            stories.sort(key=lambda x: x["part"] if x["part"] else 999)
        
        # Get last published dates
        last_published_by_series = {}
        for story_key, story in data["stories"].items():
            pub_date = story.get("published_date")
            if pub_date and story.get("series"):
                series = story["series"]
                pub_dt = datetime.strptime(pub_date, "%Y-%m-%d")
                if series not in last_published_by_series or pub_dt > last_published_by_series[series]:
                    last_published_by_series[series] = pub_dt
        
        # Generate calendar
        calendar = []
        current_date = start_date
        published_this_week = 0
        series_last_scheduled = {}
        
        def get_spacing(series_name):
            if series_name in data.get("series", {}):
                return data["series"][series_name].get("spacing_days", settings.get("series_spacing_days", 7))
            return settings.get("series_spacing_days", 7)
        
        def get_next_available_date(series_name, target_date):
            spacing = get_spacing(series_name)
            last_published = last_published_by_series.get(series_name)
            last_scheduled = series_last_scheduled.get(series_name)
            
            earliest = target_date
            if last_published:
                earliest = max(earliest, last_published + timedelta(days=spacing))
            if last_scheduled:
                earliest = max(earliest, last_scheduled + timedelta(days=spacing))
            
            return earliest
        
        remaining = unpublished.copy()
        
        while remaining and len(calendar) < 200:
            if published_this_week >= stories_per_week:
                days_to_next_week = 7 - current_date.weekday()
                current_date += timedelta(days=days_to_next_week)
                published_this_week = 0
            
            while current_date.weekday() not in preferred_weekdays:
                current_date += timedelta(days=1)
            
            best_story = None
            best_date = None
            
            for story in remaining:
                series = story["series"]
                available_date = get_next_available_date(series, current_date)
                
                if available_date <= current_date:
                    best_story = story
                    best_date = current_date
                    break
                
                if best_story is None or available_date < best_date:
                    best_story = story
                    best_date = available_date
            
            if best_story is None:
                break
            
            if best_date > current_date:
                current_date = best_date
                published_this_week = 0
            
            calendar.append({
                "date": best_date.strftime("%Y-%m-%d"),
                "weekday": best_date.strftime("%A"),
                "story_key": best_story["key"],
                "name": best_story["name"],
                "series": best_story["series"],
                "part": best_story["part"],
                "read_time": best_story["read_time"]
            })
            
            series_last_scheduled[best_story["series"]] = best_date
            remaining.remove(best_story)
            published_this_week += 1
            current_date += timedelta(days=1)
        
        # Summary
        series_counts = defaultdict(int)
        for entry in calendar:
            series_counts[entry["series"]] += 1
        
        summary = {
            "total_scheduled": len(calendar),
            "stories_per_week": stories_per_week,
            "series_spacing_default": settings.get("series_spacing_days", 7),
            "start_date": start_date.strftime("%Y-%m-%d"),
            "series_counts": dict(series_counts),
            "remaining_unpublished": len(unpublished) - len(calendar)
        }
        
        return calendar, summary
    
    @staticmethod
    async def save_calendar_files() -> CalendarResponse:
        """Generate and save calendar files"""
        calendar, summary = await CalendarService.generate_calendar()
        
        # Prepare response
        calendar_entries = [
            CalendarEntry(**entry)
            for entry in calendar
        ]
        
        response = CalendarResponse(
            generated=datetime.now().isoformat(),
            summary=summary,
            schedule=calendar_entries
        )
        
        # Save JSON
        json_path = get_calendar_json_path()
        import json
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Generate and save markdown
        md_content = CalendarService._generate_markdown(calendar, summary)
        md_path = get_calendar_md_path()
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return response
    
    @staticmethod
    def _generate_markdown(calendar: List[Dict], summary: Dict[str, Any]) -> str:
        """Generate markdown calendar"""
        lines = []
        
        lines.append("# Publishing Calendar")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Stories Scheduled | {summary['total_scheduled']} |")
        lines.append(f"| Stories Per Week | {summary['stories_per_week']} |")
        lines.append(f"| Default Series Spacing | {summary['series_spacing_default']} days |")
        lines.append(f"| Remaining Unpublished | {summary['remaining_unpublished']} |")
        lines.append(f"| Start Date | {summary['start_date']} |")
        lines.append("")
        
        if summary["series_counts"]:
            lines.append("## Series Breakdown")
            lines.append("")
            lines.append("| Series | Scheduled Stories |")
            lines.append("|--------|-------------------|")
            for series, count in sorted(summary["series_counts"].items()):
                series_display = series if series else "Standalone"
                lines.append(f"| {series_display} | {count} |")
            lines.append("")
        
        lines.append("## Schedule")
        lines.append("")
        
        current_month = None
        for entry in calendar:
            date_obj = datetime.strptime(entry["date"], "%Y-%m-%d")
            month_key = date_obj.strftime("%B %Y")
            
            if month_key != current_month:
                current_month = month_key
                lines.append(f"### {month_key}")
                lines.append("")
                lines.append("| Date | Story | Series | Part | Read Time |")
                lines.append("|------|-------|--------|------|-----------|")
            
            part_display = f"Part {entry['part']}" if entry.get("part") else "—"
            series_display = entry["series"] if entry["series"] else "Standalone"
            lines.append(f"| {entry['date']} ({entry['weekday'][:3]}) | {entry['name']} | {series_display} | {part_display} | {entry['read_time']} min |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*This calendar is auto-generated.*")
        
        return "\n".join(lines)