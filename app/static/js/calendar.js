// ============================================
// Calendar Functions
// ============================================

let calendarSortState = { column: 'date', direction: 'asc' };
let allCalendar = [];

function sortCalendar(column) {
    const direction = calendarSortState.column === column && calendarSortState.direction === 'asc' ? 'desc' : 'asc';
    calendarSortState = { column, direction };
    const sorted = [...allCalendar].sort((a, b) => {
        if (column === 'date') {
            return direction === 'asc' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
        }
        if (column === 'read_time') {
            const aVal = a.read_time || 0;
            const bVal = b.read_time || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        const aVal = String(a[column] || '').toLowerCase();
        const bVal = String(b[column] || '').toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderCalendarTable(sorted);
    updateSortIcons('calendar', column, direction);
}

async function loadCalendar() {
    const res = await fetch(`${API_BASE}/calendar/`);
    const calendar = await res.json();
    allCalendar = calendar.schedule || [];
    
    document.getElementById('content').innerHTML = `
        <div class="d-flex justify-content-between mb-3">
            <h1 class="h3">Publishing Calendar</h1>
            <button class="btn btn-sm btn-primary" onclick="generateCalendar()"><i class="bi bi-arrow-repeat"></i> Regenerate</button>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-3">
                <div class="card bg-info text-white p-2">
                    <small>Scheduled</small>
                    <h5>${calendar.summary?.total_scheduled || 0}</h5>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-white p-2">
                    <small>Stories/Week</small>
                    <h5>${calendar.summary?.stories_per_week || 3}</h5>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-secondary text-white p-2">
                    <small>Series Spacing</small>
                    <h5>${calendar.summary?.series_spacing_default || 7} days</h5>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark text-white p-2">
                    <small>Remaining</small>
                    <h5>${calendar.summary?.remaining_unpublished || 0}</h5>
                </div>
            </div>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="calendarTableHeader" class="table-light">
                    <tr>
                        <th class="sortable" data-sort="date" onclick="sortCalendar('date')" style="width: 120px;">Date <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="name" onclick="sortCalendar('name')">Story <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="series" onclick="sortCalendar('series')" style="width: 150px;">Series <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="part" onclick="sortCalendar('part')" style="width: 80px;">Part <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="read_time" onclick="sortCalendar('read_time')" style="width: 100px;">Read Time <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th style="width: 100px;">Actions</th>
                    </tr>
                </thead>
                <tbody id="calendarTableBody"></tbody>
            </table>
        </div>
    `;
    renderCalendarTable(allCalendar);
    sortCalendar(calendarSortState.column);
}

function renderCalendarTable(calendar) {
    const tbody = document.getElementById('calendarTableBody');
    if (!tbody) return;
    
    if (!calendar || calendar.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No scheduled stories</td></tr>';
        return;
    }
    
    let html = '';
    for (const c of calendar) {
        const dateStr = c.date || '';
        const weekdayStr = c.weekday || '';
        const nameStr = escapeHtml(c.name || '');
        const seriesStr = escapeHtml(c.series || 'Standalone');
        const partStr = c.part ? `Part ${c.part}` : '—';
        const readTimeStr = c.read_time ? `${c.read_time} min` : '—';
        const storyKey = (c.story_key || '').replace(/'/g, "\\'");
        
        html += `
            <tr class="table-row-clickable" onclick="markPublished('${storyKey}')">
                <td><strong>${dateStr}</strong><br><small>${weekdayStr}</small></td>
                <td>${nameStr}</td>
                <td>${seriesStr}</td>
                <td>${partStr}</td>
                <td>${readTimeStr}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="event.stopPropagation(); markPublished('${storyKey}')">Publish</button>
                </td>
            </tr>
        `;
    }
    tbody.innerHTML = html;
}

async function generateCalendar() {
    try {
        const res = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        if (res.ok) {
            await loadCalendar();
            alert('Calendar regenerated successfully');
        } else {
            const error = await res.json();
            alert('Failed to generate calendar: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        alert('Error generating calendar: ' + error.message);
    }
}

async function markPublished(storyKey) {
    if (!storyKey) return;
    
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) {
        cleanKey = cleanKey.slice(0, -3);
    }
    
    try {
        const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}/publish`, { method: 'POST' });
        if (res.ok) {
            await loadCalendar();
            if (typeof loadView === 'function') {
                await loadView(window.currentView);
            }
            alert('Story marked as published');
        } else {
            const error = await res.json();
            alert('Failed to mark as published: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function updateSortIcons(table, column, direction) {
    const headerId = table === 'stories' ? 'storiesTableHeader' : (table === 'series' ? 'seriesTableHeader' : 'calendarTableHeader');
    const header = document.getElementById(headerId);
    if (!header) return;
    
    const sortableHeaders = header.querySelectorAll('.sortable');
    for (const th of sortableHeaders) {
        th.classList.remove('active');
        const iconSpan = th.querySelector('.sort-icon');
        if (iconSpan) {
            iconSpan.textContent = '↕';
        }
    }
    
    const activeTh = header.querySelector(`.sortable[data-sort="${column}"]`);
    if (activeTh) {
        activeTh.classList.add('active');
        const iconSpan = activeTh.querySelector('.sort-icon');
        if (iconSpan) {
            iconSpan.textContent = direction === 'asc' ? '↑' : '↓';
        }
    }
}