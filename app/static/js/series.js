// ============================================
// SERIES PAGE - With Status Icons and Single Line Format
// ============================================

let allSeries = [];
let currentSort = { column: 'total_reads', direction: 'desc' };

// ============================================
// FORMAT NUMBERS
// ============================================

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

// ============================================
// SORTING
// ============================================

function sortSeries(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    
    const sorted = [...allSeries].sort((a, b) => {
        let aVal, bVal;
        
        switch(column) {
            case 'draft_count':
                aVal = a.status_counts?.Draft || 0;
                bVal = b.status_counts?.Draft || 0;
                break;
            case 'total_reads':
                aVal = a.total_reads || 0;
                bVal = b.total_reads || 0;
                break;
            case 'total_claps':
                aVal = a.total_claps || 0;
                bVal = b.total_claps || 0;
                break;
            case 'progress_percent':
                aVal = a.progress_percent || 0;
                bVal = b.progress_percent || 0;
                break;
            case 'spacing_days':
                aVal = a.spacing_days || 7;
                bVal = b.spacing_days || 7;
                break;
            case 'name':
                aVal = (a.name || '').toLowerCase();
                bVal = (b.name || '').toLowerCase();
                if (currentSort.direction === 'asc') {
                    return aVal.localeCompare(bVal);
                } else {
                    return bVal.localeCompare(aVal);
                }
            default:
                aVal = a[column] || 0;
                bVal = b[column] || 0;
        }
        
        if (currentSort.direction === 'asc') {
            return aVal - bVal;
        } else {
            return bVal - aVal;
        }
    });
    
    renderSeriesTable(sorted);
    updateSeriesSortIcons(column, currentSort.direction);
}

function updateSeriesSortIcons(column, direction) {
    const headers = document.querySelectorAll('#seriesTableHeader .sortable');
    headers.forEach(header => {
        header.classList.remove('active');
        const icon = header.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    });
    const activeHeader = document.querySelector(`#seriesTableHeader .sortable[data-sort="${column}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active');
        const icon = activeHeader.querySelector('i');
        if (icon) icon.className = direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
}

// ============================================
// LOAD SERIES
// ============================================

async function loadSeries() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/series/list`);
        const data = await res.json();
        
        allSeries = data.series || [];
        renderSeriesTable(allSeries);
        
        if (allSeries.length > 0) {
            sortSeries(currentSort.column);
        }
        
    } catch (error) {
        console.error('Error loading series:', error);
        showToast('Error loading series: ' + error.message, 'error');
        const tbody = document.getElementById('seriesTableBody');
        if (tbody) {
            tbody.innerHTML = '';
            const row = tbody.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 7;
            cell.className = 'text-center text-danger';
            cell.textContent = 'Error loading series. Please refresh.';
        }
    } finally {
        hideLoading();
    }
}

function renderSeriesTable(series) {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!series || series.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 7;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No series found. Click "Add Series" to create one.';
        return;
    }
    
    series.forEach(s => {
        const row = tbody.insertRow();
        
        // Column 0: Series Name - Clickable with story count
        const nameCell = row.insertCell(0);
        const nameLink = document.createElement('a');
        nameLink.href = '#';
        nameLink.textContent = `${s.name} (${s.story_count || s.total_stories || 0})`;
        nameLink.style.textDecoration = 'none';
        nameLink.style.fontWeight = 'bold';
        nameLink.style.cursor = 'pointer';
        nameLink.style.color = '#0d6efd';
        nameLink.onclick = (e) => {
            e.preventDefault();
            filterStoriesBySeries(s.name);
        };
        nameCell.appendChild(nameLink);
        
        // Column 1: Status counts - Icons only with numbers
        const statusCell = row.insertCell(1);
        const statusDiv = document.createElement('div');
        statusDiv.style.fontSize = '0.75rem';
        statusDiv.style.whiteSpace = 'nowrap';
        
        const counts = s.status_counts || {
            "Published": 0, "Published Due": 0, "Ready": 0, "Done": 0, "Draft": 0
        };
        
        // Icons: ✅ Published, ⏰ Published Due, 🚀 Ready, ✓ Done, 📝 Draft
        statusDiv.innerHTML = `
            <span title="Published">✅ ${counts.Published || 0}</span> / 
            <span title="Published Due">⏰ ${counts["Published Due"] || 0}</span> / 
            <span title="Ready">🚀 ${counts.Ready || 0}</span> / 
            <span title="Done">✓ ${counts.Done || 0}</span> / 
            <span title="Draft">📝 ${counts.Draft || 0}</span>
        `;
        statusCell.appendChild(statusDiv);
        
        // Column 2: Performance - Single line
        const performanceCell = row.insertCell(2);
        const performanceDiv = document.createElement('div');
        performanceDiv.style.fontSize = '0.75rem';
        performanceDiv.style.whiteSpace = 'nowrap';
        
        const presentations = s.total_presentations || 0;
        const views = s.total_views || 0;
        const reads = s.total_reads || 0;
        
        performanceDiv.innerHTML = `📊 ${formatNumber(presentations)} / 👁️ ${formatNumber(views)} / 📖 ${formatNumber(reads)}`;
        performanceCell.appendChild(performanceDiv);
        
        // Column 3: Engagement - Single line
        const engagementCell = row.insertCell(3);
        const engagementDiv = document.createElement('div');
        engagementDiv.style.fontSize = '0.75rem';
        engagementDiv.style.whiteSpace = 'nowrap';
        
        const claps = s.total_claps || 0;
        const responses = s.total_responses || 0;
        
        engagementDiv.innerHTML = `💚 ${formatNumber(claps)} / 💬 ${formatNumber(responses)}`;
        engagementCell.appendChild(engagementDiv);
        
        // Column 4: Progress (Published/Total with progress bar)
        const progressCell = row.insertCell(4);
        const progressDiv = document.createElement('div');
        progressDiv.className = 'd-flex align-items-center gap-2';
        
        const progressWrapper = document.createElement('div');
        progressWrapper.className = 'progress';
        progressWrapper.style.width = '150px';
        progressWrapper.style.height = '6px';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar bg-success';
        progressBar.style.width = `${s.progress_percent}%`;
        progressWrapper.appendChild(progressBar);
        
        const progressText = document.createElement('small');
        progressText.className = 'text-muted';
        progressText.textContent = `${s.published}/${s.total_stories}`;
        
        progressDiv.appendChild(progressWrapper);
        progressDiv.appendChild(progressText);
        progressCell.appendChild(progressDiv);
        
        // Column 5: Spacing (editable)
        const spacingCell = row.insertCell(5);
        const spacingInput = document.createElement('input');
        spacingInput.type = 'number';
        spacingInput.className = 'form-control form-control-sm';
        spacingInput.style.width = '80px';
        spacingInput.value = s.spacing_days;
        spacingInput.min = '1';
        spacingInput.max = '30';
        spacingInput.onchange = () => updateSeriesSpacing(s.name, spacingInput.value);
        spacingCell.appendChild(spacingInput);
        
        // Column 6: Actions (Delete button)
        const actionsCell = row.insertCell(6);
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.title = 'Delete Series';
        deleteBtn.onclick = () => deleteSeries(s.name);
        actionsCell.appendChild(deleteBtn);
    });
}

function filterStoriesBySeries(seriesName) {
    if (!seriesName) return;
    
    // Store the series filter in sessionStorage
    sessionStorage.setItem('storiesFilterSeries', seriesName);
    sessionStorage.setItem('storiesFilterStatus', 'All');
    
    // Navigate to stories page
    window.location.href = '/stories';
}

// ============================================
// SERIES ACTIONS
// ============================================

async function addSeries() {
    const name = prompt('Enter series name:');
    if (!name || !name.trim()) return;
    
    const cleanName = name.trim();
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: cleanName, spacing_days: 7 })
        });
        
        if (response.ok) {
            await loadSeries();
            showToast(`Series "${cleanName}" added`, 'success');
        } else {
            const error = await response.json();
            showToast('Error adding series: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error adding series: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function updateSeriesSpacing(seriesName, days) {
    const spacingDays = parseInt(days);
    if (isNaN(spacingDays) || spacingDays < 1 || spacingDays > 30) {
        showToast('Spacing must be between 1 and 30', 'error');
        loadSeries();
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spacing_days: spacingDays })
        });
        
        if (response.ok) {
            await loadSeries();
            showToast('Spacing updated', 'success');
        } else {
            const error = await response.json();
            showToast('Error updating spacing: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error updating spacing: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteSeries(seriesName) {
    if (!confirm(`Are you sure you want to delete the series "${seriesName}"?\n\nThis will NOT delete the stories, only remove the series association.`)) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        
        if (response.ok) {
            await loadSeries();
            showToast(`Series "${seriesName}" deleted`, 'success');
        } else {
            const error = await response.json();
            showToast('Error deleting series: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error deleting series: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadSeries();
});

// Make functions globally available
window.sortSeries = sortSeries;
window.addSeries = addSeries;
window.updateSeriesSpacing = updateSeriesSpacing;
window.deleteSeries = deleteSeries;
window.filterStoriesBySeries = filterStoriesBySeries;