// ============================================
// Enhanced Edit Story Functions
// ============================================

let currentEditStoryKey = null;
let currentEditStoryYear = null;
let currentEditStoryMonth = null;
let storyAvailableMonths = [];

async function openEditStory(storyKey) {
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    currentEditStoryKey = cleanKey;
    
    try {
        const modeData = await fetch(`${API_BASE}/stories/mode`).then(r => r.json());
        currentEditStoryYear = modeData?.current_month?.year || new Date().getFullYear();
        currentEditStoryMonth = modeData?.current_month?.month || new Date().getMonth() + 1;
    } catch (error) {
        console.warn('Error getting mode, using current month:', error);
        currentEditStoryYear = new Date().getFullYear();
        currentEditStoryMonth = new Date().getMonth() + 1;
    }
    
    await loadStoryForEdit(cleanKey, currentEditStoryYear, currentEditStoryMonth);
    await loadStoryAvailableMonths(cleanKey);
    
    const modalEl = document.getElementById('editStoryModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

async function loadStoryForEdit(storyKey, year, month) {
    try {
        const storyRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`);
        const story = await storyRes.json();
        
        const monthlyRes = await fetch(`${API_BASE}/stories/stats-by-url?medium_url=${encodeURIComponent(story.medium_url || '')}`);
        let monthlyStats = {};
        if (monthlyRes.ok) {
            const monthlyData = await monthlyRes.json();
            monthlyStats = monthlyData.current_month || {};
        }
        
        document.getElementById('editStoryKey').value = storyKey;
        document.getElementById('editStoryNameDisplay').textContent = story.name || '';
        document.getElementById('editStoryPath').textContent = story.raw_path || story.rel_path || storyKey;
        document.getElementById('editStoryStatus').value = story.status || 'Draft';
        document.getElementById('editStorySeries').textContent = story.series || 'Standalone';
        document.getElementById('editStoryPublication').value = story.medium_publication || '';
        document.getElementById('editStoryCreatedDate').value = story.created_date?.split('T')[0] || '';
        document.getElementById('editStoryMediumUrl').value = story.medium_url || '';
        document.getElementById('editStoryNotes').value = story.notes || '';
        document.getElementById('editStoryTags').value = story.tags?.join(', ') || '';
        
        document.getElementById('editStoryLifetimeReads').innerHTML = '0';
        document.getElementById('editStoryLifetimeViews').innerHTML = '0';
        document.getElementById('editStoryLifetimeClaps').innerHTML = '0';
        document.getElementById('editStoryPresentationCount').innerHTML = '0';
        document.getElementById('editStoryLifetimeEarnings').innerHTML = '$0.00';
        
        const memberReads = monthlyStats.member_reads || 0;
        const totalReads = monthlyStats.reads || 0;
        const memberViews = monthlyStats.member_views || 0;
        const totalViews = monthlyStats.views || 0;
        const memberReadPercent = totalReads > 0 ? Math.round((memberReads / totalReads) * 100) : 0;
        const memberViewPercent = totalViews > 0 ? Math.round((memberViews / totalViews) * 100) : 0;
        const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
        
        document.getElementById('editStoryMemberReads').innerHTML = `${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%`;
        document.getElementById('editStoryMemberViews').innerHTML = `${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%`;
        document.getElementById('editStoryReadRatio').innerHTML = `${readRatio}%`;
        document.getElementById('editStoryMemberPercent').innerHTML = `${memberReadPercent}%`;
        document.getElementById('editStoryReadTimeWordCount').innerHTML = `${story.medium_reading_time || story.read_time || 0} min / ${formatNumber(story.word_count || 0)} words`;
        document.getElementById('editStoryReads').value = totalReads;
        document.getElementById('editStoryViews').value = totalViews;
        document.getElementById('editStoryClaps').value = monthlyStats.claps || 0;
        document.getElementById('editStoryResponses').value = monthlyStats.responses || 0;
        document.getElementById('editStoryNewFollowers').value = monthlyStats.new_followers || 0;
        document.getElementById('editStoryHighlights').value = monthlyStats.highlights || 0;
        
        const leaderboard = monthlyStats.leaderboard || false;
        document.getElementById('editStoryLeaderboard').value = leaderboard ? 'true' : 'false';
        document.getElementById('editStoryLeaderboardNanos').value = monthlyStats.leaderboard_nanos || 0;
        
        document.getElementById('editStoryLinkedinStatus').value = story.linkedin_status || '';
        document.getElementById('editStoryLinkedinTimestamp').value = story.linkedin_timestamp || '';
        document.getElementById('editStoryLinkedinImpressions').value = story.linkedin_impressions || 0;
        document.getElementById('editStoryLinkedinUrl').value = story.linkedin_url || '';
        document.getElementById('editStoryLastUpdated').textContent = story.last_updated || 'Never';
        
        updateLinkedinDisplay();
        updateEditStoryMonthSelector(year, month);
        
    } catch (error) {
        console.error('Error loading story for edit:', error);
        alert('Error loading story: ' + error.message);
    }
}

async function loadStoryAvailableMonths(storyKey) {
    try {
        const response = await fetch(`${API_BASE}/stories/story-months/${encodeURIComponent(storyKey)}`);
        const data = await response.json();
        storyAvailableMonths = data.months || [];
        
        const container = document.getElementById('storyAvailableMonthsList');
        if (container) {
            if (storyAvailableMonths.length === 0) {
                container.innerHTML = '<div class="text-muted small text-center py-2">No monthly data yet</div>';
                return;
            }
            
            let html = '<div class="list-group list-group-flush" style="max-height: 250px; overflow-y: auto;">';
            for (const month of storyAvailableMonths) {
                const icon = month.has_data ? '●' : '○';
                const color = month.has_data ? '#27ae60' : '#e74c3c';
                const isCurrent = currentEditStoryYear === month.year && currentEditStoryMonth === month.month;
                
                html += `
                    <div class="list-group-item list-group-item-action ${isCurrent ? 'active' : ''}" 
                         style="cursor: pointer; font-size: 0.75rem; padding: 0.3rem 0.5rem;"
                         onclick="switchEditStoryMonth(${month.year}, ${month.month})">
                        <span style="color: ${color};">${icon}</span>
                        ${month.display}
                        ${month.leaderboard ? ' <i class="bi bi-trophy-fill text-warning" style="font-size: 0.6rem;"></i>' : ''}
                        ${isCurrent ? ' <i class="bi bi-check"></i>' : ''}
                    </div>
                `;
            }
            html += '</div>';
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading story months:', error);
    }
}

function updateEditStoryMonthSelector(year, month) {
    const selector = document.getElementById('editStoryMonthSelector');
    if (!selector) return;
    
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let html = '<select class="form-select form-select-sm" id="editStoryMonthSelect" onchange="onEditStoryMonthChange()">';
    html += `<option value="${year}-${month}" selected>${monthNames[month-1]} ${year}</option>`;
    
    if (window.availableMonths && Array.isArray(window.availableMonths)) {
        for (const availMonth of window.availableMonths) {
            if (availMonth.year === year && availMonth.month === month) continue;
            html += `<option value="${availMonth.year}-${availMonth.month}">${availMonth.display}</option>`;
        }
    }
    
    html += '</select>';
    selector.innerHTML = html;
}

async function onEditStoryMonthChange() {
    const select = document.getElementById('editStoryMonthSelect');
    if (!select) return;
    
    const [year, month] = select.value.split('-');
    currentEditStoryYear = parseInt(year);
    currentEditStoryMonth = parseInt(month);
    await loadStoryForEdit(currentEditStoryKey, currentEditStoryYear, currentEditStoryMonth);
}

async function switchEditStoryMonth(year, month) {
    currentEditStoryYear = year;
    currentEditStoryMonth = month;
    updateEditStoryMonthSelector(year, month);
    await loadStoryForEdit(currentEditStoryKey, year, month);
}

async function saveStoryEdit() {
    let storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) return;
    if (storyKey.toLowerCase().endsWith('.md')) storyKey = storyKey.slice(0, -3);
    
    const permanentData = {
        status: document.getElementById('editStoryStatus')?.value || 'Draft',
        tags: document.getElementById('editStoryTags')?.value.split(',').map(t=>t.trim()).filter(t=>t) || [],
        medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
        notes: document.getElementById('editStoryNotes')?.value || '',
        created_date: document.getElementById('editStoryCreatedDate')?.value || null,
        medium_publication: document.getElementById('editStoryPublication')?.value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions')?.value) || 0,
        linkedin_url: document.getElementById('editStoryLinkedinUrl')?.value || null,
        lifetime_reads: 0,
        lifetime_views: 0,
        lifetime_claps: 0,
        presentation_count: 0,
        leaderboard_nanos_lifetime: 0
    };
    
    const monthlyData = {
        reads: parseInt(document.getElementById('editStoryReads')?.value) || 0,
        view_count: parseInt(document.getElementById('editStoryViews')?.value) || 0,
        claps: parseInt(document.getElementById('editStoryClaps')?.value) || 0,
        responses: parseInt(document.getElementById('editStoryResponses')?.value) || 0,
        medium_new_followers: parseInt(document.getElementById('editStoryNewFollowers')?.value) || 0,
        medium_highlights: parseInt(document.getElementById('editStoryHighlights')?.value) || 0,
        leaderboard: document.getElementById('editStoryLeaderboard')?.value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editStoryLeaderboardNanos')?.value) || 0
    };
    
    try {
        const permRes = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`, { 
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(permanentData) 
        });
        
        if (!permRes.ok) {
            const error = await permRes.json();
            alert('Error saving story: ' + (error.detail || 'Unknown error'));
            return;
        }
        
        if (currentEditStoryYear && currentEditStoryMonth) {
            await fetch(`${API_BASE}/stories/update-story-monthly-stats/${encodeURIComponent(storyKey)}?year=${currentEditStoryYear}&month=${currentEditStoryMonth}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(monthlyData)
            });
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
        if (modal) modal.hide();
        
        if (typeof saveFilterState === 'function') saveFilterState();
        if (typeof loadView === 'function') await loadView(window.currentView);
        if (typeof restoreFilterState === 'function') restoreFilterState();
        if (typeof updateLeaderboardTotal === 'function') updateLeaderboardTotal();
        
        alert('Story saved successfully');
        
    } catch (error) {
        console.error('Error saving story:', error);
        alert('Error saving story: ' + error.message);
    }
}

async function ensureStoryInCurrentMonth() {
    if (!currentEditStoryKey || !currentEditStoryYear || !currentEditStoryMonth) {
        alert('No month selected. Please select a month from the dropdown first.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/ensure-story-in-month?story_key=${encodeURIComponent(currentEditStoryKey)}&year=${currentEditStoryYear}&month=${currentEditStoryMonth}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Story added to current month');
            await loadStoryAvailableMonths(currentEditStoryKey);
        } else {
            const error = await response.json();
            alert('Failed to add story to month: ' + (error.detail || error.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error ensuring story in month:', error);
        alert('Error: ' + error.message);
    }
}

function setEditStoryTodayDate() {
    const el = document.getElementById('editStoryCreatedDate');
    if (el) el.value = getTodayDate();
}

function setEditStoryNowLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) {
        el.value = getNowTimestamp();
        updateLinkedinDisplay();
    }
}

function clearEditStoryLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) {
        el.value = '';
        updateLinkedinDisplay();
    }
}

function clearAllEditStoryLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;
    
    const statusEl = document.getElementById('editStoryLinkedinStatus');
    const timestampEl = document.getElementById('editStoryLinkedinTimestamp');
    const impressionsEl = document.getElementById('editStoryLinkedinImpressions');
    const urlEl = document.getElementById('editStoryLinkedinUrl');
    
    if (statusEl) statusEl.value = '';
    if (timestampEl) timestampEl.value = '';
    if (impressionsEl) impressionsEl.value = '0';
    if (urlEl) urlEl.value = '';
    updateLinkedinDisplay();
}

document.addEventListener('DOMContentLoaded', function() {
    const setTodayBtn = document.getElementById('editStorySetTodayBtn');
    if (setTodayBtn) setTodayBtn.addEventListener('click', setEditStoryTodayDate);
    
    const setNowBtn = document.getElementById('editStorySetNowLinkedinBtn');
    const clearTimestampBtn = document.getElementById('editStoryClearLinkedinTimestampBtn');
    const clearAllBtn = document.getElementById('editStoryClearAllLinkedinBtn');
    const linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    const saveBtn = document.getElementById('saveStoryEditBtn');
    const addToMonthBtn = document.getElementById('addStoryToCurrentMonthBtn');
    
    if (setNowBtn) setNowBtn.addEventListener('click', setEditStoryNowLinkedinTimestamp);
    if (clearTimestampBtn) clearTimestampBtn.addEventListener('click', clearEditStoryLinkedinTimestamp);
    if (clearAllBtn) clearAllBtn.addEventListener('click', clearAllEditStoryLinkedinData);
    if (linkedinStatus) linkedinStatus.addEventListener('change', updateLinkedinDisplay);
    if (saveBtn) saveBtn.addEventListener('click', saveStoryEdit);
    if (addToMonthBtn) addToMonthBtn.addEventListener('click', ensureStoryInCurrentMonth);
});

// Make functions globally available
window.openEditStory = openEditStory;
window.saveStoryEdit = saveStoryEdit;
window.switchEditStoryMonth = switchEditStoryMonth;
window.onEditStoryMonthChange = onEditStoryMonthChange;
window.ensureStoryInCurrentMonth = ensureStoryInCurrentMonth;