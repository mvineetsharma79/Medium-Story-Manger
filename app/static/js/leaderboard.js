// ============================================
// Leaderboard Functions
// ============================================

async function loadLeaderboardFileList() {
    const container = document.getElementById('leaderboardFileList');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE}/stories/leaderboard-files`);
        const data = await response.json();
        
        if (data.error || !data.leaderboard_files || data.leaderboard_files.length === 0) {
            container.innerHTML = `<div class="text-muted small text-center py-1"><i class="bi bi-info-circle"></i> No files</div>`;
            return;
        }
        
        let html = '';
        data.leaderboard_files.forEach(month => {
            html += `<div class="leaderboard-file-item p-1 mb-1" style="background: rgba(255,255,255,0.04);">
                <div class="d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-calendar-month"></i> <strong>${month.display_name}</strong> <span class="text-muted">(${month.files.length})</span></div>
                    <button class="btn btn-sm btn-warning py-0 px-1" onclick="fetchLeaderboardForMonth(${month.year}, ${month.month}, '${month.display_name}')" style="font-size: 0.6rem;"><i class="bi bi-cloud-download"></i></button>
                </div>
            </div>`;
        });
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="text-danger small text-center">Error</div>`;
    }
}

async function fetchLeaderboardForMonth(year, month, displayName) {
    if (!confirm(`Fetch leaderboard data for ${displayName}?`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-leaderboard-for-month`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year, month })
        });
        const data = await response.json();
        
        if (response.ok && !data.error) {
            // Also set the leaderboard month in the backend
            await fetch(`${API_BASE}/stories/leaderboard-month?year=${year}&month=${month}`, { method: 'POST' });
            
            // Reload the month display
            if (typeof loadLeaderboardMonth === 'function') await loadLeaderboardMonth();
            
            if (typeof saveFilterState === 'function') saveFilterState();
            if (typeof loadView === 'function') await loadView(window.currentView);
            if (typeof restoreFilterState === 'function') restoreFilterState();
            if (typeof updateLeaderboardTotal === 'function') updateLeaderboardTotal();
            await loadLeaderboardFileList();
            
            alert(`✅ ${displayName}: ${data.updated || 0} updated, ${data.added || 0} added\nTotal: $${(data.total_dollars || 0).toFixed(2)}`);
        } else {
            alert(`Error: ${data.error || data.message || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}