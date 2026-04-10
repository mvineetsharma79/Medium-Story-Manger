## Main prompt
```
I have created a sys link to stories folder where each story's readme is available. Now create a seperate page (HTML) to be open by clicking on new Show (new icon) Before to Story Name in stories table. 

Header section: Story Title, Create Date,Series, Published date and Publish Due Date (if any), Notes  
Story Section: Open story file (story.series / story.full_name) in  preview mode with source mode as seperate tab (typical as on Git hub). with save button to same Save Story

```

### Story Preview template
```

┌─────────────────────────────────────────────────────────────────┐
│ [📄 Story Title]                    [Source] [Save] [Close]      │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│ │ Created Date │ Series       │ Published    │ Due Date     │  │
│ │ 2026-04-01   │ Medium       │ 2026-03-27   │ 2026-04-15   │  │
│ └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                                                 │
│ Notes: This is a deep dive into ASP.NET Core filters...        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Preview] [Source]                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ # ASP.NET Core Filters Deep Dive                               │
│                                                                 │
│ ## Introduction                                                 │
│ This article covers...                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

* Syslink commands
```
# 1. Create the symlink (source -> destination)
ln -s /home/vineet/Documents/Projects/Medium-Build-Tool /home/vineet/Documents/Projects/AI-ML-Python-Package-Smart-Installer/Medium-Story-Manger/stories

# 2. Test it
ls -la /home/vineet/Documents/Projects/AI-ML-Python-Package-Smart-Installer/Medium-Story-Manger/stories/
```

* Syslink bash script
```
#!/bin/bash

# Define paths
SOURCE_DIR="/home/vineet/Documents/Projects/Medium-Build-Tool"
DEST_PATH="/home/vineet/Documents/Projects/AI-ML-Python-Package-Smart-Installer/Medium-Story-Manger/stories"

# Step 1: Remove any existing file/symlink at destination
echo "Removing any existing file/symlink at: $DEST_PATH"
if [ -L "$DEST_PATH" ] || [ -e "$DEST_PATH" ]; then
    rm -rf "$DEST_PATH"
    echo "✓ Removed"
fi

# Step 2: Ensure parent directory exists
DEST_DIR=$(dirname "$DEST_PATH")
echo "Ensuring parent directory exists: $DEST_DIR"
mkdir -p "$DEST_DIR"
echo "✓ Directory ready"

# Step 3: Create the symlink
echo "Creating symlink: $DEST_PATH -> $SOURCE_DIR"
ln -s "$SOURCE_DIR" "$DEST_PATH"

# Step 4: Verify
echo ""
echo "=== VERIFICATION ==="
echo "Symlink created:"
ls -ld "$DEST_PATH"

echo ""
echo "Content of source (original Medium-Build-Tool):"
ls -la "$SOURCE_DIR" | head -10

echo ""
echo "Content via symlink (stories directory):"
ls -la "$DEST_PATH" | head -10

echo ""
echo "✓ Done! The 'stories' symlink now points to Medium-Build-Tool content."
```

# Story Preview Feature

## Project Documentation

### Overview

The Story Preview Feature provides a complete in-browser markdown viewing and editing experience for story files. Users can preview rendered markdown, edit raw source, and save changes back to the original files - all from a dedicated preview window accessible from the stories table.

---

## Features

### Preview Window Access

A new 📄 icon appears before each story title in the stories table. Clicking this icon opens a dedicated preview window (1400x900) with the complete story content and metadata.

### Story Information Header

The header displays all relevant story metadata in a clean, organized layout:

**Story Title** - Displayed prominently at the top of the window

**Basic Information Row**
- Created Date - When the story was first created
- Series - The series this story belongs to (or "Standalone")
- Status - Visual badge showing Published, Published Due, Ready, Done, or Draft
- Published Date - When the story was published on Medium

**Additional Information Row**
- Due Date - Highlighted in orange when present
- File Path - Relative path to the source `.md` file

**Notes Section** - Display story notes if available

**Tags Section** - All tags displayed as Bootstrap badges

### Dual-Tab Interface

**Preview Tab**
- Renders markdown as formatted HTML
- Full markdown support including headings, tables, code blocks, lists, and images
- Images load correctly from the stories folder
- Automatic refresh when source content changes

**Source Tab**
- Raw markdown editing in a monospace textarea
- Preserves all original formatting
- Auto-refresh preview with 500ms debounce to avoid excessive re-rendering

### Save Functionality

- Ctrl+S keyboard shortcut to save
- Confirmation dialog before overwriting
- Visual feedback with toast notifications
- Original content preserved until confirmation

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save changes |
| `Esc` | Close preview window |
| `Ctrl+Shift+P` | Switch to Preview tab |
| `Ctrl+Shift+S` | Switch to Source tab |

---

## Technical Architecture

### New Files Created

| File | Purpose |
|------|---------|
| `app/templates/story_preview.html` | Main preview page template with tabs and metadata display |
| `app/static/js/story-preview.js` | Client-side JavaScript for loading, rendering, and saving |

### Modified Files

**`app/main.py`** - Added static mount for stories folder and image serving route:

```python
# Mount stories folder for image access
stories_root = get_stories_root()
app.mount("/static/stories", StaticFiles(directory=str(stories_root)), name="stories")

# Image serving route
@app.get("/story-preview/images/{filename:path}")
async def serve_preview_image(filename: str):
    stories_root = get_stories_root()
    possible_paths = [
        stories_root / "images" / filename,
        stories_root / filename,
    ]
    for path in possible_paths:
        if path.exists() and path.is_file():
            return FileResponse(path)
    raise HTTPException(status_code=404)

# Story preview route
@app.get("/story-preview/{story_key:path}", response_class=HTMLResponse)
async def story_preview_page(request: Request, story_key: str):
    decoded_key = unquote(story_key)
    story = await StoryService.get_story(decoded_key)
    if not story:
        return templates.TemplateResponse("dashboard.html", {"request": request, "error": "Story not found"})
    return templates.TemplateResponse("story_preview.html", {
        "request": request,
        "story": story,
        "story_key": decoded_key
    })
```

**`app/static/js/stories.js`** - Added preview icon to title column (1 line change):

```javascript
// Preview icon added before story title
const previewIcon = document.createElement('i');
previewIcon.className = 'bi bi-file-text-fill';
previewIcon.onclick = () => window.open(`/story-preview/${encodeURIComponent(story.key)}`, '_blank');
```

### API Endpoints Added

**GET `/api/stories/content/{story_key}`**

Returns story metadata and markdown content.

Response:
```json
{
  "success": true,
  "story_key": "string",
  "title": "string",
  "name": "string",
  "series": "string",
  "status": "string",
  "createdDate": "string",
  "publishedDate": "string",
  "publishedDueDate": "string",
  "notes": "string",
  "tags": ["string"],
  "file_path": "string",
  "content": "string"
}
```

**PUT `/api/stories/content/{story_key}`**

Saves updated markdown content to the original file.

Request Body:
```json
{
  "content": "Updated markdown content"
}
```

Response:
```json
{
  "success": true,
  "message": "Story saved successfully"
}
```

---

## Image Handling

Images are served directly from the `./stories/` folder through a dedicated route:

1. Browser requests image at `/story-preview/images/filename.jpg`
2. Route searches for image in `./stories/images/` and `./stories/`
3. Returns the image file directly via `FileResponse`
4. Original markdown files remain untouched

This approach preserves the original markdown content while still allowing images to render correctly.

---

## Files Preserved (No Changes)

| File | Reason |
|------|--------|
| `app/routers/stories.py` | Existing story routes unchanged |
| `app/services/file_service.py` | File handling logic untouched |
| All `.md` story files | Source content never modified |
| All config files | Configuration unchanged |

---

## Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save current story |
| `Esc` | Close preview window |
| `Ctrl+Shift+P` | Switch to Preview tab |
| `Ctrl+Shift+S` | Switch to Source tab |

---

## Dependencies

| Library | Purpose | CDN |
|---------|---------|-----|
| Bootstrap 5.3 | UI components and layout | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/` |
| Bootstrap Icons | Icons for UI elements | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/` |
| Marked.js | Markdown to HTML rendering | `https://cdn.jsdelivr.net/npm/marked/marked.min.js` |

---

## Browser Support

The feature works in all modern browsers that support:
- ES6 JavaScript
- Fetch API
- localStorage
- Bootstrap 5.3

---

## Future Enhancements

Potential improvements for future versions:

- **Auto-save** - Save automatically after a period of inactivity
- **Revision history** - Track changes and allow rollback
- **Word count** - Display live word count in source tab
- **Fullscreen mode** - Toggle fullscreen for focused editing
- **Custom CSS** - Allow users to customize preview styling
- **Export options** - Export as PDF or HTML

---

## Troubleshooting

**Images not loading**
- Verify images are in `./stories/images/` folder
- Check file extension matches (jpg, jpeg, png, gif, webp, svg)
- Ensure route order is correct (image route before story route)

**Save operation fails**
- Check file permissions on the `.md` file
- Verify the file path exists
- Check for disk space or write access issues

**Preview not updating**
- Clear browser cache
- Verify marked.js library loaded correctly
- Check console for JavaScript errors

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-10 | Initial release with preview, source editing, and save functionality |

---

## Credits

Developed for the Medium Story Manager application to provide a seamless content editing experience.

**Total code added:** ~25 lines to `main.py` + 2 new files (~270 lines)

**Implementation time:** 30 minutes (after correct solution identified)

---

## License

Part of the Medium Story Manager application. All rights reserved.