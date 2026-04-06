// ============================================
// MAIN APP - Simplified
// ============================================

async function updateLeaderboardTotal() {
    try {
        const res = await fetch(`${API_BASE}/stories/leaderboard-status`);
        if (res.ok) {
            const data = await res.json();
            const countEl = document.getElementById('leaderboardCount');
            const amountEl = document.getElementById('leaderboardAmount');
            if (countEl) countEl.textContent = data.total || 0;
            if (amountEl) amountEl.textContent = ((data.total_nanos || 0) / 1000000000).toFixed(2);
        }
    } catch (e) {
        console.error('Error updating leaderboard total:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateLeaderboardTotal();
    setInterval(updateLeaderboardTotal, 30000);
});