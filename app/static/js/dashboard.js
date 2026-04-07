// Dashboard Page - Specific functionality

async function loadDashboard() {
    showLoading();
    try {
        const statsRes = await fetch(`${API_BASE}/dashboard/stats`);
        const stats = await statsRes.json();
        
        // Update stats cards
        document.getElementById('totalCount').textContent = stats.total;
        document.getElementById('publishedCount').textContent = stats.published;
        document.getElementById('readyCount').textContent = stats.ready;
        document.getElementById('doneCount').textContent = stats.done;
        document.getElementById('bookmarkedCount').textContent = stats.bookmarked;
        document.getElementById('leaderboardCount').textContent = stats.leaderboard_count;
        
        document.getElementById('totalReads').innerHTML = `${formatNumber(stats.member_reads)}/${formatNumber(stats.total_reads)}`;
        document.getElementById('memberReadPercent').textContent = `${stats.member_read_percent}% members`;
        document.getElementById('totalViews').innerHTML = `${formatNumber(stats.member_views)}/${formatNumber(stats.total_views)}`;
        document.getElementById('memberViewPercent').textContent = `${stats.member_view_percent || 0}% members`;
        document.getElementById('readRatio').textContent = `${stats.read_ratio}%`;
        document.getElementById('totalClaps').textContent = formatNumber(stats.total_claps);
        
        document.getElementById('leaderboardStoryCount').textContent = stats.leaderboard_count;
        document.getElementById('leaderboardReads').textContent = formatNumber(stats.leaderboard_total_reads);
        document.getElementById('leaderboardClaps').textContent = formatNumber(stats.leaderboard_total_claps);
        
        // Render recent stories
        const recentContainer = document.getElementById('recentStories');
        if (stats.recent_stories && stats.recent_stories.length) {
            recentContainer.innerHTML = stats.recent_stories.map(s => `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <span class="status-badge status-${s.status?.toLowerCase()}">${s.status || 'Draft'}</span>
                        <small>${escapeHtml(s.name.substring(0, 40))}</small>
                        ${s.leaderboard ? ' <i class="bi bi-trophy-fill text-warning"></i>' : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="window.location.href='/stories'">View</button>
                </div>
            `).join('');
        } else {
            recentContainer.innerHTML = '<div class="list-group-item text-muted">No stories found</div>';
        }
        
        // Load schedule
        const scheduleRes = await fetch(`${API_BASE}/dashboard/schedule`);
        const schedule = await scheduleRes.json();
        
        const scheduleContainer = document.getElementById('upcomingSchedule');
        if (schedule.schedule && schedule.schedule.length) {
            scheduleContainer.innerHTML = schedule.schedule.map(s => `
                <div class="list-group-item">
                    <small><strong>${s.date}</strong> - ${escapeHtml(s.name)}</small>
                    ${s.series ? `<span class="series-badge ms-2">${escapeHtml(s.series)}</span>` : ''}
                </div>
            `).join('');
        } else {
            scheduleContainer.innerHTML = '<div class="list-group-item text-muted">No scheduled stories</div>';
        }
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard', 'error');
    } finally {
        hideLoading();
    }
}

function filterStoriesByStatus(status) {
    sessionStorage.setItem('storiesFilterStatus', status);
    window.location.href = '/stories';
}

function filterStoriesByBookmarked() {
    sessionStorage.setItem('storiesFilterBookmarked', 'true');
    window.location.href = '/stories';
}

function filterStoriesByLeaderboard() {
    sessionStorage.setItem('storiesFilterLeaderboard', 'true');
    window.location.href = '/stories';
}

async function updateLeaderboardStatsForMonth() {
    if (!confirm('Update stats for current month?')) return;
    
    const btn = event?.target?.closest('button');
    const originalText = btn ? btn.innerHTML : 'Updating...';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }
    
    try {
        const response = await fetch(`${API_BASE}/stories/update-leaderboard-stats`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            await loadDashboard();
            showToast(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`, 'success');
        } else {
            showToast('Error: ' + (data.detail || data.error), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    }
}

async function syncStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        if (response.ok) {
            showToast('Stories synced successfully', 'success');
            await loadDashboard();
        } else {
            showToast('Error syncing stories', 'error');
        }
    } catch (error) {
        showToast('Error syncing stories: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function generateCalendar() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        if (response.ok) {
            showToast('Calendar generated successfully', 'success');
            await loadDashboard();
        } else {
            showToast('Error generating calendar', 'error');
        }
    } catch (error) {
        showToast('Error generating calendar: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', loadDashboard);