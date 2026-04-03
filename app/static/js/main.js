// ============================================
// Main Application
// ============================================

const API_BASE = '/api';
window.currentView = 'dashboard';
window.allStories = [];
window.allSeries = [];

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
    document.getElementById('setNowLinkedinBtn')?.addEventListener('click', setNowLinkedinTimestamp);
    document.getElementById('clearLinkedinTimestampBtn')?.addEventListener('click', clearLinkedinTimestamp);
    document.getElementById('clearAllLinkedinBtn')?.addEventListener('click', clearAllLinkedinData);
    document.getElementById('editStoryLinkedinStatus')?.addEventListener('change', onLinkedinStatusChange);
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
    document.getElementById('refreshStatsBtn')?.addEventListener('click', () => {
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
        document.getElementById('addStoryCreatedDate').value = getTodayDate();
    }
});