// ============================================
// Stats Dashboard Functions
// ============================================

let currentStatsStoryKey = null;
let currentStatsYear = null;
let currentStatsMonth = null;
let currentStatsModal = null;

async function showStatsDashboard(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentStatsStoryKey = cleanKey;
    
    // Get current mode and month
    let monthDisplay = '';
    let targetYear = null;
    let targetMonth = null;
    
    try {
        const modeRes = await fetch(`${API_BASE}/stories/mode`);
        const modeData = await modeRes.json();
        
        if (modeData.mode === 'month' && modeData.current_month) {
            targetYear = modeData.current_month.year;
            targetMonth = modeData.current_month.month;
            const date = new Date(targetYear, targetMonth - 1, 1);
            const monthName = date.toLocaleString('default', { month: 'long', year: 'numeric' });
            monthDisplay = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #e3f2fd; font-size: 0.75rem;">
                <i class="bi bi-calendar-month"></i> Stats for: <strong>${monthName}</strong>
            </div>`;
        } else {
            const now = new Date();
            targetYear = now.getFullYear();
            targetMonth = now.getMonth() + 1;
            const monthName = now.toLocaleString('default', { month: 'long', year: 'numeric' });
            monthDisplay = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #e3f2fd; font-size: 0.75rem;">
                <i class="bi bi-calendar-month"></i> Stats for: <strong>${monthName}</strong> (Current Month)
            </div>`;
        }
        currentStatsYear = targetYear;
        currentStatsMonth = targetMonth;
    } catch (error) {
        console.error('Error getting mode:', error);
        const now = new Date();
        targetYear = now.getFullYear();
        targetMonth = now.getMonth() + 1;
        currentStatsYear = targetYear;
        currentStatsMonth = targetMonth;
    }
    
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    
    currentStatsModal = new bootstrap.Modal(modalEl);
    
    contentDiv.innerHTML = `
        ${monthDisplay}
        <div class="text-center py-3">
            <div class="spinner-border text-primary"></div>
            <p class="mt-2">Loading stats from database...</p>
        </div>
    `;
    currentStatsModal.show();
    
    try {
        const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`);
        const story = await storyRes.json();
        
        let monthlyStats = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/stats-by-url?medium_url=${encodeURIComponent(story.medium_url || '')}`);
            if (monthlyRes.ok) {
                const monthlyData = await monthlyRes.json();
                monthlyStats = monthlyData.current_month || {};
            }
        } catch (e) {
            console.warn('Could not fetch monthly stats:', e);
        }
        
        const memberReads = monthlyStats.member_reads || 0;
        const totalReads = monthlyStats.reads || 0;
        const memberViews = monthlyStats.member_views || 0;
        const totalViews = monthlyStats.views || 0;
        const memberReadPercent = totalReads > 0 ? Math.round((memberReads / totalReads) * 100) : 0;
        const memberViewPercent = totalViews > 0 ? Math.round((memberViews / totalViews) * 100) : 0;
        const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        contentDiv.innerHTML = `
            ${monthDisplay}
            <div class="compact-stats">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${escapeHtml(story.name)}</strong>
                    <a href="${escapeHtml(story.medium_url)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-box-arrow-up-right"></i></a>
                </div>
                <div class="row g-1 mb-2">
                    <div class="col-12"><strong><i class="bi bi-calendar-month"></i> Monthly Stats</strong></div>
                </div>
                <div class="row g-1 mb-2">
                    <div class="col-4">
                        <div class="card bg-light p-1 text-center">
                            <small>Reads</small>
                            <strong>${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%</strong>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="card bg-light p-1 text-center">
                            <small>Views</small>
                            <strong>${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%</strong>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="card bg-light p-1 text-center">
                            <small>Claps</small>
                            <strong>${formatNumber(monthlyStats.claps || 0)}</strong>
                        </div>
                    </div>
                </div>
                <div class="row g-1 mb-2">
                    <div class="col-12"><strong><i class="bi bi-infinity"></i> Lifetime Stats</strong></div>
                </div>
                <div class="row g-1">
                    <div class="col-4">
                        <div class="card" style="background:#6f42c1;color:white;">
                            <div class="card-body p-1 text-center">
                                <small>Reads</small><br>
                                <strong>${formatNumber(story.lifetime_reads || 0)}</strong>
                            </div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="card" style="background:#fd7e14;color:white;">
                            <div class="card-body p-1 text-center">
                                <small>Claps</small><br>
                                <strong>${formatNumber(story.lifetime_claps || 0)}</strong>
                            </div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="card" style="background:#20c997;color:white;">
                            <div class="card-body p-1 text-center">
                                <small>Views</small><br>
                                <strong>${formatNumber(story.lifetime_views || 0)}</strong>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="text-center mt-2">
                    <small class="text-muted">Read Ratio: ${readRatio}%</small>
                </div>
                <div class="text-center mt-1">
                    <small class="text-muted">Stats updated: ${monthlyStats.last_stats_update ? monthlyStats.last_stats_update.split('T')[0] : story.last_stats_update?.split('T')[0] || 'Never'}</small>
                </div>
            </div>
        `;
        
        const refreshBtn = document.getElementById('refreshStatsBtn');
        if (refreshBtn) {
            const newRefreshBtn = refreshBtn.cloneNode(true);
            refreshBtn.parentNode.replaceChild(newRefreshBtn, refreshBtn);
            newRefreshBtn.onclick = () => refreshStatsForCurrentMonth();
        }
        
        modalEl.addEventListener('hidden.bs.modal', function() {
            document.body.classList.remove('modal-open');
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true });
        
    } catch (error) {
        console.error('Error loading stats:', error);
        contentDiv.innerHTML = `<div class="alert alert-danger m-2">Error loading stats: ${error.message}</div>`;
    }
}

async function refreshStatsForCurrentMonth() {
    if (!currentStatsStoryKey) return;
    
    if (!confirm(`Refresh stats from Medium for the current month?`)) {
        return;
    }
    
    const contentDiv = document.getElementById('statsDashboardContent');
    if (contentDiv) {
        contentDiv.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Fetching fresh stats from Medium...</p>
            </div>
        `;
    }
    
    try {
        let url = `${API_BASE}/stories/fetch-lifetime-stats/${encodeURIComponent(currentStatsStoryKey)}`;
        
        if (currentStatsYear && currentStatsMonth) {
            url += `?year=${currentStatsYear}&month=${currentStatsMonth}`;
        }
        
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok && data.stats) {
            await showStatsDashboard(currentStatsStoryKey);
            alert(`Stats refreshed successfully`);
        } else {
            alert('Error refreshing stats: ' + (data.error || 'Unknown error'));
            await showStatsDashboard(currentStatsStoryKey);
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
        alert('Error refreshing stats: ' + error.message);
        await showStatsDashboard(currentStatsStoryKey);
    }
}

// Make functions globally available
window.showStatsDashboard = showStatsDashboard;
window.refreshStatsForCurrentMonth = refreshStatsForCurrentMonth;