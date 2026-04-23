// ============================================
// CALENDAR PAGE - Large Grid View + List View
// ============================================

let allCalendar = [];
let allStories = [];
let currentSort = { column: 'date', direction: 'desc' };
let currentView = 'grid';
let currentDate = new Date();
let currentMonth = currentDate.getMonth();
let currentYear = currentDate.getFullYear();
let allStoriesMap = new Map();
let currentContextStoryKey = null;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function getMonthDays(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year, month) {
    return new Date(year, month, 1).getDay();
}

function formatMonthYear(year, month) {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
    return `${monthNames[month]} ${year}`;
}

function isToday(year, month, day) {
    const today = new Date();
    return today.getFullYear() === year && 
           today.getMonth() === month && 
           today.getDate() === day;
}

// ============================================
// BUILD STORIES MAP - BY PUBLISH DUE DATE
// ============================================

function buildStoriesMapFromAllStories(stories) {
    const map = new Map();
    let publishedCount = 0;
    let publishedDueCount = 0;
    let draftCount = 0;
    let readyCount = 0;
    let doneCount = 0;
    console.log('Building stories map from', stories.length, 'stories');
    
    stories.forEach(story => {
        // Count by status for legend
        switch(story.status) {
            case 'Published': publishedCount++; break;
            case 'Published Due': publishedDueCount++; break;
            case 'Draft': draftCount++; break;
            case 'Ready': readyCount++; break;
            case 'Done': doneCount++; break;
            default: break;
        }
        
        // Get publish due date
        let dueDate = story.publishedDueDate;
        
        if (dueDate) {
            // Ensure date is in YYYY-MM-DD format
            if (dueDate.includes('T')) {
                dueDate = dueDate.split('T')[0];
            }
            
            if (!map.has(dueDate)) {
                map.set(dueDate, []);
            }
            
            // Determine display status
            let displayStatus = story.status;
            let statusClass = '';
            let statusIcon = '';
            
            if (story.status === 'Published') {
                statusClass = 'published';
                statusIcon = '✅ ';
            } else if (story.status === 'Published Due') {
                statusClass = 'scheduled';
                statusIcon = '⏰ ';
            } else if (story.status === 'Ready') {
                statusClass = 'ready';
                statusIcon = '🚀 ';
            } else if (story.status === 'Done') {
                statusClass = 'done';
                statusIcon = '✓ ';
            } else {
                statusClass = 'draft';
                statusIcon = '📝 ';
            }
            
            map.get(dueDate).push({
                story_key: story.key,
                name: story.name || story.title,
                series: story.series,
                status: displayStatus,
                statusClass: statusClass,
                statusIcon: statusIcon,
                date: dueDate,
                uniqueSlug: story.uniqueSlug
            });            
        }
        let publishDate = story.publishedDate;
        
        if (publishDate) {
            // Ensure date is in YYYY-MM-DD format
            if (publishDate.includes('T')) {
                publishDate = publishDate.split('T')[0];
            }
            
            if (!map.has(publishDate)) {
                map.set(publishDate, []);
            }
            
            // Determine display status
            let displayStatus = story.status;
            let statusClass = '';
            let statusIcon = '';
            
            if (story.status === 'Published') {
                statusClass = 'published';
                statusIcon = '✅ ';
            } else if (story.status === 'Published Due') {
                statusClass = 'scheduled';
                statusIcon = '⏰ ';
            } else if (story.status === 'Ready') {
                statusClass = 'ready';
                statusIcon = '🚀 ';
            } else if (story.status === 'Done') {
                statusClass = 'done';
                statusIcon = '✓ ';
            } else {
                statusClass = 'draft';
                statusIcon = '📝 ';
            }

            map.get(publishDate).push({
                story_key: story.key,
                name: story.name || story.title,
                series: story.series,
                status: displayStatus,
                statusClass: statusClass,
                statusIcon: statusIcon,
                date: publishDate,
                uniqueSlug: story.uniqueSlug
            });   
                     
        }
    });
    
    console.log(`Stats - Published: ${publishedCount}, Published Due: ${publishedDueCount}, Draft: ${draftCount}, Ready: ${readyCount}, Done: ${doneCount}`);
    console.log(`Dates with stories: ${map.size}`);
    
    // Update legend counts
    updateLegendCounts(publishedCount, publishedDueCount, draftCount, readyCount, doneCount);
    
    return map;
}

function updateLegendCounts(published, publishedDue, draft, ready, done) {
    const publishedEl = document.getElementById('legendPublishedCount');
    const publishedDueEl = document.getElementById('legendPublishedDueCount');
    const draftEl = document.getElementById('legendDraftCount');
    const readyEl = document.getElementById('legendReadyCount');
    const doneEl = document.getElementById('legendDoneCount');
    const totalEl = document.getElementById('legendTotalCount');
    
    if (publishedEl) publishedEl.textContent = published;
    if (publishedDueEl) publishedDueEl.textContent = publishedDue;
    if (draftEl) draftEl.textContent = draft;
    if (readyEl) readyEl.textContent = ready;
    if (doneEl) doneEl.textContent = done;
    if (totalEl) totalEl.textContent = published + publishedDue + draft + ready + done;
}

// ============================================
// LOAD ALL STORIES
// ============================================

async function loadAllStories() {
    try {
        const response = await fetch(`${API_BASE}/stories/list`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        
        if (data && data.stories) {
            allStories = data.stories;
            console.log('Loaded stories:', allStories.length);
            allStoriesMap = buildStoriesMapFromAllStories(allStories);
        }
    } catch (error) {
        console.error('Error loading stories:', error);
    }
}

// ============================================
// RENDER GRID CALENDAR
// ============================================

function renderGridView() {
    const calendarGrid = document.getElementById('calendarGrid');
    const weekdayHeader = document.getElementById('weekdayHeader');
    const currentMonthYear = document.getElementById('currentMonthYear');
    
    if (!calendarGrid) return;
    
    currentMonthYear.textContent = formatMonthYear(currentYear, currentMonth);
    
    const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    weekdayHeader.innerHTML = weekdays.map((day, index) => {
        const isWeekend = index === 0 || index === 6;
        return `<div class="weekday-cell ${isWeekend ? 'weekend' : ''}">${day.substring(0, 3)}</div>`;
    }).join('');
    
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
    const daysInMonth = getMonthDays(currentYear, currentMonth);
    const prevMonthDays = getMonthDays(currentYear, currentMonth - 1);
    
    let gridHTML = '';
    let dayCounter = 1;
    let nextMonthCounter = 1;
    
    for (let i = 0; i < 42; i++) {
        let year = currentYear;
        let month = currentMonth;
        let day;
        let isCurrentMonth = true;
        
        if (i < firstDay) {
            isCurrentMonth = false;
            day = prevMonthDays - (firstDay - i) + 1;
            month = currentMonth - 1;
            if (month < 0) {
                month = 11;
                year = currentYear - 1;
            }
        } else if (dayCounter > daysInMonth) {
            isCurrentMonth = false;
            day = nextMonthCounter++;
            month = currentMonth + 1;
            if (month > 11) {
                month = 0;
                year = currentYear + 1;
            }
        } else {
            day = dayCounter++;
        }
        
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const stories = allStoriesMap.get(dateStr) || [];
        const isTodayDate = isToday(year, month, day);
        
        gridHTML += `<div class="calendar-day ${!isCurrentMonth ? 'other-month' : ''} ${isTodayDate ? 'today' : ''}">`;
        gridHTML += `<div class="calendar-day-number">`;
        gridHTML += `<span class="day-number">${day}</span>`;
        if (stories.length > 0) {
            gridHTML += `<span class="story-count">${stories.length}</span>`;
        }
        gridHTML += `</div>`;
        
        if (stories.length > 0) {
            gridHTML += `<div class="stories-list">`;
            stories.forEach(story => {
                const encodedKey = encodeURIComponent(story.story_key);
                const encodedName = encodeURIComponent(story.name);
                
                gridHTML += `
                    <div class="story-card-mini ${story.statusClass}" 
                         onclick="event.stopPropagation(); showContextMenu(event, '${encodedKey}', '${escapeHtml(story.name)}')"
                         oncontextmenu="event.preventDefault(); showContextMenu(event, '${encodedKey}', '${escapeHtml(story.name)}')">
                        <div class="story-title" title="${escapeHtml(story.name)}">
                            ${story.statusIcon}${escapeHtml(story.name.length > 25 ? story.name.substring(0, 25) + '...' : story.name)}
                        </div>
                        <div class="story-meta">
                            ${story.series ? `<span class="story-badge">📁 ${escapeHtml(story.series.substring(0, 20))}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            gridHTML += `</div>`;
        } else {
            gridHTML += `<div class="empty-day">📝 No posts</div>`;
        }
        
        gridHTML += `</div>`;
    }
    
    calendarGrid.innerHTML = gridHTML;
}

// ============================================
// CONTEXT MENU
// ============================================

function showContextMenu(event, storyKey, storyName) {
    event.preventDefault();
    event.stopPropagation();
    
    currentContextStoryKey = storyKey;
    
    const existingMenu = document.getElementById('storyContextMenu');
    if (existingMenu) existingMenu.remove();
    
    const menu = document.createElement('div');
    menu.id = 'storyContextMenu';
    menu.className = 'context-menu';
    menu.style.position = 'fixed';
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;
    menu.style.backgroundColor = 'white';
    menu.style.border = '1px solid #dee2e6';
    menu.style.borderRadius = '8px';
    menu.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    menu.style.zIndex = '10000';
    menu.style.minWidth = '180px';
    menu.style.overflow = 'hidden';
    
    menu.innerHTML = `
        <div style="padding: 8px 12px; background: #f8f9fa; border-bottom: 1px solid #dee2e6; font-weight: 600; font-size: 0.8rem;">
            ${escapeHtml(storyName)}
        </div>
        <div class="context-menu-item" onclick="openStoryPreview('${storyKey}')" style="padding: 8px 12px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-eye"></i> Preview Story
        </div>
        <div class="context-menu-item" onclick="openStoryEdit('${storyName}')" style="padding: 8px 12px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-pencil-square"></i> Edit Story
        </div>
        <div class="context-menu-divider" style="height: 1px; background: #dee2e6; margin: 4px 0;"></div>
        <div class="context-menu-item" onclick="clearPublishDueDate('${storyKey}')" style="padding: 8px 12px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 8px; color: #dc3545;">
            <i class="bi bi-calendar-x"></i> Remove Publish Due Date
        </div>
        <div class="context-menu-divider" style="height: 1px; background: #dee2e6; margin: 4px 0;"></div>
        <div class="context-menu-item" onclick="copyStoryLink('${storyKey}')" style="padding: 8px 12px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-link-45deg"></i> Copy Link
        </div>
        <div class="context-menu-item" onclick="closeContextMenu()" style="padding: 8px 12px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 8px; color: #6c757d;">
            <i class="bi bi-x-lg"></i> Cancel
        </div>
    `;
    
    document.body.appendChild(menu);
    
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (menu && !menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 0);
}

function closeContextMenu() {
    const menu = document.getElementById('storyContextMenu');
    if (menu) menu.remove();
}

function openStoryPreview(storyKey) {
    closeContextMenu();
    window.open(`/story-preview/${storyKey}`, '_blank', 'width=1200,height=800');
}

// function openStoryEdit(storyKey) {
//     closeContextMenu();
//     console.log("Story Key : "+ storyKey)
//     const decodedKey = decodeURIComponent(storyKey);
//     if (typeof window.openEditStory === 'function') {
//         window.openEditStory(decodedKey);
//     } else {
//         console.error('openEditStory not available');
//         alert('Edit functionality not available. Please refresh.');
//     }
// }

function openStoryEdit(storyKey) {
    closeContextMenu();
    console.log("Story Key: " + storyKey);
    
    // Decode the story key if it's encoded
    let cleanKey = storyKey;
    if (typeof cleanKey === 'string') {
        try {
            cleanKey = decodeURIComponent(cleanKey);
        } catch (e) {
            // Already decoded or not encoded
            cleanKey = storyKey;
        }
    }
    
    // Remove .md extension if present
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) {
        cleanKey = cleanKey.slice(0, -3);
    }
    
    // Use the EditStoryModal global object
    if (window.EditStoryModal && typeof window.EditStoryModal.open === 'function') {
        window.EditStoryModal.open(encodeURIComponent(cleanKey));
    } else {
        console.error('EditStoryModal not available. Make sure edit-story.js is loaded.');
        alert('Edit functionality not available. Please refresh the page.');
    }
}


async function clearPublishDueDate(storyKey) {
    closeContextMenu();
    if (!confirm('Remove publish due date from this story?\n\nThis will NOT change the story status.')) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/clear-due-date/${storyKey}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Publish due date removed', 'success');
            await loadCalendar();
        } else {
            const error = await response.json();
            showToast('Error: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function copyStoryLink(storyKey) {
    closeContextMenu();
    const url = `${window.location.origin}/story-preview/${storyKey}`;
    navigator.clipboard.writeText(url).then(() => {
        showToast('Link copied to clipboard!', 'success');
    }).catch(() => {
        alert('Failed to copy link');
    });
}

// ============================================
// SORTING FOR LIST VIEW
// ============================================

function sortStoriesList(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    const storiesWithDueDates = allStories.filter(s => {
        return s.publishedDueDate || s.published_due_date;
    });
    
    const sorted = [...storiesWithDueDates].sort((a, b) => {
        let aVal, bVal;
        
        const getDate = (story) => {
            return story.publishedDueDate || story.published_due_date || '';
        };
        
        switch(column) {
            case 'date':
                aVal = getDate(a);
                bVal = getDate(b);
                break;
            case 'name':
                aVal = (a.name || a.title || '').toLowerCase();
                bVal = (b.name || b.title || '').toLowerCase();
                return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            case 'series':
                aVal = (a.series || '').toLowerCase();
                bVal = (b.series || '').toLowerCase();
                return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            case 'status':
                aVal = a.status || '';
                bVal = b.status || '';
                break;
            default:
                aVal = a[column] || '';
                bVal = b[column] || '';
        }
        
        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
        return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    renderListView(sorted);
    updateListSortIcons(column, currentSort.direction);
}

function updateListSortIcons(column, direction) {
    const headers = document.querySelectorAll('#calendarTableHeader .sortable');
    headers.forEach(header => {
        header.classList.remove('active');
        const icon = header.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    });
    const activeHeader = document.querySelector(`#calendarTableHeader .sortable[data-sort="${column}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active');
        const icon = activeHeader.querySelector('i');
        if (icon) icon.className = direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
}

// ============================================
// RENDER LIST VIEW
// ============================================

function renderListView(stories) {
    const tbody = document.getElementById('calendarTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!stories || stories.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 7;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No stories with publish due dates found.';
        return;
    }
    
    stories.forEach(story => {
        const row = tbody.insertRow();
        
        const dueDate = story.publishedDueDate || story.publishedDate || '-';
        
        const dateCell = row.insertCell(0);
        dateCell.innerHTML = `<strong>${dueDate}</strong>`;
        
        const nameCell = row.insertCell(1);
        nameCell.textContent = story.name || story.title;
        
        const seriesCell = row.insertCell(2);
        seriesCell.textContent = story.series || 'Standalone';
        
        const statusCell = row.insertCell(3);
        const statusClass = story.status === 'Published' ? 'status-published' : 
                           story.status === 'Published Due' ? 'status-published-due' :
                           story.status === 'Ready' ? 'status-ready' :
                           story.status === 'Done' ? 'status-done' : 'status-draft';
        statusCell.innerHTML = `<span class="status-badge ${statusClass}">${story.status || 'Draft'}</span>`;
        
        const readsCell = row.insertCell(4);
        readsCell.textContent = story.reads || 0;
        
        const readTimeCell = row.insertCell(5);
        const readTime = story.reading_time || story.read_time || story.medium_reading_time || 0;
        readTimeCell.textContent = readTime ? `${readTime} min` : '—';
        
        const actionsCell = row.insertCell(6);
        const encodedKey = encodeURIComponent(story.key);
        const encodedName = encodeURIComponent(story.name);
        
        actionsCell.innerHTML = `
            <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); openStoryPreview('${encodedKey}')" title="Preview">
                <i class="bi bi-eye"></i> Preview
            </button>
            <button class="btn btn-sm btn-outline-primary ms-1" onclick="event.stopPropagation(); openStoryEdit('${encodedName}')" title="Edit">
                <i class="bi bi-pencil-square"></i> Edit
            </button>
        `;
    });
}

// ============================================
// SCHEDULE DRAFTS
// ============================================

async function scheduleDrafts() {
    if (!confirm('Schedule draft stories?\n\nThis will:\n- Keep existing due dates\n- Fill empty slots (max 2 per day)\n- Respect series spacing (7 days)\n- Start from tomorrow')) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/schedule-drafts`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            await loadCalendar();
            showToast(`${data.message}: ${data.scheduled} scheduled, ${data.remaining_drafts} remaining`, 'success');
        } else {
            showToast('Error: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// LOAD CALENDAR DATA
// ============================================

async function loadCalendar() {
    showLoading();
    try {
        await loadAllStories();
        
        const res = await fetch(`${API_BASE}/calendar/schedule`);
        const data = await res.json();
        
        allCalendar = data.schedule || [];
        
        const scheduledCount = document.getElementById('scheduledCount');
        const storiesPerWeek = document.getElementById('storiesPerWeek');
        const seriesSpacing = document.getElementById('seriesSpacing');
        const remainingCount = document.getElementById('remainingCount');
        
        if (scheduledCount) scheduledCount.textContent = data.summary?.total_scheduled || 0;
        if (storiesPerWeek) storiesPerWeek.textContent = data.summary?.stories_per_week || 3;
        if (seriesSpacing) seriesSpacing.textContent = `${data.summary?.series_spacing_default || 7} days`;
        if (remainingCount) remainingCount.textContent = data.summary?.remaining_unpublished || 0;
        
        if (data.summary?.series_counts) {
            renderSeriesBreakdown(data.summary.series_counts);
        }
        
        if (currentView === 'grid') {
            renderGridView();
        } else {
            const storiesWithDueDates = allStories.filter(s => s.publishedDueDate || s.publishedDate);
            renderListView(storiesWithDueDates);
        }
        
    } catch (error) {
        console.error('Error loading calendar:', error);
        showToast('Error loading calendar: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderSeriesBreakdown(seriesCounts) {
    const container = document.getElementById('seriesBreakdown');
    if (!container) return;
    
    container.innerHTML = '';
    const entries = Object.entries(seriesCounts);
    
    if (entries.length === 0) {
        container.innerHTML = '<div class="text-muted small">No series scheduled</div>';
        return;
    }
    
    entries.forEach(([series, count]) => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-secondary me-1 mb-1 p-2';
        badge.style.cursor = 'pointer';
        badge.innerHTML = `${escapeHtml(series || 'Standalone')}: ${count}`;
        badge.onclick = () => filterBySeries(series);
        container.appendChild(badge);
    });
}

// ============================================
// NAVIGATION FUNCTIONS
// ============================================

function previousMonth() {
    currentMonth--;
    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    renderGridView();
}

function nextMonth() {
    currentMonth++;
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }
    renderGridView();
}

function toggleCalendarView() {
    const gridView = document.getElementById('calendarGridView');
    const listView = document.getElementById('calendarListView');
    const toggleText = document.getElementById('viewToggleText');
    
    if (currentView === 'grid') {
        gridView.style.display = 'none';
        listView.style.display = 'block';
        currentView = 'list';
        toggleText.textContent = 'Switch to Grid';
        const storiesWithDueDates = allStories.filter(s => s.publishedDueDate || s.published_due_date);
        renderListView(storiesWithDueDates);
    } else {
        gridView.style.display = 'block';
        listView.style.display = 'none';
        currentView = 'grid';
        toggleText.textContent = 'Switch to List';
        renderGridView();
    }
}

function filterBySeries(seriesName) {
    if (!seriesName) return;
    sessionStorage.setItem('storiesFilterSeries', seriesName);
    window.location.href = '/stories';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type) {
    console.log(`[${type.toUpperCase()}] ${message}`);
    if (type === 'error') {
        alert(message);
    }
}

function showLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'none';
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadCalendar();
});

// Make functions globally available
window.sortStoriesList = sortStoriesList;
window.scheduleDrafts = scheduleDrafts;
window.filterBySeries = filterBySeries;
window.previousMonth = previousMonth;
window.nextMonth = nextMonth;
window.toggleCalendarView = toggleCalendarView;
window.showContextMenu = showContextMenu;
window.closeContextMenu = closeContextMenu;
window.openStoryPreview = openStoryPreview;
window.openStoryEdit = openStoryEdit;
window.clearPublishDueDate = clearPublishDueDate;
window.copyStoryLink = copyStoryLink;