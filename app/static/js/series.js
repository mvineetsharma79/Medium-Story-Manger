// ============================================
// Series Management Functions
// ============================================

let seriesSortState = { column: 'name', direction: 'asc' };

function sortSeries(column) {
    const direction = seriesSortState.column === column && seriesSortState.direction === 'asc' ? 'desc' : 'asc';
    seriesSortState = { column, direction };
    const sorted = [...window.allSeries].sort((a, b) => {
        let aVal = a[column], bVal = b[column];
        if (column === 'total_stories' || column === 'published') {
            return direction === 'asc' ? (aVal||0) - (bVal||0) : (bVal||0) - (aVal||0);
        }
        return direction === 'asc' ? String(aVal||'').localeCompare(String(bVal||'')) : String(bVal||'').localeCompare(String(aVal||''));
    });
    renderSeriesTable(sorted);
    updateSortIcons('series', column, direction);
}

async function loadSeries() {
    document.getElementById('content').innerHTML = `
        <div class="d-flex justify-content-between mb-3">
            <h1 class="h3">Series</h1>
            <button class="btn btn-sm btn-primary" onclick="addSeries()"><i class="bi bi-plus-lg"></i> Add Series</button>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="seriesTableHeader" class="table-light">
                    <tr>
                        <th class="sortable" data-sort="name" onclick="sortSeries('name')">Series Name <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="total_stories" onclick="sortSeries('total_stories')">Progress <i class="bi bi-arrow-down-up"></i></th>
                        <th class="sortable" data-sort="spacing_days" onclick="sortSeries('spacing_days')">Spacing (days) <i class="bi bi-arrow-down-up"></i></th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="seriesTableBody"></tbody>
            </table>
        </div>
    `;
    renderSeriesTable(window.allSeries);
    sortSeries(seriesSortState.column);
}

function renderSeriesTable(series) {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) return;
    tbody.innerHTML = series.map(s => `
        <tr>
            <td><strong class="series-link" onclick="filterBySeries('${s.name}')">${escapeHtml(s.name)}</strong></td>
            <td><div class="progress" style="width:150px;height:6px;"><div class="progress-bar" style="width:${(s.published / (s.total_stories || 1)) * 100}%"></div></div><small>${s.published}/${s.total_stories || 0}</small></td>
            <td><input type="number" class="form-control form-control-sm" style="width:80px;" value="${s.spacing_days}" onchange="updateSeriesSpacing('${s.name}', this.value)"></td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteSeries('${s.name}')"><i class="bi bi-trash"></i></button></td>
        </tr>`).join('');
}

async function addSeries() {
    const name = prompt('Series name:');
    if (name) {
        await fetch(`${API_BASE}/series/`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ name, spacing_days:7 }) });
        await loadAllSeries();
        await loadView('series');
    }
}

async function updateSeriesSpacing(seriesName, days) {
    await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ spacing_days:parseInt(days) }) });
    await loadView('series');
}

async function deleteSeries(seriesName) {
    if (confirm(`Delete "${seriesName}"?`)) {
        await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method:'DELETE' });
        await loadAllSeries();
        await loadView('series');
    }
}

async function loadAllSeries() {
    const res = await fetch(`${API_BASE}/series/`);
    window.allSeries = await res.json();
}