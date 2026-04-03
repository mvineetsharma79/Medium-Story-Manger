// ============================================
// Dashboard Functions
// ============================================

async function loadDashboard() {
    const res = await fetch(`${API_BASE}/stories/`);
    const stories = await res.json();
    window.allStories = stories;
    
    const published = stories.filter(s => s.status === 'Published').length;
    const draft = stories.filter(s => s.status === 'Draft').length;
    const ready = stories.filter(s => s.status === 'Ready').length;
    const done = stories.filter(s => s.status === 'Done').length;
    const bookmarked = stories.filter(s => s.bookmarked === true).length;
    const leaderboard = stories.filter(s => s.leaderboard === true).length;
    
    const totalMemberReads = stories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
    const totalReads = stories.reduce((sum, s) => sum + (s.reads || 0), 0);
    const totalMemberViews = stories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
    const totalViews = stories.reduce((sum, s) => sum + (s.view_count || 0), 0);
    const totalClaps = stories.reduce((sum, s) => sum + (s.claps || 0), 0);
    
    const totalMemberReadPercent = calcMemberPercent(totalMemberReads, totalReads);
    const totalMemberViewPercent = calcMemberPercent(totalMemberViews, totalViews);
    const totalReadRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
    
    const leaderboardStories = stories.filter(s => s.leaderboard === true);
    const leaderboardMemberReads = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
    const leaderboardTotalReads = leaderboardStories.reduce((sum, s) => sum + (s.reads || 0), 0);
    const leaderboardMemberViews = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
    const leaderboardTotalViews = leaderboardStories.reduce((sum, s) => sum + (s.view_count || 0), 0);
    const leaderboardClaps = leaderboardStories.reduce((sum, s) => sum + (s.claps || 0), 0);
    const leaderboardMemberReadPercent = calcMemberPercent(leaderboardMemberReads, leaderboardTotalReads);
    
    const calendarRes = await fetch(`${API_BASE}/calendar/`);
    const calendar = await calendarRes.json();
    
    document.getElementById('content').innerHTML = `
        <h1 class="h3 mb-3">Dashboard</h1>
        <div class="row g-2 mb-3">
            <div class="col-md-2"><div class="card stat-card bg-primary text-white" onclick="filterStoriesByStatus('all')"><div class="card-body"><h6>Total</h6><h2>${stories.length}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-success text-white" onclick="filterStoriesByStatus('Published')"><div class="card-body"><h6>Published</h6><h2>${published}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-info text-white" onclick="filterStoriesByStatus('Ready')"><div class="card-body"><h6>Ready</h6><h2>${ready}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card bg-secondary text-white" onclick="filterStoriesByStatus('Done')"><div class="card-body"><h6>Done</h6><h2>${done}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card" style="background:#ffc107;color:#000;" onclick="filterStoriesByBookmarked()"><div class="card-body"><h6>Bookmarked</h6><h2>${bookmarked}</h2></div></div></div>
            <div class="col-md-2"><div class="card stat-card" style="background:#ffd700;color:#000;" onclick="filterStoriesByLeaderboard()"><div class="card-body"><h6>Leaderboard</h6><h2>${leaderboard}</h2></div></div></div>
        </div>
        <div class="row g-2 mb-3">
            <div class="col-md-3"><div class="card mini-stat-card bg-info text-white"><div class="card-body"><h6>All Reads</h6><h2>${formatNumber(totalMemberReads)}/${formatNumber(totalReads)} - ${totalMemberReadPercent}%</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-primary text-white"><div class="card-body"><h6>All Views</h6><h2>${formatNumber(totalMemberViews)}/${formatNumber(totalViews)} - ${totalMemberViewPercent}%</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-warning text-white"><div class="card-body"><h6>Read Ratio</h6><h2>${totalReadRatio}%</h2></div></div></div>
            <div class="col-md-3"><div class="card mini-stat-card bg-success text-white"><div class="card-body"><h6>Total Claps</h6><h2>${formatNumber(totalClaps)}</h2></div></div></div>
        </div>
        <div class="row mb-3">
            <div class="col-12">
                <div class="card leaderboard-section" style="border:1px solid #ffd700;background:#fff8e7;">
                    <div class="card-header py-1" style="background:#ffd700;color:#000;">
                        <small><i class="bi bi-trophy"></i> <strong>Leaderboard</strong> (${leaderboardStories.length} stories)
                            <button class="btn btn-sm btn-primary py-0 px-2 ms-2" onclick="updateLeaderboardStats()" style="font-size:0.7rem;"><i class="bi bi-arrow-repeat"></i> Update Stats</button>
                        </small>
                    </div>
                    <div class="card-body py-1">
                        <div class="row g-1">
                            <div class="col-md-4"><div class="bg-info text-white p-1 rounded text-center"><small>Reads</small><br><strong>${formatNumber(leaderboardMemberReads)}/${formatNumber(leaderboardTotalReads)} - ${leaderboardMemberReadPercent}%</strong></div></div>
                            <div class="col-md-4"><div class="bg-primary text-white p-1 rounded text-center"><small>Views</small><br><strong>${formatNumber(leaderboardMemberViews)}/${formatNumber(leaderboardTotalViews)}</strong></div></div>
                            <div class="col-md-4"><div class="bg-warning text-white p-1 rounded text-center"><small>Claps</small><br><strong>${formatNumber(leaderboardClaps)}</strong></div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6"><div class="card"><div class="card-header py-1"><small>Recent Stories</small><button class="btn btn-sm btn-primary float-end py-0" onclick="loadView('stories')">View All</button></div>
            <div class="card-body p-0"><div class="list-group list-group-flush">${stories.slice(0,8).map(s => `<div class="list-group-item py-1 d-flex justify-content-between align-items-center"><div><span class="status-badge ${s.status==='Published'?'status-published':s.status==='Ready'?'status-ready':s.status==='Done'?'status-done':'status-draft'}">${s.status}</span> <small>${escapeHtml(s.name.substring(0,40))}</small>${s.leaderboard?' <i class="bi bi-trophy-fill text-warning"></i>':''}</div><button class="btn btn-sm btn-outline-primary py-0" onclick="editStory('${s.key}')">Edit</button></div>`).join('')}</div></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-header py-1"><small>Upcoming Schedule</small><button class="btn btn-sm btn-primary float-end py-0" onclick="generateCalendar()">Generate</button></div><div class="card-body p-0"><div class="list-group list-group-flush">${calendar.schedule?.slice(0,8).map(c => `<div class="list-group-item py-1"><small><strong>${c.date}</strong> - ${escapeHtml(c.name)}</small>${c.series?` <span class="series-badge">${c.series}</span>`:''}</div>`).join('') || '<div class="list-group-item text-muted">No scheduled stories</div>'}</div></div></div></div>
        </div>
        <div class="mt-3">
            <button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync Files</button>
            <button class="btn btn-sm btn-success ms-2" onclick="updateLeaderboardStats()"><i class="bi bi-trophy"></i> Update Leaderboard Stats</button>
        </div>
    `;
}

function filterStoriesByStatus(status) {
    if (typeof filterState !== 'undefined') {
        filterState.status = status === 'all' ? 'All' : status;
    }
    loadView('stories');
}

function filterStoriesByBookmarked() {
    if (typeof filterState !== 'undefined') {
        filterState.bookmarked = true;
    }
    loadView('stories');
}

function filterStoriesByLeaderboard() {
    if (typeof filterState !== 'undefined') {
        filterState.leaderboard = true;
    }
    loadView('stories');
}

function filterBySeries(seriesName) {
    if (typeof filterState !== 'undefined') {
        filterState.series = seriesName;
        filterState.status = 'All';
    }
    loadView('stories');
}