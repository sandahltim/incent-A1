// script.js
// Version: 1.2.86
// Note: Fixed point decay editing by removing duplicate handler and dynamically populating days. Added CSRF token support when saving rule order. Compatible with app.py (1.2.108), forms.py (1.2.19), config.py (1.2.6), admin_manage.html (1.2.45), incentive.html (1.2.47), quick_adjust.html (1.2.18), style.css (1.2.31), base.html (1.2.21), macros.html (1.2.14), start_voting.html (1.2.7), settings.html (1.2.6), admin_login.html (1.2.6), incentive_service.py (1.2.27), history.html (1.2.6), error.html, init_db.py (1.2.4).

// Verify Bootstrap Availability
if (typeof bootstrap === 'undefined') {
    console.error('Bootstrap 5.3.0 not loaded. Ensure Bootstrap JavaScript is included in base.html.');
    alert('Error: Bootstrap JavaScript not loaded. Some features may be unavailable. Check console for details.');
    // [PLACEHOLDER: Removed illegal `return` statement to prevent script termination]
    // Fallback: Continue script execution, but some Bootstrap-dependent features (e.g., modals, tooltips) may not work
}

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

// Initialize Bootstrap Tooltips (with fallback if bootstrap is undefined)
if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    console.log('Initialized Bootstrap Tooltips for rule details');
} else {
    console.warn('Skipping tooltip initialization due to missing Bootstrap');
    // [PLACEHOLDER: Add fallback for tooltips if needed, e.g., basic hover text]
}

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

// Clear Existing Modal Backdrops and Modals
function clearModalBackdrops() {
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => {
        console.log('Removing existing modal backdrop:', backdrop);
        backdrop.remove();
    });
    const modals = document.querySelectorAll('.modal.show');
    modals.forEach(modal => {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.removeAttribute('aria-hidden');
        modal.setAttribute('inert', '');
        console.log('Hiding existing modal:', modal.id);
    });
    const highZElements = document.querySelectorAll('body *');
    highZElements.forEach(el => {
        const zIndex = window.getComputedStyle(el).zIndex;
        if (zIndex && zIndex !== 'auto' && parseInt(zIndex) > 1100 && el !== document.getElementById('quickAdjustModal')) {
            console.log('Removing conflicting high z-index element:', el);
            el.style.zIndex = 'auto';
        }
    });
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    console.log('Cleared modal backdrops, modals, and body styles');
}

// Log Overlapping Elements
function logOverlappingElements() {
    const elements = document.querySelectorAll('body *');
    elements.forEach(el => {
        const zIndex = window.getComputedStyle(el).zIndex;
        if (zIndex && zIndex !== 'auto' && parseInt(zIndex) >= 1200) {
            console.warn(`Element with high z-index detected: ${el.tagName}${el.className ? '.' + el.className : ''} (id: ${el.id || 'none'}), z-index: ${zIndex}, position: ${window.getComputedStyle(el).position}`);
        }
    });
}

// Handle Response
function handleResponse(response) {
    if (!response.ok) {
        console.error(`HTTP error! Status: ${response.status}`);
        return response.text().then(text => {
            console.error('Response text:', text.substring(0, 100) + '...');
            throw new Error(`HTTP error! Status: ${response.status}`);
        });
    }
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        console.error('Response is not JSON:', contentType);
        return response.text().then(text => {
            console.error('Response text:', text.substring(0, 100) + '...');
            throw new Error('Invalid response format');
        });
    }
    return response.json();
}

// [PLACEHOLDER: Rest of the script remains unchanged. Include all subsequent functions and event listeners as in the original script.js]
// [NOTE: Ensure the following code is copied from the original script.js starting from `document.addEventListener('DOMContentLoaded', function () {` to the end]
document.addEventListener('DOMContentLoaded', function () {
    // [UNCHANGED_CODE_BLOCK: Bootstrap verification, CSS load check, tooltip initialization, debounce function, clearModalBackdrops, logOverlappingElements, handleResponse]

    function handleQuickAdjustClick(e) {
        e.preventDefault();
        const points = this.getAttribute('data-points') || '';
        const reason = this.getAttribute('data-reason') || 'Other';
        const employee = this.getAttribute('data-employee') || '';
        console.log('Quick Adjust Link Clicked:', { points, reason, employee });
        if (window.location.pathname !== '/') {
            console.log('Redirecting to / for quick adjust modal');
            sessionStorage.setItem('quickAdjustData', JSON.stringify({ points, reason, employee }));
            window.location.href = '/';
            return;
        }
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        if (!quickAdjustModal) {
            console.error('Quick Adjust Modal not found');
            alert('Error: Quick Adjust Modal unavailable. Please refresh the page.');
            return;
        }
        if (quickAdjustModal.parentNode !== document.body) {
            console.log('Moving quickAdjustModal to direct child of body');
            document.body.appendChild(quickAdjustModal);
        }
        console.log('Initializing Quick Adjust Modal');
        clearModalBackdrops();
        logOverlappingElements();
        if (typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(quickAdjustModal, { backdrop: 'static', keyboard: true, focus: true });
            quickAdjustModal.removeEventListener('show.bs.modal', handleModalShow);
            quickAdjustModal.removeEventListener('shown.bs.modal', handleModalShown);
            quickAdjustModal.removeEventListener('hidden.bs.modal', handleModalHidden);
            quickAdjustModal.addEventListener('show.bs.modal', handleModalShow);
            quickAdjustModal.addEventListener('shown.bs.modal', () => {
                setTimeout(() => handleModalShown(quickAdjustModal, employee, points, reason, '', ''), 200);
            });
            quickAdjustModal.addEventListener('hidden.bs.modal', handleModalHidden);
            setTimeout(() => {
                try {
                    modal.show();
                    console.log('Quick Adjust Modal Shown');
                    const employeeInput = quickAdjustModal.querySelector('#quick_adjust_employee_id');
                    if (employeeInput) {
                        employeeInput.focus();
                        employeeInput.addEventListener('keydown', (e) => {
                            if (e.key === 'Enter') {
                                const form = quickAdjustModal.querySelector('#adjustPointsForm');
                                if (form) form.submit();
                            }
                        });
                    }
                } catch (error) {
                    console.error('Error showing Quick Adjust Modal:', error);
                    alert('Error opening Quick Adjust Modal. Please check console for details.');
                }
            }, 100);
        } else {
            console.error('Cannot show Quick Adjust Modal: Bootstrap not loaded');
            alert('Modal functionality unavailable due to missing Bootstrap.');
        }
    }

    function handleModalShow() {
        console.log('Quick Adjust Modal Show Event');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        quickAdjustModal.removeAttribute('inert');
        quickAdjustModal.removeAttribute('aria-hidden');
        const inputs = quickAdjustModal.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            input.disabled = false;
            input.style.pointerEvents = 'auto';
            input.style.opacity = '1';
            input.style.cursor = input.tagName === 'SELECT' ? 'pointer' : 'text';
            input.removeAttribute('aria-hidden');
            console.log(`Input Enabled: ${input.id || 'unnamed'}, Disabled: ${input.disabled}, PointerEvents: ${input.style.pointerEvents}, Opacity: ${input.style.opacity}, Cursor: ${input.style.cursor}`);
        });
    }

    function handleModalShown(modal, employee, points, reason, notes, username) {
        console.log("Quick Adjust Modal Fully Shown");
        if (!(modal instanceof HTMLElement)) {
            console.error("Invalid modal parameter:", modal);
            alert("Error: Modal not found. Please refresh and try again.");
            return;
        }
        const form = modal.querySelector('#adjustPointsForm');
        if (!form) {
            console.error("Form #adjustPointsForm not found in modal");
            alert("Error: Form not found. Please refresh and try again.");
            return;
        }
        const inputs = {
            employeeInput: form.querySelector('#quick_adjust_employee_id'),
            pointsInput: form.querySelector('#quick_adjust_points'),
            reasonInput: form.querySelector('#quick_adjust_reason'),
            notesInput: form.querySelector('#quick_adjust_notes'),
            usernameInput: form.querySelector('#quick_adjust_username'),
            passwordInput: form.querySelector('#quick_adjust_password'),
            csrfInput: form.querySelector('#adjust_csrf_token')
        };
        const inputsFound = {
            employeeInput: !!inputs.employeeInput,
            pointsInput: !!inputs.pointsInput,
            reasonInput: !!inputs.reasonInput,
            notesInput: !!inputs.notesInput,
            usernameInput: !!inputs.usernameInput,
            passwordInput: !!inputs.passwordInput,
            csrfInput: !!inputs.csrfInput
        };
        console.log("Quick Adjust Form Inputs Found:", inputsFound);
        if (!inputsFound.employeeInput || !inputsFound.pointsInput || !inputsFound.reasonInput || !inputsFound.csrfInput) {
            console.error("Required form inputs not found:", inputsFound);
            alert("Error: Required form fields (employee, points, reason, or csrf_token) are missing. Please refresh and try again.");
            return;
        }
        const isAdmin = !(inputs.usernameInput && inputs.passwordInput);
        inputs.employeeInput.value = employee || '';
        inputs.pointsInput.value = points || '';
        inputs.reasonInput.value = reason || 'Other';
        inputs.notesInput.value = notes || '';
        if (!isAdmin && inputs.usernameInput) inputs.usernameInput.value = username || '';
        if (!isAdmin && inputs.passwordInput) inputs.passwordInput.value = '';
        Object.values(inputs).forEach(input => {
            if (input) {
                input.disabled = false;
                input.style.pointerEvents = 'auto';
                input.style.opacity = '1';
                input.style.cursor = input.tagName === 'SELECT' ? 'pointer' : 'text';
                console.log(`Input Enabled: ${input.id || 'unnamed'}, Disabled: ${input.disabled}, PointerEvents: ${input.style.pointerEvents}, Opacity: ${input.style.opacity}, Cursor: ${input.style.cursor}`);
            }
        });
        console.log("Quick Adjust Form Populated:", {
            employee: inputs.employeeInput.value,
            points: inputs.pointsInput.value,
            reason: inputs.reasonInput.value,
            notes: inputs.notesInput.value,
            username: inputs.usernameInput ? inputs.usernameInput.value : 'N/A'
        });
    }

    function handleModalHidden() {
        console.log('Quick Adjust Modal Hidden');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        if (quickAdjustModal) {
            if (typeof bootstrap !== 'undefined') {
                const modalInstance = bootstrap.Modal.getInstance(quickAdjustModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }
            const mainContent = document.querySelector('main') || document.body;
            mainContent.setAttribute('tabindex', '0');
            mainContent.focus();
            setTimeout(() => {
                const closeBtn = quickAdjustModal.querySelector('.btn-close');
                if (closeBtn && closeBtn === document.activeElement) {
                    console.log('Blurring close button');
                    closeBtn.blur();
                }
                const focusableElements = quickAdjustModal.querySelectorAll('input, select, textarea, button');
                focusableElements.forEach(element => {
                    if (element === document.activeElement) {
                        console.log('Blurring active element in modal:', element);
                        element.blur();
                    }
                    element.setAttribute('inert', '');
                });
                quickAdjustModal.setAttribute('inert', '');
                quickAdjustModal.setAttribute('aria-hidden', 'true');
                mainContent.removeAttribute('tabindex');
                console.log('Added inert to quickAdjustModal and its elements, focused main content');
            }, 100);
            clearModalBackdrops();
        }
    }

    // Quick Adjust Link Handling
    const quickAdjustLinks = document.querySelectorAll('.quick-adjust-link');
    quickAdjustLinks.forEach(link => {
        link.addEventListener('click', handleQuickAdjustClick);
    });
    console.log('Bound click event to quick-adjust-link elements');

    // Quick Adjust Form Submission
    if (window.location.pathname === '/') {
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
                const csrfToken = this.querySelector('#adjust_csrf_token');
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
                    alert('Please select a reason.');
                    return;
                }
                const isAdmin = !(usernameInput && passwordInput);
                if (!isAdmin && (!usernameInput || !usernameInput.value.trim())) {
                    console.error('Quick Adjust Form Error: Username Missing for Non-Admin');
                    alert('Please enter your admin username.');
                    return;
                }
                if (!isAdmin && (!passwordInput || !passwordInput.value.trim())) {
                    console.error('Quick Adjust Form Error: Password Missing for Non-Admin');
                    alert('Please enter your admin password.');
                    return;
                }
                if (!isAdmin) {
                    data['username'] = usernameInput.value;
                    data['password'] = passwordInput.value;
                }
                data['employee_id'] = employeeInput.value;
                data['points'] = pointsInput.value;
                data['reason'] = reasonInput.value;
                data['notes'] = notesInput && notesInput.value.trim() ? notesInput.value : '';
                if (csrfToken) {
                    data['csrf_token'] = csrfToken.value;
                    console.log(`CSRF Token Included: ${data['csrf_token']}`);
                } else {
                    console.error('CSRF Token not found in form');
                    console.log('Form HTML:', this.outerHTML);
                    alert('Error: CSRF token missing. Please refresh and try again.');
                    return;
                }
                console.log('Quick Adjust Form Data:', { ...data, password: data['password'] ? '****' : '' });
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
                        if (data.success) {
                            const modal = bootstrap.Modal.getInstance(document.getElementById('quickAdjustModal'));
                            if (modal) modal.hide();
                            window.location.reload();
                        }
                    }
                })
                .catch(error => {
                    console.error('Error adjusting points:', error);
                    alert('Failed to adjust points. Please try again.');
                });
            });
        }
    }

    // Set Point Decay Form Submission
    if (window.location.pathname === '/admin') {
        const setPointDecayForm = document.getElementById('setPointDecayFormUnique');
        if (setPointDecayForm) {
            const decayData = JSON.parse(setPointDecayForm.getAttribute('data-decay') || '{}');
            const roleSelect = setPointDecayForm.querySelector('#set_point_decay_role_name');
            const pointsInput = setPointDecayForm.querySelector('#set_point_decay_points');
            const dayCheckboxes = setPointDecayForm.querySelectorAll('input[name="days[]"]');

            function populateDecayFields() {
                const info = decayData[roleSelect.value] || {points: 0, days: []};
                pointsInput.value = info.points;
                dayCheckboxes.forEach(cb => {
                    cb.checked = info.days.includes(cb.value);
                });
            }

            populateDecayFields();
            roleSelect.addEventListener('change', populateDecayFields);

            setPointDecayForm.addEventListener('submit', function (e) {
                e.preventDefault();
                console.log('Set Point Decay Form Submitted');
                const roleInput = roleSelect;
                const selectedDays = this.querySelectorAll('input[name="days[]"]:checked');
                const csrfToken = this.querySelector('input[name="csrf_token"]');
                if (!roleInput || !roleInput.value.trim()) {
                    console.error('Set Point Decay Form Error: Role Missing');
                    alert('Please select a role.');
                    return;
                }
                if (!pointsInput || !pointsInput.value.trim()) {
                    console.error('Set Point Decay Form Error: Points Missing');
                    alert('Please enter points.');
                    return;
                }
                const dataLog = {
                    'role_name': roleInput.value,
                    'points': pointsInput.value,
                    'days[]': Array.from(selectedDays).map(input => input.value)
                };
                if (csrfToken) {
                    dataLog['csrf_token'] = csrfToken.value;
                    console.log(`CSRF Token Included: ${csrfToken.value}`);
                } else {
                    console.error('CSRF Token not found in form');
                    console.log('Form HTML:', this.outerHTML);
                    alert('Error: CSRF token missing. Please refresh and try again.');
                    return;
                }
                console.log('Set Point Decay Form Data:', dataLog);
                const params = new URLSearchParams();
                params.append('role_name', roleInput.value);
                params.append('points', pointsInput.value);
                Array.from(selectedDays).forEach(input => params.append('days[]', input.value));
                params.append('csrf_token', csrfToken.value);
                fetch(this.action, {
                    method: 'POST',
                    body: params,
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Set Point Decay Response:', data);
                        alert(`Point decay for ${data.role_name} set to ${data.points} points on ${data.days.join(', ') || 'none'}`);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error setting point decay:', error);
                    alert('Failed to set point decay. Please try again.');
                });
            });
        }
    }

    // Add Employee Form Submission
    if (window.location.pathname === '/admin') {
        const addEmployeeForm = document.getElementById('addEmployeeForm') || document.getElementById('addEmployeeFormUnique');
        if (addEmployeeForm) {
            addEmployeeForm.addEventListener('submit', function (e) {
                e.preventDefault();
                console.log('Add Employee Form Submitted');
                const formData = new FormData(this);
                const data = {};
                const nameInput = this.querySelector('#add_employee_name') || this.querySelector('input[name="name"]');
                const initialsInput = this.querySelector('#add_employee_initials') || this.querySelector('input[name="initials"]');
                const roleInput = this.querySelector('#add_employee_role') || this.querySelector('select[name="role"]');
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
    }

    // Delete Employee Button Handling
    if (window.location.pathname === '/admin') {
        const deleteButtons = document.querySelectorAll('.delete-btn');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function (e) {
                e.preventDefault();
                const employeeId = this.getAttribute('data-employee-id');
                console.log('Delete Employee Initiated:', employeeId);
                if (!employeeId) {
                    console.error('Delete Employee Error: Employee ID Missing');
                    alert('Employee ID not found.');
                    return;
                }
                if (!confirm(`Are you sure you want to permanently delete employee ${employeeId}?`)) {
                    return;
                }
                const data = {
                    employee_id: employeeId,
                    csrf_token: document.querySelector('input[name="csrf_token"]').value
                };
                console.log('Delete Employee Data:', data);
                fetch('/admin/delete_employee', {
                    method: 'POST',
                    body: new URLSearchParams(data),
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                })
                .then(handleResponse)
                .then(data => {
                    console.log('Delete Employee Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                })
                .catch(error => {
                    console.error('Error deleting employee:', error);
                    alert('Failed to delete employee. Please try again.');
                });
            });
        });
    }

    // Scoreboard Update
    const scoreboardTable = document.querySelector('#scoreboard tbody');
    if (scoreboardTable) {
        function updateScoreboard() {
            fetch('/data')
                .then(response => {
                    if (!response.ok) {
                        console.error(`HTTP error! Status: ${response.status}`);
                        return response.text().then(text => {
                            console.error('Response text:', text.substring(0, 100) + '...');
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        });
                    }
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
                            'Warehouse Labor': 'warehouse_labor',
                            'Warehouse': 'warehouse',
                            'Master': 'master'
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
                .catch(error => {
                    console.error('Error updating scoreboard:', error);
                    alert('Failed to update scoreboard. Please check server connection or refresh the page.');
                    scoreboardTable.innerHTML = '<tr><td colspan="5" class="text-center">Unable to load scoreboard. Please try refreshing the page.</td></tr>';
                });
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
    const pauseVotingForm = document.getElementById('pauseVotingForm') || document.getElementById('pauseVotingFormUnique');
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

    const closeVotingForm = document.getElementById('closeVotingForm') || document.getElementById('closeVotingFormUnique');
    if (closeVotingForm) {
        closeVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Close Voting Form Submitted');
            const passwordInput = this.querySelector('#close_voting_password');
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (!passwordInput || !passwordInput.value.trim()) {
                console.error('Close Voting Form Error: Password Missing');
                alert('Admin password is required.');
                return;
            }
            if (!csrfToken || !csrfToken.value.trim()) {
                console.error('Close Voting Form Error: CSRF Token Missing');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            if (confirm('Close the current voting session and process votes?')) {
                const formData = new FormData(this);
                console.log('Close Voting Form Data:', {
                    password: '****',
                    csrf_token: formData.get('csrf_token')
                });
                fetch('/close_voting', {
                    method: 'POST',
                    body: formData
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Close Voting Response:', data);
                        alert(data.message);
                        if (data.success) window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error closing voting:', error);
                    alert('Failed to close voting. Please try again.');
                });
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
    if (editRuleForms) {
        editRuleForms.forEach(form => {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                console.log('Edit Rule Form Submitted');
                const formData = new FormData(this);
                const data = {};
                for (let [key, value] of formData.entries()) {
                    if (value && !value.startsWith('<')) {
                        if (key === 'percentage') {
                            data[key] = parseInt(value) || 0;
                            console.log(`Edit Rule Form Percentage: ${data[key]}`);
                        } else {
                            data[key] = value;
                            console.log(`Edit Rule Form Data: ${key}=${data[key]}`);
                        }
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
                console.log('Edit Rule Raw Form Data:', Array.from(formData.entries()));
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
    }

    const startVotingForm = document.getElementById('startVotingForm') || document.getElementById('startVotingFormUnique');
    if (startVotingForm) {
        startVotingForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Start Voting Form Submitted');
            const usernameInput = this.querySelector('#start_voting_username');
            const passwordInput = this.querySelector('#start_voting_password');
            const csrfToken = this.querySelector('input[name="csrf_token"]');
            if (!usernameInput || !usernameInput.value.trim()) {
                console.error('Start Voting Form Error: Username Missing');
                alert('Please enter your admin username.');
                return;
            }
            if (!passwordInput || !passwordInput.value.trim()) {
                console.error('Start Voting Form Error: Password Missing');
                alert('Please enter your admin password.');
                return;
            }
            if (!csrfToken || !csrfToken.value.trim()) {
                console.error('Start Voting Form Error: CSRF Token Missing');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            const data = {
                username: usernameInput.value,
                password: passwordInput.value,
                csrf_token: csrfToken.value
            };
            console.log('Start Voting Form Data:', {
                username: data.username,
                password: '****',
                csrf_token: data.csrf_token
            });
            fetch('/start_voting', {
                method: 'POST',
                body: new URLSearchParams(data),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Start Voting Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error starting voting:', error);
                alert('Failed to start voting. Please try again.');
            });
        });
    }

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

    // Sortable Rules List
    const rulesList = document.getElementById('RulesList');
    if (rulesList) {
        console.log('Initializing Sortable for RulesList');

        function saveRuleOrder() {
            const order = Array.from(rulesList.children).map(item => item.getAttribute('data-description'));
            const csrfToken = document.getElementById('reorder_rules_csrf_token');
            if (!csrfToken) {
                console.error('CSRF Token for rule reordering not found');
                alert('Error: CSRF token missing. Please refresh and try again.');
                return;
            }
            const params = new URLSearchParams();
            order.forEach(desc => params.append('order[]', desc));
            params.append('csrf_token', csrfToken.value);
            console.log(`CSRF Token Included: ${csrfToken.value}`);
            fetch('/admin/reorder_rules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: params
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

        if (typeof Sortable !== 'undefined') {
            new Sortable(rulesList, {
                animation: 150,
                ghostClass: 'sortable-ghost',
                onEnd: saveRuleOrder
            });
        } else {
            console.warn('Sortable.js not loaded, skipping rules list initialization');
        }

        const sortAlphaBtn = document.getElementById('sortAlpha');
        if (sortAlphaBtn) {
            sortAlphaBtn.addEventListener('click', () => {
                const items = Array.from(rulesList.children);
                items.sort((a, b) => a.getAttribute('data-description').localeCompare(b.getAttribute('data-description')));
                items.forEach(item => rulesList.appendChild(item));
                saveRuleOrder();
            });
        }

        const sortPointsBtn = document.getElementById('sortPoints');
        if (sortPointsBtn) {
            sortPointsBtn.addEventListener('click', () => {
                const items = Array.from(rulesList.children);
                items.sort((a, b) => parseInt(b.getAttribute('data-points')) - parseInt(a.getAttribute('data-points')));
                items.forEach(item => rulesList.appendChild(item));
                saveRuleOrder();
            });
        }
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
            const selectedOption = employeeSelect.options[employeeSelect.selectedIndex];
            if (!selectedOption.text.includes('(Retired)')) {
                console.error('Reactivate Employee Error: Employee already active');
                alert('Selected employee is already active.');
                return;
            }
            if (confirm(`Reactivate employee ${selectedOption.text}?`)) {
                console.log('Reactivate Employee Initiated:', employeeSelect.value);
                const params = new URLSearchParams();
                params.append('employee_id', employeeSelect.value);
                const csrfToken = document.querySelector('#editEmployeeFormUnique input[name="csrf_token"]');
                if (csrfToken) {
                    params.append('csrf_token', csrfToken.value);
                }
                fetch('/admin/reactivate_employee', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: params
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

    // Modal event listeners for aria-hidden fix
    const quickAdjustModal = document.getElementById('quickAdjustModal');
    if (quickAdjustModal) {
        quickAdjustModal.addEventListener('hidden.bs.modal', handleModalHidden);
        quickAdjustModal.addEventListener('shown.bs.modal', () => {
            quickAdjustModal.removeAttribute('inert');
            const modalElements = quickAdjustModal.querySelectorAll('input, select, textarea, button');
            modalElements.forEach(element => {
                element.removeAttribute('inert');
            });
            const modalDialog = quickAdjustModal.querySelector('.modal-dialog');
            if (modalDialog) {
                modalDialog.setAttribute('tabindex', '0');
                modalDialog.focus();
            }
            console.log('Removed inert from quickAdjustModal and its elements, focused modal dialog');
        });
    }
});