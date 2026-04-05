// ============================================
// Monthly Mode Functions
// ============================================

let currentMode = 'dashboard';
let currentMonthYear = null;
let currentMonthDisplay = null;
let availableMonths = [];

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
    
    let html = `
        <div class="dropdown">
            <button class="btn btn-sm btn-outline-secondary w-100 dropdown-toggle" type="button" data-bs-toggle="dropdown" style="font-size: 0.7rem;">
                <i class="bi bi-calendar-month"></i> ${currentMonthDisplay || 'Select Month'}
            </button>
            <ul class="dropdown-menu w-100" style="min-width: 200px;">
                <li><a class="dropdown-item ${currentMode === 'dashboard' ? 'active bg-primary text-white' : ''}" href="#" onclick="switchToDashboardMode(); return false;">
                    <i class="bi bi-speedometer2"></i> Dashboard (All Stories)
                </a></li>
                <li><hr class="dropdown-divider"></li>
    `;
    
    for (const month of availableMonths) {
        const isActive = currentMode === 'month' && 
                         currentMonthYear?.year === month.year && 
                         currentMonthYear?.month === month.month;
        html += `
            <li><a class="dropdown-item ${isActive ? 'active bg-primary text-white' : ''}" href="#" onclick="switchToMonthMode(${month.year}, ${month.month}); return false;">
                <i class="bi bi-calendar-month"></i> ${month.display}
                ${isActive ? ' <i class="bi bi-check"></i>' : ''}
            </a></li>
        `;
    }
    
    html += `</ul></div>`;
    container.innerHTML = html;
}

function updateModeIndicator() {
    const indicator = document.getElementById('currentModeIndicator');
    if (!indicator) return;
    
    if (currentMode === 'dashboard') {
        indicator.innerHTML = `
            <div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #0f3460; border: none; font-size: 0.7rem;">
                <i class="bi bi-speedometer2"></i> Mode: <strong>Dashboard</strong> (All Stories)
                <br><small class="text-muted">Showing current month stats</small>
            </div>
        `;
        currentMonthDisplay = 'Dashboard';
    } else if (currentMonthYear) {
        const monthName = new Date(currentMonthYear.year, currentMonthYear.month - 1, 1)
            .toLocaleString('default', { month: 'long', year: 'numeric' });
        currentMonthDisplay = monthName;
        indicator.innerHTML = `
            <div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #0f3460; border: none; font-size: 0.7rem;">
                <i class="bi bi-calendar-month"></i> Mode: <strong>Month View</strong>
                <br>Showing: <strong>${monthName}</strong>
            </div>
        `;
    }
}

async function switchToDashboardMode() {
    if (!confirm('Switch to Dashboard mode? This will show all stories with current month stats.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/switch-to-dashboard`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            currentMode = 'dashboard';
            currentMonthDisplay = 'Dashboard';
            updateModeIndicator();
            updateSidebarMonthSelector();
            await loadStories();
            alert('Switched to Dashboard mode');
        } else {
            alert('Error switching mode: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error switching mode:', error);
        alert('Error switching mode: ' + error.message);
    }
}

async function switchToMonthMode(year, month) {
    const monthName = new Date(year, month - 1, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
    if (!confirm(`Switch to ${monthName}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/switch-month?year=${year}&month=${month}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            currentMode = 'month';
            currentMonthYear = { year, month };
            updateModeIndicator();
            updateSidebarMonthSelector();
            await loadStoriesForMonth(year, month);
            alert(`Switched to ${data.display}`);
        } else {
            alert('Error switching month: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error switching month:', error);
        alert('Error switching month: ' + error.message);
    }
}

async function loadStoriesForMonth(year, month) {
    try {
        const response = await fetch(`${API_BASE}/stories/?year=${year}&month=${month}`);
        const stories = await response.json();
        window.allStories = Array.isArray(stories) ? stories : [];
        if (typeof renderStoryTable === 'function') {
            renderStoryTable(window.allStories);
        }
        return window.allStories;
    } catch (error) {
        console.error('Error loading stories for month:', error);
        return [];
    }
}

async function updateLeaderboardStatsForMonth() {
    if (currentMode === 'dashboard') {
        if (!confirm('Update stats for current month? This will fetch fresh stats from Medium API for all leaderboard stories.')) {
            return;
        }
    } else if (!currentMonthYear) {
        alert('Please select a month from the sidebar first');
        return;
    }
    
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Updating...';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }
    
    try {
        let url = `${API_BASE}/stories/update-leaderboard-stats`;
        if (currentMode === 'month' && currentMonthYear) {
            url += `?year=${currentMonthYear.year}&month=${currentMonthYear.month}`;
        }
        
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            if (currentMode === 'month' && currentMonthYear) {
                await loadStoriesForMonth(currentMonthYear.year, currentMonthYear.month);
            } else {
                await loadStories();
            }
            updateLeaderboardTotal();
            alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
        } else {
            alert('Error: ' + (data.detail || data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error updating stats: ' + error.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// Make functions globally available
window.loadModeAndMonths = loadModeAndMonths;
window.switchToDashboardMode = switchToDashboardMode;
window.switchToMonthMode = switchToMonthMode;
window.loadStoriesForMonth = loadStoriesForMonth;
window.updateLeaderboardStatsForMonth = updateLeaderboardStatsForMonth;
window.availableMonths = availableMonths;