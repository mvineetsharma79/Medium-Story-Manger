// ============================================
// Helper Functions
// ============================================
function getTodayDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function getNowTimestamp() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T${hh}:${min}:${ss}`;
}

function formatTimestampForDisplay(timestamp) {
    if (!timestamp) return '';
    return timestamp.replace('T', ' ').substring(0, 19);
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

window.setTodayDate = function(elementId) {
    document.getElementById(elementId).value = getTodayDate();
};

window.clearDate = function(elementId) {
    document.getElementById(elementId).value = '';
};

function formatDateForDisplay(dateStr) {
    if (!dateStr || dateStr === 'Unknown') return '';
    if (dateStr.includes('-')) return dateStr.split('T')[0];
    return '';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// LinkedIn Functions
// ============================================
function setNowLinkedinTimestamp() {
    document.getElementById('editStoryLinkedinTimestamp').value = getNowTimestamp();
    updateLinkedinDisplay();
}

function clearLinkedinTimestamp() {
    document.getElementById('editStoryLinkedinTimestamp').value = '';
    updateLinkedinDisplay();
}

function clearAllLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;

    const storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) {
        alert('No story selected');
        return;
    }

    document.getElementById('editStoryLinkedinStatus').value = '';
    document.getElementById('editStoryLinkedinTimestamp').value = '';
    document.getElementById('editStoryLinkedinImpressions').value = '0';
    document.getElementById('editStoryLinkedinUrl').value = '';
    updateLinkedinDisplay();

    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const encodedKey = encodeURIComponent(cleanKey);

    const data = {
        status: document.getElementById('editStoryStatus').value,
        read_time: document.getElementById('editStoryReadTime').value ? parseInt(document.getElementById('editStoryReadTime').value) : null,
        reads: parseInt(document.getElementById('editStoryReads').value) || 0,
        tags: document.getElementById('editStoryTags').value.split(',').map(t => t.trim()).filter(t => t),
        medium_url: document.getElementById('editStoryMediumUrl').value || null,
        notes: document.getElementById('editStoryNotes').value,
        created_date: document.getElementById('editStoryCreatedDate').value || null,
        published_date: document.getElementById('editStoryPublishedDate').value || null,
        linkedin_status: null,
        linkedin_timestamp: null,
        linkedin_impressions: 0,
        linkedin_url: null
    };

    fetch(`${API_BASE}/stories/${encodedKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(response => {
        const btn = document.getElementById('clearAllLinkedinBtn');
        if (response.ok) {
            if (btn) {
                const original = btn.innerHTML;
                btn.innerHTML = '<i class="bi bi-check"></i> Cleared!';
                setTimeout(() => { btn.innerHTML = original; }, 1500);
            }
            saveFilterState();
            loadView(currentView).then(() => restoreFilterState());
        } else {
            btn.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Failed!';
            setTimeout(() => { btn.innerHTML = 'Clear All LinkedIn Data'; }, 1500);
        }
    });
}

function onLinkedinStatusChange() {
    const status = document.getElementById('editStoryLinkedinStatus').value;
    if (status === 'scheduled' || status === 'posted') {
        const ts = document.getElementById('editStoryLinkedinTimestamp').value;
        if (!ts) document.getElementById('editStoryLinkedinTimestamp').value = getNowTimestamp();
    } else if (status === '') {
        document.getElementById('editStoryLinkedinTimestamp').value = '';
    }
    updateLinkedinDisplay();
}

function updateLinkedinDisplay() {
    const status = document.getElementById('editStoryLinkedinStatus')?.value || '';
    const timestamp = document.getElementById('editStoryLinkedinTimestamp')?.value || '';
    const impressions = document.getElementById('editStoryLinkedinImpressions')?.value || '0';
    const display = document.getElementById('editStoryLinkedinDisplay');
    if (!display) return;

    if (status === 'scheduled') {
        display.innerHTML = `<i class="bi bi-calendar"></i> <strong>LinkedIn:</strong> Scheduled for ${timestamp ? formatTimestampForDisplay(timestamp) : 'No date'} | Impressions: ${impressions}`;
    } else if (status === 'posted') {
        display.innerHTML = `<i class="bi bi-linkedin"></i> <strong>LinkedIn:</strong> Posted on ${timestamp ? formatTimestampForDisplay(timestamp) : 'No date'} | Impressions: ${impressions}`;
    } else {
        display.innerHTML = '<i class="bi bi-linkedin"></i> <strong>LinkedIn:</strong> Not posted';
    }
}

// ============================================
// Bookmark Functions
// ============================================
async function toggleBookmark(storyKey, event) {
    event.stopPropagation();
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const story = allStories.find(s => s.key === cleanKey);
    if (!story) return;
    const newBookmarkState = !story.bookmarked;
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bookmarked: newBookmarkState })
    });
    if (res.ok) {
        story.bookmarked = newBookmarkState;
        renderStoryTable(allStories);
    } else {
        alert('Failed to update bookmark');
    }
}

// ============================================
// Filter State
// ============================================
let filterState = { status: 'All', series: '', search: '', bookmarked: false };

function saveFilterState() {
    filterState.status = document.getElementById('statusFilter')?.value || 'All';
    filterState.series = document.getElementById('seriesFilter')?.value || '';
    filterState.search = document.getElementById('searchFilter')?.value || '';
    filterState.bookmarked = document.getElementById('bookmarkFilter')?.checked || false;
}

function restoreFilterState() {
    if (document.getElementById('statusFilter')) document.getElementById('statusFilter').value = filterState.status;
    if (document.getElementById('seriesFilter')) document.getElementById('seriesFilter').value = filterState.series;
    if (document.getElementById('searchFilter')) document.getElementById('searchFilter').value = filterState.search;
    if (document.getElementById('bookmarkFilter')) document.getElementById('bookmarkFilter').checked = filterState.bookmarked;
    filterStories();
}

// ============================================
// Sorting Functions
// ============================================
let sortState = {
    stories: { column: 'reads', direction: 'desc' },
    series: { column: 'name', direction: 'asc' },
    calendar: { column: 'date', direction: 'asc' }
};
let allCalendar = [];

function sortStories(column) {
    const direction = sortState.stories.column === column && sortState.stories.direction === 'asc' ? 'desc' : 'asc';
    sortState.stories = { column, direction };
    const sorted = [...allStories].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'reads' || column === 'claps' || column === 'linkedin_impressions' || column === 'medium_total_views') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        if (column === 'created_date' || column === 'published_date') {
            aVal = aVal || '';
            bVal = bVal || '';
            return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        if (column === 'bookmarked') {
            aVal = aVal ? 1 : 0;
            bVal = bVal ? 1 : 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderStoryTable(sorted);
    updateSortIcons('stories', column, direction);
}

function sortSeries(column) {
    const direction = sortState.series.column === column && sortState.series.direction === 'asc' ? 'desc' : 'asc';
    sortState.series = { column, direction };
    const sorted = [...allSeries].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'total_stories' || column === 'published') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderSeriesTable(sorted);
    updateSortIcons('series', column, direction);
}

function sortCalendar(column) {
    const direction = sortState.calendar.column === column && sortState.calendar.direction === 'asc' ? 'desc' : 'asc';
    sortState.calendar = { column, direction };
    const sorted = [...allCalendar].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'date') return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        if (column === 'read_time') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderCalendarTable(sorted);
    updateSortIcons('calendar', column, direction);
}

function updateSortIcons(table, column, direction) {
    const headerId = table === 'stories' ? 'storiesTableHeader' : (table === 'series' ? 'seriesTableHeader' : 'calendarTableHeader');
    const header = document.getElementById(headerId);
    if (!header) return;
    header.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('active');
        const icon = th.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    });
    const activeTh = header.querySelector(`.sortable[data-sort="${column}"]`);
    if (activeTh) {
        activeTh.classList.add('active');
        const icon = activeTh.querySelector('i');
        if (icon) icon.className = direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
}

// ============================================
// API & Variables
// ============================================
const API_BASE = '/api';
let currentView = 'dashboard';
let allStories = [];
let allSeries = [];
let currentStatsStoryKey = null;

// Dashboard HTML template
function getDashboardHTML(stories, calendar) {
    const published = stories.filter(s => s.status === 'Published').length;
    const draft = stories.filter(s => s.status === 'Draft').length;
    const done = stories.filter(s => s.status === 'Done').length;
    const ready = stories.filter(s => s.status === 'Ready').length;
    const bookmarked = stories.filter(s => s.bookmarked === true).length;
    const totalLinkedin = stories.filter(s => s.linkedin_status === 'posted').length;
    const totalImpressions = stories.reduce((sum, s) => sum + (s.linkedin_impressions || 0), 0);
    const totalReads = stories.reduce((sum, s) => sum + (s.reads || 0), 0);
    const totalClaps = stories.reduce((sum, s) => sum + (s.claps || 0), 0);
    const totalViews = stories.reduce((sum, s) => sum + (s.medium_total_views || 0), 0);

    return `
        <h1 class="h3 mb-4">Dashboard</h1>
        <div class="row g-2 mb-4">
            <div class="col-md-2"><div class="card stat-card bg-primary text-white" onclick="filterStoriesByStatus('all')"><div class="card-body"><h6>Total</h6><h2>${stories.length}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-success text-white" onclick="filterStoriesByStatus('Published')"><div class="card-body"><h6>Published</h6><h2>${published}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-info text-white" onclick="filterStoriesByStatus('Ready')"><div class="card-body"><h6>Ready</h6><h2>${ready}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-secondary text-white" onclick="filterStoriesByStatus('Done')"><div class="card-body"><h6>Done</h6><h2>${done}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card" style="background:#ffc107;color:#000;" onclick="filterStoriesByBookmarked()"><div class="card-body"><h6>Bookmarked</h6><h2>${bookmarked}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-dark text-white"><div class="card-body"><h6>Impressions</h6><h2>${formatNumber(totalImpressions)}</h2></div></div></div>
        </div>
        <div class="row g-1 mb-4">
            <div class="col-md-3"><div class="card mini-stat-card bg-info text-white"><div class="card-body"><h6 class="mb-0">Total Reads</h6><h2 class="mb-0">${formatNumber(totalReads)}</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-warning text-white"><div class="card-body"><h6 class="mb-0">Total Claps</h6><h2 class="mb-0">${formatNumber(totalClaps)}</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-primary text-white"><div class="card-body"><h6 class="mb-0">Total Views</h6><h2 class="mb-0">${formatNumber(totalViews)}</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-success text-white"><div class="card-body"><h6 class="mb-0">Avg Reads/Story</h6><h2 class="mb-0">${formatNumber(Math.round(totalReads / (published || 1)))}</h2></div></div></div>
        </div>
        <div class="row">
            <div class="col-md-6"><div class="card"><div class="card-header d-flex justify-content-between"><h6>Recent Stories</h6><button class="btn btn-sm btn-primary" onclick="loadView('stories')">View All</button></div>
            <div class="card-body p-0"><div class="list-group list-group-flush">${stories.slice(0, 10).map(s => `<div class="list-group-item d-flex justify-content-between"><div><span class="status-badge ${s.status === 'Published' ? 'status-published' : s.status === 'Ready' ? 'status-ready' : s.status === 'Done' ? 'status-done' : 'status-draft'}">${s.status}</span> ${escapeHtml(s.name.length > 35 ? s.name.substring(0, 35) + '...' : s.name)} ${s.series ? `<span class="series-badge">📚 ${s.series}</span>` : ''} ${s.bookmarked ? `<i class="bi bi-bookmark-fill text-warning"></i>` : ''}</div><button class="btn btn-sm btn-outline-primary" onclick="editStory('${s.key.replace(/'/g, "\\'")}')">Edit</button></div>`).join('')}</div></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-header d-flex justify-content-between"><h6>Upcoming Schedule</h6><button class="btn btn-sm btn-primary" onclick="generateCalendar()">Generate</button></div>
            <div class="card-body p-0"><div class="list-group list-group-flush">${calendar.schedule?.slice(0, 10).map(c => `<div class="list-group-item"><div class="d-flex justify-content-between"><div><strong>${c.date}</strong> (${c.weekday})<br><small>${escapeHtml(c.name)}</small>${c.series ? `<span class="series-badge ms-2">📚 ${c.series}</span>` : ''}</div><button class="btn btn-sm btn-success" onclick="markPublished('${c.story_key.replace(/'/g, "\\'")}')">Publish</button></div></div>`).join('') || '<div class="list-group-item text-muted">No scheduled stories</div>'}</div></div></div></div>
        </div>
        <div class="mt-3"><button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync</button><button class="btn btn-sm btn-info ms-2" onclick="syncAllStats()"><i class="bi bi-cloud-download"></i> Sync All Stats</button><button class="btn btn-sm btn-outline-success ms-2" onclick="fetchAllStats()"><i class="bi bi-database-down"></i> Fetch Stats</button></div>
    `;
}

// Stories table header template
function getStoriesHeaderHTML() {
    return `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h1 class="h3">Stories</h1>
            <div>
                <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addStoryModal"><i class="bi bi-plus-lg"></i> Add Story</button>
                <button class="btn btn-sm btn-outline-info ms-2" onclick="syncAllStats()"><i class="bi bi-cloud-download"></i> Sync All Stats</button>
                <button class="btn btn-sm btn-outline-success ms-2" onclick="fetchAllStats()"><i class="bi bi-database-down"></i> Fetch Stats</button>
            </div>
        </div>
        <div class="filter-bar d-flex gap-2 flex-wrap">
            <i class="bi bi-funnel"></i><span>Filter:</span>
            <select id="statusFilter" class="form-select form-select-sm w-auto" onchange="saveFilterState(); filterStories()">
                <option value="All">All</option>
                <option value="Draft">Draft</option>
                <option value="Done">Done</option>
                <option value="Ready">Ready</option>
                <option value="Published">Published</option>
            </select>
            <select id="seriesFilter" class="form-select form-select-sm w-auto" onchange="saveFilterState(); filterStories()">
                <option value="">All Series</option>
                ${allSeries.map(s => `<option value="${s.name}">${s.name}</option>`).join('')}
            </select>
            <input type="text" id="searchFilter" class="form-control form-control-sm w-auto" placeholder="Search..." onkeyup="saveFilterState(); filterStories()">
            <div class="form-check ms-2">
                <input class="form-check-input" type="checkbox" id="bookmarkFilter" onchange="saveFilterState(); filterStories()">
                <label class="form-check-label small" for="bookmarkFilter">Bookmarked only</label>
            </div>
            <button class="btn btn-sm btn-outline-secondary" onclick="clearFilters()">Clear</button>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="storiesTableHeader" class="table-light">
                    <tr>
                        <th class="sortable" data-sort="bookmarked" onclick="sortStories('bookmarked')"><i class="bi bi-bookmark"></i> <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="status" onclick="sortStories('status')">Status <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="name" onclick="sortStories('name')">Story Name <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="series" onclick="sortStories('series')">Series <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="reads" onclick="sortStories('reads')">Reads <small class="text-muted">(Member / Total)</small> <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="medium_total_views" onclick="sortStories('medium_total_views')">Views <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="claps" onclick="sortStories('claps')">Claps <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="created_date" onclick="sortStories('created_date')">Created <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="published_date" onclick="sortStories('published_date')">Published <i class="bi bi-arrow-down-up"></i></th>
                        <th>LinkedIn</th>
                        <th class="sortable" data-sort="linkedin_impressions" onclick="sortStories('linkedin_impressions')">Impressions <i class="bi bi-arrow-down-up"></i></th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="storiesTableBody"></tbody>
            </table>
        </div>
    `;
}

// Series header template
function getSeriesHeaderHTML() {
    return `
        <div class="d-flex justify-content-between mb-3">
            <h1 class="h3">Series</h1>
            <button class="btn btn-sm btn-primary" onclick="addSeries()"><i class="bi bi-plus-lg"></i> Add Series</button>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="seriesTableHeader" class="table-light">
                    <tr>
                        <th class="sortable" data-sort="name" onclick="sortSeries('name')">Series Name <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="total_stories" onclick="sortSeries('total_stories')">Progress <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="spacing_days" onclick="sortSeries('spacing_days')">Spacing (days) <i class="bi bi-arrow-down-up"></i></th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="seriesTableBody"></tbody>
            </table>
        </div>
    `;
}

// Calendar header template
function getCalendarHeaderHTML(calendar) {
    return `
        <div class="d-flex justify-content-between mb-3">
            <h1 class="h3">Publishing Calendar</h1>
            <button class="btn btn-sm btn-primary" onclick="generateCalendar()"><i class="bi bi-arrow-repeat"></i> Regenerate</button>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-3"><div class="card bg-info text-white p-2"><small>Scheduled</small><h5>${calendar.summary?.total_scheduled || 0}</h5></div></div>
            <div class="col-md-3"><div class="card bg-warning text-white p-2"><small>Stories/Week</small><h5>${calendar.summary?.stories_per_week || 3}</h5></div></div>
            <div class="col-md-3"><div class="card bg-secondary text-white p-2"><small>Series Spacing</small><h5>${calendar.summary?.series_spacing_default || 7} days</h5></div></div>
            <div class="col-md-3"><div class="card bg-dark text-white p-2"><small>Remaining</small><h5>${calendar.summary?.remaining_unpublished || 0}</h5></div></div>
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
}

// Settings HTML template
function getSettingsHTML(settings, root) {
    return `<h1 class="h3 mb-3">Settings</h1><div class="row"><div class="col-md-6"><div class="card mb-3"><div class="card-header"><h6>Calendar Settings</h6></div><div class="card-body"><form id="calendarSettingsForm"><div class="mb-2"><label>Series Spacing (days)</label><input type="number" class="form-control form-control-sm" name="series_spacing_days" value="${settings.series_spacing_days || 7}" min="5" max="14"></div><div class="mb-2"><label>Stories Per Week</label><input type="number" class="form-control form-control-sm" name="stories_per_week" value="${settings.stories_per_week || 3}" min="1" max="7"></div><div class="mb-2"><label>Preferred Publish Days</label><div class="d-flex gap-2 flex-wrap">${['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => `<div class="form-check"><input class="form-check-input" type="checkbox" name="preferred_days" value="${day}" ${settings.preferred_publish_days?.includes(day) ? 'checked' : ''}><label class="form-check-label small">${day.slice(0, 3)}</label></div>`).join('')}</div></div><div class="mb-2"><label>Start Date</label><input type="date" class="form-control form-control-sm" name="start_date" value="${settings.start_date || ''}"></div><button type="submit" class="btn btn-sm btn-primary">Save</button></form></div></div></div>
    <div class="col-md-6"><div class="card mb-3"><div class="card-header"><h6>System</h6></div><div class="card-body"><p><strong>Stories Root:</strong> ${root.stories_root}</p><p><strong>Data Directory:</strong> ${settings.data_dir || './data'}</p><hr><button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync</button><button class="btn btn-sm btn-secondary ms-2" onclick="generateCalendar()"><i class="bi bi-calendar"></i> Generate Calendar</button><button class="btn btn-sm btn-info ms-2" onclick="syncAllStats()"><i class="bi bi-cloud-download"></i> Sync All Stats</button><button class="btn btn-sm btn-outline-success ms-2" onclick="fetchAllStats()"><i class="bi bi-database-down"></i> Fetch Stats</button></div></div></div></div>`;
}

// ============================================
// Render Functions
// ============================================
function renderStoryTable(stories) {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;

    let filtered = [...stories];
    if (filterState.status !== 'All') filtered = filtered.filter(s => s.status === filterState.status);
    if (filterState.series) filtered = filtered.filter(s => s.series === filterState.series);
    if (filterState.search) {
        const searchLower = filterState.search.toLowerCase();
        filtered = filtered.filter(s => s.name.toLowerCase().includes(searchLower) || (s.series && s.series.toLowerCase().includes(searchLower)));
    }
    if (filterState.bookmarked) filtered = filtered.filter(s => s.bookmarked === true);

    const { column, direction } = sortState.stories;
    filtered.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'reads' || column === 'claps' || column === 'linkedin_impressions' || column === 'medium_total_views') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        if (column === 'created_date' || column === 'published_date') {
            aVal = aVal || '';
            bVal = bVal || '';
            return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        if (column === 'bookmarked') {
            aVal = aVal ? 1 : 0;
            bVal = bVal ? 1 : 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });

    tbody.innerHTML = filtered.map(story => {
        let storyKey = story.key;
        if (storyKey.toLowerCase().endsWith('.md')) storyKey = storyKey.slice(0, -3);

        let linkedinHtml = '<span class="linkedin-badge linkedin-not-posted">Not Posted</span>';
        if (story.linkedin_status === 'scheduled') linkedinHtml = `<span class="linkedin-badge linkedin-scheduled">📅 Scheduled</span><br><small>${story.linkedin_timestamp ? formatTimestampForDisplay(story.linkedin_timestamp).substring(5) : ''}</small>`;
        else if (story.linkedin_status === 'posted') linkedinHtml = `<span class="linkedin-badge linkedin-posted">✅ Posted</span><br><small>${story.linkedin_timestamp ? formatTimestampForDisplay(story.linkedin_timestamp).substring(5) : ''}</small>`;

        const memberReads = story.medium_member_reads || 0;
        const totalReads = story.reads || 0;
        const totalViews = story.medium_total_views || 0;
        const memberViews = story.medium_member_views || 0;
        const nonmemberViews = story.medium_nonmember_views || 0;
        const readRatio = story.medium_read_ratio || 0;
        const memberPercent = story.medium_member_read_percentage || 0;

        const formattedMemberReads = formatNumber(memberReads);
        const formattedTotalReads = formatNumber(totalReads);
        const formattedTotalViews = formatNumber(totalViews);

        return `<tr class="table-row-clickable" onclick="editStory('${storyKey.replace(/'/g, "\\'")}')">
            <td class="text-center" onclick="event.stopPropagation()">
                <i class="bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}" 
                   onclick="toggleBookmark('${storyKey.replace(/'/g, "\\'")}', event)"></i>
            </td>
            <td><span class="status-badge ${story.status === 'Published' ? 'status-published' : story.status === 'Ready' ? 'status-ready' : story.status === 'Done' ? 'status-done' : 'status-draft'}">${story.status}</span></td>
            <td><strong title="${escapeHtml(story.name)}">${escapeHtml(story.name.length > 50 ? story.name.substring(0, 50) + '...' : story.name)}</strong></td>
            <td>${story.series ? `<span class="series-badge">📚 ${story.series}</span>` : '—'}</td>
            <td class="stats-tooltip reads-cell" title="Member Reads: ${memberReads} | Total Reads: ${totalReads} | Member: ${memberPercent}%">
                <span class="fw-bold">${formattedMemberReads}</span> / ${formattedTotalReads}
                ${memberPercent > 0 ? `<br><small class="text-muted">${memberPercent}% members</small>` : ''}
            </td
            <td class="stats-tooltip" title="Member Views: ${memberViews} | Non-member Views: ${nonmemberViews}">
                ${formattedTotalViews}
                ${readRatio > 0 ? `<br><small class="text-muted">${readRatio}% read ratio</small>` : ''}
             </td
            <td>${formatNumber(story.claps || 0)}</td
            <td><small>${story.created_date ? story.created_date.split('T')[0] : 'Unknown'}</small></td
            <td><small>${story.published_date ? (story.published_date.split('T')[0] || story.published_date) : '—'}</small></td
            <td class="text-center">${linkedinHtml}</td
            <td class="text-center">${story.linkedin_impressions ? formatNumber(story.linkedin_impressions) : '—'}</td
            <td class="action-buttons" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-success" onclick="markPublished('${storyKey.replace(/'/g, "\\'")}')" title="Publish"><i class="bi bi-check-lg"></i></button>
                <button class="btn btn-sm btn-info" onclick="quickMarkLinkedin('${storyKey.replace(/'/g, "\\'")}', 'posted')" title="Mark Posted"><i class="bi bi-linkedin"></i></button>
                <button class="btn btn-sm btn-warning" onclick="quickMarkLinkedin('${storyKey.replace(/'/g, "\\'")}', 'scheduled')" title="Mark Scheduled"><i class="bi bi-calendar"></i></button>
                <button class="btn btn-sm btn-secondary" onclick="quickMarkLinkedin('${storyKey.replace(/'/g, "\\'")}', '')" title="Not Posted"><i class="bi bi-x-circle"></i></button>
                <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); showStatsDashboard('${storyKey.replace(/'/g, "\\'")}')" title="Stats Dashboard"><i class="bi bi-graph-up"></i></button>
                <button class="btn btn-sm btn-danger" onclick="deleteStory('${storyKey.replace(/'/g, "\\'")}')" title="Delete"><i class="bi bi-trash"></i></button>
            </td
         </tr`;
    }).join('');
}

function renderSeriesTable(series) {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) return;
    const { column, direction } = sortState.series;
    const sorted = [...series].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'total_stories' || column === 'published' || column === 'spacing_days') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    tbody.innerHTML = sorted.map(s => `
        <tr>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td><div class="d-flex gap-2 align-items-center"><div class="progress" style="width:150px;height:6px;"><div class="progress-bar" style="width:${(s.published / (s.total_stories || 1)) * 100}%"></div></div><small>${s.published}/${s.total_stories || 0}</small></div></td>
            <td><input type="number" class="form-control form-control-sm" style="width:80px;" value="${s.spacing_days}" onchange="updateSeriesSpacing('${s.name}', this.value)"></td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteSeries('${s.name}')"><i class="bi bi-trash"></i></button></td>
        </tr>
    `).join('');
}

function renderCalendarTable(calendar) {
    const tbody = document.getElementById('calendarTableBody');
    if (!tbody) return;
    tbody.innerHTML = calendar.map(c => `
        <tr>
            <td><strong>${c.date}</strong><br><small>${c.weekday}</small></td>
            <td>${escapeHtml(c.name)}</td>
            <td>${c.series || 'Standalone'}</td>
            <td>${c.part ? `Part ${c.part}` : '—'}</td>
            <td>${c.read_time} min</td>
            <td><button class="btn btn-sm btn-success" onclick="markPublished('${c.story_key.replace(/'/g, "\\'")}')">Publish</button></td>
        </tr>
    `).join('') || '<tr><td colspan="6" class="text-center">No scheduled stories</td></tr>';
}

// ============================================
// Load View Functions
// ============================================
async function loadView(view) {
    currentView = view;
    const contentDiv = document.getElementById('content');
    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'block';
    contentDiv.innerHTML = '';
    try {
        await loadAllSeries();
        if (view === 'dashboard') await loadDashboard();
        else if (view === 'stories') await loadStories();
        else if (view === 'series') await loadSeries();
        else if (view === 'calendar') await loadCalendar();
        else if (view === 'settings') await loadSettings();
    } catch (error) {
        contentDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    } finally {
        loadingDiv.style.display = 'none';
    }
}

async function loadAllSeries() {
    const res = await fetch(`${API_BASE}/series/`);
    allSeries = await res.json();
}

async function loadDashboard() {
    const res = await fetch(`${API_BASE}/stories/`);
    const stories = await res.json();
    allStories = stories;
    const calendarRes = await fetch(`${API_BASE}/calendar/`);
    const calendar = await calendarRes.json();
    document.getElementById('content').innerHTML = getDashboardHTML(stories, calendar);
}

async function loadStories() {
    const res = await fetch(`${API_BASE}/stories/`);
    const stories = await res.json();
    allStories = stories;
    document.getElementById('content').innerHTML = getStoriesHeaderHTML();
    renderStoryTable(stories);
    restoreFilterState();
    sortStories(sortState.stories.column);
}

async function loadSeries() {
    const res = await fetch(`${API_BASE}/series/`);
    const series = await res.json();
    allSeries = series;
    document.getElementById('content').innerHTML = getSeriesHeaderHTML();
    renderSeriesTable(series);
    sortSeries(sortState.series.column);
}

async function loadCalendar() {
    const res = await fetch(`${API_BASE}/calendar/`);
    const calendar = await res.json();
    allCalendar = calendar.schedule || [];
    document.getElementById('content').innerHTML = getCalendarHeaderHTML(calendar);
    renderCalendarTable(allCalendar);
    sortCalendar(sortState.calendar.column);
}

async function loadSettings() {
    const settingsRes = await fetch(`${API_BASE}/settings/`);
    const settings = await settingsRes.json();
    const rootRes = await fetch(`${API_BASE}/settings/stories-root`);
    const root = await rootRes.json();
    document.getElementById('content').innerHTML = getSettingsHTML(settings, root);
    document.getElementById('calendarSettingsForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const data = { series_spacing_days: parseInt(fd.get('series_spacing_days')), stories_per_week: parseInt(fd.get('stories_per_week')), preferred_publish_days: fd.getAll('preferred_days'), start_date: fd.get('start_date') };
        const res = await fetch(`${API_BASE}/settings/calendar`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (res.ok) { alert('Saved'); loadSettings(); } else { alert('Error'); }
    });
}

// ============================================
// Edit & Actions
// ============================================
function filterStories() {
    if (allStories.length > 0) {
        renderStoryTable(allStories);
    }
}

function clearFilters() {
    filterState = { status: 'All', series: '', search: '', bookmarked: false };
    if (document.getElementById('statusFilter')) document.getElementById('statusFilter').value = 'All';
    if (document.getElementById('seriesFilter')) document.getElementById('seriesFilter').value = '';
    if (document.getElementById('searchFilter')) document.getElementById('searchFilter').value = '';
    if (document.getElementById('bookmarkFilter')) document.getElementById('bookmarkFilter').checked = false;
    filterStories();
}

function filterStoriesByStatus(status) {
    filterState.status = status === 'all' ? 'All' : status;
    loadView('stories');
}

function filterStoriesByBookmarked() {
    filterState.bookmarked = true;
    loadView('stories');
}

async function editStory(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const encodedKey = encodeURIComponent(cleanKey);
    const res = await fetch(`${API_BASE}/stories/${encodedKey}`);
    if (!res.ok) { alert('Story not found'); return; }
    const story = await res.json();
    document.getElementById('editStoryNameDisplay').textContent = story.name;
    document.getElementById('editStoryKey').value = cleanKey;
    document.getElementById('editStorySeries').textContent = story.series || 'Standalone';
    document.getElementById('editStoryPath').textContent = story.raw_path || story.rel_path || story.key;
    document.getElementById('editStoryCreatedDate').value = formatDateForDisplay(story.created_date);
    document.getElementById('editStoryPublishedDate').value = formatDateForDisplay(story.published_date);
    document.getElementById('editStoryLastUpdated').textContent = story.last_updated || 'Never';
    document.getElementById('editStoryStatus').value = story.status || 'Draft';
    document.getElementById('editStoryReadTime').value = story.read_time || '';
    document.getElementById('editStoryReads').value = story.reads || 0;
    document.getElementById('editStoryTags').value = story.tags ? story.tags.join(', ') : '';
    document.getElementById('editStoryMediumUrl').value = story.medium_url || '';
    document.getElementById('editStoryNotes').value = story.notes || '';
    document.getElementById('editStoryLinkedinStatus').value = story.linkedin_status || '';
    document.getElementById('editStoryLinkedinTimestamp').value = story.linkedin_timestamp || '';
    document.getElementById('editStoryLinkedinImpressions').value = story.linkedin_impressions || 0;
    document.getElementById('editStoryLinkedinUrl').value = story.linkedin_url || '';
    updateLinkedinDisplay();
    new bootstrap.Modal(document.getElementById('editStoryModal')).show();
}

async function saveStoryEdit() {
    let storyKey = document.getElementById('editStoryKey').value;
    if (storyKey.toLowerCase().endsWith('.md')) storyKey = storyKey.slice(0, -3);
    const data = {
        status: document.getElementById('editStoryStatus').value,
        read_time: document.getElementById('editStoryReadTime').value ? parseInt(document.getElementById('editStoryReadTime').value) : null,
        reads: parseInt(document.getElementById('editStoryReads').value) || 0,
        tags: document.getElementById('editStoryTags').value.split(',').map(t => t.trim()).filter(t => t),
        medium_url: document.getElementById('editStoryMediumUrl').value || null,
        notes: document.getElementById('editStoryNotes').value,
        created_date: document.getElementById('editStoryCreatedDate').value || null,
        published_date: document.getElementById('editStoryPublishedDate').value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus').value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp').value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions').value) || 0,
        linkedin_url: document.getElementById('editStoryLinkedinUrl').value || null
    };
    if (data.status === 'Published' && !data.published_date) data.published_date = getTodayDate();
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (res.ok) { bootstrap.Modal.getInstance(document.getElementById('editStoryModal')).hide(); saveFilterState(); await loadView(currentView); restoreFilterState(); } else { const err = await res.json(); alert('Error: ' + (err.detail || 'Unknown')); }
}

async function quickMarkLinkedin(storyKey, status) {
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const now = getNowTimestamp();
    const data = { linkedin_status: status === '' ? null : status, linkedin_timestamp: status === '' ? null : now };
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (res.ok) { saveFilterState(); await loadView(currentView); restoreFilterState(); } else alert('Failed to update LinkedIn status');
}

window.createNewStory = async function() {
    const data = {
        name: document.getElementById('addStoryName').value,
        series: document.getElementById('addStorySeries').value || null,
        tags: document.getElementById('addStoryTags').value.split(',').map(t => t.trim()).filter(t => t),
        read_time: parseInt(document.getElementById('addStoryReadTime').value) || null,
        created_date: document.getElementById('addStoryCreatedDate').value || getTodayDate()
    };
    if (!data.name) { alert('Story name required'); return; }
    const res = await fetch(`${API_BASE}/stories/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (res.ok) { bootstrap.Modal.getInstance(document.getElementById('addStoryModal')).hide(); document.getElementById('addStoryForm').reset(); await syncStories(); saveFilterState(); loadView('stories'); restoreFilterState(); } else alert('Error creating story');
};

// ============================================
// Stats Dashboard Functions
// ============================================
async function showStatsDashboard(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentStatsStoryKey = cleanKey;
    const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`);
    if (!storyRes.ok) { alert('Story not found'); return; }
    const story = await storyRes.json();
    if (!story.medium_url) { alert('This story has no Medium URL. Add one in edit mode first.'); return; }
    const modal = new bootstrap.Modal(document.getElementById('statsDashboardModal'));
    const contentDiv = document.getElementById('statsDashboardContent');
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-2">Loading stats...</p></div>';
    modal.show();
    try {
        const res = await fetch(`${API_BASE}/stories/stats-by-url?medium_url=${encodeURIComponent(story.medium_url)}`);
        const dashboard = await res.json();
        if (res.ok && !dashboard.error) {
            contentDiv.innerHTML = generateDashboardHTML(dashboard);
            document.getElementById('refreshStatsBtn').onclick = () => syncStoryStatsByUrl(story.medium_url);
        } else {
            contentDiv.innerHTML = `<div class="alert alert-danger">Error: ${dashboard.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        contentDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}

async function syncStoryStatsByUrl(mediumUrl) {
    try {
        const res = await fetch(`${API_BASE}/stories/sync-stats-by-url?medium_url=${encodeURIComponent(mediumUrl)}`, { method: 'POST' });
        const data = await res.json();
        if (res.ok && !data.error) {
            alert(`Stats updated! Reads: ${data.stats?.reads || 0}`);
            if (currentStatsStoryKey) showStatsDashboard(currentStatsStoryKey);
            saveFilterState();
            await loadView(currentView);
            restoreFilterState();
        } else {
            alert('Failed to sync stats: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error syncing stats: ' + error.message);
    }
}

async function syncAllStats() {
    if (confirm('Fetch stats for all stories with Medium URLs? This may take a while.')) {
        try {
            const res = await fetch(`${API_BASE}/stories/sync-stats`, { method: 'POST' });
            const data = await res.json();
            alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
            saveFilterState();
            await loadView(currentView);
            restoreFilterState();
        } catch (error) {
            alert('Error syncing stats: ' + error.message);
        }
    }
}

async function fetchAllStats() {
    if (confirm('Fetch detailed stats from Medium for all stories with URLs? Close your browser first (to release cookie lock).')) {
        try {
            const res = await fetch(`${API_BASE}/stories/fetch-stats`, { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
                saveFilterState();
                await loadView(currentView);
                restoreFilterState();
            } else {
                alert('Error: ' + (data.detail || data.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Error fetching stats: ' + error.message);
        }
    }
}

function generateDashboardHTML(dashboard) {
    return `
        <div class="row">
            <div class="col-12 mb-3">
                <h4>${escapeHtml(dashboard.story_name)}</h4>
                <small class="text-muted">Last updated: ${dashboard.last_stats_update ? dashboard.last_stats_update.split('T')[0] : 'Never'}</small>
                ${dashboard.medium_url ? `<br><small><a href="${escapeHtml(dashboard.medium_url)}" target="_blank">View on Medium</a></small>` : ''}
            </div>
        </div>
        <div class="row mb-4">
            <div class="col-12"><h5><i class="bi bi-bar-chart"></i> Engagement Metrics</h5>
                <div class="row g-2">
                    <div class="col-md-3"><div class="card bg-primary text-white"><div class="card-body"><h6>Reads</h6><h3>${formatNumber(dashboard.engagement.reads)}</h3></div></div></div>
                    <div class="col-md-3"><div class="card bg-success text-white"><div class="card-body"><h6>Claps</h6><h3>${formatNumber(dashboard.engagement.claps)}</h3></div></div></div>
                    <div class="col-md-3"><div class="card bg-info text-white"><div class="card-body"><h6>Responses</h6><h3>${formatNumber(dashboard.engagement.responses)}</h3></div></div></div>
                    <div class="col-md-3"><div class="card bg-warning text-white"><div class="card-body"><h6>Bookmarks</h6><h3>${formatNumber(dashboard.engagement.bookmarks)}</h3></div></div></div>
                </div>
            </div>
        </div>
        <div class="row mb-4">
            <div class="col-md-6"><div class="card"><div class="card-body"><h6><i class="bi bi-eye"></i> Views & Read Ratio</h6><h2>${formatNumber(dashboard.engagement.view_count)}</h2><div class="progress mt-2"><div class="progress-bar bg-success" style="width: ${dashboard.engagement.read_ratio}%"></div></div><small>Read ratio: ${dashboard.engagement.read_ratio}% (${formatNumber(dashboard.engagement.reads)} reads)</small></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-body"><h6><i class="bi bi-heart"></i> Fan Metrics</h6><h2>${formatNumber(dashboard.engagement.fan_count)}</h2><small>Fans who clapped</small></div></div></div>
        </div>
        <div class="row mb-4">
            <div class="col-12"><h5><i class="bi bi-speedometer2"></i> Performance Indicators</h5>
                <div class="row">
                    <div class="col-md-3"><div class="card"><div class="card-body"><small>Claps per Read</small><h4>${dashboard.performance.claps_per_read}</h4></div></div></div>
                    <div class="col-md-3"><div class="card"><div class="card-body"><small>Responses per Read</small><h4>${dashboard.performance.responses_per_read}</h4></div></div></div>
                    <div class="col-md-3"><div class="card"><div class="card-body"><small>Bookmarks per Read</small><h4>${dashboard.performance.bookmarks_per_read}</h4></div></div></div>
                    <div class="col-md-3"><div class="card"><div class="card-body"><small>Views to Reads</small><h4>${dashboard.performance.views_to_reads}%</h4></div></div></div>
                </div>
            </div>
        </div>
        <div class="row mb-4">
            <div class="col-md-6"><div class="card"><div class="card-body"><h6><i class="bi bi-file-text"></i> Content</h6><p><strong>Word Count:</strong> ${formatNumber(dashboard.content.word_count)}</p><p><strong>Reading Time:</strong> ${dashboard.content.reading_time_minutes} min</p><p><strong>Tags:</strong> ${dashboard.content.tags.map(t => `<span class="badge bg-secondary me-1">${escapeHtml(t)}</span>`).join('') || 'None'}</p></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-body"><h6><i class="bi bi-info-circle"></i> Metadata</h6><p><strong>Author:</strong> ${escapeHtml(dashboard.metadata.author || 'Unknown')}</p><p><strong>Publication:</strong> ${escapeHtml(dashboard.metadata.publication || 'Independent')}</p><p><strong>Published:</strong> ${dashboard.metadata.first_published ? dashboard.metadata.first_published.split('T')[0] : 'Unknown'}</p><p><strong>Last Updated:</strong> ${dashboard.metadata.last_updated ? dashboard.metadata.last_updated.split('T')[0] : 'Unknown'}</p></div></div></div>
        </div>
    `;
}

// ============================================
// Core Actions
// ============================================
async function syncStories() {
    const res = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
    if (res.ok) { saveFilterState(); await loadView(currentView); restoreFilterState(); } else alert('Sync failed');
}

async function generateCalendar() {
    const res = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
    if (res.ok) { saveFilterState(); await loadView('calendar'); restoreFilterState(); } else alert('Generation failed');
}

async function markPublished(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}/publish`, { method: 'POST' });
    if (res.ok) { saveFilterState(); await loadView(currentView); restoreFilterState(); } else alert('Failed');
}

async function deleteStory(storyKey) {
    if (confirm('Delete this story?')) {
        let cleanKey = storyKey;
        if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
        const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, { method: 'DELETE' });
        if (res.ok) { saveFilterState(); await loadView(currentView); restoreFilterState(); } else alert('Delete failed');
    }
}

async function addSeries() {
    const name = prompt('Series name:');
    if (name) {
        const res = await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, spacing_days: 7 })
        });
        if (res.ok) { await loadAllSeries(); loadView('series'); } else alert('Failed');
    }
}

async function updateSeriesSpacing(seriesName, days) {
    const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spacing_days: parseInt(days) })
    });
    if (!res.ok) { alert('Failed'); loadView('series'); }
}

async function deleteSeries(seriesName) {
    if (confirm(`Delete "${seriesName}"?`)) {
        const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        if (res.ok) { await loadAllSeries(); loadView('series'); } else alert('Failed');
    }
}

// ============================================
// Event Listeners
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    loadView('dashboard');

    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) loadView(view);
            document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    document.getElementById('setNowLinkedinBtn')?.addEventListener('click', setNowLinkedinTimestamp);
    document.getElementById('clearLinkedinTimestampBtn')?.addEventListener('click', clearLinkedinTimestamp);
    document.getElementById('clearAllLinkedinBtn')?.addEventListener('click', clearAllLinkedinData);
    document.getElementById('editStoryLinkedinStatus')?.addEventListener('change', onLinkedinStatusChange);
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
});

document.addEventListener('show.bs.modal', function(event) {
    if (event.target.id === 'addStoryModal') {
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect && allSeries.length) {
            seriesSelect.innerHTML = '<option value="">Create in root (no series)</option>' +
                allSeries.map(s => `<option value="${s.name}">📁 ${s.name}</option>`).join('');
        }
        if (document.getElementById('addStoryCreatedDate')) {
            document.getElementById('addStoryCreatedDate').value = getTodayDate();
        }
    }
});