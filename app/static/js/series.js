// ============================================
// SERIES PAGE - Restored with utils.js support
// ============================================

let allSeries = [];
let currentSort = { column: 'name', direction: 'asc' };

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
        let aVal = a[column];
        let bVal = b[column];
        
        if (column === 'total_stories' || column === 'published') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        if (column === 'spacing_days') {
            aVal = aVal || 7;
            bVal = bVal || 7;
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
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
            cell.colSpan = 4;
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
        cell.colSpan = 4;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No series found. Click "Add Series" to create one.';
        return;
    }
    
    series.forEach(s => {
        const row = tbody.insertRow();
        
        // Series Name cell - clickable to filter stories
        const nameCell = row.insertCell(0);
        const nameLink = document.createElement('a');
        nameLink.href = '#';
        nameLink.textContent = s.name;
        nameLink.style.textDecoration = 'none';
        nameLink.style.fontWeight = 'bold';
        nameLink.onclick = (e) => {
            e.preventDefault();
            filterStoriesBySeries(s.name);
        };
        nameCell.appendChild(nameLink);
        
        // Progress cell
        const progressCell = row.insertCell(1);
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
        
        // Spacing cell
        const spacingCell = row.insertCell(2);
        const spacingInput = document.createElement('input');
        spacingInput.type = 'number';
        spacingInput.className = 'form-control form-control-sm';
        spacingInput.style.width = '80px';
        spacingInput.value = s.spacing_days;
        spacingInput.min = '1';
        spacingInput.max = '30';
        spacingInput.onchange = () => updateSeriesSpacing(s.name, spacingInput.value);
        spacingCell.appendChild(spacingInput);
        
        // Actions cell
        const actionsCell = row.insertCell(3);
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
    sessionStorage.setItem('storiesFilterSeries', seriesName);
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