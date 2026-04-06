// ============================================
// SERIES PAGE - API calls and rendering only
// ============================================

async function loadSeries() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/series/list`);
        const data = await res.json();
        
        const tbody = document.getElementById('seriesTableBody');
        
        if (!data.series.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No series found</td</tr>';
            return;
        }
        
        tbody.innerHTML = data.series.map(s => `
            <tr>
                <td><strong>${escapeHtml(s.name)}</strong></td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div class="progress" style="width:150px;height:6px;">
                            <div class="progress-bar bg-success" style="width: ${s.progress_percent}%"></div>
                        </div>
                        <small>${s.published}/${s.total_stories}</small>
                    </div>
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" style="width:80px;" value="${s.spacing_days}" 
                           onchange="updateSeriesSpacing('${escapeHtml(s.name)}', this.value)">
                </td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteSeries('${escapeHtml(s.name)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
             </tr
        `).join('');
        
    } catch (error) {
        console.error('Error loading series:', error);
        showToast('Error loading series', 'error');
    } finally {
        hideLoading();
    }
}

async function addSeries() {
    const name = prompt('Enter series name:');
    if (!name || !name.trim()) return;
    
    showLoading();
    try {
        await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim(), spacing_days: 7 })
        });
        await loadSeries();
        showToast('Series added', 'success');
    } catch (error) {
        showToast('Error adding series', 'error');
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
        await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spacing_days: spacingDays })
        });
        await loadSeries();
        showToast('Spacing updated', 'success');
    } catch (error) {
        showToast('Error updating spacing', 'error');
    } finally {
        hideLoading();
    }
}

async function deleteSeries(seriesName) {
    if (!confirm(`Delete "${seriesName}"? This will NOT delete the stories.`)) return;
    
    showLoading();
    try {
        await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        await loadSeries();
        showToast('Series deleted', 'success');
    } catch (error) {
        showToast('Error deleting series', 'error');
    } finally {
        hideLoading();
    }
}

document.addEventListener('DOMContentLoaded', loadSeries);