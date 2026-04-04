// ============================================
// Main Application - Entry Point
// ============================================

// Global variables
window.API_BASE = '/api';
window.currentView = 'dashboard';
window.allStories = [];
window.allSeries = [];
window.currentStatsStoryKey = null;

// Main load function
async function loadView(view) {
    window.currentView = view;
    const loadingDiv = document.getElementById('loading');
    const contentDiv = document.getElementById('content');
    
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (contentDiv) contentDiv.innerHTML = '';
    
    try {
        await loadAllSeries();
        
        if (view === 'dashboard') await loadDashboard();
        else if (view === 'stories') await loadStories();
        else if (view === 'series') await loadSeries();
        else if (view === 'calendar') await loadCalendar();
        else if (view === 'settings') await loadSettings();
    } catch (error) {
        console.error('Load view error:', error);
        if (contentDiv) contentDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    } finally {
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadLastFetchTime();
    loadView('dashboard');
    loadLeaderboardFileList();
    loadLeaderboardMonth();  // Add this line
    setInterval(loadLeaderboardFileList, 30000);
    
    // Sidebar navigation
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) loadView(view);
            document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });
    
    // Modal event handlers
    const setNowBtn = document.getElementById('setNowLinkedinBtn');
    const clearTimestampBtn = document.getElementById('clearLinkedinTimestampBtn');
    const clearAllBtn = document.getElementById('clearAllLinkedinBtn');
    const linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    const saveBtn = document.getElementById('saveStoryEditBtn');
    const refreshStatsBtn = document.getElementById('refreshStatsBtn');
    
    if (setNowBtn) setNowBtn.addEventListener('click', setNowLinkedinTimestamp);
    if (clearTimestampBtn) clearTimestampBtn.addEventListener('click', clearLinkedinTimestamp);
    if (clearAllBtn) clearAllBtn.addEventListener('click', clearAllLinkedinData);
    if (linkedinStatus) linkedinStatus.addEventListener('change', onLinkedinStatusChange);
    if (saveBtn) saveBtn.addEventListener('click', saveStoryEdit);
    if (refreshStatsBtn) refreshStatsBtn.addEventListener('click', () => {
        if (window.currentStatsStoryKey) showStatsDashboard(window.currentStatsStoryKey);
    });
});

// Add Story Modal handler
document.addEventListener('show.bs.modal', function(event) {
    if (event.target.id === 'addStoryModal') {
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect && window.allSeries.length) {
            seriesSelect.innerHTML = '<option value="">Create in root (no series)</option>' + 
                window.allSeries.map(s => `<option value="${s.name}">📁 ${s.name}</option>`).join('');
        }
        const createdDateEl = document.getElementById('addStoryCreatedDate');
        if (createdDateEl) createdDateEl.value = getTodayDate();
    }
});

// Helper function to load all series (used by multiple views)
async function loadAllSeries() {
    const res = await fetch(`${window.API_BASE}/series/`);
    window.allSeries = await res.json();
}

// ============================================
// Leaderboard Month Display
// ============================================

let currentLeaderboardMonth = null;

async function loadLeaderboardMonth() {
    try {
        const response = await fetch(`${API_BASE}/stories/leaderboard-month`);
        const data = await response.json();
        
        const monthContainer = document.getElementById('leaderboardMonthContainer');
        const monthDisplay = document.getElementById('leaderboardMonthDisplay');
        
        if (monthContainer && monthDisplay) {
            if (data.leaderboard_month) {
                currentLeaderboardMonth = data.leaderboard_month;
                const [year, month] = data.leaderboard_month.split('-');
                const date = new Date(parseInt(year), parseInt(month) - 1, 1);
                const monthName = date.toLocaleString('default', { month: 'long', year: 'numeric' });
                
                monthDisplay.innerHTML = `<i class="bi bi-calendar-month"></i> <strong>${monthName}</strong>`;
                monthContainer.style.display = 'block';
            } else {
                monthDisplay.innerHTML = `<i class="bi bi-calendar-month"></i> No month loaded`;
                monthContainer.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error loading leaderboard month:', error);
    }
}

async function updateLeaderboardStats() {
    if (!confirm('Fetch stats for the loaded leaderboard month?\n\nThis will update stats from Medium API.')) {
        return;
    }
    
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }
    
    try {
        const res = await fetch(`${API_BASE}/stories/update-leaderboard-stats`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok) {
            if (typeof saveFilterState === 'function') saveFilterState();
            if (typeof loadView === 'function') await loadView(window.currentView);
            if (typeof restoreFilterState === 'function') restoreFilterState();
            if (typeof updateLeaderboardTotal === 'function') updateLeaderboardTotal();
            
            await loadLeaderboardMonth();
            
            alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
        } else {
            alert('Error: ' + (data.detail || data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error updating leaderboard stats: ' + error.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}