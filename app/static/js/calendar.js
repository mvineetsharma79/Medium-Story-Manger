// ============================================
// CALENDAR PAGE - API calls and rendering only (NO HTML)
// ============================================

async function loadCalendar() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/calendar/schedule`);
        const data = await res.json();
        
        // Update summary cards
        const scheduledCount = document.getElementById('scheduledCount');
        const storiesPerWeek = document.getElementById('storiesPerWeek');
        const seriesSpacing = document.getElementById('seriesSpacing');
        const remainingCount = document.getElementById('remainingCount');
        
        if (scheduledCount) scheduledCount.textContent = data.summary?.total_scheduled || 0;
        if (storiesPerWeek) storiesPerWeek.textContent = data.summary?.stories_per_week || 3;
        if (seriesSpacing) seriesSpacing.textContent = `${data.summary?.series_spacing_default || 7} days`;
        if (remainingCount) remainingCount.textContent = data.summary?.remaining_unpublished || 0;
        
        // Render table
        const tbody = document.getElementById('calendarTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!data.schedule || !data.schedule.length) {
            const row = tbody.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 6;
            cell.className = 'text-center text-muted';
            cell.textContent = 'No scheduled stories. Click "Regenerate" to create a schedule.';
            return;
        }
        
        for (const c of data.schedule) {
            const row = tbody.insertRow();
            row.className = 'table-row-clickable';
            row.style.cursor = 'pointer';
            row.onclick = () => markPublished(c.story_key);
            
            // Date cell
            const dateCell = row.insertCell(0);
            const dateStrong = document.createElement('strong');
            dateStrong.textContent = c.date;
            dateCell.appendChild(dateStrong);
            const dateBreak = document.createElement('br');
            dateCell.appendChild(dateBreak);
            const weekdaySmall = document.createElement('small');
            weekdaySmall.className = 'text-muted';
            weekdaySmall.textContent = c.weekday;
            dateCell.appendChild(weekdaySmall);
            
            // Name cell
            const nameCell = row.insertCell(1);
            nameCell.textContent = c.name;
            
            // Series cell
            const seriesCell = row.insertCell(2);
            seriesCell.textContent = c.series || 'Standalone';
            
            // Part cell
            const partCell = row.insertCell(3);
            partCell.textContent = c.part ? `Part ${c.part}` : '—';
            
            // Read Time cell
            const readTimeCell = row.insertCell(4);
            readTimeCell.textContent = c.read_time ? `${c.read_time} min` : '—';
            
            // Actions cell
            const actionsCell = row.insertCell(5);
            const publishBtn = document.createElement('button');
            publishBtn.className = 'btn btn-sm btn-success';
            publishBtn.innerHTML = '<i class="bi bi-check-lg"></i> Publish';
            publishBtn.onclick = (e) => {
                e.stopPropagation();
                markPublished(c.story_key);
            };
            actionsCell.appendChild(publishBtn);
        }
        
    } catch (error) {
        console.error('Error loading calendar:', error);
        showToast('Error loading calendar: ' + error.message, 'error');
        const tbody = document.getElementById('calendarTableBody');
        if (tbody) {
            tbody.innerHTML = '';
            const row = tbody.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 6;
            cell.className = 'text-center text-danger';
            cell.textContent = 'Error loading calendar. Please refresh.';
        }
    } finally {
        hideLoading();
    }
}

async function regenerateCalendar() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/calendar/generate`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            await loadCalendar();
            showToast('Calendar regenerated successfully', 'success');
        } else {
            showToast('Error generating calendar: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error generating calendar: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function markPublished(storyKey) {
    if (!storyKey) return;
    if (!confirm('Mark this story as published?')) return;
    
    let cleanKey = storyKey;
    if (cleanKey && cleanKey.toLowerCase().endsWith('.md')) {
        cleanKey = cleanKey.slice(0, -3);
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(cleanKey)}/publish`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        if (response.ok) {
            await loadCalendar();
            showToast('Story marked as published', 'success');
        } else {
            const error = await response.json();
            showToast('Error marking as published: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error marking as published: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

document.addEventListener('DOMContentLoaded', loadCalendar);