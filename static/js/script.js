document.addEventListener('DOMContentLoaded', function () {
    const scoreboardTable = document.querySelector('#scoreboard tbody');
    if (scoreboardTable) {
        function updateScoreboard() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    scoreboardTable.innerHTML = '';
                    data.scoreboard.forEach(emp => {
                        const scoreClass = getScoreClass(emp.score);
                        const row = `
                            <tr class="${scoreClass}">
                                <td>${emp.employee_id}</td>
                                <td>${emp.name}</td>
                                <td>${emp.score}</td>
                                <td>${emp.role.charAt(0).toUpperCase() + emp.role.slice(1)}</td>
                                <td>$${data.pot_info[emp.role + '_point_value'] ? (emp.score < 50 ? 0 : (emp.score * data.pot_info[emp.role + '_point_value']).toFixed(2)) : '0.00'}</td>
                            </tr>`;
                        scoreboardTable.insertAdjacentHTML('beforeend', row);
                    });
                })
                .catch(error => console.error('Error updating scoreboard:', error));
        }

        function getScoreClass(score) {
            if (score <= 5) return 'score-low-0';
            if (score <= 10) return 'score-low-5';
            if (score <= 15) return 'score-low-10';
            if (score <= 20) return 'score-low-15';
            if (score <= 25) return 'score-low-20';
            if (score <= 30) return 'score-low-25';
            if (score <= 35) return 'score-low-30';
            if (score <= 40) return 'score-low-35';
            if (score <= 45) return 'score-low-40';
            if (score <= 50) return 'score-low-45';
            if (score <= 55) return 'score-mid-50';
            if (score <= 60) return 'score-mid-55';
            if (score <= 65) return 'score-mid-60';
            if (score <= 70) return 'score-mid-65';
            if (score <= 75) return 'score-mid-70';
            if (score <= 80) return 'score-high-75';
            if (score <= 85) return 'score-high-80';
            if (score <= 90) return 'score-high-85';
            if (score <= 95) return 'score-high-90';
            if (score <= 100) return 'score-high-95';
            return 'score-high-100';
        }

        // Initial load
        updateScoreboard();
        // Update every 60 seconds
        setInterval(updateScoreboard, 60000);
    }

    // Quick adjust modal handling (already included in incentive.html)
    const adjustModal = document.getElementById('adjustModal');
    if (adjustModal) {
        const adjustBtn = document.getElementById('adjustBtn');
        const closeModal = document.querySelector('#adjustModal .close');
        if (adjustBtn) {
            adjustBtn.addEventListener('click', function () {
                adjustModal.style.display = 'block';
            });
        }
        if (closeModal) {
            closeModal.addEventListener('click', function () {
                adjustModal.style.display = 'none';
            });
        }
        window.addEventListener('click', function (event) {
            if (event.target == adjustModal) {
                adjustModal.style.display = 'none';
            }
        });

        document.querySelectorAll('#quickAdjustForm .rule-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('points').value = link.getAttribute('data-points');
                document.getElementById('reason').value = link.getAttribute('data-reason');
            });
        });

        document.getElementById('quickAdjustForm').addEventListener('submit', function (e) {
            e.preventDefault();
            const employeeId = document.getElementById('employee_id').value;
            const points = document.getElementById('points').value;
            const reason = document.getElementById('reason').value;
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            if (!employeeId || !points || !reason || !username || !password) {
                alert('All required fields must be filled.');
                return;
            }
            fetch('/admin/quick_adjust_points', {
                method: 'POST',
                body: new FormData(this)
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    adjustModal.style.display = 'none';
                    window.location.reload();
                }
            })
            .catch(error => console.error('Error adjusting points:', error));
        });
    }
});