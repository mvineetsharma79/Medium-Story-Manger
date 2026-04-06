// ============================================
// SERIES PAGE - API calls and rendering only (NO HTML)
// ============================================

async function loadSeries() {
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/series/list`);
        const data = await res.json();
        
        const tbody = document.getElementById('seriesTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!data.series || data.series.length === 0) {
            const row = tbody.insertRow();
            const cell = row.insertCell(0);
            cell.colSpan = 4;
            cell.className = 'text-center text-muted';
            cell.textContent = 'No series found. Click "Add Series" to create one.';
            return;
        }
        
        for (const s of data.series) {
            const row = tbody.insertRow();
            
            // Series Name cell
            const nameCell = row.insertCell(0);
            const nameStrong = document.createElement('strong');
            nameStrong.textContent = s.name;
            nameCell.appendChild(nameStrong);
            
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
            deleteBtn.onclick = () => deleteSeries(s.name);
            actionsCell.appendChild(deleteBtn);
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

async function addSeries() {
    const name = prompt('Enter series name:');
    if (!name || !name.trim()) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/series/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim(), spacing_days: 7 })
        });
        
        if (response.ok) {
            await loadSeries();
            showToast('Series added', 'success');
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
    if (!confirm(`Delete "${seriesName}"? This will NOT delete the stories.`)) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/series/${encodeURIComponent(seriesName)}`, { method: 'DELETE' });
        
        if (response.ok) {
            await loadSeries();
            showToast('Series deleted', 'success');
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

document.addEventListener('DOMContentLoaded', loadSeries);