// ============================================
// Stats Dashboard Functions
// ============================================

let currentStatsStoryKey = null;
let currentStatsYear = null;
let currentStatsMonth = null;
let currentStatsModal = null;

async function showStatsDashboard(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentStatsStoryKey = cleanKey;
    
    // Get current leaderboard month
    let monthDisplay = '';
    try {
        const monthRes = await fetch(`${API_BASE}/stories/leaderboard-month`);
        const monthData = await monthRes.json();
        if (monthData.leaderboard_month) {
            const [year, month] = monthData.leaderboard_month.split('-');
            currentStatsYear = parseInt(year);
            currentStatsMonth = parseInt(month);
            const date = new Date(currentStatsYear, currentStatsMonth - 1, 1);
            const monthName = date.toLocaleString('default', { month: 'long', year: 'numeric' });
            monthDisplay = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #e3f2fd; font-size: 0.75rem;">
                <i class="bi bi-calendar-month"></i> Stats for: <strong>${monthName}</strong>
            </div>`;
        } else {
            monthDisplay = `<div class="alert alert-warning py-1 px-2 mb-2 text-center" style="background: #fff3cd; font-size: 0.75rem;">
                <i class="bi bi-exclamation-triangle"></i> No leaderboard month loaded
            </div>`;
        }
    } catch (error) {
        console.error('Error getting leaderboard month:', error);
    }
    
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    
    // Store modal instance for later cleanup
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
        // First, get the story from database (already has stats)
        const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`);
        const story = await storyRes.json();
        
        // Display stats from database
        const memberReads = story.medium_member_reads || 0;
        const totalReads = story.reads || 0;
        const memberViews = story.medium_member_views || 0;
        const totalViews = story.view_count || 0;
        const memberReadPercent = calcMemberPercent(memberReads, totalReads);
        const memberViewPercent = calcMemberPercent(memberViews, totalViews);
        const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        let statsMonthDisplay = monthDisplay;
        if (currentStatsYear && currentStatsMonth) {
            const date = new Date(currentStatsYear, currentStatsMonth - 1, 1);
            const monthName = date.toLocaleString('default', { month: 'long', year: 'numeric' });
            statsMonthDisplay = `<div class="alert alert-info py-1 px-2 mb-2 text-center" style="background: #e3f2fd; font-size: 0.75rem;">
                <i class="bi bi-calendar-month"></i> Stats for: <strong>${monthName}</strong>
            </div>`;
        }
        
        contentDiv.innerHTML = `
            ${statsMonthDisplay}
            <div class="compact-stats">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <strong>${escapeHtml(story.name)}</strong>
                    <a href="${escapeHtml(story.medium_url)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-box-arrow-up-right"></i></a>
                </div>
                <div class="row g-1 mb-2">
                    <div class="col-12"><strong><i class="bi bi-calendar-month"></i> Current Month Stats</strong></div>
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
                            <strong>${formatNumber(story.claps || 0)}</strong>
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
                ${story.presentation_count ? `
                <div class="row g-1 mt-2">
                    <div class="col-12">
                        <div class="card bg-secondary text-white p-1 text-center">
                            <small>Presentation Count</small>
                            <strong>${formatNumber(story.presentation_count)}</strong>
                        </div>
                    </div>
                </div>
                ` : ''}
                <div class="text-center mt-2">
                    <small class="text-muted">Read Ratio: ${readRatio}%</small>
                </div>
                <div class="text-center mt-1">
                    <small class="text-muted">Stats updated: ${story.last_stats_update ? story.last_stats_update.split('T')[0] : 'Never'}</small>
                </div>
            </div>
        `;
        
        // Update refresh button
        const refreshBtn = document.getElementById('refreshStatsBtn');
        if (refreshBtn) {
            // Remove any existing event listeners by cloning and replacing
            const newRefreshBtn = refreshBtn.cloneNode(true);
            refreshBtn.parentNode.replaceChild(newRefreshBtn, refreshBtn);
            newRefreshBtn.onclick = () => refreshStatsForCurrentMonth();
        }
        
        // Handle modal close properly
        modalEl.addEventListener('hidden.bs.modal', function() {
            document.body.classList.remove('modal-open');
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true });
        
    } catch (error) {
        contentDiv.innerHTML = `<div class="alert alert-danger m-2">Error: ${error.message}</div>`;
    }
}

async function refreshStatsForCurrentMonth() {
    if (!currentStatsStoryKey) return;
    
    if (!confirm(`Refresh stats from Medium for the loaded leaderboard month?`)) {
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
        
        // Pass the year and month as query parameters
        if (currentStatsYear && currentStatsMonth) {
            url += `?year=${currentStatsYear}&month=${currentStatsMonth}`;
        }
        
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok && data.stats) {
            // Refresh the display with new data
            await showStatsDashboard(currentStatsStoryKey);
            alert(`Stats refreshed successfully for ${data.stats_month_display || 'the loaded month'}`);
        } else {
            alert('Error refreshing stats: ' + (data.error || 'Unknown error'));
            await showStatsDashboard(currentStatsStoryKey);
        }
    } catch (error) {
        alert('Error refreshing stats: ' + error.message);
        await showStatsDashboard(currentStatsStoryKey);
    }
}