// ============================================
// CALENDAR PAGE - Using utils.js for common functions
// ============================================

let allCalendar = [];
let currentSort = { column: 'date', direction: 'asc' };

// ============================================
// SORTING
// ============================================

function sortCalendar(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    const sorted = [...allCalendar].sort((a, b) => {
        if (column === 'date') {
            return currentSort.direction === 'asc' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
        }
        if (column === 'read_time') {
            const aVal = a.read_time || 0;
            const bVal = b.read_time || 0;
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        if (column === 'part') {
            const aVal = a.part || 999;
            const bVal = b.part || 999;
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        const aVal = String(a[column] || '').toLowerCase();
        const bVal = String(b[column] || '').toLowerCase();
        return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    renderCalendarTable(sorted);
    updateCalendarSortIcons(column, currentSort.direction);
}

function updateCalendarSortIcons(column, direction) {
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
// LOAD CALENDAR
// ============================================

async function loadCalendar() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/calendar/schedule`);
        const data = await res.json();
        
        allCalendar = data.schedule || [];
        
        // Update summary cards
        const scheduledCount = document.getElementById('scheduledCount');
        const storiesPerWeek = document.getElementById('storiesPerWeek');
        const seriesSpacing = document.getElementById('seriesSpacing');
        const remainingCount = document.getElementById('remainingCount');
        
        if (scheduledCount) scheduledCount.textContent = data.summary?.total_scheduled || 0;
        if (storiesPerWeek) storiesPerWeek.textContent = data.summary?.stories_per_week || 3;
        if (seriesSpacing) seriesSpacing.textContent = `${data.summary?.series_spacing_default || 7} days`;
        if (remainingCount) remainingCount.textContent = data.summary?.remaining_unpublished || 0;
        
        // Render series breakdown
        if (data.summary?.series_counts) {
            renderSeriesBreakdown(data.summary.series_counts);
        }
        
        // Render table
        renderCalendarTable(allCalendar);
        sortCalendar(currentSort.column);
        
    } catch (error) {
        console.error('Error loading calendar:', error);
        showToast('Error loading calendar: ' + error.message, 'error');
        const tbody = document.getElementById('calendarTableBody');
        if (tbody) {
            tbody.innerHTML = '';
            const row = tbody.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 6;
            cell.className = 'text-center text-danger';
            cell.textContent = 'Error loading calendar. Please refresh.';
        }
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

function filterBySeries(seriesName) {
    if (!seriesName) return;
    sessionStorage.setItem('storiesFilterSeries', seriesName);
    window.location.href = '/stories';
}

function renderCalendarTable(calendar) {
    const tbody = document.getElementById('calendarTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!calendar || calendar.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 6;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No scheduled stories. Click "Regenerate" to create a schedule.';
        return;
    }
    
    calendar.forEach(c => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        row.style.cursor = 'pointer';
        row.onclick = () => markPublished(c.story_key);
        
        // Date cell
        const dateCell = row.insertCell(0);
        const dateStrong = document.createElement('strong');
        dateStrong.textContent = c.date;
        dateCell.appendChild(dateStrong);
        const dateBreak = document.createElement('br');
        dateCell.appendChild(dateBreak);
        const weekdaySmall = document.createElement('small');
        weekdaySmall.className = 'text-muted';
        weekdaySmall.textContent = c.weekday;
        dateCell.appendChild(weekdaySmall);
        
        // Name cell
        const nameCell = row.insertCell(1);
        nameCell.textContent = c.name;
        
        // Series cell
        const seriesCell = row.insertCell(2);
        const seriesLink = document.createElement('a');
        seriesLink.href = '#';
        seriesLink.textContent = c.series || 'Standalone';
        seriesLink.style.textDecoration = 'none';
        seriesLink.onclick = (e) => {
            e.stopPropagation();
            filterBySeries(c.series);
        };
        seriesCell.appendChild(seriesLink);
        
        // Part cell
        const partCell = row.insertCell(3);
        partCell.textContent = c.part ? `Part ${c.part}` : '—';
        
        // Read Time cell
        const readTimeCell = row.insertCell(4);
        readTimeCell.textContent = c.read_time ? `${c.read_time} min` : '—';
        
        // Actions cell
        const actionsCell = row.insertCell(5);
        const publishBtn = document.createElement('button');
        publishBtn.className = 'btn btn-sm btn-success';
        publishBtn.innerHTML = '<i class="bi bi-check-lg"></i> Publish';
        publishBtn.onclick = (e) => {
            e.stopPropagation();
            markPublished(c.story_key);
        };
        actionsCell.appendChild(publishBtn);
    });
}

// ============================================
// CALENDAR ACTIONS - Using story_identifier
// ============================================

async function regenerateCalendar() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            await loadCalendar();
            showToast('Calendar regenerated successfully', 'success');
        } else {
            showToast('Error generating calendar: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error generating calendar: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function markPublished(storyKey) {
    if (!storyKey) return;
    if (!confirm('Mark this story as published?')) return;
    
    // Clean the story key
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) {
        cleanKey = cleanKey.slice(0, -3);
    }
    
    showLoading();
    try {
        // First, fetch the story to get its medium_url or name for identifier
        const allStoriesRes = await fetch(`${API_BASE}/stories/`);
        if (!allStoriesRes.ok) {
            throw new Error('Failed to fetch stories');
        }
        
        const allStories = await allStoriesRes.json();
        const story = allStories.find(s => s.key === cleanKey);
        
        if (!story) {
            throw new Error('Story not found');
        }
        
        // Get the story identifier using utils function
        const identifier = getStoryIdentifier(story);
        
        // Call the publish endpoint with the identifier
        const response = await fetch(`${API_BASE}/stories/story/${encodeStoryIdentifier(identifier)}/publish`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        if (response.ok) {
            await loadCalendar();
            showToast('Story marked as published', 'success');
        } else {
            const error = await response.json();
            showToast('Error marking as published: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error marking as published:', error);
        showToast('Error marking as published: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadCalendar();
});

// Make functions globally available
window.sortCalendar = sortCalendar;
window.regenerateCalendar = regenerateCalendar;
window.markPublished = markPublished;
window.filterBySeries = filterBySeries;