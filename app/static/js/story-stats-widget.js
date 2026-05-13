// static/js/story-stats-widget.js
// Expandable/Collapsible Monthly Stats Widget

class MonthlyStatsWidget {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            apiBase: options.apiBase || '/api',
            ...options
        };

        this.chart = null;
        this.currentYear = new Date().getFullYear();
        this.currentMonth = new Date().getMonth() + 1;
        this.isCollapsed = true; // Default collapsed

        this.init();
    }

    async init() {
        if (!this.container) {
            console.error('Container not found:', this.containerId);
            return;
        }

        // Load HTML template from correct path
        await this.loadTemplate();

        // Attach event listeners
        this.attachEventListeners();

        // Load initial stats
        await this.loadStats();
    }

    async loadTemplate() {
        try {
            // Correct path: /static/templates/components/story-stats-widget.html
            const response = await fetch('/templates/components/story-stats-widget.html');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const html = await response.text();
            this.container.innerHTML = html;
        } catch (error) {
            console.error('Error loading widget template:', error);
            this.container.innerHTML = '<div class="alert alert-danger">Failed to load stats widget</div>';
        }
    }

    attachEventListeners() {
        // Expand/Collapse on header click
        const header = this.container.querySelector('#statsWidgetHeader');
        const body = this.container.querySelector('#statsWidgetBody');
        const icon = this.container.querySelector('.collapse-icon');

        if (header) {
            header.addEventListener('click', (e) => {
                // Don't toggle if clicking on selects or buttons
                if (e.target.closest('select') || e.target.closest('button')) {
                    return;
                }

                if (body) {
                    if (body.classList.contains('show')) {
                        body.classList.remove('show');
                        this.isCollapsed = true;
                        if (icon) icon.classList.add('rotated');
                    } else {
                        body.classList.add('show');
                        this.isCollapsed = false;
                        if (icon) icon.classList.remove('rotated');
                    }
                }
            });
        }

        // Year selector change
        const yearSelect = this.container.querySelector('#statsYearSelect');
        if (yearSelect) {
            yearSelect.value = this.currentYear;
            yearSelect.addEventListener('change', () => {
                this.currentYear = parseInt(yearSelect.value);
                this.loadStats();
                this.notifyParent();
            });
        }

        // Month selector change
        const monthSelect = this.container.querySelector('#statsMonthSelect');
        if (monthSelect) {
            monthSelect.value = this.currentMonth;
            monthSelect.addEventListener('change', () => {
                this.currentMonth = parseInt(monthSelect.value);
                this.loadStats();
                this.notifyParent();
            });
        }

        // Refresh button
        const refreshBtn = this.container.querySelector('#statsRefreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadStats();
            });
        }

        // Sync button
        const syncBtn = this.container.querySelector('#statsSyncBtn');
        if (syncBtn) {
            syncBtn.addEventListener('click', () => {
                this.syncStats();
            });
        }
    }

    async loadStats() {
        this.showLoading(true);
        this.hideError();

        const period = `${this.currentYear}-${String(this.currentMonth).padStart(2, '0')}`;
        const periodDisplay = this.getMonthName(this.currentMonth) + ' ' + this.currentYear;

        // Update display
        const displaySpan = this.container.querySelector('#statsPeriodDisplay');
        if (displaySpan) displaySpan.textContent = periodDisplay;

        try {
            const response = await fetch(`${this.options.apiBase}/stories/monthly-stats/${period}`);
            const data = await response.json();

            if (data.success) {
                this.updateStats(data.totals);
                this.updateChart(data.points);
            } else {
                this.showError(data.message || 'No stats available');
                this.clearStats();
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showError('Failed to load stats: ' + error.message);
            this.clearStats();
        } finally {
            this.showLoading(false);
        }
    }

    async syncStats() {
        const period = `${this.currentYear}-${String(this.currentMonth).padStart(2, '0')}`;
        const monthName = this.getMonthName(this.currentMonth);

        if (!confirm(`Sync stats from Medium for ${monthName} ${this.currentYear}?`)) return;

        this.showLoading(true);
        this.hideError();

        try {
            const response = await fetch(`${this.options.apiBase}/stories/refresh-stats/${period}`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.showToast(`Sync complete: ${data.new_stories || 0} new, ${data.updated_stories || 0} updated`, 'success');
                await this.loadStats();

                // Also refresh the stories table if function exists
                if (typeof window.loadStories === 'function') {
                    await window.loadStories();
                }
            } else {
                this.showError(data.message || 'Sync failed');
            }
        } catch (error) {
            console.error('Error syncing stats:', error);
            this.showError('Failed to sync: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    updateStats(totals) {
        const presentations = this.container.querySelector('.presentations');
        const viewers = this.container.querySelector('.viewers');
        const readers = this.container.querySelector('.readers');
        const followers = this.container.querySelector('.followers');
        const subscribers = this.container.querySelector('.subscribers');
        const readRatio = this.container.querySelector('.read-ratio');

        const presentationsFull = totals.presentations || 0;
        const viewersFull = totals.viewers || 0;
        const readersFull = totals.readers || 0;
        const followersFull = totals.netFollowersGained || 0;
        const subscribersFull = totals.netSubscribersGained || 0;

        const ratio = viewersFull > 0 ? Math.round((readersFull / viewersFull) * 100) : 0;

        if (presentations) {
            presentations.textContent = this.formatNumber(presentationsFull);
            const item = presentations.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', presentationsFull.toLocaleString());
        }

        if (viewers) {
            viewers.textContent = this.formatNumber(viewersFull);
            const item = viewers.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', viewersFull.toLocaleString());
        }

        if (readers) {
            readers.textContent = this.formatNumber(readersFull);
            const item = readers.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', readersFull.toLocaleString());
        }

        if (followers) {
            followers.textContent = this.formatNumber(followersFull);
            const item = followers.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', followersFull.toLocaleString());
        }

        if (subscribers) {
            subscribers.textContent = this.formatNumber(subscribersFull);
            const item = subscribers.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', subscribersFull.toLocaleString());
        }

        if (readRatio) {
            readRatio.textContent = `${ratio}%`;
            const item = readRatio.closest('.stat-item');
            if (item) item.setAttribute('data-full-number', `${ratio}% (${readersFull.toLocaleString()} / ${viewersFull.toLocaleString()})`);
        }
    }

    updateChart(points) {
        const canvas = this.container.querySelector('#monthlyStatsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        if (!points || points.length === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#999';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No data available for this period', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Sort points by timestamp
        const sortedPoints = [...points].sort((a, b) => a.timestamp - b.timestamp);

        // Format labels
        const labels = sortedPoints.map(point => {
            const date = new Date(point.timestamp);
            return `${date.getMonth() + 1}/${date.getDate()}`;
        });

        const viewersData = sortedPoints.map(point => point.viewers || 0);
        const readersData = sortedPoints.map(point => point.readers || 0);

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Viewers',
                        data: viewersData,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.05)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#3498db'
                    },
                    {
                        label: 'Readers',
                        data: readersData,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.05)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#27ae60'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.dataset.label}: ${context.raw.toLocaleString()}`;
                            }
                        }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            font: { size: 11 }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count',
                            font: { size: 11 }
                        },
                        ticks: {
                            callback: function (value) {
                                return value.toLocaleString();
                            },
                            font: { size: 10 }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date',
                            font: { size: 11 }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            font: { size: 9 },
                            autoSkip: true,
                            maxTicksLimit: 15
                        }
                    }
                }
            }
        });
    }

    // Public method to update year/month from parent page
    setYearMonth(year, month) {
        if (year && year !== this.currentYear) {
            this.currentYear = year;
            const yearSelect = this.container.querySelector('#statsYearSelect');
            if (yearSelect) yearSelect.value = year;
        }

        if (month && month !== this.currentMonth) {
            this.currentMonth = month;
            const monthSelect = this.container.querySelector('#statsMonthSelect');
            if (monthSelect) monthSelect.value = month;
        }

        this.loadStats();
    }

    // Public method to get current period
    getCurrentPeriod() {
        return `${this.currentYear}-${String(this.currentMonth).padStart(2, '0')}`;
    }

    // Notify parent when month/year changes
    notifyParent() {
        const event = new CustomEvent('statsPeriodChanged', {
            detail: {
                year: this.currentYear,
                month: this.currentMonth,
                period: this.getCurrentPeriod()
            }
        });
        window.dispatchEvent(event);
    }

    // Public methods to control collapse/expand
    expand() {
        const body = this.container.querySelector('#statsWidgetBody');
        const icon = this.container.querySelector('.collapse-icon');
        if (body && !body.classList.contains('show')) {
            body.classList.add('show');
            this.isCollapsed = false;
            if (icon) icon.classList.remove('rotated');
        }
    }

    collapse() {
        const body = this.container.querySelector('#statsWidgetBody');
        const icon = this.container.querySelector('.collapse-icon');
        if (body && body.classList.contains('show')) {
            body.classList.remove('show');
            this.isCollapsed = true;
            if (icon) icon.classList.add('rotated');
        }
    }

    toggle() {
        if (this.isCollapsed) {
            this.expand();
        } else {
            this.collapse();
        }
    }

    clearStats() {
        const stats = ['presentations', 'viewers', 'readers', 'followers', 'subscribers'];
        stats.forEach(stat => {
            const el = this.container.querySelector(`.${stat}`);
            if (el) el.textContent = '-';
        });

        const readRatio = this.container.querySelector('.read-ratio');
        if (readRatio) readRatio.textContent = '-';

        const canvas = this.container.querySelector('#monthlyStatsChart');
        if (canvas && canvas.getContext) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }

    showLoading(show) {
        const overlay = this.container.querySelector('.loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    showError(message) {
        const errorDiv = this.container.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }
    }

    hideError() {
        const errorDiv = this.container.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'info'} position-fixed bottom-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.style.minWidth = '200px';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    getMonthName(month) {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'];
        return monthNames[month - 1];
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('storyStatsWidget');
    if (container && !window.monthlyStatsWidget) {
        window.monthlyStatsWidget = new MonthlyStatsWidget('storyStatsWidget', {
            apiBase: '/api'
        });
    }
});