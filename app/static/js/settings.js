// ============================================
// Settings Functions
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
                        <div class="card-header">
                            <h6>Calendar Settings</h6>
                        </div>
                        <div class="card-body">
                            <form id="calendarSettingsForm">
                                <div class="mb-2">
                                    <label>Series Spacing (days)</label>
                                    <input type="number" class="form-control form-control-sm" name="series_spacing_days" 
                                           value="${settings.series_spacing_days || 7}" min="5" max="14">
                                </div>
                                <div class="mb-2">
                                    <label>Stories Per Week</label>
                                    <input type="number" class="form-control form-control-sm" name="stories_per_week" 
                                           value="${settings.stories_per_week || 3}" min="1" max="7">
                                </div>
                                <div class="mb-2">
                                    <label>Preferred Publish Days</label>
                                    <div class="d-flex gap-2 flex-wrap">
                                        ${['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => `
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="preferred_days" value="${day}" 
                                                       ${settings.preferred_publish_days?.includes(day) ? 'checked' : ''}>
                                                <label class="form-check-label small">${day.slice(0, 3)}</label>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                                <div class="mb-2">
                                    <label>Start Date</label>
                                    <input type="date" class="form-control form-control-sm" name="start_date" 
                                           value="${settings.start_date || ''}">
                                </div>
                                <button type="submit" class="btn btn-sm btn-primary">Save Settings</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6>System</h6>
                        </div>
                        <div class="card-body">
                            <p><strong>Stories Root:</strong> ${root.stories_root}</p>
                            <p><strong>Data Directory:</strong> ${settings.data_dir || './data'}</p>
                            <hr>
                            <button class="btn btn-sm btn-primary" onclick="syncStories()">
                                <i class="bi bi-arrow-repeat"></i> Sync Files
                            </button>
                            <button class="btn btn-sm btn-secondary ms-2" onclick="generateCalendar()">
                                <i class="bi bi-calendar"></i> Generate Calendar
                            </button>
                            <hr>
                            <button class="btn btn-sm btn-danger" onclick="clearAllLeaderboardFlags()">
                                <i class="bi bi-trash"></i> Clear All Leaderboard Flags
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const form = document.getElementById('calendarSettingsForm');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fd = new FormData(e.target);
                const data = {
                    series_spacing_days: parseInt(fd.get('series_spacing_days')),
                    stories_per_week: parseInt(fd.get('stories_per_week')),
                    preferred_publish_days: fd.getAll('preferred_days'),
                    start_date: fd.get('start_date')
                };
                
                try {
                    const res = await fetch(`${API_BASE}/settings/calendar`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    if (res.ok) {
                        alert('Settings saved successfully');
                        loadSettings();
                    } else {
                        const error = await res.json();
                        alert('Error saving settings: ' + (error.detail || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error saving settings:', error);
                    alert('Error saving settings: ' + error.message);
                }
            });
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading settings: ${error.message}</div>`;
    }
}

async function clearAllLeaderboardFlags() {
    if (!confirm('Are you sure you want to clear ALL leaderboard flags from ALL months?\n\nThis action cannot be undone.')) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/stories/clear-leaderboard`, { method: 'POST' });
        if (res.ok) {
            alert('All leaderboard flags cleared successfully');
            if (typeof loadView === 'function') {
                await loadView(window.currentView);
            }
        } else {
            const error = await res.json();
            alert('Error clearing leaderboard flags: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error clearing leaderboard flags:', error);
        alert('Error clearing leaderboard flags: ' + error.message);
    }
}

// Make functions globally available
window.loadSettings = loadSettings;
window.clearAllLeaderboardFlags = clearAllLeaderboardFlags;