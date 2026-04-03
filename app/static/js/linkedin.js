// ============================================
// LinkedIn Marketing Functions
// ============================================

function setNowLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) el.value = getNowTimestamp();
    updateLinkedinDisplay();
}

function clearLinkedinTimestamp() {
    const el = document.getElementById('editStoryLinkedinTimestamp');
    if (el) el.value = '';
    updateLinkedinDisplay();
}

function clearAllLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;
    
    const storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) {
        alert('No story selected');
        return;
    }
    
    let cleanKey = storyKey;
    if (cleanKey.toLowerCase().endsWith('.md')) cleanKey = cleanKey.slice(0, -3);
    
    fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            status: document.getElementById('editStoryStatus')?.value || 'Draft',
            tags: document.getElementById('editStoryTags')?.value.split(',').map(t=>t.trim()).filter(t=>t) || [],
            medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
            notes: document.getElementById('editStoryNotes')?.value || '',
            created_date: document.getElementById('editStoryCreatedDate')?.value || null,
            medium_publication: document.getElementById('editStoryPublication')?.value || null,
            linkedin_status: null,
            linkedin_timestamp: null,
            linkedin_impressions: 0,
            linkedin_url: null
        })
    }).then(() => {
        if (typeof saveFilterState === 'function') saveFilterState();
        if (typeof loadView === 'function') loadView(window.currentView).then(() => {
            if (typeof restoreFilterState === 'function') restoreFilterState();
        });
    });
}

function onLinkedinStatusChange() {
    const statusEl = document.getElementById('editStoryLinkedinStatus');
    const timestampEl = document.getElementById('editStoryLinkedinTimestamp');
    const status = statusEl?.value || '';
    
    if (status === 'scheduled' || status === 'posted') {
        if (timestampEl && !timestampEl.value) {
            timestampEl.value = getNowTimestamp();
        }
    }
    updateLinkedinDisplay();
}

function updateLinkedinDisplay() {
    const status = document.getElementById('editStoryLinkedinStatus')?.value || '';
    const timestamp = document.getElementById('editStoryLinkedinTimestamp')?.value || '';
    const impressions = document.getElementById('editStoryLinkedinImpressions')?.value || '0';
    const display = document.getElementById('editStoryLinkedinDisplay');
    if (!display) return;
    
    if (status === 'scheduled') {
        display.innerHTML = `<i class="bi bi-calendar"></i> Scheduled for ${timestamp ? formatTimestampForDisplay(timestamp) : 'No date'} | Impressions: ${impressions}`;
    } else if (status === 'posted') {
        display.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i> Posted ${timestamp ? formatTimestampForDisplay(timestamp) : ''} | Impressions: ${impressions}`;
    } else {
        display.innerHTML = '<i class="bi bi-linkedin"></i> Not posted';
    }
}