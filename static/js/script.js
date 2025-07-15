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

        updateScoreboard();
        setInterval(updateScoreboard, 60000);
    }

    function handleResponse(response) {
        if (response.redirected) {
            window.location.href = response.url;
            return null;
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            if (text.startsWith('<!DOCTYPE')) {
                window.location.href = '/admin';
                throw new Error('Received HTML, redirecting to login');
            }
            try {
                return JSON.parse(text);
            } catch (e) {
                throw new Error('Invalid JSON response');
            }
        });
    }

    const voteForm = document.getElementById('voteForm');
    if (voteForm) {
        voteForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const initials = document.getElementById('initials');
            if (!initials || !initials.value.trim()) {
                alert('Please enter your initials.');
                return;
            }
            const votes = document.querySelectorAll('input[name^="vote_"]:checked');
            let plusVotes = 0, minusVotes = 0;
            votes.forEach(vote => {
                const value = parseInt(vote.value);
                if (value > 0) plusVotes++;
                if (value < 0) minusVotes++;
            });
            if (plusVotes > 2) {
                alert('You can only cast up to 2 positive (+1) votes.');
                return;
            }
            if (minusVotes > 3) {
                alert('You can only cast up to 3 negative (-1) votes.');
                return;
            }
            if (plusVotes + minusVotes > 3) {
                alert('You can only cast a maximum of 3 votes total.');
                return;
            }
            fetch('/vote', {
                method: 'POST',
                body: new FormData(voteForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error submitting vote:', error));
        });

        const checkVoteBtn = document.getElementById('checkVoteBtn');
        if (checkVoteBtn) {
            checkVoteBtn.addEventListener('click', function () {
                const initials = document.getElementById('initials');
                if (!initials || !initials.value.trim()) {
                    alert('Please enter your initials.');
                    return;
                }
                fetch('/check_vote', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `initials=${encodeURIComponent(initials.value.trim())}`
                })
                .then(response => response.json())
                .then(data => alert(data.message))
                .catch(error => console.error('Error checking vote:', error));
            });
        }
    }

    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const comment = document.getElementById('comment');
            if (!comment || !comment.value.trim()) {
                alert('Please enter a feedback comment.');
                return;
            }
            fetch('/submit_feedback', {
                method: 'POST',
                body: new FormData(feedbackForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error submitting feedback:', error));
        });
    }

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
            if (event.target === adjustModal) {
                adjustModal.style.display = 'none';
            }
        });

        const quickAdjustForm = document.getElementById('quickAdjustForm');
        if (quickAdjustForm) {
            document.querySelectorAll('#quickAdjustForm .rule-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const points = document.getElementById('points');
                    const reason = document.getElementById('reason');
                    if (points && reason) {
                        points.value = link.getAttribute('data-points');
                        reason.value = link.getAttribute('data-reason');
                    }
                });
            });

            quickAdjustForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const employeeId = document.getElementById('employee_id');
                const points = document.getElementById('points');
                const reason = document.getElementById('reason');
                const username = document.getElementById('username');
                const password = document.getElementById('password');
                if (!employeeId?.value || !points?.value || !reason?.value || !username?.value || !password?.value) {
                    alert('All required fields must be filled.');
                    return;
                }
                fetch('/admin/quick_adjust_points', {
                    method: 'POST',
                    body: new FormData(quickAdjustForm)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) {
                            adjustModal.style.display = 'none';
                        }
                    }
                })
                .catch(error => console.error('Error adjusting points:', error));
            });
        }
    }

    const pauseVotingForm = document.getElementById('pauseVotingForm');
    if (pauseVotingForm) {
        pauseVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Pause the current voting session?')) {
                fetch('/pause_voting', {
                    method: 'POST',
                    body: new FormData(pauseVotingForm)
                })
                .then(handleResponse)
                .catch(error => console.error('Error pausing voting:', error));
            }
        });
    }

    const closeVotingForm = document.getElementById('closeVotingForm');
    if (closeVotingForm) {
        closeVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const password = document.querySelector('#closeVotingForm input[name="password"]');
            if (!password || !password.value) {
                alert('Admin password is required.');
                return;
            }
            if (confirm('Close the current voting session and process votes?')) {
                fetch('/close_voting', {
                    method: 'POST',
                    body: new FormData(closeVotingForm)
                })
                .then(handleResponse)
                .catch(error => console.error('Error closing voting:', error));
            }
        });
    }

    const markReadForms = document.querySelectorAll('.markReadForm');
    markReadForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            fetch('/admin/mark_feedback_read', {
                method: 'POST',
                body: new FormData(form)
            })
            .then(handleResponse)
            .catch(error => console.error('Error marking feedback read:', error));
        });
    });

    const adjustPointsForm = document.getElementById('adjustPointsForm');
    if (adjustPointsForm) {
        adjustPointsForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const employeeId = document.getElementById('adjust_employee_id');
            const points = document.getElementById('adjust_points');
            const reason = document.getElementById('reason');
            if (!employeeId?.value || !points?.value || !reason?.value) {
                alert('All required fields must be filled.');
                return;
            }
            fetch('/admin/adjust_points', {
                method: 'POST',
                body: new FormData(adjustPointsForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error adjusting points:', error));
        });

        document.querySelectorAll('.rule-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const points = document.getElementById('adjust_points');
                const reason = document.getElementById('reason');
                if (points && reason) {
                    points.value = link.getAttribute('data-points');
                    reason.value = link.getAttribute('data-reason');
                }
            });
        });
    }

    const addRuleForm = document.getElementById('addRuleForm');
    if (addRuleForm) {
        addRuleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const description = document.getElementById('description');
            const points = document.getElementById('rule_points');
            if (!description?.value || !points?.value) {
                alert('Description and points are required.');
                return;
            }
            fetch('/admin/add_rule', {
                method: 'POST',
                body: new FormData(addRuleForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error adding rule:', error));
        });
    }

    const editRuleForms = document.querySelectorAll('.editRuleForm');
    editRuleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const newDescription = form.querySelector('input[name="new_description"]');
            const points = form.querySelector('input[name="points"]');
            if (!newDescription?.value || !points?.value) {
                alert('Description and points are required.');
                return;
            }
            fetch('/admin/edit_rule', {
                method: 'POST',
                body: new FormData(form)
            })
            .then(handleResponse)
            .catch(error => console.error('Error editing rule:', error));
        });
    });

    const removeRuleForms = document.querySelectorAll('.removeRuleForm');
    removeRuleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this rule?')) {
                fetch('/admin/remove_rule', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .catch(error => console.error('Error removing rule:', error));
            }
        });
    });

    const resetScoresForm = document.getElementById('resetScoresForm');
    if (resetScoresForm) {
        resetScoresForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Reset all scores to 50 and log to history?')) {
                fetch('/admin/reset', {
                    method: 'POST',
                    body: new FormData(resetScoresForm)
                })
                .then(handleResponse)
                .catch(error => console.error('Error resetting scores:', error));
            }
        });
    }

    const addEmployeeForm = document.getElementById('addEmployeeForm');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const name = document.getElementById('name');
            const initials = document.getElementById('initials');
            const role = document.getElementById('role');
            if (!name?.value || !initials?.value || !role?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/add', {
                method: 'POST',
                body: new FormData(addEmployeeForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error adding employee:', error));
        });
    }

    const editEmployeeForm = document.getElementById('editEmployeeForm');
    if (editEmployeeForm) {
        editEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const employeeId = document.getElementById('edit_employee_id');
            const name = document.getElementById('edit_name');
            const role = document.getElementById('edit_role');
            if (!employeeId?.value || !name?.value || !role?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/edit_employee', {
                method: 'POST',
                body: new FormData(editEmployeeForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error editing employee:', error));
        });

        const retireBtn = document.getElementById('retireBtn');
        if (retireBtn) {
            retireBtn.addEventListener('click', function () {
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    alert('Please select an employee.');
                    return;
                }
                if (confirm('Retire this employee?')) {
                    fetch('/admin/retire_employee', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .catch(error => console.error('Error retiring employee:', error));
                }
            });
        }

        const reactivateBtn = document.getElementById('reactivateBtn');
        if (reactivateBtn) {
            reactivateBtn.addEventListener('click', function () {
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    alert('Please select an employee.');
                    return;
                }
                if (confirm('Reactivate this employee?')) {
                    fetch('/admin/reactivate_employee', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .catch(error => console.error('Error reactivating employee:', error));
                }
            });
        }

        const deleteBtn = document.getElementById('deleteBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function () {
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    alert('Please select an employee.');
                    return;
                }
                if (confirm('Permanently delete this employee?')) {
                    fetch('/admin/delete_employee', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .catch(error => console.error('Error deleting employee:', error));
                }
            });
        }
    }

    const updatePotForm = document.getElementById('updatePotForm');
    if (updatePotForm) {
        updatePotForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const salesDollars = document.getElementById('sales_dollars');
            const bonusPercent = document.getElementById('bonus_percent');
            if (!salesDollars?.value || !bonusPercent?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/update_pot', {
                method: 'POST',
                body: new FormData(updatePotForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error updating pot:', error));
        });
    }

    const updatePriorYearSalesForm = document.getElementById('updatePriorYearSalesForm');
    if (updatePriorYearSalesForm) {
        updatePriorYearSalesForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const priorYearSales = document.getElementById('prior_year_sales');
            if (!priorYearSales?.value) {
                alert('Prior year sales is required.');
                return;
            }
            fetch('/admin/update_prior_year_sales', {
                method: 'POST',
                body: new FormData(updatePriorYearSalesForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error updating prior year sales:', error));
        });
    }

    const setPointDecayForm = document.getElementById('setPointDecayForm');
    if (setPointDecayForm) {
        setPointDecayForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const roleName = document.getElementById('role_name');
            const points = document.getElementById('points');
            if (!roleName?.value || !points?.value) {
                alert('Role and points are required.');
                return;
            }
            fetch('/admin/set_point_decay', {
                method: 'POST',
                body: new FormData(setPointDecayForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error setting point decay:', error));
        });
    }

    const addRoleForm = document.getElementById('addRoleForm');
    if (addRoleForm) {
        addRoleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const roleName = document.getElementById('role_name');
            const percentage = document.getElementById('percentage');
            if (!roleName?.value || !percentage?.value) {
                alert('Role name and percentage are required.');
                return;
            }
            fetch('/admin/add_role', {
                method: 'POST',
                body: new FormData(addRoleForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error adding role:', error));
        });
    }

    const editRoleForms = document.querySelectorAll('.editRoleForm');
    editRoleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const newRoleName = form.querySelector('input[name="new_role_name"]');
            const percentage = form.querySelector('input[name="percentage"]');
            if (!newRoleName?.value || !percentage?.value) {
                alert('Role name and percentage are required.');
                return;
            }
            fetch('/admin/edit_role', {
                method: 'POST',
                body: new FormData(form)
            })
            .then(handleResponse)
            .catch(error => console.error('Error editing role:', error));
        });
    });

    const removeRoleForms = document.querySelectorAll('.removeRoleForm');
    removeRoleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this role?')) {
                fetch('/admin/remove_role', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .catch(error => console.error('Error removing role:', error));
            }
        });
    });

    const updateAdminForm = document.getElementById('updateAdminForm');
    if (updateAdminForm) {
        updateAdminForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const oldUsername = document.getElementById('old_username');
            const newUsername = document.getElementById('new_username');
            const newPassword = document.getElementById('new_password');
            if (!oldUsername?.value || !newUsername?.value || !newPassword?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/update_admin', {
                method: 'POST',
                body: new FormData(updateAdminForm)
            })
            .then(handleResponse)
            .catch(error => console.error('Error updating admin:', error));
        });
    }

    const masterResetForm = document.getElementById('masterResetForm');
    if (masterResetForm) {
        masterResetForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const password = document.getElementById('password');
            if (!password?.value) {
                alert('Master password is required.');
                return;
            }
            if (confirm('Reset all voting data and history? This cannot be undone.')) {
                fetch('/admin/master_reset', {
                    method: 'POST',
                    body: new FormData(masterResetForm)
                })
                .then(handleResponse)
                .catch(error => console.error('Error performing master reset:', error));
            }
        });
    }

    const settingsForms = document.querySelectorAll('form[id^="settingsForm"]');
    settingsForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const key = form.querySelector('input[name="key"]')?.value;
            const value = form.querySelector('input[name="value"]')?.value || form.querySelector('textarea[name="value"]')?.value;
            if (!key || !value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/settings', {
                method: 'POST',
                body: new FormData(form)
            })
            .then(handleResponse)
            .catch(error => console.error('Error updating settings:', error));
        });
    });
});