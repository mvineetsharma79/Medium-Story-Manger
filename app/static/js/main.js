// ============================================
// MAIN APPLICATION - COMPLETE FIXED VERSION
// ============================================

const API_BASE = '/api';

// ============================================
// GLOBAL VARIABLES
// ============================================
let currentView = 'dashboard';
let allStories = [];
let allSeries = [];
let currentMode = 'dashboard';
let currentMonthYear = null;
let availableMonths = [];
let globalLeaderboardStories = new Set(); // Stories that have EVER been on leaderboard
let storyLeaderboardMonths = {}; // Track which months each story was on leaderboard

// Filter and sort state
let filterState = { status: 'All', series: '', search: '', bookmarked: false, leaderboard: false };
let sortState = {
    stories: { column: 'reads', direction: 'desc' },
    series: { column: 'name', direction: 'asc' },
    calendar: { column: 'date', direction: 'asc' }
};
let allCalendar = [];
let currentStatsStoryKey = null;
let currentEditStoryKey = null;
let currentEditStoryYear = null;
let currentEditStoryMonth = null;

let allStoriesFromJson = []; // Add this with other global variables


// ============================================
// UTILITY FUNCTIONS
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

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatTimestampForDisplay(timestamp) {
    if (!timestamp) return '';
    return timestamp.replace('T', ' ').substring(0, 16);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function calcMemberPercent(member, total) {
    if (!total || total === 0) return 0;
    return Math.round((member / total) * 100);
}

function updateLastFetchTime() {
    const now = new Date().toLocaleString();
    localStorage.setItem('lastFetchTime', now);
    const el = document.getElementById('lastFetchTime');
    if (el) el.textContent = now;
}

function loadLastFetchTime() {
    const lastTime = localStorage.getItem('lastFetchTime');
    const el = document.getElementById('lastFetchTime');
    if (el && lastTime) el.textContent = lastTime;
}

function updateLeaderboardTotal() {
    if (!allStories || !Array.isArray(allStories)) {
        const countEl = document.getElementById('leaderboardCount');
        const amountEl = document.getElementById('leaderboardAmount');
        if (countEl) countEl.textContent = '0';
        if (amountEl) amountEl.textContent = '0.00';
        return;
    }
    const storiesWithLeaderboard = allStories.filter(s => s.leaderboard === true);
    const totalNanos = storiesWithLeaderboard.reduce((sum, s) => sum + (s.leaderboard_nanos || 0), 0);
    const countEl = document.getElementById('leaderboardCount');
    const amountEl = document.getElementById('leaderboardAmount');
    if (countEl) countEl.textContent = storiesWithLeaderboard.length;
    if (amountEl) amountEl.textContent = (totalNanos / 1000000000).toFixed(2);
}

// ============================================
// MODE & MONTH FUNCTIONS
// ============================================

async function loadGlobalLeaderboardStatus() {
    try {
        const response = await fetch(`${API_BASE}/stories/leaderboard-status`);
        const data = await response.json();
        globalLeaderboardStories = new Set(data.leaderboard_stories || []);
        storyLeaderboardMonths = data.story_months || {};
        console.log(`Global leaderboard stories: ${globalLeaderboardStories.size}`);
        return data;
    } catch (error) {
        console.error('Error loading global leaderboard status:', error);
        return { leaderboard_stories: [], story_months: {} };
    }
}

async function loadModeAndMonths() {
    try {
        const response = await fetch(`${API_BASE}/stories/mode`);
        const data = await response.json();
        currentMode = data.mode;
        currentMonthYear = data.current_month;
        availableMonths = data.available_months || [];
        updateSidebarMonthSelector();
        updateModeIndicator();
        return data;
    } catch (error) {
        console.error('Error loading mode:', error);
        return null;
    }
}

function updateSidebarMonthSelector() {
    const container = document.getElementById('monthSelectorContainer');
    if (!container) return;
    
    if (availableMonths.length === 0) {
        container.innerHTML = `<div class="text-muted small text-center py-1"><i class="bi bi-info-circle"></i> No monthly data</div>`;
        return;
    }
    
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let displayText = currentMode === 'dashboard' ? 'Dashboard' : (currentMonthYear ? `${monthNames[currentMonthYear.month-1]} ${currentMonthYear.year}` : 'Select Month');
    
    let html = `<div class="dropdown">
        <button class="btn btn-sm btn-outline-secondary w-100 dropdown-toggle" type="button" data-bs-toggle="dropdown" style="font-size: 0.7rem; color: #ecf0f1; border-color: rgba(255,255,255,0.3);">
            <i class="bi bi-calendar-month"></i> ${displayText}
        </button>
        <ul class="dropdown-menu w-100" style="background-color: #2c3e50; border: 1px solid rgba(255,255,255,0.1);">
            <li><a class="dropdown-item ${currentMode === 'dashboard' ? 'active bg-primary text-white' : ''}" href="#" onclick="switchToDashboardMode(); return false;" style="color: #ecf0f1;"><i class="bi bi-speedometer2"></i> Dashboard</a></li>
            <li><hr class="dropdown-divider" style="border-top-color: rgba(255,255,255,0.1);"></li>`;
    
    for (const month of availableMonths) {
        const isActive = currentMode === 'month' && currentMonthYear?.year === month.year && currentMonthYear?.month === month.month;
        html += `<li><a class="dropdown-item ${isActive ? 'active bg-primary text-white' : ''}" href="#" onclick="switchToMonthMode(${month.year}, ${month.month}); return false;" style="color: #ecf0f1;"><i class="bi bi-calendar-month"></i> ${month.display}${isActive ? ' ✓' : ''}</a></li>`;
    }
    html += `</ul></div>`;
    container.innerHTML = html;
}

function updateModeIndicator() {
    const indicator = document.getElementById('currentModeIndicator');
    if (!indicator) return;
    
    if (currentMode === 'dashboard') {
        indicator.innerHTML = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #0f3460; font-size: 0.7rem;"><i class="bi bi-speedometer2"></i> Mode: <strong>Dashboard</strong><br><small>Leaderboard = Ever been on leaderboard<br>Stats = Current month</small></div>`;
    } else if (currentMonthYear) {
        const monthName = new Date(currentMonthYear.year, currentMonthYear.month - 1, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
        indicator.innerHTML = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #0f3460; font-size: 0.7rem;"><i class="bi bi-calendar-month"></i> Mode: <strong>Month View</strong><br>Showing: <strong>${monthName}</strong><br><small>Leaderboard = Only for this month</small></div>`;
    }
}

async function switchToDashboardMode() {
    if (!confirm('Switch to Dashboard mode?')) return;
    try {
        const response = await fetch(`${API_BASE}/stories/switch-to-dashboard`, { method: 'POST' });
        if (response.ok) {
            currentMode = 'dashboard';
            updateModeIndicator();
            updateSidebarMonthSelector();
            await loadStories();
            alert('Switched to Dashboard mode');
        }
    } catch (error) { alert('Error: ' + error.message); }
}

async function switchToMonthMode(year, month) {
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthName = `${monthNames[month-1]} ${year}`;
    if (!confirm(`Switch to ${monthName}?`)) return;
    try {
        const response = await fetch(`${API_BASE}/stories/switch-month?year=${year}&month=${month}`, { method: 'POST' });
        if (response.ok) {
            currentMode = 'month';
            currentMonthYear = { year, month };
            updateModeIndicator();
            updateSidebarMonthSelector();
            await loadStories();
            alert(`Switched to ${monthName}`);
        }
    } catch (error) { 
        console.error('Error switching month:', error);
        alert('Error: ' + error.message); 
    }
}

// ============================================
// STORIES CRUD FUNCTIONS
// ============================================

function saveFilterState() {
    filterState.status = document.getElementById('statusFilter')?.value || 'All';
    filterState.series = document.getElementById('seriesFilter')?.value || '';
    filterState.search = document.getElementById('searchFilter')?.value || '';
    filterState.bookmarked = document.getElementById('bookmarkFilter')?.checked || false;
    filterState.leaderboard = document.getElementById('leaderboardFilter')?.checked || false;
}

function restoreFilterState() {
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkFilter = document.getElementById('bookmarkFilter');
    const leaderboardFilter = document.getElementById('leaderboardFilter');
    if (statusFilter) statusFilter.value = filterState.status;
    if (seriesFilter) seriesFilter.value = filterState.series;
    if (searchFilter) searchFilter.value = filterState.search;
    if (bookmarkFilter) bookmarkFilter.checked = filterState.bookmarked;
    if (leaderboardFilter) leaderboardFilter.checked = filterState.leaderboard;
    filterStories();
}

function filterStories() { 
    if (allStories) {
        const isMonthMode = currentMode === 'month' && currentMonthYear;
        renderStoryTable(allStories, isMonthMode);
    }
}

function clearFilters() {
    filterState = { status: 'All', series: '', search: '', bookmarked: false, leaderboard: false };
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkFilter = document.getElementById('bookmarkFilter');
    const leaderboardFilter = document.getElementById('leaderboardFilter');
    if (statusFilter) statusFilter.value = 'All';
    if (seriesFilter) seriesFilter.value = '';
    if (searchFilter) searchFilter.value = '';
    if (bookmarkFilter) bookmarkFilter.checked = false;
    if (leaderboardFilter) leaderboardFilter.checked = false;
    filterStories();
}


function sortStories(column) {
    const direction = sortState.stories.column === column && sortState.stories.direction === 'asc' ? 'desc' : 'asc';
    sortState.stories = { column, direction };
    if (allStories && allStories.length) {
        renderStoryTable(allStories);
    }
}

async function loadStories() {
    console.log('loadStories called');
    try {
        // Simple test - just load stories.json first
        const res = await fetch(`${API_BASE}/stories/`);
        const stories = await res.json();
        
        // Create a simple table to test
        document.getElementById('content').innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h1 class="h3 mb-0">Stories (Test)</h1>
                <div>
                    <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addStoryModal"><i class="bi bi-plus-lg"></i> Add Story</button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Status</th>
                            <th>Story Name</th>
                            <th>Series</th>
                            <th>Reads</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="storiesTableBody"></tbody>
                </table>
            </div>
        `;
        
        const tbody = document.getElementById('storiesTableBody');
        if (!tbody) {
            console.error('tbody not found');
            return;
        }
        
        let html = '';
        for (const story of stories.slice(0, 10)) {
            html += `
                <tr>
                    <td><span class="status-badge status-draft">${story.status || 'Draft'}</span></td
                    <td><strong>${escapeHtml(story.name || 'Unknown')}</strong></td
                    <td>${story.series || '—'}</td
                    <td>${story.reads || 0}</td
                    <td><button class="btn btn-sm btn-outline-info" onclick="openEditStory('${story.key}')">Edit</button></td
                 </tr
            `;
        }
        tbody.innerHTML = html;
        
        window.allStories = stories;
        console.log(`Loaded ${stories.length} stories`);
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}

function renderStoryTable(stories) {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) {
        console.log('Table body not found yet');
        return;
    }
    
    if (!stories || stories.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-3">No stories available</td></tr>';
        return;
    }
    
    let filtered = [...stories];
    if (filterState.status !== 'All') filtered = filtered.filter(s => s.status === filterState.status);
    if (filterState.series) filtered = filtered.filter(s => s.series === filterState.series);
    if (filterState.search) filtered = filtered.filter(s => s.name && s.name.toLowerCase().includes(filterState.search.toLowerCase()));
    if (filterState.bookmarked) filtered = filtered.filter(s => s.bookmarked === true);
    if (filterState.leaderboard) filtered = filtered.filter(s => s.leaderboard === true);
    
    document.getElementById('filterCountDisplay').innerHTML = `Showing ${filtered.length} of ${stories.length} stories`;
    
    let html = '';
    for (const story of filtered) {
        let storyKey = story.key || '';
        if (storyKey.endsWith('.md')) storyKey = storyKey.slice(0, -3);
        
        const publishDate = story.medium_first_published ? story.medium_first_published.split('T')[0] : (story.published_date || '-');
        const seriesName = story.series || '—';
        const totalReads = story.reads || 0;
        const memberReadPercent = story.medium_member_reads && totalReads > 0 ? Math.round((story.medium_member_reads / totalReads) * 100) : 0;
        const lifetimeText = `${formatNumber(story.lifetime_reads || 0)}/${formatNumber(story.lifetime_views || 0)}/${formatNumber(story.lifetime_claps || 0)}`;
        
        let linkedinHtml = '<span class="linkedin-badge linkedin-not-posted">Not Posted</span>';
        if (story.linkedin_status === 'scheduled') linkedinHtml = '<span class="linkedin-badge linkedin-scheduled">📅 Scheduled</span>';
        else if (story.linkedin_status === 'posted') linkedinHtml = '<span class="linkedin-badge linkedin-posted">✅ Posted</span>';
        
        const statusClass = story.status === 'Published' ? 'status-published' : 
                           story.status === 'Ready' ? 'status-ready' : 
                           story.status === 'Done' ? 'status-done' : 'status-draft';
        
        html += `
            <tr class="table-row-clickable" onclick="openEditStory('${storyKey.replace(/'/g, "\\'")}')">
                <td class="text-center" onclick="event.stopPropagation()">
                    <i class="bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}" 
                       onclick="toggleBookmark('${storyKey.replace(/'/g, "\\'")}', event)"></i>
                </td>
                <td class="text-center" onclick="event.stopPropagation()">
                    <i class="bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}" 
                       onclick="toggleLeaderboard('${storyKey.replace(/'/g, "\\'")}', event)"></i>
                </td>
                <td><span class="status-badge ${statusClass}">${story.status || 'Draft'}</span></td>
                <td><strong>${escapeHtml(story.name || 'Unknown')}</strong></td>
                <td>${escapeHtml(seriesName)}</td
                <td>${publishDate}</td
                <td class="stats-tooltip" title="${memberReadPercent}% members">
                    ${formatNumber(totalReads)}<br><small>${memberReadPercent}%</small>
                </td
                <td>${formatNumber(story.view_count || 0)}</td
                <td>${formatNumber(story.claps || 0)}</td
                <td>${formatNumber(story.linkedin_impressions || 0)}</td
                <td>${linkedinHtml}</td
                <td class="stats-tooltip" title="Lifetime Reads/Views/Claps">${lifetimeText}</td
                <td class="action-buttons" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-outline-info" onclick="showStatsDashboard('${storyKey.replace(/'/g, "\\'")}')" title="Stats"><i class="bi bi-graph-up"></i></button>
                    <button class="btn btn-sm btn-danger" onclick="deleteStory('${storyKey.replace(/'/g, "\\'")}')" title="Delete"><i class="bi bi-trash"></i></button>
                 </td
             </tr
        `;
    }
    tbody.innerHTML = html;
}

async function toggleBookmark(storyKey, event) {
    event.stopPropagation();
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    const story = allStories?.find(s => s.key === cleanKey);
    if (!story) return;
    await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ bookmarked: !story.bookmarked }) 
    });
    await loadStories();
}

async function toggleLeaderboard(storyKey, event) {
    event.stopPropagation();
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    
    // Get target month based on mode
    let targetYear, targetMonth;
    if (currentMode === 'month' && currentMonthYear) {
        targetYear = currentMonthYear.year;
        targetMonth = currentMonthYear.month;
    } else {
        const now = new Date();
        targetYear = now.getFullYear();
        targetMonth = now.getMonth() + 1;
    }
    
    const story = allStories?.find(s => s.key === cleanKey);
    if (!story) return;
    
    const newLeaderboardStatus = !story.leaderboard;
    
    const monthlyData = {
        leaderboard: newLeaderboardStatus,
        leaderboard_nanos: story.leaderboard_nanos || 0
    };
    
    try {
        const response = await fetch(`${API_BASE}/stories/update-story-monthly-stats/${encodeURIComponent(cleanKey)}?year=${targetYear}&month=${targetMonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        if (response.ok) {
            await loadStories();
            updateLeaderboardTotal();
        } else {
            alert('Failed to update leaderboard status');
        }
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
        alert('Error: ' + error.message);
    }
}

async function deleteStory(storyKey) {
    if (confirm('Delete this story?')) {
        let cleanKey = storyKey;
        if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
        await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, { method: 'DELETE' });
        await loadStories();
    }
}

async function syncStories() { 
    await fetch(`${API_BASE}/stories/sync`, { method: 'POST' }); 
    await loadStories(); 
}

// ============================================
// DASHBOARD FUNCTIONS
// ============================================

async function loadDashboard() {
    console.log('loadDashboard called');
    try {
        // Load global leaderboard status
        await loadGlobalLeaderboardStatus();
        
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        
        // Fetch monthly stats for current month
        let monthlyStatsMap = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/month/${currentYear}/${currentMonth}`);
            if (monthlyRes.ok) {
                const monthlyStories = await monthlyRes.json();
                monthlyStatsMap = monthlyStories.reduce((map, story) => {
                    map[story.key] = story.monthly_stats || {};
                    return map;
                }, {});
            }
        } catch (e) {
            console.log('No monthly stats available');
        }
        
        // Get all stories
        const res = await fetch(`${API_BASE}/stories/`);
        const stories = await res.json();
        
        // Merge data - for dashboard, leaderboard = TRUE if ever on leaderboard in ANY month
        const mergedStories = stories.map(story => {
            const monthlyStats = monthlyStatsMap[story.key] || {};
            return {
                ...story,
                leaderboard: globalLeaderboardStories.has(story.key),
                leaderboard_nanos: monthlyStats.leaderboard_nanos || 0,
                reads: monthlyStats.reads || 0,
                view_count: monthlyStats.view_count || 0,
                claps: monthlyStats.claps || 0,
                responses: monthlyStats.responses || 0,
                medium_member_reads: monthlyStats.medium_member_reads || 0,
                medium_member_views: monthlyStats.medium_member_views || 0,
                medium_nonmember_reads: monthlyStats.medium_nonmember_reads || 0,
                medium_nonmember_views: monthlyStats.medium_nonmember_views || 0,
                medium_read_ratio: monthlyStats.medium_read_ratio || 0,
                medium_member_read_percentage: monthlyStats.medium_member_read_percentage || 0
            };
        });
        
        allStories = mergedStories;
        
        const published = allStories.filter(s => s.status === 'Published').length;
        const draft = allStories.filter(s => s.status === 'Draft').length;
        const ready = allStories.filter(s => s.status === 'Ready').length;
        const done = allStories.filter(s => s.status === 'Done').length;
        const bookmarked = allStories.filter(s => s.bookmarked === true).length;
        const leaderboard = allStories.filter(s => s.leaderboard === true).length;
        
        const totalMemberReads = allStories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
        const totalReads = allStories.reduce((sum, s) => sum + (s.reads || 0), 0);
        const totalMemberViews = allStories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
        const totalViews = allStories.reduce((sum, s) => sum + (s.view_count || 0), 0);
        const totalClaps = allStories.reduce((sum, s) => sum + (s.claps || 0), 0);
        
        const totalMemberReadPercent = calcMemberPercent(totalMemberReads, totalReads);
        const totalMemberViewPercent = calcMemberPercent(totalMemberViews, totalViews);
        const totalReadRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        const leaderboardStories = allStories.filter(s => s.leaderboard === true);
        const leaderboardMemberReads = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
        const leaderboardTotalReads = leaderboardStories.reduce((sum, s) => sum + (s.reads || 0), 0);
        const leaderboardMemberViews = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
        const leaderboardTotalViews = leaderboardStories.reduce((sum, s) => sum + (s.view_count || 0), 0);
        const leaderboardClaps = leaderboardStories.reduce((sum, s) => sum + (s.claps || 0), 0);
        const leaderboardCount = leaderboardStories.length;
        const leaderboardMemberReadPercent = calcMemberPercent(leaderboardMemberReads, leaderboardTotalReads);
        
        const calendarRes = await fetch(`${API_BASE}/calendar/`);
        const calendar = await calendarRes.json();
        
        document.getElementById('content').innerHTML = `
            <h1 class="h3 mb-3">Dashboard</h1>
            
            <div class="row g-2 mb-3">
                <div class="col-md-2"><div class="card stat-card bg-primary text-white" onclick="filterStoriesByStatus('all')"><div class="card-body"><h6>Total</h6><h2>${allStories.length}</h2></div></div></div>
                <div class="col-md-2"><div class="card stat-card bg-success text-white" onclick="filterStoriesByStatus('Published')"><div class="card-body"><h6>Published</h6><h2>${published}</h2></div></div></div>
                <div class="col-md-2"><div class="card stat-card bg-info text-white" onclick="filterStoriesByStatus('Ready')"><div class="card-body"><h6>Ready</h6><h2>${ready}</h2></div></div></div>
                <div class="col-md-2"><div class="card stat-card bg-secondary text-white" onclick="filterStoriesByStatus('Done')"><div class="card-body"><h6>Done</h6><h2>${done}</h2></div></div></div>
                <div class="col-md-2"><div class="card stat-card" style="background:#ffc107;color:#000;" onclick="filterStoriesByBookmarked()"><div class="card-body"><h6>Bookmarked</h6><h2>${bookmarked}</h2></div></div></div>
                <div class="col-md-2"><div class="card stat-card" style="background:#ffd700;color:#000;" onclick="filterStoriesByLeaderboard()"><div class="card-body"><h6>Leaderboard</h6><h2>${leaderboard}</h2></div></div></div>
            </div>
            
            <div class="row g-2 mb-3">
                <div class="col-md-3"><div class="card mini-stat-card bg-info text-white"><div class="card-body"><h6>Reads</h6><h2>${formatNumber(totalMemberReads)}/${formatNumber(totalReads)} - ${totalMemberReadPercent}%</h2></div></div></div>
                <div class="col-md-3"><div class="card mini-stat-card bg-primary text-white"><div class="card-body"><h6>Views</h6><h2>${formatNumber(totalMemberViews)}/${formatNumber(totalViews)} - ${totalMemberViewPercent}%</h2></div></div></div>
                <div class="col-md-3"><div class="card mini-stat-card bg-warning text-white"><div class="card-body"><h6>Read Ratio</h6><h2>${totalReadRatio}%</h2></div></div></div>
                <div class="col-md-3"><div class="card mini-stat-card bg-success text-white"><div class="card-body"><h6>Total Claps</h6><h2>${formatNumber(totalClaps)}</h2></div></div></div>
            </div>
            
            <div class="row mb-3">
                <div class="col-12">
                    <div class="card leaderboard-section" style="border:1px solid #ffd700;background:#fff8e7;">
                        <div class="card-header py-1" style="background:#ffd700;color:#000;">
                            <small><i class="bi bi-trophy"></i> <strong>Leaderboard</strong> (${leaderboardCount} stories)
                                <button class="btn btn-sm btn-primary py-0 px-2 ms-2" onclick="updateLeaderboardStatsForMonth()" style="font-size:0.7rem;"><i class="bi bi-arrow-repeat"></i> Update Stats</button>
                            </small>
                        </div>
                        <div class="card-body py-1">
                            <div class="row g-1">
                                <div class="col-md-4"><div class="bg-info text-white p-1 rounded text-center"><small>Reads</small><br><strong>${formatNumber(leaderboardMemberReads)}/${formatNumber(leaderboardTotalReads)} - ${leaderboardMemberReadPercent}%</strong></div></div>
                                <div class="col-md-4"><div class="bg-primary text-white p-1 rounded text-center"><small>Views</small><br><strong>${formatNumber(leaderboardMemberViews)}/${formatNumber(leaderboardTotalViews)}</strong></div></div>
                                <div class="col-md-4"><div class="bg-warning text-white p-1 rounded text-center"><small>Claps</small><br><strong>${formatNumber(leaderboardClaps)}</strong></div></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6"><div class="card"><div class="card-header py-1"><small>Recent Stories</small><button class="btn btn-sm btn-primary float-end py-0" onclick="loadView('stories')">View All</button></div>
                <div class="card-body p-0"><div class="list-group list-group-flush">${allStories.slice(0,8).map(s => `<div class="list-group-item py-1 d-flex justify-content-between align-items-center"><div><span class="status-badge ${s.status==='Published'?'status-published':s.status==='Ready'?'status-ready':s.status==='Done'?'status-done':'status-draft'}">${s.status}</span> <small>${escapeHtml(s.name.substring(0,40))}</small>${s.leaderboard?' <i class="bi bi-trophy-fill text-warning"></i>':''}</div><button class="btn btn-sm btn-outline-primary py-0" onclick="openEditStory('${s.key.replace(/'/g, "\\'")}')">Edit</button></div>`).join('')}</div></div></div></div>
                <div class="col-md-6"><div class="card"><div class="card-header py-1"><small>Upcoming Schedule</small><button class="btn btn-sm btn-primary float-end py-0" onclick="generateCalendar()">Generate</button></div><div class="card-body p-0"><div class="list-group list-group-flush">${calendar.schedule?.slice(0,8).map(c => `<div class="list-group-item py-1"><small><strong>${c.date}</strong> - ${escapeHtml(c.name)}</small>${c.series?` <span class="series-badge">${c.series}</span>`:''}</div>`).join('') || '<div class="list-group-item text-muted">No scheduled stories</div>'}</div></div></div></div>
            </div>
            <div class="mt-3">
                <button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync Files</button>
                <button class="btn btn-sm btn-success ms-2" onclick="updateLeaderboardStatsForMonth()"><i class="bi bi-trophy"></i> Update Leaderboard Stats</button>
            </div>
        `;
        
        updateLeaderboardTotal();
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading dashboard: ${error.message}</div>`;
    }
}

async function updateLeaderboardStatsForMonth() {
    if (currentMode === 'dashboard') {
        if (!confirm('Update stats for current month?')) return;
    } else if (!currentMonthYear) {
        alert('Please select a month from the sidebar first');
        return;
    }
    
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Updating...';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
    
    try {
        let url = `${API_BASE}/stories/update-leaderboard-stats`;
        if (currentMode === 'month' && currentMonthYear) {
            url += `?year=${currentMonthYear.year}&month=${currentMonthYear.month}`;
        }
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            await loadStories();
            updateLeaderboardTotal();
            alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
        } else {
            alert('Error: ' + (data.detail || data.error));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}

// ============================================
// SERIES FUNCTIONS - FIXED
// ============================================

function sortSeries(column) {
    const direction = sortState.series.column === column && sortState.series.direction === 'asc' ? 'desc' : 'asc';
    sortState.series = { column, direction };
    if (allSeries) {
        const sorted = [...allSeries].sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];
            if (column === 'total_stories' || column === 'published') {
                aVal = aVal || 0;
                bVal = bVal || 0;
                return direction === 'asc' ? aVal - bVal : bVal - aVal;
            }
            if (column === 'spacing_days') {
                aVal = aVal || 7;
                bVal = bVal || 7;
                return direction === 'asc' ? aVal - bVal : bVal - aVal;
            }
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
            return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        });
        renderSeriesTable(sorted);
        updateSeriesSortIcons(column, direction);
    }
}

function updateSeriesSortIcons(column, direction) {
    const headers = document.querySelectorAll('#seriesTableHeader .sortable');
    headers.forEach(header => {
        header.classList.remove('active');
        const icon = header.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    });
    const activeHeader = document.querySelector(`#seriesTableHeader .sortable[data-sort="${column}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active');
        const icon = activeHeader.querySelector('i');
        if (icon) icon.className = direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
}

async function loadSeries() {
    try {
        const res = await fetch(`${API_BASE}/series/`);
        allSeries = await res.json();
        
        document.getElementById('content').innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h1 class="h3 mb-0">Series</h1>
                <button class="btn btn-sm btn-primary" onclick="addSeries()">
                    <i class="bi bi-plus-lg"></i> Add Series
                </button>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead id="seriesTableHeader" class="table-light">
                        <tr>
                            <th class="sortable" data-sort="name" onclick="sortSeries('name')" style="cursor: pointer;">
                                Series Name <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="total_stories" onclick="sortSeries('total_stories')" style="cursor: pointer;">
                                Progress <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="spacing_days" onclick="sortSeries('spacing_days')" style="cursor: pointer;">
                                Spacing (days) <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th style="width: 100px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="seriesTableBody"></tbody>
                </table>
            </div>
        `;
        renderSeriesTable(allSeries);
        sortSeries(sortState.series.column);
    } catch (error) {
        console.error('Error loading series:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading series: ${error.message}</div>`;
    }
}

function renderSeriesTable(series) {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) return;
    
    if (!series || !Array.isArray(series) || series.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No series found. Click "Add Series" to create one.</td></tr>';
        return;
    }
    
    let html = '';
    for (const s of series) {
        const progressPercent = s.total_stories > 0 ? (s.published / s.total_stories) * 100 : 0;
        html += `
            <tr>
                <td>
                    <strong class="series-link" onclick="filterBySeries('${escapeHtml(s.name)}')" style="cursor: pointer; color: #0d6efd;">
                        ${escapeHtml(s.name)}
                    </strong>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div class="progress flex-grow-1" style="height: 6px; max-width: 150px;">
                            <div class="progress-bar bg-success" style="width: ${progressPercent}%"></div>
                        </div>
                        <small class="text-muted">${s.published}/${s.total_stories || 0}</small>
                    </div>
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" style="width: 80px;" value="${s.spacing_days}" 
                           min="1" max="30" onchange="updateSeriesSpacing('${escapeHtml(s.name)}', this.value)">
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteSeries('${escapeHtml(s.name)}')" title="Delete Series">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }
    tbody.innerHTML = html;
}

async function addSeries() {
    const name = prompt('Enter series name:');
    if (!name || name.trim() === '') return;
    
    const cleanName = name.trim();
    
    try {
        const res = await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: cleanName, spacing_days: 7 })
        });
        
        if (res.ok) {
            await loadAllSeries();
            await loadSeries();
        } else {
            const error = await res.json();
            alert('Failed to add series: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error adding series:', error);
        alert('Error adding series: ' + error.message);
    }
}

async function updateSeriesSpacing(seriesName, days) {
    const spacingDays = parseInt(days);
    if (isNaN(spacingDays) || spacingDays < 1 || spacingDays > 30) {
        alert('Spacing days must be between 1 and 30');
        await loadSeries();
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spacing_days: spacingDays })
        });
        
        if (!res.ok) {
            const error = await res.json();
            alert('Failed to update spacing: ' + (error.detail || 'Unknown error'));
        }
        await loadSeries();
    } catch (error) {
        console.error('Error updating series spacing:', error);
        alert('Error updating spacing: ' + error.message);
        await loadSeries();
    }
}

async function deleteSeries(seriesName) {
    if (!confirm(`Are you sure you want to delete the series "${seriesName}"?\n\nThis will NOT delete the stories, only remove the series association.`)) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        
        if (res.ok) {
            await loadAllSeries();
            await loadSeries();
        } else {
            const error = await res.json();
            alert('Failed to delete series: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Error deleting series: ' + error.message);
    }
}

async function loadAllSeries() {
    try {
        const res = await fetch(`${API_BASE}/series/`);
        allSeries = await res.json();
    } catch (error) {
        console.error('Error loading all series:', error);
        allSeries = [];
    }
}

// ============================================
// CALENDAR FUNCTIONS - FIXED
// ============================================

function sortCalendar(column) {
    const direction = sortState.calendar.column === column && sortState.calendar.direction === 'asc' ? 'desc' : 'asc';
    sortState.calendar = { column, direction };
    const sorted = [...allCalendar].sort((a, b) => {
        if (column === 'date') {
            return direction === 'asc' ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date);
        }
        if (column === 'read_time') {
            const aVal = a.read_time || 0;
            const bVal = b.read_time || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        if (column === 'part') {
            const aVal = a.part || 999;
            const bVal = b.part || 999;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        const aVal = String(a[column] || '').toLowerCase();
        const bVal = String(b[column] || '').toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderCalendarTable(sorted);
    updateCalendarSortIcons(column, direction);
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

async function loadCalendar() {
    try {
        const res = await fetch(`${API_BASE}/calendar/`);
        const calendar = await res.json();
        allCalendar = calendar.schedule || [];
        
        document.getElementById('content').innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h1 class="h3 mb-0">Publishing Calendar</h1>
                <button class="btn btn-sm btn-primary" onclick="generateCalendar()">
                    <i class="bi bi-arrow-repeat"></i> Regenerate
                </button>
            </div>
            
            <div class="row g-2 mb-3">
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body p-2">
                            <small>Scheduled</small>
                            <h4 class="mb-0">${calendar.summary?.total_scheduled || 0}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body p-2">
                            <small>Stories/Week</small>
                            <h4 class="mb-0">${calendar.summary?.stories_per_week || 3}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-secondary text-white">
                        <div class="card-body p-2">
                            <small>Series Spacing</small>
                            <h4 class="mb-0">${calendar.summary?.series_spacing_default || 7} days</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-dark text-white">
                        <div class="card-body p-2">
                            <small>Remaining Unpublished</small>
                            <h4 class="mb-0">${calendar.summary?.remaining_unpublished || 0}</h4>
                        </div>
                    </div>
                </div>
            </div>
            
            ${calendar.summary?.series_counts ? `
            <div class="card mb-3">
                <div class="card-header py-1">
                    <small><i class="bi bi-collection"></i> Series Breakdown</small>
                </div>
                <div class="card-body p-2">
                    <div class="row g-1">
                        ${Object.entries(calendar.summary.series_counts).map(([series, count]) => `
                            <div class="col-md-3">
                                <div class="badge bg-secondary me-1 p-2">${escapeHtml(series || 'Standalone')}: ${count}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            ` : ''}
            
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead id="calendarTableHeader" class="table-light">
                        <tr>
                            <th class="sortable" data-sort="date" onclick="sortCalendar('date')" style="cursor: pointer; width: 120px;">
                                Date <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="name" onclick="sortCalendar('name')" style="cursor: pointer;">
                                Story <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="series" onclick="sortCalendar('series')" style="cursor: pointer; width: 150px;">
                                Series <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="part" onclick="sortCalendar('part')" style="cursor: pointer; width: 80px;">
                                Part <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th class="sortable" data-sort="read_time" onclick="sortCalendar('read_time')" style="cursor: pointer; width: 100px;">
                                Read Time <i class="bi bi-arrow-down-up"></i>
                            </th>
                            <th style="width: 100px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="calendarTableBody"></tbody>
                </table>
            </div>
        `;
        renderCalendarTable(allCalendar);
        sortCalendar(sortState.calendar.column);
    } catch (error) {
        console.error('Error loading calendar:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading calendar: ${error.message}</div>`;
    }
}

function renderCalendarTable(calendar) {
    const tbody = document.getElementById('calendarTableBody');
    if (!tbody) return;
    
    if (!calendar || calendar.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No scheduled stories. Click "Regenerate" to create a schedule.</td></tr>';
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
            <tr class="table-row-clickable" onclick="markPublished('${storyKey}')" style="cursor: pointer;">
                <td>
                    <strong>${dateStr}</strong><br>
                    <small class="text-muted">${weekdayStr}</small>
                </td>
                <td>${nameStr}</td>
                <td>${seriesStr}</td>
                <td>${partStr}</td>
                <td>${readTimeStr}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="event.stopPropagation(); markPublished('${storyKey}')">
                        <i class="bi bi-check-lg"></i> Publish
                    </button>
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
        console.error('Error generating calendar:', error);
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
            if (currentView === 'calendar') {
                await loadCalendar();
            }
            alert('Story marked as published');
        } else {
            const error = await res.json();
            alert('Failed to mark as published: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error marking as published:', error);
        alert('Error: ' + error.message);
    }
}

// ============================================
// SETTINGS FUNCTIONS
// ============================================

async function loadSettings() {
    try {
        const settingsRes = await fetch(`${API_BASE}/settings/`);
        const settings = await settingsRes.json();
        const rootRes = await fetch(`${API_BASE}/settings/stories-root`);
        const root = await rootRes.json();
        document.getElementById('content').innerHTML = `
            <h1 class="h3 mb-3">Settings</h1>
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-3">
                        <div class="card-header"><h6>Calendar Settings</h6></div>
                        <div class="card-body">
                            <form id="calendarSettingsForm">
                                <div class="mb-2"><label>Series Spacing (days)</label><input type="number" class="form-control form-control-sm" name="series_spacing_days" value="${settings.series_spacing_days || 7}" min="5" max="14"></div>
                                <div class="mb-2"><label>Stories Per Week</label><input type="number" class="form-control form-control-sm" name="stories_per_week" value="${settings.stories_per_week || 3}" min="1" max="7"></div>
                                <div class="mb-2"><label>Preferred Publish Days</label><div class="d-flex gap-2 flex-wrap">${['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => `<div class="form-check"><input class="form-check-input" type="checkbox" name="preferred_days" value="${day}" ${settings.preferred_publish_days?.includes(day) ? 'checked' : ''}><label class="form-check-label small">${day.slice(0,3)}</label></div>`).join('')}</div></div>
                                <div class="mb-2"><label>Start Date</label><input type="date" class="form-control form-control-sm" name="start_date" value="${settings.start_date || ''}"></div>
                                <button type="submit" class="btn btn-sm btn-primary">Save Settings</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card mb-3">
                        <div class="card-header"><h6>System</h6></div>
                        <div class="card-body">
                            <p><strong>Stories Root:</strong> ${root.stories_root}</p>
                            <p><strong>Data Directory:</strong> ${settings.data_dir || './data'}</p>
                            <hr>
                            <button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync Files</button>
                            <button class="btn btn-sm btn-secondary ms-2" onclick="generateCalendar()"><i class="bi bi-calendar"></i> Generate Calendar</button>
                            <hr>
                            <div class="alert alert-warning small"><i class="bi bi-exclamation-triangle"></i> This will overwrite all monthly data with values from leaderboard JSON files.</div>
                            <button class="btn btn-sm btn-danger w-100" onclick="importAllLeaderboard()"><i class="bi bi-cloud-upload"></i> Import All Leaderboard Data</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const form = document.getElementById('calendarSettingsForm');
        if (form) form.addEventListener('submit', async (e) => {
            e.preventDefault(); const fd = new FormData(e.target); const data = { series_spacing_days: parseInt(fd.get('series_spacing_days')), stories_per_week: parseInt(fd.get('stories_per_week')), preferred_publish_days: fd.getAll('preferred_days'), start_date: fd.get('start_date') };
            await fetch(`${API_BASE}/settings/calendar`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            alert('Settings saved'); await loadSettings();
        });
    } catch (error) { console.error('Error loading settings:', error); document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading settings: ${error.message}</div>`; }
}

async function importAllLeaderboard() {
    if (!confirm('⚠️ WARNING: This will OVERWRITE all monthly data with values from leaderboard JSON files.\n\nThis action cannot be undone. Continue?')) return;
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Importing...';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Importing...'; }
    try {
        const response = await fetch(`${API_BASE}/stories/import-all-leaderboard`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert(`✅ Import Complete!\n\nFiles processed: ${data.files_processed}\nMonths imported: ${data.months_imported}\nStories updated: ${data.total_stories}\n\nClick OK to refresh.`);
            await loadView(currentView);
            await loadModeAndMonths();
        } else {
            alert('Error: ' + (data.error || data.message || 'Unknown error'));
        }
    } catch (error) {
        alert('Error importing leaderboard data: ' + error.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}

// ============================================
// STATS DASHBOARD FUNCTIONS
// ============================================

async function showStatsDashboard(storyKey) {
    let cleanKey = storyKey; if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentStatsStoryKey = cleanKey;
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    contentDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Loading stats...</p></div>';
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    try {
        const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`);
        const story = await storyRes.json();
        let monthlyStats = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/stats-by-url?medium_url=${encodeURIComponent(story.medium_url || '')}`);
            if (monthlyRes.ok) monthlyStats = (await monthlyRes.json()).current_month || {};
        } catch(e) {}
        const memberReads = monthlyStats.member_reads || 0, totalReads = monthlyStats.reads || 0;
        const memberViews = monthlyStats.member_views || 0, totalViews = monthlyStats.views || 0;
        const memberReadPercent = calcMemberPercent(memberReads, totalReads);
        const memberViewPercent = calcMemberPercent(memberViews, totalViews);
        const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        contentDiv.innerHTML = `
            <div class="compact-stats">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${escapeHtml(story.name)}</strong>
                    <a href="${escapeHtml(story.medium_url)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-box-arrow-up-right"></i></a>
                </div>
                <div class="row g-1 mb-2"><div class="col-12"><strong>Monthly Stats</strong></div></div>
                <div class="row g-1 mb-2">
                    <div class="col-4"><div class="card bg-light p-1 text-center"><small>Reads</small><strong>${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%</strong></div></div>
                    <div class="col-4"><div class="card bg-light p-1 text-center"><small>Views</small><strong>${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%</strong></div></div>
                    <div class="col-4"><div class="card bg-light p-1 text-center"><small>Claps</small><strong>${formatNumber(monthlyStats.claps || 0)}</strong></div></div>
                </div>
                <div class="row g-1 mb-2"><div class="col-12"><strong>Lifetime Stats</strong></div></div>
                <div class="row g-1">
                    <div class="col-4"><div class="card" style="background:#6f42c1;color:white;"><div class="card-body p-1 text-center"><small>Reads</small><br><strong>${formatNumber(story.lifetime_reads || 0)}</strong></div></div></div>
                    <div class="col-4"><div class="card" style="background:#fd7e14;color:white;"><div class="card-body p-1 text-center"><small>Claps</small><br><strong>${formatNumber(story.lifetime_claps || 0)}</strong></div></div></div>
                    <div class="col-4"><div class="card" style="background:#20c997;color:white;"><div class="card-body p-1 text-center"><small>Views</small><br><strong>${formatNumber(story.lifetime_views || 0)}</strong></div></div></div>
                </div>
                <div class="text-center mt-2"><small class="text-muted">Read Ratio: ${readRatio}%</small></div>
            </div>
        `;
        const refreshBtn = document.getElementById('refreshStatsBtn');
        if (refreshBtn) { const newBtn = refreshBtn.cloneNode(true); refreshBtn.parentNode.replaceChild(newBtn, refreshBtn); newBtn.onclick = () => refreshStatsForCurrentMonth(); }
    } catch (error) { contentDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`; }
}

async function refreshStatsForCurrentMonth() {
    if (!currentStatsStoryKey) return;
    if (!confirm('Refresh stats from Medium?')) return;
    const contentDiv = document.getElementById('statsDashboardContent');
    if (contentDiv) contentDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Fetching fresh stats...</p></div>';
    try {
        const res = await fetch(`${API_BASE}/stories/fetch-lifetime-stats/${encodeURIComponent(currentStatsStoryKey)}`, { method: 'POST' });
        if (res.ok) await showStatsDashboard(currentStatsStoryKey);
        else alert('Error refreshing stats');
    } catch (error) { alert('Error: ' + error.message); await showStatsDashboard(currentStatsStoryKey); }
}

// ============================================
// EDIT STORY FUNCTIONS
// ============================================

async function openEditStory(storyKey) {
    let cleanKey = storyKey; if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentEditStoryKey = cleanKey;
    const now = new Date();
    currentEditStoryYear = now.getFullYear();
    currentEditStoryMonth = now.getMonth() + 1;
    try { const modeData = await fetch(`${API_BASE}/stories/mode`).then(r => r.json()); if (modeData.current_month) { currentEditStoryYear = modeData.current_month.year; currentEditStoryMonth = modeData.current_month.month; } } catch(e) {}
    await loadStoryForEdit(cleanKey, currentEditStoryYear, currentEditStoryMonth);
    const modalEl = document.getElementById('editStoryModal');
    if (modalEl) new bootstrap.Modal(modalEl).show();
}

async function loadStoryForEdit(storyKey, year, month) {
    try {
        const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`);
        const story = await storyRes.json();
        
        let monthlyStats = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/month/${year}/${month}`);
            if (monthlyRes.ok) {
                const monthlyData = await monthlyRes.json();
                const foundStory = monthlyData.find(s => s.key === storyKey);
                if (foundStory && foundStory.monthly_stats) {
                    monthlyStats = foundStory.monthly_stats;
                }
            }
        } catch(e) { console.warn('Could not fetch monthly stats:', e); }
        
        document.getElementById('editStoryKey').value = storyKey;
        document.getElementById('editStoryNameDisplay').textContent = story.name || '';
        document.getElementById('editStoryPath').textContent = story.raw_path || story.rel_path || storyKey;
        document.getElementById('editStoryStatus').value = story.status || 'Draft';
        document.getElementById('editStorySeries').textContent = story.series || 'Standalone';
        document.getElementById('editStoryPublishedDate').value = story.published_date || '';
        document.getElementById('editStoryPublication').value = story.medium_publication || '';
        document.getElementById('editStoryMediumUrl').value = story.medium_url || '';
        document.getElementById('editStoryNotes').value = story.notes || '';
        document.getElementById('editStoryTags').value = story.tags?.join(', ') || '';
        document.getElementById('editStoryLifetimeReads').innerHTML = formatNumber(story.lifetime_reads || 0);
        document.getElementById('editStoryLifetimeViews').innerHTML = formatNumber(story.lifetime_views || 0);
        document.getElementById('editStoryLifetimeClaps').innerHTML = formatNumber(story.lifetime_claps || 0);
        document.getElementById('editStoryPresentationCount').innerHTML = formatNumber(story.presentation_count || 0);
        
        const memberReads = monthlyStats.medium_member_reads || monthlyStats.member_reads || 0;
        const totalReads = monthlyStats.reads || 0;
        const memberViews = monthlyStats.medium_member_views || monthlyStats.member_views || 0;
        const totalViews = monthlyStats.view_count || 0;
        const memberReadPercent = calcMemberPercent(memberReads, totalReads);
        const memberViewPercent = calcMemberPercent(memberViews, totalViews);
        const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        document.getElementById('editStoryMemberReads').innerHTML = `${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%`;
        document.getElementById('editStoryMemberViews').innerHTML = `${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%`;
        document.getElementById('editStoryReadRatio').innerHTML = `${readRatio}%`;
        document.getElementById('editStoryMemberPercent').innerHTML = `${memberReadPercent}%`;
        document.getElementById('editStoryReadTimeWordCount').innerHTML = `${story.medium_reading_time || story.read_time || 0} min / ${formatNumber(story.word_count || 0)} words`;
        document.getElementById('editStoryReads').value = totalReads;
        document.getElementById('editStoryViews').value = totalViews;
        document.getElementById('editStoryClaps').value = monthlyStats.claps || 0;
        document.getElementById('editStoryResponses').value = monthlyStats.responses || 0;
        document.getElementById('editStoryNewFollowers').value = monthlyStats.medium_new_followers || 0;
        document.getElementById('editStoryHighlights').value = monthlyStats.medium_highlights || 0;
        document.getElementById('editStoryLeaderboard').value = (monthlyStats.leaderboard || false) ? 'true' : 'false';
        document.getElementById('editStoryLeaderboardNanos').value = monthlyStats.leaderboard_nanos || 0;
        document.getElementById('editStoryLinkedinStatus').value = story.linkedin_status || '';
        document.getElementById('editStoryLinkedinTimestamp').value = story.linkedin_timestamp || '';
        document.getElementById('editStoryLinkedinImpressions').value = story.linkedin_impressions || 0;
        document.getElementById('editStoryLinkedinUrl').value = story.linkedin_url || '';
        document.getElementById('editStoryLastUpdated').textContent = story.last_updated || 'Never';
        updateLinkedinDisplay();
        
        // Update month selector
        const monthSelector = document.getElementById('editStoryMonthSelector');
        if (monthSelector && availableMonths.length) {
            let html = `<select class="form-select form-select-sm" id="editStoryMonthSelect" onchange="onEditStoryMonthChange()" style="background-color: #2c3e50; color: #ecf0f1; border-color: rgba(255,255,255,0.2);">`;
            for (const m of availableMonths) {
                const isSelected = m.year === year && m.month === month;
                html += `<option value="${m.year}-${m.month}" ${isSelected ? 'selected' : ''} style="background-color: #2c3e50; color: #ecf0f1;">${m.display}</option>`;
            }
            html += `</select>`;
            monthSelector.innerHTML = html;
        }
        
        // Update available months list
        const monthsList = document.getElementById('storyAvailableMonthsList');
        if (monthsList && availableMonths.length) {
            let html = '<div class="list-group list-group-flush" style="max-height: 250px; overflow-y: auto;">';
            for (const m of availableMonths) {
                const icon = '○';
                const color = '#6c757d';
                const isActive = m.year === year && m.month === month;
                html += `<div class="list-group-item ${isActive ? 'active' : ''}" style="cursor: pointer; font-size: 0.75rem; padding: 0.3rem 0.5rem; background-color: ${isActive ? '#0d6efd' : 'transparent'};" onclick="switchEditStoryMonth(${m.year}, ${m.month})">
                    <span style="color: ${color};">${icon}</span> ${m.display}
                    ${isActive ? ' <i class="bi bi-check"></i>' : ''}
                </div>`;
            }
            html += '</div>';
            monthsList.innerHTML = html;
        }
    } catch (error) { console.error('Error loading story for edit:', error); alert('Error loading story: ' + error.message); }
}

async function onEditStoryMonthChange() {
    const select = document.getElementById('editStoryMonthSelect');
    if (!select) return;
    const [year, month] = select.value.split('-');
    currentEditStoryYear = parseInt(year);
    currentEditStoryMonth = parseInt(month);
    await loadStoryForEdit(currentEditStoryKey, currentEditStoryYear, currentEditStoryMonth);
}

async function switchEditStoryMonth(year, month) {
    currentEditStoryYear = year;
    currentEditStoryMonth = month;
    await loadStoryForEdit(currentEditStoryKey, year, month);
}

async function saveStoryEdit() {
    let storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) return;
    if (storyKey.toLowerCase().endsWith('.md')) storyKey = storyKey.slice(0, -3);
    
    let targetYear = currentEditStoryYear;
    let targetMonth = currentEditStoryMonth;
    if (!targetYear || !targetMonth) {
        const now = new Date();
        targetYear = now.getFullYear();
        targetMonth = now.getMonth() + 1;
    }
    
    const permanentData = {
        status: document.getElementById('editStoryStatus')?.value || 'Draft',
        published_date: document.getElementById('editStoryPublishedDate')?.value || null,
        tags: document.getElementById('editStoryTags')?.value.split(',').map(t=>t.trim()).filter(t=>t) || [],
        medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
        notes: document.getElementById('editStoryNotes')?.value || '',
        medium_publication: document.getElementById('editStoryPublication')?.value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions')?.value) || 0,
        linkedin_url: document.getElementById('editStoryLinkedinUrl')?.value || null
    };
    
    const monthlyData = {
        reads: parseInt(document.getElementById('editStoryReads')?.value) || 0,
        view_count: parseInt(document.getElementById('editStoryViews')?.value) || 0,
        claps: parseInt(document.getElementById('editStoryClaps')?.value) || 0,
        responses: parseInt(document.getElementById('editStoryResponses')?.value) || 0,
        medium_new_followers: parseInt(document.getElementById('editStoryNewFollowers')?.value) || 0,
        medium_highlights: parseInt(document.getElementById('editStoryHighlights')?.value) || 0,
        leaderboard: document.getElementById('editStoryLeaderboard')?.value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editStoryLeaderboardNanos')?.value) || 0
    };
    
    try {
        const permRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`, { 
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(permanentData) 
        });
        
        if (!permRes.ok) {
            const error = await permRes.json();
            alert('Error saving story: ' + (error.detail || 'Unknown error'));
            return;
        }
        
        const monthlyRes = await fetch(`${API_BASE}/stories/update-story-monthly-stats/${encodeURIComponent(storyKey)}?year=${targetYear}&month=${targetMonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        if (!monthlyRes.ok) {
            console.warn('Failed to save monthly stats');
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
        if (modal) modal.hide();
        
        await loadStories();
        updateLeaderboardTotal();
        alert('Story saved successfully');
        
    } catch (error) {
        console.error('Error saving story:', error);
        alert('Error saving story: ' + error.message);
    }
}

async function ensureStoryInCurrentMonth() {
    if (!currentEditStoryKey || !currentEditStoryYear || !currentEditStoryMonth) {
        alert('Please select a month from the dropdown first.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/ensure-story-in-month?story_key=${encodeURIComponent(currentEditStoryKey)}&year=${currentEditStoryYear}&month=${currentEditStoryMonth}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Story added to current month');
            await loadStoryForEdit(currentEditStoryKey, currentEditStoryYear, currentEditStoryMonth);
        } else {
            const error = await response.json();
            alert('Failed to add story to month: ' + (error.detail || error.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error ensuring story in month:', error);
        alert('Error: ' + error.message);
    }
}

function setEditStoryTodayDate() {
    const el = document.getElementById('editStoryCreatedDate');
    if (el) el.value = getTodayDate();
}

function setEditStoryNowLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) {
        el.value = getNowTimestamp();
        updateLinkedinDisplay();
    }
}

function clearEditStoryLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) {
        el.value = '';
        updateLinkedinDisplay();
    }
}

function clearAllEditStoryLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;
    
    const statusEl = document.getElementById('editStoryLinkedinStatus');
    const timestampEl = document.getElementById('editStoryLinkedinTimestamp');
    const impressionsEl = document.getElementById('editStoryLinkedinImpressions');
    const urlEl = document.getElementById('editStoryLinkedinUrl');
    
    if (statusEl) statusEl.value = '';
    if (timestampEl) timestampEl.value = '';
    if (impressionsEl) impressionsEl.value = '0';
    if (urlEl) urlEl.value = '';
    updateLinkedinDisplay();
}

// ============================================
// LINKEDIN FUNCTIONS
// ============================================

function setNowLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) el.value = getNowTimestamp();
    updateLinkedinDisplay();
}

function clearLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) el.value = '';
    updateLinkedinDisplay();
}

function clearAllLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;
    
    const storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) {
        alert('No story selected');
        return;
    }
    
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    
    const statusEl = document.getElementById('editStoryLinkedinStatus');
    const timestampEl = document.getElementById('editStoryLinkedinTimestamp');
    const impressionsEl = document.getElementById('editStoryLinkedinImpressions');
    const urlEl = document.getElementById('editStoryLinkedinUrl');
    
    if (statusEl) statusEl.value = '';
    if (timestampEl) timestampEl.value = '';
    if (impressionsEl) impressionsEl.value = '0';
    if (urlEl) urlEl.value = '';
    updateLinkedinDisplay();
    
    fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            linkedin_status: null,
            linkedin_timestamp: null,
            linkedin_impressions: 0,
            linkedin_url: null
        })
    }).then(() => {
        loadStories();
    });
}

function onLinkedinStatusChange() {
    const statusEl = document.getElementById('editStoryLinkedinStatus');
    const timestampEl = document.getElementById('editStoryLinkedinTimestamp');
    const status = statusEl?.value || '';
    
    if (status === 'scheduled' || status === 'posted') {
        if (timestampEl && !timestampEl.value) {
            timestampEl.value = getNowTimestamp();
        }
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
        display.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i> Posted ${timestamp ? formatTimestampForDisplay(timestamp) : ''} | Impressions: ${impressions}`;
    } else {
        display.innerHTML = '<i class="bi bi-linkedin"></i> <strong>LinkedIn:</strong> Not posted';
    }
}

// ============================================
// FILTER HELPER FUNCTIONS
// ============================================

function filterStoriesByStatus(status) { 
    if (typeof filterState !== 'undefined') { 
        filterState.status = status === 'all' ? 'All' : status; 
    } 
    loadView('stories'); 
}

function filterStoriesByBookmarked() { 
    if (typeof filterState !== 'undefined') { 
        filterState.bookmarked = true; 
    } 
    loadView('stories'); 
}

function filterStoriesByLeaderboard() { 
    if (typeof filterState !== 'undefined') { 
        filterState.leaderboard = true; 
    } 
    loadView('stories'); 
}

function filterBySeries(seriesName) { 
    if (typeof filterState !== 'undefined') { 
        filterState.series = seriesName; 
        filterState.status = 'All'; 
    } 
    loadView('stories'); 
}

// ============================================
// MAIN LOAD VIEW FUNCTION
// ============================================

async function loadView(view) {
    currentView = view;
    document.getElementById('loading').style.display = 'block';
    document.getElementById('content').innerHTML = '';
    try {
        await loadAllSeries();
        if (view === 'dashboard') await loadDashboard();
        else if (view === 'stories') await loadStories();
        else if (view === 'series') await loadSeries();
        else if (view === 'calendar') await loadCalendar();
        else if (view === 'settings') await loadSettings();
    } catch (error) { document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`; }
    finally { document.getElementById('loading').style.display = 'none'; }
}

// ============================================
// EVENT LISTENERS & INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadLastFetchTime();
    loadView('dashboard');
    loadModeAndMonths();
    setInterval(() => loadModeAndMonths(), 30000);
    
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) loadView(view);
            document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });
    
    // Add Story Modal
    document.getElementById('addStoryCreateBtn')?.addEventListener('click', async () => {
        const name = document.getElementById('addStoryName')?.value;
        if (!name) { alert('Story name required'); return; }
        await fetch(`${API_BASE}/stories/`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ 
                name, 
                series: document.getElementById('addStorySeries')?.value || null, 
                tags: document.getElementById('addStoryTags')?.value.split(',').map(t=>t.trim()), 
                read_time: parseInt(document.getElementById('addStoryReadTime')?.value) || null, 
                created_date: document.getElementById('addStoryCreatedDate')?.value || getTodayDate() 
            }) 
        });
        bootstrap.Modal.getInstance(document.getElementById('addStoryModal'))?.hide();
        await loadView('stories');
    });
    
    document.getElementById('addStorySetTodayBtn')?.addEventListener('click', () => { 
        document.getElementById('addStoryCreatedDate').value = getTodayDate(); 
    });
    
    // Edit Story Modal Buttons
    document.getElementById('editStorySetNowLinkedinBtn')?.addEventListener('click', setEditStoryNowLinkedinTimestamp);
    document.getElementById('editStoryClearLinkedinTimestampBtn')?.addEventListener('click', clearEditStoryLinkedinTimestamp);
    document.getElementById('editStoryClearAllLinkedinBtn')?.addEventListener('click', clearAllEditStoryLinkedinData);
    document.getElementById('editStoryLinkedinStatus')?.addEventListener('change', onLinkedinStatusChange);
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
    document.getElementById('addStoryToCurrentMonthBtn')?.addEventListener('click', ensureStoryInCurrentMonth);
    document.getElementById('updateMonthStatsBtn')?.addEventListener('click', async () => {
        if (!currentEditStoryKey || !currentEditStoryYear || !currentEditStoryMonth) {
            alert('Please select a month first');
            return;
        }
        if (!confirm(`Fetch latest stats from Medium for ${currentEditStoryYear}-${currentEditStoryMonth}?`)) return;
        const btn = document.getElementById('updateMonthStatsBtn');
        const originalText = btn ? btn.innerHTML : 'Updating...';
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
        try {
            const response = await fetch(`${API_BASE}/stories/fetch-lifetime-stats/${encodeURIComponent(currentEditStoryKey)}?year=${currentEditStoryYear}&month=${currentEditStoryMonth}`, { method: 'POST' });
            if (response.ok) {
                await loadStoryForEdit(currentEditStoryKey, currentEditStoryYear, currentEditStoryMonth);
                alert('Stats updated successfully');
            } else alert('Failed to fetch stats');
        } catch (error) { alert('Error: ' + error.message); }
        finally { if (btn) { btn.disabled = false; btn.innerHTML = originalText; } }
    });
    
    // Stats Modal
    document.getElementById('refreshStatsBtn')?.addEventListener('click', refreshStatsForCurrentMonth);
});

document.addEventListener('show.bs.modal', function(event) {
    if (event.target.id === 'addStoryModal') {
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect && allSeries) {
            seriesSelect.innerHTML = '<option value="">Create in root (no series)</option>' + allSeries.map(s => `<option value="${s.name}">📁 ${s.name}</option>`).join('');
        }
        document.getElementById('addStoryCreatedDate').value = getTodayDate();
    }
});



// Make functions globally available
window.loadView = loadView;
window.filterStoriesByStatus = filterStoriesByStatus;
window.filterStoriesByBookmarked = filterStoriesByBookmarked;
window.filterStoriesByLeaderboard = filterStoriesByLeaderboard;
window.filterBySeries = filterBySeries;
window.openEditStory = openEditStory;
window.showStatsDashboard = showStatsDashboard;
window.updateLeaderboardStatsForMonth = updateLeaderboardStatsForMonth;
window.switchToDashboardMode = switchToDashboardMode;
window.switchToMonthMode = switchToMonthMode;
window.generateCalendar = generateCalendar;
window.syncStories = syncStories;
window.importAllLeaderboard = importAllLeaderboard;
window.onEditStoryMonthChange = onEditStoryMonthChange;
window.switchEditStoryMonth = switchEditStoryMonth;
window.ensureStoryInCurrentMonth = ensureStoryInCurrentMonth;
window.saveStoryEdit = saveStoryEdit;
window.toggleBookmark = toggleBookmark;
window.toggleLeaderboard = toggleLeaderboard;
window.deleteStory = deleteStory;
window.markPublished = markPublished;
window.addSeries = addSeries;
window.updateSeriesSpacing = updateSeriesSpacing;
window.deleteSeries = deleteSeries;
window.sortStories = sortStories;
window.sortSeries = sortSeries;
window.sortCalendar = sortCalendar;
window.clearFilters = clearFilters;
window.filterStories = filterStories;
window.saveFilterState = saveFilterState;
window.restoreFilterState = restoreFilterState;
window.setNowLinkedinTimestamp = setNowLinkedinTimestamp;
window.clearLinkedinTimestamp = clearLinkedinTimestamp;
window.clearAllLinkedinData = clearAllLinkedinData;
window.onLinkedinStatusChange = onLinkedinStatusChange;
window.updateLinkedinDisplay = updateLinkedinDisplay;
window.setEditStoryTodayDate = setEditStoryTodayDate;
window.setEditStoryNowLinkedinTimestamp = setEditStoryNowLinkedinTimestamp;
window.clearEditStoryLinkedinTimestamp = clearEditStoryLinkedinTimestamp;
window.clearAllEditStoryLinkedinData = clearAllEditStoryLinkedinData;