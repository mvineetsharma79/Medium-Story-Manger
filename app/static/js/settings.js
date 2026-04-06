// ============================================
// SETTINGS PAGE - API calls and rendering only
// ============================================

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
        document.getElementById('dataDir').textContent = settings.data_dir || './data';
        
        // Render preferred days checkboxes
        const preferredDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const savedDays = settings.preferred_publish_days || ['Monday', 'Tuesday', 'Wednesday', 'Thursday'];
        
        const container = document.getElementById('preferredDays');
        container.innerHTML = preferredDays.map(day => `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${day}" id="day_${day}" 
                       ${savedDays.includes(day) ? 'checked' : ''}>
                <label class="form-check-label small" for="day_${day}">${day.slice(0,3)}</label>
            </div>
        `).join('');
        
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
        
        await fetch(`${API_BASE}/settings/calendar`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        showToast('Settings saved', 'success');
    } catch (error) {
        showToast('Error saving settings', 'error');
    } finally {
        hideLoading();
    }
}

async function syncStories() {
    showLoading();
    try {
        await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        showToast('Stories synced', 'success');
    } catch (error) {
        showToast('Error syncing stories', 'error');
    } finally {
        hideLoading();
    }
}

async function generateCalendar() {
    showLoading();
    try {
        await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        showToast('Calendar generated', 'success');
    } catch (error) {
        showToast('Error generating calendar', 'error');
    } finally {
        hideLoading();
    }
}

async function importAllLeaderboard() {
    if (!confirm('⚠️ WARNING: This will OVERWRITE all monthly data. Continue?')) return;
    
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/stories/import-all-leaderboard`, { method: 'POST' });
        const data = await res.json();
        showToast(`Import complete: ${data.months_imported} months, ${data.total_stories} stories`, 'success');
    } catch (error) {
        showToast('Error importing leaderboard data', 'error');
    } finally {
        hideLoading();
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