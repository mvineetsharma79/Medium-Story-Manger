// ============================================
// Calendar Functions
// ============================================

let calendarSortState = { column: 'date', direction: 'asc' };
let allCalendar = [];

function sortCalendar(column) {
    const direction = calendarSortState.column === column && calendarSortState.direction === 'asc' ? 'desc' : 'asc';
    calendarSortState = { column, direction };
    const sorted = [...allCalendar].sort((a, b) => {
        if (column === 'date') return direction === 'asc' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
        if (column === 'read_time') return direction === 'asc' ? (a.read_time||0) - (b.read_time||0) : (b.read_time||0) - (a.read_time||0);
        return direction === 'asc' ? String(a[column]||'').localeCompare(String(b[column]||'')) : String(b[column]||'').localeCompare(String(a[column]||''));
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
            <div class="col-md-3"><div class="card bg-info text-white p-2"><small>Scheduled</small><h5>${calendar.summary?.total_scheduled||0}</h5></div></div>
            <div class="col-md-3"><div class="card bg-warning text-white p-2"><small>Stories/Week</small><h5>${calendar.summary?.stories_per_week||3}</h5></div></div>
            <div class="col-md-3"><div class="card bg-secondary text-white p-2"><small>Series Spacing</small><h5>${calendar.summary?.series_spacing_default||7} days</h5></div></div>
            <div class="col-md-3"><div class="card bg-dark text-white p-2"><small>Remaining</small><h5>${calendar.summary?.remaining_unpublished||0}</h5></div></div>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="calendarTableHeader" class="table-light">
                    <tr>
                        <th class="sortable" data-sort="date" onclick="sortCalendar('date')">Date <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="name" onclick="sortCalendar('name')">Story <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="series" onclick="sortCalendar('series')">Series <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="part" onclick="sortCalendar('part')">Part <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="read_time" onclick="sortCalendar('read_time')">Read Time <i class="bi bi-arrow-down-up"></i></th>
                        <th>Actions</th>
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
    tbody.innerHTML = calendar.map(c => `
        <tr>
            <td><strong>${c.date}</strong><br><small>${c.weekday}</small></td>
            <td>${escapeHtml(c.name)}</td
            <td>${c.series || 'Standalone'}</td
            <td>${c.part ? `Part ${c.part}` : '—'}</td
            <td>${c.read_time} min</td
            <td><button class="btn btn-sm btn-success" onclick="markPublished('${c.story_key.replace(/'/g,"\\'")}')">Publish</button></td
         </tr
    `).join('') || '<tr><td colspan="6" class="text-center">No scheduled stories</tr';
}

async function generateCalendar() {
    await fetch(`${API_BASE}/calendar/generate`, { method:'POST' });
    await loadView('calendar');
}

async function markPublished(storyKey) {
    await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey.replace('.md',''))}/publish`, { method:'POST' });
    await loadView(window.currentView);
}