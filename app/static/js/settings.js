// Settings Page - Specific functionality

async function loadSettings() {
    showLoading();
    try {
        const [settingsRes, rootRes] = await Promise.all([
            fetch(`${API_BASE}/settings/`),
            fetch(`${API_BASE}/settings/stories-root`)
        ]);
        
        const settings = await settingsRes.json();
        const root = await rootRes.json();
        
        document.getElementById('seriesSpacingDays').value = settings.series_spacing_days || 7;
        document.getElementById('storiesPerWeek').value = settings.stories_per_week || 3;
        document.getElementById('startDate').value = settings.start_date || '';
        document.getElementById('storiesRoot').textContent = root.stories_root;
        document.getElementById('dataDir').textContent = root.data_dir || './data';
        
        // Render preferred days checkboxes
        const preferredDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const savedDays = settings.preferred_publish_days || ['Monday', 'Tuesday', 'Wednesday', 'Thursday'];
        
        const container = document.getElementById('preferredDays');
        container.innerHTML = '';
        preferredDays.forEach(day => {
            const div = document.createElement('div');
            div.className = 'form-check';
            
            const input = document.createElement('input');
            input.className = 'form-check-input';
            input.type = 'checkbox';
            input.value = day;
            input.id = `day_${day}`;
            input.checked = savedDays.includes(day);
            
            const label = document.createElement('label');
            label.className = 'form-check-label small';
            label.htmlFor = `day_${day}`;
            label.textContent = day.slice(0, 3);
            
            div.appendChild(input);
            div.appendChild(label);
            container.appendChild(div);
        });
        
    } catch (error) {
        console.error('Error loading settings:', error);
        showToast('Error loading settings', 'error');
    } finally {
        hideLoading();
    }
}

async function saveSettings() {
    showLoading();
    try {
        const preferredDays = Array.from(document.querySelectorAll('#preferredDays input:checked'))
            .map(cb => cb.value);
        
        const data = {
            series_spacing_days: parseInt(document.getElementById('seriesSpacingDays').value),
            stories_per_week: parseInt(document.getElementById('storiesPerWeek').value),
            preferred_publish_days: preferredDays,
            start_date: document.getElementById('startDate').value || null
        };
        
        const response = await fetch(`${API_BASE}/settings/calendar`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showToast('Settings saved', 'success');
        } else {
            showToast('Error saving settings', 'error');
        }
    } catch (error) {
        showToast('Error saving settings', 'error');
    } finally {
        hideLoading();
    }
}

async function syncStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        if (response.ok) {
            showToast('Stories synced', 'success');
        } else {
            showToast('Error syncing stories', 'error');
        }
    } catch (error) {
        showToast('Error syncing stories', 'error');
    } finally {
        hideLoading();
    }
}

async function generateCalendar() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        if (response.ok) {
            showToast('Calendar generated', 'success');
        } else {
            showToast('Error generating calendar', 'error');
        }
    } catch (error) {
        showToast('Error generating calendar', 'error');
    } finally {
        hideLoading();
    }
}

async function importAllLeaderboard() {
    if (!confirm('⚠️ WARNING: This will OVERWRITE all monthly data with values from leaderboard JSON files.\n\nThis action cannot be undone. Continue?')) return;
    
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Importing...';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Importing...'; }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/import-all-leaderboard`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Import complete: ${data.months_imported} months, ${data.total_stories} stories`, 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showToast('Error: ' + (data.error || data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error importing leaderboard:', error);
        showToast('Error importing leaderboard data: ' + error.message, 'error');
    } finally {
        hideLoading();
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    document.getElementById('calendarSettingsForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        saveSettings();
    });
});

// Add to settings.js

async function refreshStats() {
    const period = getCurrentYearMonth();
    if (!confirm(`Refresh stats from Medium for ${period}?`)) return;
    
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Refreshing...';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/refresh-stats/${period}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast(`Stats refreshed: ${data.new_stories} new, ${data.updated_stories} updated`, 'success');
        } else {
            showToast('Error: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}


window.refreshStats = refreshStats;