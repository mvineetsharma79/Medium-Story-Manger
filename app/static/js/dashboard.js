// ============================================
// Dashboard Functions - COMPLETE FIXED VERSION
// ============================================

// Utility functions (in case they're not available from utils.js)
function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function calcMemberPercent(member, total) {
    if (!total || total === 0) return 0;
    return Math.round((member / total) * 100);
}

function updateLeaderboardTotal() {
    if (!window.allStories || !Array.isArray(window.allStories)) {
        const countEl = document.getElementById('leaderboardCount');
        const amountEl = document.getElementById('leaderboardAmount');
        if (countEl) countEl.textContent = '0';
        if (amountEl) amountEl.textContent = '0.00';
        return;
    }
    const storiesWithLeaderboard = window.allStories.filter(s => s.leaderboard === true);
    const totalNanos = storiesWithLeaderboard.reduce((sum, s) => sum + (s.leaderboard_nanos || 0), 0);
    const countEl = document.getElementById('leaderboardCount');
    const amountEl = document.getElementById('leaderboardAmount');
    if (countEl) countEl.textContent = storiesWithLeaderboard.length;
    if (amountEl) amountEl.textContent = (totalNanos / 1000000000).toFixed(2);
}

async function loadDashboard() {
    console.log('loadDashboard called');
    const contentDiv = document.getElementById('content');
    if (!contentDiv) {
        console.error('Content div not found');
        return;
    }
    
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p>Loading dashboard...</p></div>';
    
    try {
        // Get current year and month for monthly stats
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        
        console.log(`Fetching stories for ${currentYear}-${currentMonth}`);
        
        // Try to get monthly stats for current month from monthly file
        let monthlyStatsMap = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/month/${currentYear}/${currentMonth}`);
            if (monthlyRes.ok) {
                const monthlyStories = await monthlyRes.json();
                console.log(`Found ${monthlyStories.length} stories in monthly file`);
                monthlyStatsMap = monthlyStories.reduce((map, story) => {
                    map[story.key] = story.monthly_stats || {};
                    return map;
                }, {});
            } else {
                console.log(`No monthly file for ${currentYear}-${currentMonth}`);
            }
        } catch (e) {
            console.log('Error fetching monthly stats:', e);
        }
        
        // Get all stories from permanent storage
        const storiesRes = await fetch(`${API_BASE}/stories/`);
        if (!storiesRes.ok) {
            throw new Error(`HTTP ${storiesRes.status}: ${await storiesRes.text()}`);
        }
        
        const allStories = await storiesRes.json();
        console.log(`Found ${allStories.length} stories in permanent storage`);
        
        // Merge monthly stats into stories
        const mergedStories = allStories.map(story => {
            const monthlyStats = monthlyStatsMap[story.key] || {};
            return {
                ...story,
                // Monthly stats (with defaults if not found)
                reads: monthlyStats.reads || 0,
                view_count: monthlyStats.view_count || 0,
                claps: monthlyStats.claps || 0,
                responses: monthlyStats.responses || 0,
                leaderboard: monthlyStats.leaderboard || false,
                leaderboard_nanos: monthlyStats.leaderboard_nanos || 0,
                medium_member_reads: monthlyStats.medium_member_reads || 0,
                medium_member_views: monthlyStats.medium_member_views || 0,
                medium_nonmember_reads: monthlyStats.medium_nonmember_reads || 0,
                medium_nonmember_views: monthlyStats.medium_nonmember_views || 0,
                medium_read_ratio: monthlyStats.medium_read_ratio || 0,
                medium_member_read_percentage: monthlyStats.medium_member_read_percentage || 0,
                medium_new_followers: monthlyStats.medium_new_followers || 0,
                medium_highlights: monthlyStats.medium_highlights || 0
            };
        });
        
        window.allStories = mergedStories;
        
        // Calculate statistics
        const published = mergedStories.filter(s => s.status === 'Published').length;
        const draft = mergedStories.filter(s => s.status === 'Draft').length;
        const ready = mergedStories.filter(s => s.status === 'Ready').length;
        const done = mergedStories.filter(s => s.status === 'Done').length;
        const bookmarked = mergedStories.filter(s => s.bookmarked === true).length;
        const leaderboard = mergedStories.filter(s => s.leaderboard === true).length;
        
        // Calculate aggregated stats using monthly stats
        const totalMemberReads = mergedStories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
        const totalReads = mergedStories.reduce((sum, s) => sum + (s.reads || 0), 0);
        const totalMemberViews = mergedStories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
        const totalViews = mergedStories.reduce((sum, s) => sum + (s.view_count || 0), 0);
        const totalClaps = mergedStories.reduce((sum, s) => sum + (s.claps || 0), 0);
        
        const totalMemberReadPercent = calcMemberPercent(totalMemberReads, totalReads);
        const totalMemberViewPercent = calcMemberPercent(totalMemberViews, totalViews);
        const totalReadRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        // Leaderboard specific stats
        const leaderboardStories = mergedStories.filter(s => s.leaderboard === true);
        const leaderboardMemberReads = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_reads || 0), 0);
        const leaderboardTotalReads = leaderboardStories.reduce((sum, s) => sum + (s.reads || 0), 0);
        const leaderboardMemberViews = leaderboardStories.reduce((sum, s) => sum + (s.medium_member_views || 0), 0);
        const leaderboardTotalViews = leaderboardStories.reduce((sum, s) => sum + (s.view_count || 0), 0);
        const leaderboardClaps = leaderboardStories.reduce((sum, s) => sum + (s.claps || 0), 0);
        const leaderboardCount = leaderboardStories.length;
        const leaderboardMemberReadPercent = calcMemberPercent(leaderboardMemberReads, leaderboardTotalReads);
        
        // Get calendar
        let calendar = { schedule: [], summary: {} };
        try {
            const calendarRes = await fetch(`${API_BASE}/calendar/`);
            if (calendarRes.ok) {
                calendar = await calendarRes.json();
            }
        } catch (e) {
            console.log('Could not load calendar:', e);
        }
        
        // Get recent stories (last 8)
        const recentStories = mergedStories.slice(0, 8);
        
        // Get upcoming schedule (first 8)
        const upcomingSchedule = (calendar.schedule || []).slice(0, 8);
        
        // Build dashboard HTML
        const html = `
            <h1 class="h3 mb-3">Dashboard</h1>
            
            <div class="row g-2 mb-3">
                <div class="col-md-2">
                    <div class="card stat-card bg-primary text-white" onclick="filterStoriesByStatus('all')" style="cursor: pointer;">
                        <div class="card-body">
                            <h6>Total</h6>
                            <h2>${mergedStories.length}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="card stat-card bg-success text-white" onclick="filterStoriesByStatus('Published')" style="cursor: pointer;">
                        <div class="card-body">
                            <h6>Published</h6>
                            <h2>${published}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="card stat-card bg-info text-white" onclick="filterStoriesByStatus('Ready')" style="cursor: pointer;">
                        <div class="card-body">
                            <h6>Ready</h6>
                            <h2>${ready}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="card stat-card bg-secondary text-white" onclick="filterStoriesByStatus('Done')" style="cursor: pointer;">
                        <div class="card-body">
                            <h6>Done</h6>
                            <h2>${done}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="card stat-card" style="background:#ffc107;color:#000;cursor: pointer;" onclick="filterStoriesByBookmarked()">
                        <div class="card-body">
                            <h6>Bookmarked</h6>
                            <h2>${bookmarked}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="card stat-card" style="background:#ffd700;color:#000;cursor: pointer;" onclick="filterStoriesByLeaderboard()">
                        <div class="card-body">
                            <h6>Leaderboard</h6>
                            <h2>${leaderboard}</h2>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row g-2 mb-3">
                <div class="col-md-3">
                    <div class="card mini-stat-card bg-info text-white">
                        <div class="card-body">
                            <h6>Reads (Member/Total)</h6>
                            <h2>${formatNumber(totalMemberReads)}/${formatNumber(totalReads)}</h2>
                            <small>${totalMemberReadPercent}% members</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card mini-stat-card bg-primary text-white">
                        <div class="card-body">
                            <h6>Views (Member/Total)</h6>
                            <h2>${formatNumber(totalMemberViews)}/${formatNumber(totalViews)}</h2>
                            <small>${totalMemberViewPercent}% members</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card mini-stat-card bg-warning text-white">
                        <div class="card-body">
                            <h6>Read Ratio</h6>
                            <h2>${totalReadRatio}%</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card mini-stat-card bg-success text-white">
                        <div class="card-body">
                            <h6>Total Claps</h6>
                            <h2>${formatNumber(totalClaps)}</h2>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-12">
                    <div class="card leaderboard-section" style="border:1px solid #ffd700;background:#fff8e7;">
                        <div class="card-header py-1" style="background:#ffd700;color:#000;">
                            <small><i class="bi bi-trophy"></i> <strong>Leaderboard</strong> (${leaderboardCount} stories)
                                <button class="btn btn-sm btn-primary py-0 px-2 ms-2" onclick="updateLeaderboardStatsForMonth()" style="font-size:0.7rem;"><i class="bi bi-arrow-repeat"></i> Update Stats</button>
                            </small>
                        </div>
                        <div class="card-body py-1">
                            <div class="row g-1">
                                <div class="col-md-4">
                                    <div class="bg-info text-white p-1 rounded text-center">
                                        <small>Reads</small><br>
                                        <strong>${formatNumber(leaderboardMemberReads)}/${formatNumber(leaderboardTotalReads)}</strong>
                                        <br><small>${leaderboardMemberReadPercent}% members</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="bg-primary text-white p-1 rounded text-center">
                                        <small>Views</small><br>
                                        <strong>${formatNumber(leaderboardMemberViews)}/${formatNumber(leaderboardTotalViews)}</strong>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="bg-warning text-white p-1 rounded text-center">
                                        <small>Claps</small><br>
                                        <strong>${formatNumber(leaderboardClaps)}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header py-1 d-flex justify-content-between align-items-center">
                            <small>Recent Stories</small>
                            <button class="btn btn-sm btn-primary py-0" onclick="loadView('stories')">View All</button>
                        </div>
                        <div class="card-body p-0">
                            <div class="list-group list-group-flush">
                                ${recentStories.map(s => `
                                    <div class="list-group-item py-1 d-flex justify-content-between align-items-center">
                                        <div>
                                            <span class="status-badge ${s.status==='Published'?'status-published':s.status==='Ready'?'status-ready':s.status==='Done'?'status-done':'status-draft'}">${s.status}</span>
                                            <small>${escapeHtml(s.name.substring(0, 40))}</small>
                                            ${s.leaderboard ? ' <i class="bi bi-trophy-fill text-warning"></i>' : ''}
                                        </div>
                                        <button class="btn btn-sm btn-outline-primary py-0" onclick="openEditStory('${s.key.replace(/'/g, "\\'")}')">Edit</button>
                                    </div>
                                `).join('')}
                                ${recentStories.length === 0 ? '<div class="list-group-item text-muted">No stories found</div>' : ''}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header py-1 d-flex justify-content-between align-items-center">
                            <small>Upcoming Schedule</small>
                            <button class="btn btn-sm btn-primary py-0" onclick="generateCalendar()">Generate</button>
                        </div>
                        <div class="card-body p-0">
                            <div class="list-group list-group-flush">
                                ${upcomingSchedule.map(c => `
                                    <div class="list-group-item py-1">
                                        <small><strong>${c.date}</strong> - ${escapeHtml(c.name)}</small>
                                        ${c.series ? ` <span class="series-badge">${c.series}</span>` : ''}
                                    </div>
                                `).join('')}
                                ${upcomingSchedule.length === 0 ? '<div class="list-group-item text-muted">No scheduled stories</div>' : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="mt-3">
                <button class="btn btn-sm btn-primary" onclick="syncStories()"><i class="bi bi-arrow-repeat"></i> Sync Files</button>
                <button class="btn btn-sm btn-success ms-2" onclick="updateLeaderboardStatsForMonth()"><i class="bi bi-trophy"></i> Update Leaderboard Stats</button>
                <button class="btn btn-sm btn-info ms-2" onclick="fetchLeaderboardFiles()"><i class="bi bi-cloud-download"></i> Load Leaderboard Data</button>
            </div>
        `;
        
        contentDiv.innerHTML = html;
        
        // Update leaderboard total display in sidebar
        updateLeaderboardTotal();
        
        console.log('Dashboard loaded successfully');
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        contentDiv.innerHTML = `<div class="alert alert-danger">Error loading dashboard: ${error.message}<br><br>Check console for details.</div>`;
    }
}

function filterStoriesByStatus(status) {
    console.log('filterStoriesByStatus:', status);
    if (typeof window.filterState !== 'undefined') {
        window.filterState.status = status === 'all' ? 'All' : status;
    }
    if (typeof loadView === 'function') {
        loadView('stories');
    } else {
        console.error('loadView not available');
        window.location.href = '#stories';
    }
}

function filterStoriesByBookmarked() {
    console.log('filterStoriesByBookmarked');
    if (typeof window.filterState !== 'undefined') {
        window.filterState.bookmarked = true;
    }
    if (typeof loadView === 'function') {
        loadView('stories');
    } else {
        console.error('loadView not available');
        window.location.href = '#stories';
    }
}

function filterStoriesByLeaderboard() {
    console.log('filterStoriesByLeaderboard');
    if (typeof window.filterState !== 'undefined') {
        window.filterState.leaderboard = true;
    }
    if (typeof loadView === 'function') {
        loadView('stories');
    } else {
        console.error('loadView not available');
        window.location.href = '#stories';
    }
}

function fetchLeaderboardFiles() {
    console.log('fetchLeaderboardFiles');
    if (typeof loadView === 'function') {
        loadView('settings');
        setTimeout(() => {
            const leaderboardSection = document.querySelector('.alert-warning');
            if (leaderboardSection) {
                leaderboardSection.scrollIntoView({ behavior: 'smooth' });
            }
        }, 500);
    }
}

// Make functions globally available
window.loadDashboard = loadDashboard;
window.filterStoriesByStatus = filterStoriesByStatus;
window.filterStoriesByBookmarked = filterStoriesByBookmarked;
window.filterStoriesByLeaderboard = filterStoriesByLeaderboard;
window.fetchLeaderboardFiles = fetchLeaderboardFiles;
window.calcMemberPercent = calcMemberPercent;
window.formatNumber = formatNumber;
window.escapeHtml = escapeHtml;
window.updateLeaderboardTotal = updateLeaderboardTotal;

console.log('dashboard.js loaded');