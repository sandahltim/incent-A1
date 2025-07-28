// script.js
// Version: 1.2.53
// Note: Increased handleModalShown delay to 300ms to ensure DOM readiness, resolving missing username/password errors. Increased handleModalHidden delay to 800ms to fix aria-hidden warning. Corrected addEmployeeForm data handling to fix 400 errors. Enhanced quickAdjustForm and addRoleForm from version 1.2.52. Added logOverlappingElements from version 1.2.47. Retained fixes from version 1.2.52, including debounce function, updatePotForm, and editEmployeeForm. Ensured compatibility with app.py (1.2.70), forms.py (1.2.7), config.py (1.2.6), admin_manage.html (1.2.29), incentive.html (1.2.27), quick_adjust.html (1.2.10), style.css (1.2.15), base.html (1.2.21), macros.html (1.2.10), start_voting.html (1.2.7), settings.html (1.2.6), admin_login.html (1.2.5), incentive_service.py (1.2.17). No removal of core functionality.

document.addEventListener('DOMContentLoaded', function () {
    // Verify Bootstrap Availability
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap 5.3.0 not loaded. Ensure Bootstrap JavaScript is included in base.html.');
        alert('Error: Bootstrap JavaScript not loaded. Please check console for details.');
        return;
    }
    console.log('Bootstrap 5.3.0 Loaded:', bootstrap);

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
            document.getElementById('dynamicStyles').textContent = css;
        })
        .catch(error => {
            console.error("CSS Load Error:", error);
            if (cssStatusElement) {
                cssStatusElement.textContent = "CSS Load Status: Failed";
            }
        });

    // Debounce Function
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Log Overlapping Elements
    function logOverlappingElements() {
        const elements = document.querySelectorAll('body *');
        elements.forEach(el => {
            const zIndex = window.getComputedStyle(el).zIndex;
            if (zIndex && zIndex !== 'auto' && parseInt(zIndex) >= 1000) {
                console.warn(`Element with high z-index detected: ${el.tagName}${el.className ? '.' + el.className : ''} (id: ${el.id || 'none'}), z-index: ${zIndex}, position: ${window.getComputedStyle(el).position}`);
            }
        });
    }

    // Quick Adjust Points Modal Handling
    function handleQuickAdjustClick(e) {
        e.preventDefault();
        const points = this.getAttribute('data-points');
        const reason = this.getAttribute('data-reason');
        const employee = this.getAttribute('data-employee');
        console.log('Quick Adjust Link Clicked:', { points, reason, employee });
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        if (!quickAdjustModal) {
            console.error('Quick Adjust Modal not found');
            return;
        }
        if (quickAdjustModal.parentNode !== document.body) {
            console.log('Moving quickAdjustModal to direct child of body');
            document.body.appendChild(quickAdjustModal);
        }
        console.log('Initializing Quick Adjust Modal');
        clearModalBackdrops();
        logOverlappingElements();
        const modal = new bootstrap.Modal(quickAdjustModal, { backdrop: 'static', keyboard: false });
        quickAdjustModal.removeEventListener('show.bs.modal', handleModalShow);
        quickAdjustModal.removeEventListener('shown.bs.modal', handleModalShown);
        quickAdjustModal.removeEventListener('hidden.bs.modal', handleModalHidden);
        quickAdjustModal.addEventListener('show.bs.modal', handleModalShow);
        quickAdjustModal.addEventListener('shown.bs.modal', () => {
            setTimeout(() => handleModalShown(points, reason, employee), 300); // Increased delay
        });
        quickAdjustModal.addEventListener('hidden.bs.modal', handleModalHidden);
        setTimeout(() => {
            try {
                modal.show();
                console.log('Quick Adjust Modal Shown');
            } catch (error) {
                console.error('Error showing Quick Adjust Modal:', error);
                alert('Error opening Quick Adjust Modal. Please check console for details.');
            }
        }, 100);
    }

    function handleModalShow() {
        console.log('Quick Adjust Modal Show Event');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        quickAdjustModal.removeAttribute('inert');
        const inputs = quickAdjustModal.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            input.disabled = false;
            input.style.pointerEvents = 'auto';
            input.style.opacity = '1';
            input.style.cursor = input.tagName === 'SELECT' ? 'pointer' : 'text';
            console.log(`Input Enabled: ${input.id}, Disabled: ${input.disabled}, PointerEvents: ${input.style.pointerEvents}, Opacity: ${input.style.opacity}, Cursor: ${input.style.cursor}`);
        });
    }

    function handleModalShown(points, reason, employee) {
        console.log('Quick Adjust Modal Fully Shown');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        const form = document.getElementById('adjustPointsForm');
        if (!form) {
            console.error('Quick Adjust Form not found');
            return;
        }
        const employeeInput = form.querySelector('#quick_adjust_employee_id');
        const pointsInput = form.querySelector('#quick_adjust_points');
        const reasonInput = form.querySelector('#quick_adjust_reason');
        const notesInput = form.querySelector('#quick_adjust_notes');
        const usernameInput = form.querySelector('#quick_adjust_username');
        const passwordInput = form.querySelector('#quick_adjust_password');
        const inputStatus = {
            employeeInput: !!employeeInput,
            pointsInput: !!pointsInput,
            reasonInput: !!reasonInput,
            notesInput: !!notesInput,
            usernameInput: !!usernameInput,
            passwordInput: !!passwordInput
        };
        if (!employeeInput || !pointsInput || !reasonInput || !notesInput || (!usernameInput && !sessionStorage.getItem('admin_id')) || (!passwordInput && !sessionStorage.getItem('admin_id'))) {
            console.error('Quick Adjust Form Inputs Not Found:', inputStatus);
            return;
        }
        form.reset();
        employeeInput.value = employee || '';
        pointsInput.value = points || '';
        reasonInput.value = reason || '';
        notesInput.value = '';
        if (usernameInput) usernameInput.value = '';
        if (passwordInput) passwordInput.value = '';
        console.log('Quick Adjust Form Populated:', {
            employee: employeeInput.value,
            points: pointsInput.value,
            reason: reasonInput.value,
            notes: notesInput.value,
            username: usernameInput ? usernameInput.value : 'N/A',
            password: passwordInput ? '****' : 'N/A'
        });
        quickAdjustModal.style.zIndex = '1100';
        const modalContent = quickAdjustModal.querySelector('.modal-content');
        if (modalContent) modalContent.style.zIndex = '1100';
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.style.zIndex = '1095';
        console.log('Modal Z-Index:', quickAdjustModal.style.zIndex);
        console.log('Modal Content Z-Index:', modalContent?.style.zIndex || 'Not found');
        console.log('Backdrop Z-Index:', backdrop ? window.getComputedStyle(backdrop).zIndex : 'No backdrop');
        logOverlappingElements();
    }

    function handleModalHidden() {
        console.log('Quick Adjust Modal Hidden');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        if (quickAdjustModal) {
            const modalInstance = bootstrap.Modal.getInstance(quickAdjustModal);
            if (modalInstance) {
                modalInstance.hide();
            }
            setTimeout(() => {
                quickAdjustModal.removeAttribute('aria-hidden');
                quickAdjustModal.setAttribute('inert', '');
                const modalElements = quickAdjustModal.querySelectorAll('input, select, textarea, button');
                modalElements.forEach(element => {
                    element.removeAttribute('aria-hidden');
                    if (element === document.activeElement) {
                        console.log('Active element in modal, blurring and moving focus to body');
                        element.blur();
                    }
                });
                document.body.focus();
                console.log('Removed aria-hidden and added inert to quickAdjustModal and its elements');
            }, 800); // Increased delay to ensure Bootstrap's hide event completes
        }
        clearModalBackdrops();
    }

    // Rule Link and Quick Adjust Link Handling
    const ruleLinks = document.querySelectorAll('.rule-link, .quick-adjust-link');
    ruleLinks.forEach(link => {
        const debouncedHandleQuickAdjustClick = debounce(handleQuickAdjustClick.bind(link), 300);
        link.removeEventListener('click', debouncedHandleQuickAdjustClick);
        link.addEventListener('click', debouncedHandleQuickAdjustClick);
    });

    // Quick Adjust Form Submission
    const quickAdjustForm = document.getElementById('adjustPointsForm');
    if (quickAdjustForm) {
        quickAdjustForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Quick Adjust Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const employeeInput = this.querySelector('#quick_adjust_employee_id');
            const pointsInput = this.querySelector('#quick_adjust_points');
            const reasonInput = this.querySelector('#quick_adjust_reason');
            const notesInput = this.querySelector('#quick_adjust_notes');
            const usernameInput = this.querySelector('#quick_adjust_username');
            const passwordInput = this.querySelector('#quick_adjust_password');
            if (!employeeInput || !employeeInput.value.trim()) {
                console.error('Quick Adjust Form Error: Employee ID Missing');
                alert('Please select an employee.');
                return;
            }
            if (!pointsInput || !pointsInput.value.trim()) {
                console.error('Quick Adjust Form Error: Points Missing');
                alert('Please enter points.');
                return;
            }
            if (!reasonInput || !reasonInput.value.trim()) {
                console.error('Quick Adjust Form Error: Reason Missing');
                alert('Please enter a reason.');
                return;
            }
            if (!sessionStorage.getItem('admin_id')) {
                if (!usernameInput || !usernameInput.value.trim()) {
                    console.error('Quick Adjust Form Error: Username Missing');
                    alert('Please enter your admin username.');
                    return;
                }
                if (!passwordInput || !passwordInput.value.trim()) {
                    console.error('Quick Adjust Form Error: Password Missing');
                    alert('Please enter your admin password.');
                    return;
                }
            }
            data['employee_id'] = employeeInput.value;
            data['points'] = pointsInput.value;
            data['reason'] = reasonInput.value;
            data['notes'] = notesInput && notesInput.value.trim() ? notesInput.value : '';
            if (usernameInput) data['username'] = usernameInput.value;
            if (passwordInput) data['password'] = passwordInput.value;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Quick Adjust Form Data:', { ...data, password: '****' });
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Quick Adjust Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error adjusting points:', error);
                alert('Failed to adjust points. Please try again.');
            });
        });
    } else {
        console.warn('Quick Adjust Form Not Found');
    }

    // Add Employee Form Handling
    const addEmployeeForm = document.getElementById('addEmployeeForm');
    if (addEmployeeForm) {
        addEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Add Employee Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const nameInput = this.querySelector('#add_employee_name');
            const initialsInput = this.querySelector('#add_employee_initials');
            const roleInput = this.querySelector('#add_employee_role');
            if (!nameInput || !nameInput.value.trim()) {
                console.error('Add Employee Form Error: Name Missing');
                alert('Please enter a name.');
                return;
            }
            if (!initialsInput || !initialsInput.value.trim()) {
                console.error('Add Employee Form Error: Initials Missing');
                alert('Please enter initials.');
                return;
            }
            if (!roleInput || !roleInput.value.trim()) {
                console.error('Add Employee Form Error: Role Missing');
                alert('Please select a role.');
                return;
            }
            data['name'] = nameInput.value;
            data['initials'] = initialsInput.value;
            data['role'] = roleInput.value;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Add Employee Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Employee Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error adding employee:', error);
                alert('Failed to add employee. Please try again.');
            });
        });
    }

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
                    console.log('Scoreboard Data Fetched:', data);
                    scoreboardTable.innerHTML = '';
                    data.scoreboard.forEach(emp => {
                        const scoreClass = getScoreClass(emp.score);
                        const roleKeyMap = {
                            'Driver': 'driver',
                            'Laborer': 'laborer',
                            'Supervisor': 'supervisor',
                            'Warehouse Labor': 'warehouse labor',
                            'Warehouse': 'warehouse'
                        };
                        const roleKey = roleKeyMap[emp.role] || emp.role.toLowerCase().replace(/ /g, '_');
                        const pointValue = data.pot_info[roleKey + '_point_value'] || 0;
                        const payout = emp.score < 50 ? 0 : (emp.score * pointValue).toFixed(2);
                        const row = `
                            <tr class="${scoreClass}">
                                <td>${emp.employee_id}</td>
                                <td>${emp.name}</td>
                                <td>${emp.score}</td>
                                <td>${emp.role.charAt(0).toUpperCase() + emp.role.slice(1)}</td>
                                <td>$${payout}</td>
                            </tr>`;
                        scoreboardTable.insertAdjacentHTML('beforeend', row);
                    });
                })
                .catch(error => console.error('Error updating scoreboard:', error));
        }

        function getScoreClass(score) {
            if (score <= 49) return 'score-low';
            else if (score <= 74) return 'score-mid';
            else return 'score-high';
        }

        updateScoreboard();
        setInterval(updateScoreboard, 60000);
    }

    // Vote Form Handling
    const voteForm = document.getElementById('voteForm');
    if (voteForm) {
        voteForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Vote Form Submitted');
            const initials = document.getElementById('hiddenInitials');
            if (!initials || !initials.value.trim()) {
                console.error('Vote Form Error: Initials Missing');
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
            console.log('Vote Counts:', { plusVotes, minusVotes });
            if (plusVotes > 2) {
                console.warn('Vote Validation Failed: Too Many Positive Votes');
                alert('You can only cast up to 2 positive (+1) votes.');
                return;
            }
            if (minusVotes > 3) {
                console.warn('Vote Validation Failed: Too Many Negative Votes');
                alert('You can only cast up to 3 negative (-1) votes.');
                return;
            }
            if (plusVotes + minusVotes > 3) {
                console.warn('Vote Validation Failed: Too Many Total Votes');
                alert('You can only cast a maximum of 3 votes total.');
                return;
            }
            const formData = new FormData(voteForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Vote Form Data: ${key}=${value}`);
            }
            fetch('/vote', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Vote Response:', data);
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
                        if (data.redirected) {
                            console.log('Vote submission redirected, reloading page');
                            window.location.reload();
                        }
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
                    console.error('Check Initials Error: Initials Missing');
                    alert('Please enter your initials.');
                    return;
                }
                console.log('Checking Initials:', initials.value.trim());
                fetch('/check_vote', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `initials=${encodeURIComponent(initials.value.trim())}`
                })
                .then(response => {
                    console.log(`Fetch finished loading: POST "/check_vote", Status: ${response.status}`);
                    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
                        console.warn('Check Vote Failed: Non-JSON or Error', { status: response.status });
                        return response.text().then(text => {
                            console.error('Check Vote response text:', text.substring(0, 100) + '...');
                            throw new Error('Invalid response format');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Check Vote Response:', data);
                    if (data && !data.can_vote) {
                        alert(data.message);
                    } else if (data && data.can_vote) {
                        fetch('/data')
                            .then(response => {
                                if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                                return response.json();
                            })
                            .then(data => {
                                const valid = data.scoreboard.some(emp => emp.initials.toLowerCase() === initials.value.toLowerCase());
                                console.log('Initials Validation:', { valid, initials: initials.value });
                                if (valid) {
                                    document.getElementById('hiddenInitials').value = initials.value;
                                    document.getElementById('voteInitialsForm').style.display = 'none';
                                    voteForm.style.display = 'block';
                                } else {
                                    console.warn('Initials Validation Failed');
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
            console.log('Feedback Form Submitted');
            const comment = document.getElementById('feedback_comment');
            if (!comment || !comment.value.trim()) {
                console.error('Feedback Form Error: Comment Missing');
                alert('Please enter a feedback comment.');
                return;
            }
            const formData = new FormData(feedbackForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Feedback Form Data: ${key}=${value}`);
            }
            fetch('/submit_feedback', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Feedback Response:', data);
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
            console.log('Pause Voting Form Submitted');
            if (confirm('Pause the current voting session?')) {
                fetch('/pause_voting', {
                    method: 'POST',
                    body: new FormData(pauseVotingForm)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Pause Voting Response:', data);
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
            console.log('Close Voting Form Submitted');
            const password = document.querySelector('#closeVotingFormUnique input[name="password"]');
            if (!password || !password.value) {
                console.error('Close Voting Form Error: Password Missing');
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
                        console.log('Close Voting Response:', data);
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
                console.log('Mark Feedback Read Form Submitted');
                fetch('/admin/mark_feedback_read', {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Mark Feedback Read Response:', data);
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
                console.log('Delete Feedback Form Submitted');
                if (confirm('Are you sure you want to delete this feedback?')) {
                    fetch('/admin/delete_feedback', {
                        method: 'POST',
                        body: new FormData(form)
                    })
                    .then(handleResponse)
                    .then(data => {
                        if (data) {
                            console.log('Delete Feedback Response:', data);
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
            console.log('Adjust Points Form Submitted');
            const formData = new FormData(this);
            const data = {};
            for (let [key, value] of formData.entries()) {
                if (value && !value.startsWith('<')) {
                    data[key] = value;
                    console.log(`Adjust Points Form Data: ${key}=${value}`);
                } else {
                    console.warn(`Filtered malformed data for key ${key}: ${value}`);
                }
            }
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Adjust Points Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adjusting points:', error));
        });

        document.querySelectorAll('#adjustPointsFormUnique .rule-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Adjust Points Rule Link Clicked:', { points: link.getAttribute('data-points'), reason: link.getAttribute('data-reason') });
                const points = document.getElementById('adjust_points');
                const reason = document.getElementById('adjust_reason');
                if (points && reason) {
                    points.value = link.getAttribute('data-points');
                    reason.value = link.getAttribute('data-reason');
                    console.log('Adjust Points Form Populated:', { points: points.value, reason: reason.value });
                } else {
                    console.error('Adjust Points Form Inputs Not Found:', { points: !!points, reason: !!reason });
                }
            });
        });
    }

    const addRuleForm = document.getElementById('addRuleFormUnique');
    if (addRuleForm) {
        addRuleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Add Rule Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const description = this.querySelector('#add_rule_description').value;
            const points = this.querySelector('#add_rule_points').value;
            const details = this.querySelector('#add_rule_details').value;
            data['description'] = description;
            data['points'] = points;
            data['details'] = details;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Add Rule Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Rule Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error adding rule:', error);
                alert('Failed to add rule. Please try again.');
            });
        });
    }

    const editRuleForms = document.querySelectorAll('.edit-rule-form');
    editRuleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Edit Rule Form Submitted');
            const formData = new FormData(this);
            const data = {};
            for (let [key, value] of formData.entries()) {
                if (value && !value.startsWith('<')) {
                    data[key] = value;
                    console.log(`Edit Rule Form Data: ${key}=${value}`);
                } else {
                    console.warn(`Filtered malformed data for key ${key}: ${value}`);
                }
            }
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Edit Rule Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error editing rule:', error);
                alert('Failed to edit rule. Please try again.');
            });
        });
    });

    const removeRuleForms = document.querySelectorAll('.remove-rule-form');
    removeRuleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Remove Rule Form Submitted');
            if (confirm('Are you sure you want to remove this rule?')) {
                const formData = new FormData(this);
                const data = {};
                for (let [key, value] of formData.entries()) {
                    if (value && !value.startsWith('<')) {
                        data[key] = value;
                        console.log(`Remove Rule Form Data: ${key}=${value}`);
                    } else {
                        console.warn(`Filtered malformed data for key ${key}: ${value}`);
                    }
                }
                const csrfToken = this.querySelector('input[name="csrf_token"]');
                if (csrfToken) {
                    data['csrf_token'] = csrfToken.value;
                    console.log(`CSRF Token Included: ${data['csrf_token']}`);
                } else {
                    console.error('CSRF Token not found in form');
                    alert('Error: CSRF token missing. Please refresh and try again.');
                    return;
                }
                fetch(this.action, {
                    method: 'POST',
                    body: new URLSearchParams(data),
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Remove Rule Response:', data);
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
            console.log('Reset Scores Form Submitted');
            if (confirm('Reset all scores to 50 and log to history?')) {
                const formData = new FormData(this);
                const data = {};
                for (let [key, value] of formData.entries()) {
                    if (value && !value.startsWith('<')) {
                        data[key] = value;
                        console.log(`Reset Scores Form Data: ${key}=${value}`);
                    } else {
                        console.warn(`Filtered malformed data for key ${key}: ${value}`);
                    }
                }
                const csrfToken = this.querySelector('input[name="csrf_token"]');
                if (csrfToken) {
                    data['csrf_token'] = csrfToken.value;
                    console.log(`CSRF Token Included: ${data['csrf_token']}`);
                } else {
                    console.error('CSRF Token not found in form');
                    alert('Error: CSRF token missing. Please refresh and try again.');
                    return;
                }
                fetch(this.action, {
                    method: 'POST',
                    body: new URLSearchParams(data),
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Reset Scores Response:', data);
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
            console.log('Add Employee Form Submitted');
            const formData = new FormData(this);
            const data = {};
            for (let [key, value] of formData.entries()) {
                if (value && !value.startsWith('<')) {
                    data[key] = value;
                    console.log(`Add Employee Form Data: ${key}=${value}`);
                } else {
                    console.warn(`Filtered malformed data for key ${key}: ${value}`);
                }
            }
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Employee Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error adding employee:', error));
        });
    }

// Role Form Handling
    const addRoleForm = document.getElementById('addRoleFormUnique');
    if (addRoleForm) {
        addRoleForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Add Role Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const roleName = this.querySelector('#add_role_name');
            const percentage = this.querySelector('#add_role_percentage');
            if (!roleName || !roleName.value.trim()) {
                console.error('Add Role Form Error: Role Name Missing');
                alert('Please enter a role name.');
                return;
            }
            if (!percentage || !percentage.value.trim()) {
                console.error('Add Role Form Error: Percentage Missing');
                alert('Please enter a percentage.');
                return;
            }
            data['role_name'] = roleName.value;
            data['percentage'] = percentage.value;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Add Role Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Role Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error adding role:', error);
                alert('Failed to add role. Please try again.');
            });
        });
    }

    const editEmployeeForm = document.getElementById('editEmployeeFormUnique');
    if (editEmployeeForm) {
        editEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Edit Employee Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const employeeId = this.querySelector('#edit_employee_id').value;
            const name = this.querySelector('#edit_employee_name').value;
            const role = this.querySelector('#edit_employee_role').value;
            data['employee_id'] = employeeId;
            data['name'] = name;
            data['role'] = role;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Edit Employee Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Edit Employee Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error editing employee:', error);
                alert('Failed to edit employee. Please try again.');
            });
        });
    }

    const updatePotForm = document.getElementById('updatePotFormUnique');
    if (updatePotForm) {
        updatePotForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Update Pot Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const salesDollars = this.querySelector('#update_pot_sales_dollars').value;
            const bonusPercent = this.querySelector('#update_pot_bonus_percent').value;
            data['sales_dollars'] = salesDollars;
            data['bonus_percent'] = bonusPercent;
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Update Pot Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Update Pot Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error updating pot:', error);
                alert('Failed to update pot. Please try again.');
            });
        });
    }

    const setPointDecayForm = document.getElementById('setPointDecayFormUnique');
    if (setPointDecayForm) {
        setPointDecayForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Set Point Decay Form Submitted');
            const formData = new FormData(this);
            const data = {};
            const roleName = this.querySelector('#set_point_decay_role_name').value;
            const points = this.querySelector('#set_point_decay_points').value;
            const days = Array.from(this.querySelectorAll('input[name="days"]:checked')).map(input => input.value);
            data['role_name'] = roleName;
            data['points'] = points;
            days.forEach((day, index) => {
                data[`days[${index}]`] = day;
            });
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (csrfToken) {
                data['csrf_token'] = csrfToken.value;
                console.log(`CSRF Token Included: ${data['csrf_token']}`);
            } else {
                console.error('CSRF Token not found in form');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            console.log('Set Point Decay Form Data:', data);
            fetch(this.action, {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Set Point Decay Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error setting point decay:', error);
                alert('Failed to set point decay. Please try again.');
            });
        });
    }

    // Sortable Rules List
    const rulesList = document.getElementById('RulesList');
    if (rulesList) {
        console.log('Initializing Sortable for RulesList');
        const sortable = new Sortable(rulesList, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function () {
                const order = Array.from(rulesList.children).map(item => item.getAttribute('data-description'));
                console.log('Rules Reordered:', order);
                fetch('/admin/reorder_rules', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: 'order[]=' + order.map(encodeURIComponent).join('&order[]=')
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Reorder Rules Response:', data);
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error reordering rules:', error));
            }
        });
    }

    // Retire Employee Button
    const retireBtn = document.getElementById('retireBtn');
    if (retireBtn) {
        retireBtn.addEventListener('click', function () {
            const employeeSelect = document.getElementById('edit_employee_id');
            if (!employeeSelect || !employeeSelect.value) {
                console.error('Retire Employee Error: No employee selected');
                alert('Please select an employee to retire.');
                return;
            }
            if (confirm(`Retire employee ${employeeSelect.options[employeeSelect.selectedIndex].text}?`)) {
                console.log('Retire Employee Initiated:', employeeSelect.value);
                fetch('/admin/retire_employee', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `employee_id=${encodeURIComponent(employeeSelect.value)}&csrf_token=${encodeURIComponent(document.querySelector('#editEmployeeFormUnique input[name="csrf_token"]').value)}`
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Retire Employee Response:', data);
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error retiring employee:', error));
            }
        });
    }

    // Reactivate Employee Button
    const reactivateBtn = document.getElementById('reactivateBtn');
    if (reactivateBtn) {
        reactivateBtn.addEventListener('click', function () {
            const employeeSelect = document.getElementById('edit_employee_id');
            if (!employeeSelect || !employeeSelect.value) {
                console.error('Reactivate Employee Error: No employee selected');
                alert('Please select an employee to reactivate.');
                return;
            }
            if (confirm(`Reactivate employee ${employeeSelect.options[employeeSelect.selectedIndex].text}?`)) {
                console.log('Reactivate Employee Initiated:', employeeSelect.value);
                fetch('/admin/reactivate_employee', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `employee_id=${encodeURIComponent(employeeSelect.value)}&csrf_token=${encodeURIComponent(document.querySelector('#editEmployeeFormUnique input[name="csrf_token"]').value)}`
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Reactivate Employee Response:', data);
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error reactivating employee:', error));
            }
        });
    }

    // Delete Employee Button
    const deleteBtn = document.getElementById('deleteBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function () {
            const employeeSelect = document.getElementById('edit_employee_id');
            if (!employeeSelect || !employeeSelect.value) {
                console.error('Delete Employee Error: No employee selected');
                alert('Please select an employee to delete.');
                return;
            }
            if (confirm(`Permanently delete employee ${employeeSelect.options[employeeSelect.selectedIndex].text}?`)) {
                console.log('Delete Employee Initiated:', employeeSelect.value);
                fetch('/admin/delete_employee', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `employee_id=${encodeURIComponent(employeeSelect.value)}&csrf_token=${encodeURIComponent(document.querySelector('#editEmployeeFormUnique input[name="csrf_token"]').value)}`
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Delete Employee Response:', data);
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => console.error('Error deleting employee:', error));
            }
        });
    }
});
