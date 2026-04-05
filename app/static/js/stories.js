// ============================================
// Series Management Functions
// ============================================

let seriesSortState = { column: 'name', direction: 'asc' };

function sortSeries(column) {
    const direction = seriesSortState.column === column && seriesSortState.direction === 'asc' ? 'desc' : 'asc';
    seriesSortState = { column, direction };
    const sorted = [...window.allSeries].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'total_stories' || column === 'published') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    renderSeriesTable(sorted);
    updateSortIcons('series', column, direction);
}

async function loadSeries() {
    try {
        const res = await fetch(`${API_BASE}/series/`);
        window.allSeries = await res.json();
        
        document.getElementById('content').innerHTML = `
            <div class="d-flex justify-content-between mb-3">
                <h1 class="h3">Series</h1>
                <button class="btn btn-sm btn-primary" onclick="addSeries()"><i class="bi bi-plus-lg"></i> Add Series</button>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead id="seriesTableHeader" class="table-light">
                        <tr>
                            <th class="sortable" data-sort="name" onclick="sortSeries('name')">Series Name <i class="bi bi-arrow-down-up sort-icon"></i></th>
                            <th class="sortable" data-sort="total_stories" onclick="sortSeries('total_stories')">Progress <i class="bi bi-arrow-down-up sort-icon"></i></th>
                            <th class="sortable" data-sort="spacing_days" onclick="sortSeries('spacing_days')">Spacing (days) <i class="bi bi-arrow-down-up sort-icon"></i></th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="seriesTableBody"></tbody>
                </table>
            </div>
        `;
        renderSeriesTable(window.allSeries);
        sortSeries(seriesSortState.column);
    } catch (error) {
        console.error('Error loading series:', error);
        document.getElementById('content').innerHTML = `<div class="alert alert-danger">Error loading series: ${error.message}</div>`;
    }
}

function renderSeriesTable(series) {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) return;
    
    if (!series || !Array.isArray(series)) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No series available</td</tr>';
        return;
    }
    
    const { column, direction } = seriesSortState;
    const sorted = [...series].sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        if (column === 'total_stories' || column === 'published' || column === 'spacing_days') {
            aVal = aVal || 0;
            bVal = bVal || 0;
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = (aVal || '').toString().toLowerCase();
        bVal = (bVal || '').toString().toLowerCase();
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    tbody.innerHTML = sorted.map(s => `
        <tr>
            <td><strong class="series-link" onclick="filterBySeries('${escapeHtml(s.name)}')">${escapeHtml(s.name)}</strong></td>
            <td>
                <div class="d-flex gap-2 align-items-center">
                    <div class="progress" style="width:150px;height:6px;">
                        <div class="progress-bar" style="width:${(s.published / (s.total_stories || 1)) * 100}%"></div>
                    </div>
                    <small>${s.published}/${s.total_stories || 0}</small>
                </div>
            </td
            <td>
                <input type="number" class="form-control form-control-sm" style="width:80px;" value="${s.spacing_days}" 
                       onchange="updateSeriesSpacing('${escapeHtml(s.name)}', this.value)">
            </td
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteSeries('${escapeHtml(s.name)}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td
         </tr
    `).join('');
}

async function addSeries() {
    const name = prompt('Enter series name:');
    if (!name || name.trim() === '') return;
    
    const cleanName = name.trim();
    
    try {
        const res = await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: cleanName, spacing_days: 7 })
        });
        
        if (res.ok) {
            await loadSeries();
            // Also refresh series dropdown in modals
            if (typeof loadAllSeries === 'function') {
                await loadAllSeries();
            }
        } else {
            const error = await res.json();
            alert('Failed to add series: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error adding series:', error);
        alert('Error adding series: ' + error.message);
    }
}

async function updateSeriesSpacing(seriesName, days) {
    const spacingDays = parseInt(days);
    if (isNaN(spacingDays) || spacingDays < 1 || spacingDays > 30) {
        alert('Spacing days must be between 1 and 30');
        await loadSeries();
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spacing_days: spacingDays })
        });
        
        if (!res.ok) {
            const error = await res.json();
            alert('Failed to update spacing: ' + (error.detail || 'Unknown error'));
            await loadSeries();
        }
    } catch (error) {
        console.error('Error updating series spacing:', error);
        alert('Error updating spacing: ' + error.message);
        await loadSeries();
    }
}

async function deleteSeries(seriesName) {
    if (!confirm(`Are you sure you want to delete the series "${seriesName}"?\n\nThis will NOT delete the stories, only remove the series association.`)) {
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        
        if (res.ok) {
            await loadSeries();
            // Also refresh series dropdown in modals
            if (typeof loadAllSeries === 'function') {
                await loadAllSeries();
            }
        } else {
            const error = await res.json();
            alert('Failed to delete series: ' + (error.detail || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Error deleting series: ' + error.message);
    }
}

function filterBySeries(seriesName) {
    // This function is called when clicking on a series name
    // It filters the stories view to show only stories from this series
    if (typeof filterState !== 'undefined') {
        filterState.series = seriesName;
        filterState.status = 'All';
    }
    if (typeof loadView === 'function') {
        loadView('stories');
    }
}

// Make functions globally available
window.sortSeries = sortSeries;
window.loadSeries = loadSeries;
window.renderSeriesTable = renderSeriesTable;
window.addSeries = addSeries;
window.updateSeriesSpacing = updateSeriesSpacing;
window.deleteSeries = deleteSeries;
window.filterBySeries = filterBySeries;