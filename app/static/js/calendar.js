// ============================================
// CALENDAR PAGE - API calls and rendering only
// ============================================

async function loadCalendar() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/calendar/schedule`);
        const data = await res.json();
        
        // Update summary cards
        document.getElementById('scheduledCount').textContent = data.summary?.total_scheduled || 0;
        document.getElementById('storiesPerWeek').textContent = data.summary?.stories_per_week || 3;
        document.getElementById('seriesSpacing').textContent = `${data.summary?.series_spacing_default || 7} days`;
        document.getElementById('remainingCount').textContent = data.summary?.remaining_unpublished || 0;
        
        // Render table
        const tbody = document.getElementById('calendarTableBody');
        
        if (!data.schedule || !data.schedule.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No scheduled stories. Click "Regenerate" to create a schedule.</td</tr>';
            return;
        }
        
        tbody.innerHTML = data.schedule.map(c => `
            <tr>
                <td><strong>${c.date}</strong><br><small>${c.weekday}</small></td>
                <td>${escapeHtml(c.name)}</td
                <td>${c.series || 'Standalone'}</td
                <td>${c.part ? `Part ${c.part}` : '—'}</td
                <td>${c.read_time} min</td
                <td><button class="btn btn-sm btn-success" onclick="markPublished('${escapeHtml(c.story_key)}')">Publish</button></td
             </tr
        `).join('');
        
    } catch (error) {
        console.error('Error loading calendar:', error);
        showToast('Error loading calendar', 'error');
    } finally {
        hideLoading();
    }
}

async function regenerateCalendar() {
    showLoading();
    try {
        await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        await loadCalendar();
        showToast('Calendar regenerated', 'success');
    } catch (error) {
        showToast('Error generating calendar', 'error');
    } finally {
        hideLoading();
    }
}

async function markPublished(storyKey) {
    if (!confirm('Mark this story as published?')) return;
    
    showLoading();
    try {
        let cleanKey = storyKey.replace(/\.md$/, '');
        await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}/publish`, { method: 'POST' });
        await loadCalendar();
        showToast('Story marked as published', 'success');
    } catch (error) {
        showToast('Error marking as published', 'error');
    } finally {
        hideLoading();
    }
}

document.addEventListener('DOMContentLoaded', loadCalendar);