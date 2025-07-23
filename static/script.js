/* script.js */
/* Version: 1.2.14 */
/* Note: Replaced prompt-based Quick Adjust Points with modal handling for incentive.html (version 1.2.7). Added delete-feedback-form handling for admin_delete_feedback route. Maintained CSS load check fix from version 1.2.12. Ensured compatibility with app.py (version 1.2.25), macros.html (version 1.2.4), and Bootstrap 5.3.0. No changes to core functionality (scoreboard updates, voting, form submissions, rule reordering). */

document.addEventListener('DOMContentLoaded', function () {
    // CSS Load Check
    const cssStatusElement = document.getElementById("css-status");
    fetch("/static/style.css?v=" + new Date().getTime())
        .then(response => {
            if (!response.ok) throw new Error("CSS fetch failed: " + response.status);
            return response.text();
        })
        .then(css => {
            console.log("CSS Loaded Successfully:", css.substring(0, 50) + "...");
            if (cssStatusElement) {
                cssStatusElement.textContent = "CSS Load Status: Loaded";
            }
        })
        .catch(error => {
            console.error("CSS Load Error:", error);
            if (cssStatusElement) {
                cssStatusElement.textContent = "CSS Load Status: Failed";
            }
        });

    // Quick Adjust Points Modal Handling
    const quickAdjustLinks = document.querySelectorAll('.quick-adjust-link');
    quickAdjustLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const points = this.getAttribute('data-points');
            const reason = this.getAttribute('data-reason');
            document.getElementById('quick_adjust_points').value = points;
            document.getElementById('quick_adjust_reason').value = reason;
            const modal = new bootstrap.Modal(document.getElementById('quickAdjustModal'));
            modal.show();
        });
    });

    // Quick Adjust Form Submission
    const quickAdjustForm = document.getElementById('quickAdjustForm');
    if (quickAdjustForm) {
        quickAdjustForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            fetch(this.action, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.redirected || !response.ok) {
                    alert('Session expired or error occurred. Please log in again.');
                    window.location.href = '/admin';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) {
                        bootstrap.Modal.getInstance(document.getElementById('quickAdjustModal')).hide();
                        window.location.reload();
                    }
                }
            })
            .catch(error => {
                console.error('Error submitting quick adjust form:', error);
                alert('Failed to adjust points');
            });
        });
    }

    // Rule Link Handling for Adjust Points (quick_adjust.html)
    const ruleLinks = document.querySelectorAll('.rule-link');
    ruleLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const points = document.getElementById('adjust_points');
            const reason = document.getElementById('adjust_reason');
            if (points && reason) {
                points.value = this.getAttribute('data-points');
                reason.value = this.getAttribute('data-reason');
            }
        });
    });

    // Scoreboard Update
    const scoreboardTable = document.querySelector('#scoreboard tbody');
    if (scoreboardTable) {
        function updateScoreboard() {
            fetch('/data')
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    return response.json();
                })
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
                                <td>$${data.pot_info[emp.role.toLowerCase().replace(/ /g, '_') + '_point_value'] ? (emp.score < 50 ? 0 : (emp.score * data.pot_info[emp.role.toLowerCase().replace(/ /g, '_') + '_point_value']).toFixed(2)) : '0.00'}</td>
                            </tr>`;
                        scoreboardTable.insertAdjacentHTML('beforeend', row);
                    });
                })
                .catch(error => console.error('Error updating scoreboard:', error));
        }

        function getScoreClass(score) {
            const ranges = [
                { max: 5, class: 'score-low-0' }, { max: 10, class: 'score-low-5' }, { max: 15, class: 'score-low-10' },
                { max: 20, class: 'score-low-15' }, { max: 25, class: 'score-low-20' }, { max: 30, class: 'score-low-25' },
                { max: 35, class: 'score-low-30' }, { max: 40, class: 'score-low-35' }, { max: 45, class: 'score-low-40' },
                { max: 50, class: 'score-low-45' }, { max: 55, class: 'score-mid-50' }, { max: 60, class: 'score-mid-55' },
                { max: 65, class: 'score-mid-60' }, { max: 70, class: 'score-mid-65' }, { max: 75, class: 'score-mid-70' },
                { max: 80, class: 'score-high-75' }, { max: 85, class: 'score-high-80' }, { max: 90, class: 'score-high-85' },
                { max: 95, class: 'score-high-90' }, { max: 100, class: 'score-high-95' }
            ];
            return ranges.find(range => score <= range.max)?.class || 'score-high-100';
        }

        updateScoreboard();
        setInterval(updateScoreboard, 60000);
    }

    function handleResponse(response) {
        if (response.redirected || !response.ok) {
            alert('Session expired or error occurred. Please log in again.');
            window.location.href = '/admin';
            return null;
        }
        return response.json().then(data => {
            if (!data) throw new Error('No data received');
            return data;
        }).catch(error => {
            console.error('Invalid JSON response:', error);
            alert('Session expired or invalid response. Please log in again.');
            window.location.href = '/admin';
            return null;
        });
    }

    // Vote Form Handling
    const voteForm = document.getElementById('voteForm');
    if (voteForm) {
        voteForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const initials = document.getElementById('hiddenInitials');
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
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) {
                        voteForm.reset();
                        document.querySelectorAll('#voteTableBody input[type="radio"]').forEach(radio => {
                            if (radio.value === "0") radio.checked = true;
                            else radio.checked = false;
                        });
                        voteForm.style.display = 'none';
                        document.getElementById('voteInitialsForm').style.display = 'block';
                        document.getElementById('voterInitials').value = '';
                        if (scoreboardTable) updateScoreboard();
                    }
                }
            })
            .catch(error => console.error('Error submitting vote:', error));
        });

        const checkInitialsBtn = document.getElementById('checkInitialsBtn');
        if (checkInitialsBtn) {
            checkInitialsBtn.addEventListener('click', function () {
                const initials = document.getElementById('voterInitials');
                if (!initials || !initials.value.trim()) {
                    alert('Please enter your initials.');
                    return;
                }
                fetch('/check_vote', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `initials=${encodeURIComponent(initials.value.trim())}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data && !data.can_vote) {
                        alert(data.message);
                    } else if (data && data.can_vote) {
                        fetch('/data')
                            .then(response => response.json())
                            .then(data => {
                                const valid = data.scoreboard.some(emp => emp.initials.toLowerCase() === initials.value.toLowerCase());
                                if (valid) {
                                    document.getElementById('hiddenInitials').value = initials.value;
                                    document.getElementById('voteInitialsForm').style.display = 'none';
                                    voteForm.style.display = 'block';
                                } else {
                                    alert('Invalid initials');
                                }
                            })
                            .catch(error => console.error('Error checking initials:', error));
                    }
                })
                .catch(error => console.error('Error checking vote:', error));
            });
        }
    }

    // Feedback Form Handling
    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const comment = document.getElementById('feedback_comment');
            if (!comment || !comment.value.trim()) {
                alert('Please enter a feedback comment.');
                return;
            }
            fetch('/submit_feedback', {
                method: 'POST',
                body: new FormData(feedbackForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error submitting feedback:', error));
        });
    }

    // Admin Form Handlers
    const pauseVotingForm = document.getElementById('pauseVotingFormUnique');
    if (pauseVotingForm) {
        pauseVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Pause the current voting session?')) {
                fetch('/pause_voting', {
                    method: 'POST',
                    body: new FormData(pauseVotingForm)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error pausing voting:', error));
            }
        });
    }

    const closeVotingForm = document.getElementById('closeVotingFormUnique');
    if (closeVotingForm) {
        closeVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const password = document.querySelector('#closeVotingFormUnique input[name="password"]');
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
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error closing voting:', error));
            }
        });
    }

    const markReadForms = document.querySelectorAll('form[action="/admin/mark_feedback_read"]');
    if (markReadForms) {
        markReadForms.forEach(form => {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                fetch('/admin/mark_feedback_read', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error marking feedback read:', error);
                    alert('Failed to mark feedback as read. Please try again or log in.');
                });
            });
        });
    }

    const deleteFeedbackForms = document.querySelectorAll('form[action="/admin/delete_feedback"]');
    if (deleteFeedbackForms) {
        deleteFeedbackForms.forEach(form => {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                if (confirm('Are you sure you want to delete this feedback?')) {
                    fetch('/admin/delete_feedback', {
                        method: 'POST',
                        body: new FormData(form)
                    })
                    .then(handleResponse)
                    .then(data => {
                        if (data) {
                            alert(data.message);
                            if (data.success) window.location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Error deleting feedback:', error);
                        alert('Failed to delete feedback. Please try again or log in.');
                    });
                }
            });
        });
    }

    const adjustPointsForm = document.getElementById('adjustPointsFormUnique');
    if (adjustPointsForm) {
        adjustPointsForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const employeeId = document.getElementById('adjust_employee_id');
            const points = document.getElementById('adjust_points');
            const reason = document.getElementById('adjust_reason');
            if (!employeeId?.value || !points?.value || !reason?.value) {
                alert('All required fields must be filled.');
                return;
            }
            fetch('/admin/adjust_points', {
                method: 'POST',
                body: new FormData(adjustPointsForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adjusting points:', error));
        });

        document.querySelectorAll('#adjustPointsFormUnique .rule-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const points = document.getElementById('adjust_points');
                const reason = document.getElementById('adjust_reason');
                if (points && reason) {
                    points.value = link.getAttribute('data-points');
                    reason.value = link.getAttribute('data-reason');
                }
            });
        });
    }

    const addRuleForm = document.getElementById('addRuleFormUnique');
    if (addRuleForm) {
        addRuleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const description = document.getElementById('add_rule_description');
            const points = document.getElementById('add_rule_points');
            if (!description?.value || !points?.value) {
                alert('Description and points are required.');
                return;
            }
            fetch('/admin/add_rule', {
                method: 'POST',
                body: new FormData(addRuleForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adding rule:', error));
        });
    }

    const editRuleForms = document.querySelectorAll('.edit-rule-form');
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
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error editing rule:', error));
        });
    });

    const removeRuleForms = document.querySelectorAll('.remove-rule-form');
    removeRuleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this rule?')) {
                fetch('/admin/remove_rule', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error removing rule:', error));
            }
        });
    });

    const resetScoresForm = document.getElementById('resetScoresFormUnique');
    if (resetScoresForm) {
        resetScoresForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Reset all scores to 50 and log to history?')) {
                fetch('/admin/reset', {
                    method: 'POST',
                    body: new FormData(resetScoresForm)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.href = '/';
                    }
                })
                .catch(error => console.error('Error resetting scores:', error));
            }
        });
    }

    const addEmployeeForm = document.getElementById('addEmployeeFormUnique');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const name = document.getElementById('add_employee_name');
            const initials = document.getElementById('add_employee_initials');
            const role = document.getElementById('add_employee_role');
            if (!name?.value || !initials?.value || !role?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/add', {
                method: 'POST',
                body: new FormData(addEmployeeForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adding employee:', error));
        });
    }

    const editEmployeeForm = document.getElementById('editEmployeeFormUnique');
    if (editEmployeeForm) {
        editEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const employeeId = document.getElementById('edit_employee_id');
            const name = document.getElementById('edit_employee_name');
            const role = document.getElementById('edit_employee_role');
            if (!employeeId?.value || !name?.value || !role?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/edit_employee', {
                method: 'POST',
                body: new FormData(editEmployeeForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
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
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .then(data => {
                        if (data) {
                            alert(data.message);
                            if (data.success) window.location.reload();
                        }
                    })
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
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .then(data => {
                        if (data) {
                            alert(data.message);
                            if (data.success) window.location.reload();
                        }
                    })
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
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: `employee_id=${encodeURIComponent(id)}`
                    })
                    .then(handleResponse)
                    .then(data => {
                        if (data) {
                            alert(data.message);
                            if (data.success) window.location.reload();
                        }
                    })
                    .catch(error => console.error('Error deleting employee:', error));
                }
            });
        }
    }

    const updatePotForm = document.getElementById('updatePotFormUnique');
    if (updatePotForm) {
        updatePotForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const salesDollars = document.getElementById('update_pot_sales_dollars');
            const bonusPercent = document.getElementById('update_pot_bonus_percent');
            if (!salesDollars?.value || !bonusPercent?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/update_pot', {
                method: 'POST',
                body: new FormData(updatePotForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error updating pot:', error));
        });
    }

    const updatePriorYearSalesForm = document.getElementById('updatePriorYearSalesFormUnique');
    if (updatePriorYearSalesForm) {
        updatePriorYearSalesForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const priorYearSales = document.getElementById('update_prior_year_sales_prior_year_sales');
            if (!priorYearSales?.value) {
                alert('Prior year sales is required.');
                return;
            }
            fetch('/admin/update_prior_year_sales', {
                method: 'POST',
                body: new FormData(updatePriorYearSalesForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error updating prior year sales:', error));
        });
    }

    const setPointDecayForm = document.getElementById('setPointDecayFormUnique');
    if (setPointDecayForm) {
        setPointDecayForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const roleName = document.getElementById('set_point_decay_role_name');
            const points = document.getElementById('set_point_decay_points');
            if (!roleName?.value || !points?.value) {
                alert('Role and points are required.');
                return;
            }
            fetch('/admin/set_point_decay', {
                method: 'POST',
                body: new FormData(setPointDecayForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error setting point decay:', error));
        });
    }

    const addRoleForm = document.getElementById('addRoleFormUnique');
    if (addRoleForm) {
        addRoleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const roleName = document.getElementById('add_role_role_name');
            const percentage = document.getElementById('add_role_percentage');
            if (!roleName?.value || !percentage?.value) {
                alert('Role name and percentage are required.');
                return;
            }
            fetch('/admin/add_role', {
                method: 'POST',
                body: new FormData(addRoleForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adding role:', error));
        });
    }

    const editRoleForms = document.querySelectorAll('.editRoleFormUnique');
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
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error editing role:', error));
        });
    });

    const removeRoleForms = document.querySelectorAll('.removeRoleFormUnique');
    removeRoleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (confirm('Are you sure you want to remove this role?')) {
                fetch('/admin/remove_role', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error removing role:', error));
            }
        });
    });

    const updateAdminForm = document.getElementById('updateAdminFormUnique');
    if (updateAdminForm) {
        updateAdminForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const oldUsername = document.getElementById('update_admin_old_username');
            const newUsername = document.getElementById('update_admin_new_username');
            const newPassword = document.getElementById('update_admin_new_password');
            if (!oldUsername?.value || !newUsername?.value || !newPassword?.value) {
                alert('All fields are required.');
                return;
            }
            fetch('/admin/update_admin', {
                method: 'POST',
                body: new FormData(updateAdminForm)
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error updating admin:', error));
        });
    }

    const masterResetForm = document.getElementById('masterResetFormUnique');
    if (masterResetForm) {
        masterResetForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const password = document.getElementById('master_reset_password');
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
                .then(data => {
                    if (data) {
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
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
            .then(data => {
                if (data) {
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error updating settings:', error));
        });
    });

    // Rule Reordering
    const rulesList = document.getElementById('RulesList');
    if (rulesList && typeof Sortable !== 'undefined') {
        Sortable.create(rulesList, {
            animation: 150,
            onEnd: function () {
                const order = Array.from(rulesList.querySelectorAll('li')).map(li => li.getAttribute('data-description'));
                fetch('/admin/reorder_rules', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'order[]=' + order.map(encodeURIComponent).join('&order[]=')
                })
                .then(handleResponse)
                .then(data => {
                    if (data && !data.success) alert(data.message);
                })
                .catch(error => console.error('Error reordering rules:', error));
            }
        });
    }
});