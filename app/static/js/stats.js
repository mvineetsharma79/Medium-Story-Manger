// ============================================
// Stats Dashboard Functions
// ============================================

async function showStatsDashboard(storyKey) {
    let cleanKey = storyKey.replace('.md', '');
    const modal = new bootstrap.Modal(document.getElementById('statsDashboardModal'));
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!contentDiv) return;
    
    contentDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Loading stats...</p></div>';
    modal.show();
    
    try {
        const res = await fetch(`${API_BASE}/stories/fetch-lifetime-stats/${encodeURIComponent(cleanKey)}`, { method: 'POST' });
        const data = await res.json();
        
        if (data.stats) {
            const s = data.stats;
            const curr = s.current_month || {};
            const life = s.lifetime || {};
            const memberReadPercent = calcMemberPercent(curr.member_reads || 0, curr.reads || 0);
            const memberViewPercent = calcMemberPercent(curr.member_views || 0, curr.views || 0);
            const readRatio = (curr.views || 0) > 0 ? Math.round(((curr.reads || 0) / (curr.views || 0)) * 100) : 0;
            
            contentDiv.innerHTML = `
                <div class="compact-stats">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>${escapeHtml(s.story_name)}</strong>
                        <a href="${escapeHtml(s.medium_url)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-box-arrow-up-right"></i></a>
                    </div>
                    <div class="row g-1 mb-2"><div class="col-12"><strong>Current Month</strong></div></div>
                    <div class="row g-1 mb-2">
                        <div class="col-4"><div class="card bg-light p-1 text-center"><small>Reads</small><strong>${formatNumber(curr.member_reads)}/${formatNumber(curr.reads)} - ${memberReadPercent}%</strong></div></div>
                        <div class="col-4"><div class="card bg-light p-1 text-center"><small>Views</small><strong>${formatNumber(curr.member_views)}/${formatNumber(curr.views)} - ${memberViewPercent}%</strong></div></div>
                        <div class="col-4"><div class="card bg-light p-1 text-center"><small>Claps</small><strong>${formatNumber(curr.claps)}</strong></div></div>
                    </div>
                    <div class="row g-1 mb-2"><div class="col-12"><strong>Lifetime</strong></div></div>
                    <div class="row g-1">
                        <div class="col-4"><div class="card" style="background:#6f42c1;color:white;"><div class="card-body p-1 text-center"><small>Reads</small><br><strong>${formatNumber(life.reads)}</strong></div></div></div>
                        <div class="col-4"><div class="card" style="background:#fd7e14;color:white;"><div class="card-body p-1 text-center"><small>Claps</small><br><strong>${formatNumber(life.claps)}</strong></div></div></div>
                        <div class="col-4"><div class="card" style="background:#20c997;color:white;"><div class="card-body p-1 text-center"><small>Views</small><br><strong>${formatNumber(life.views)}</strong></div></div></div>
                    </div>
                    <div class="text-center mt-2"><small class="text-muted">Read Ratio: ${readRatio}%</small></div>
                </div>
            `;
        } else {
            contentDiv.innerHTML = `<div class="alert alert-danger m-2">Error: ${data.error || 'Could not fetch stats'}</div>`;
        }
    } catch (error) {
        contentDiv.innerHTML = `<div class="alert alert-danger m-2">Error: ${error.message}</div>`;
    }
}