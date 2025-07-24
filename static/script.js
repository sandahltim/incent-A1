// script.js
// Version: 1.2.29
// Note: Added CSRF token handling for adjustPointsForm submission to fix 400 Bad Request error on /admin/quick_adjust_points. Maintained fixes from version 1.2.28 (modal z-index, form reset, voting results, JSON response handling). Ensured compatibility with app.py (1.2.37), incentive_service.py (1.2.10), config.py (1.2.6), forms.py (1.2.2), incentive.html (1.2.17), admin_manage.html (1.2.17), quick_adjust.html (1.2.8), style.css (1.2.11), start_voting.html (1.2.4), settings.html (1.2.5). No changes to core functionality (scoreboard, voting, modals).

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
        })
        .catch(error => {
            console.error("CSS Load Error:", error);
            if (cssStatusElement) {
                cssStatusElement.textContent = "CSS Load Status: Failed";
            }
        });

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
            console.log('Hiding existing modal:', modal.id);
        });
        // Remove conflicting high z-index elements
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

    // Debounce Function
    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
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
    const quickAdjustLinks = document.querySelectorAll('.quick-adjust-link');
    function handleQuickAdjustClick(e) {
        e.preventDefault();
        const points = this.getAttribute('data-points');
        const reason = this.getAttribute('data-reason');
        const employee = this.getAttribute('data-employee');
        console.log('Quick Adjust Link Clicked:', { points, reason, employee });
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        const form = document.getElementById('adjustPointsForm');
        if (!quickAdjustModal || !form) {
            console.error('Quick Adjust Modal or Form not found');
            return;
        }
        form.querySelector('#quick_adjust_employee_id').value = employee || '';
        form.querySelector('#quick_adjust_points').value = points || '';
        form.querySelector('#quick_adjust_reason').value = reason || '';
        form.querySelector('#quick_adjust_notes').value = '';
        console.log('Quick Adjust Form Populated:', {
            employee: employee,
            points: points,
            reason: reason,
            notes: ''
        });
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
        quickAdjustModal.addEventListener('shown.bs.modal', handleModalShown);
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
        const inputs = document.getElementById('quickAdjustModal').querySelectorAll('input, select, textarea');
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

    function handleModalShown() {
        console.log('Quick Adjust Modal Fully Shown');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        const inputs = quickAdjustModal.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            input.disabled = false;
            input.style.pointerEvents = 'auto';
            input.style.opacity = '1';
            input.style.cursor = input.tagName === 'SELECT' ? 'pointer' : 'text';
            console.log(`Input Re-Enabled: ${input.id}, Disabled: ${input.disabled}, PointerEvents: ${input.style.pointerEvents}, Opacity: ${input.style.opacity}, Cursor: ${input.style.cursor}`);
        });
        const form = document.getElementById('adjustPointsForm');
        const pointsInput = document.getElementById('quick_adjust_points');
        const reasonInput = document.getElementById('quick_adjust_reason');
        const employeeInput = document.getElementById('quick_adjust_employee_id');
        if (form && pointsInput && reasonInput && employeeInput) {
            form.reset();
            pointsInput.value = pointsInput.getAttribute('data-points') || '';
            reasonInput.value = reasonInput.getAttribute('data-reason') || '';
            employeeInput.value = employeeInput.getAttribute('data-employee') || '';
            console.log('Quick Adjust Form Reset and Repopulated:', {
                points: pointsInput.value,
                reason: reasonInput.value,
                employee: employeeInput.value
            });
        }
        quickAdjustModal.style.zIndex = '1100';
        const modalContent = quickAdjustModal.querySelector('.modal-content');
        if (modalContent) modalContent.style.zIndex = '1100';
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.style.zIndex = '1095';
        console.log('Modal Z-Index:', quickAdjustModal.style.zIndex);
        console.log('Modal Content Z-Index:', quickAdjustModal.querySelector('.modal-content')?.style.zIndex || 'Not found');
        console.log('Backdrop Z-Index:', backdrop ? window.getComputedStyle(backdrop).zIndex : 'No backdrop');
        logOverlappingElements();
    }

    function handleModalHidden() {
        console.log('Quick Adjust Modal Hidden');
        const quickAdjustModal = document.getElementById('quickAdjustModal');
        if (quickAdjustModal) {
            quickAdjustModal.removeAttribute('aria-hidden');
            const modalInputs = quickAdjustModal.querySelectorAll('input, select, textarea, button');
            modalInputs.forEach(input => input.removeAttribute('aria-hidden'));
            console.log('Removed aria-hidden from quickAdjustModal and its inputs');
        }
        clearModalBackdrops();
    }

    quickAdjustLinks.forEach(link => {
        const debouncedHandleQuickAdjustClick = debounce(handleQuickAdjustClick.bind(link), 300);
        link.removeEventListener('click', debouncedHandleQuickAdjustClick);
        link.addEventListener('click', debouncedHandleQuickAdjustClick);
    });

    // Quick Adjust Form Submission
    const quickAdjustForm = document.getElementById('adjustPointsForm');
    if (quickAdjustForm) {
        quickAdjustForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Quick Adjust Form Submitted');
            const formData = new FormData(this);
            const data = {};
            for (let [key, value] of formData.entries()) {
                console.log(`Form Data: ${key}=${value}`);
                data[key] = value;
            }
            // Include CSRF token
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
            .then(response => {
                console.log(`Fetch finished loading: POST "${this.action}", Status: ${response.status}`);
                if (response.redirected || !response.ok) {
                    console.warn('Quick Adjust Form Submission Failed: Redirected or Error', { status: response.status, redirected: response.redirected });
                    alert('Session expired or error occurred. Please log in again.');
                    window.location.href = '/admin';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data) {
                    console.log('Quick Adjust Response:', data);
                    alert(data.message);
                    if (data.success) {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('quickAdjustModal'));
                        if (modal) {
                            modal.hide();
                            console.log('Quick Adjust Modal Hidden');
                        }
                        window.location.reload();
                    }
                }
            })
            .catch(error => {
                console.error('Error submitting quick adjust form:', error);
                alert('Failed to adjust points. Please check console for details.');
            });
        });
    } else {
        console.warn('Quick Adjust Form Not Found');
    }

    // Rule Link Handling for Adjust Points (quick_adjust.html)
    const ruleLinks = document.querySelectorAll('.rule-link');
    ruleLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Rule Link Clicked:', { points: this.getAttribute('data-points'), reason: this.getAttribute('data-reason') });
            const points = document.getElementById('adjust_points');
            const reason = document.getElementById('adjust_reason');
            if (points && reason) {
                points.value = this.getAttribute('data-points');
                reason.value = this.getAttribute('data-reason');
                console.log('Adjust Points Form Populated:', { points: points.value, reason: reason.value });
            } else {
                console.error('Adjust Points Form Inputs Not Found:', { points: !!points, reason: !!reason });
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
        console.log(`Response received: Status ${response.status}, Redirected: ${response.redirected}, Content-Type: ${response.headers.get('content-type')}`);
        if (!response.ok) {
            console.warn('Response Failed: Error', { status: response.status, redirected: response.redirected });
            return response.text().then(text => {
                console.error('Non-OK response text:', text.substring(0, 100) + '...');
                alert('Error occurred. Please try again.');
                return null;
            });
        }
        if (!response.headers.get('content-type')?.includes('application/json')) {
            console.warn('Non-JSON response received');
            return response.text().then(text => {
                console.error('Response text:', text.substring(0, 100) + '...');
                alert('Invalid response format. Please try again.');
                return null;
            });
        }
        return response.json().then(data => {
            if (!data) throw new Error('No data received');
            return { ...data, redirected: response.redirected };
        }).catch(error => {
            console.error('Invalid JSON response:', error);
            return response.text().then(text => {
                console.error('Response text:', text.substring(0, 100) + '...');
                alert('Invalid response. Please try again.');
                return null;
            });
        });
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
            const employeeId = document.getElementById('adjust_employee_id');
            const points = document.getElementById('adjust_points');
            const reason = document.getElementById('adjust_reason');
            if (!employeeId?.value || !points?.value || !reason?.value) {
                console.error('Adjust Points Form Error: Missing Required Fields', { employeeId: employeeId?.value, points: points?.value, reason: reason?.value });
                alert('All required fields must be filled.');
                return;
            }
            const formData = new FormData(adjustPointsForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Adjust Points Form Data: ${key}=${value}`);
            }
            fetch('/admin/adjust_points', {
                method: 'POST',
                body: formData
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
            const description = document.getElementById('add_rule_description');
            const points = document.getElementById('add_rule_points');
            if (!description?.value || !points?.value) {
                console.error('Add Rule Form Error: Missing Required Fields', { description: description?.value, points: points?.value });
                alert('Description and points are required.');
                return;
            }
            const formData = new FormData(addRuleForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Add Rule Form Data: ${key}=${value}`);
            }
            fetch('/admin/add_rule', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Rule Response:', data);
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
            console.log('Edit Rule Form Submitted');
            const newDescription = form.querySelector('input[name="new_description"]');
            const points = form.querySelector('input[name="points"]');
            if (!newDescription?.value || !points?.value) {
                console.error('Edit Rule Form Error: Missing Required Fields', { newDescription: newDescription?.value, points: points?.value });
                alert('Description and points are required.');
                return;
            }
            const formData = new FormData(form);
            for (let [key, value] of formData.entries()) {
                console.log(`Edit Rule Form Data: ${key}=${value}`);
            }
            fetch('/admin/edit_rule', {
                method: 'POST',
                body: formData
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
                const formData = new FormData(form);
                for (let [key, value] of formData.entries()) {
                    console.log(`Remove Rule Form Data: ${key}=${value}`);
                }
                fetch('/admin/remove_rule', {
                    method: 'POST',
                    body: formData
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
                fetch('/admin/reset', {
                    method: 'POST',
                    body: new FormData(resetScoresForm)
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
            const name = document.getElementById('add_employee_name');
            const initials = document.getElementById('add_employee_initials');
            const role = document.getElementById('add_employee_role');
            if (!name?.value || !initials?.value || !role?.value) {
                console.error('Add Employee Form Error: Missing Required Fields', { name: name?.value, initials: initials?.value, role: role?.value });
                alert('All fields are required.');
                return;
            }
            const formData = new FormData(addEmployeeForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Add Employee Form Data: ${key}=${value}`);
            }
            fetch('/admin/add', {
                method: 'POST',
                body: formData
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

    const editEmployeeForm = document.getElementById('editEmployeeFormUnique');
    if (editEmployeeForm) {
        editEmployeeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Edit Employee Form Submitted');
            const employeeId = document.getElementById('edit_employee_id');
            const name = document.getElementById('edit_employee_name');
            const role = document.getElementById('edit_employee_role');
            if (!employeeId?.value || !name?.value || !role?.value) {
                console.error('Edit Employee Form Error: Missing Required Fields', { employeeId: employeeId?.value, name: name?.value, role: role?.value });
                alert('All fields are required.');
                return;
            }
            const formData = new FormData(editEmployeeForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Edit Employee Form Data: ${key}=${value}`);
            }
            fetch('/admin/edit_employee', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Edit Employee Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => console.error('Error editing employee:', error));
        });

        const retireBtn = document.getElementById('retireBtn');
        if (retireBtn) {
            retireBtn.addEventListener('click', function () {
                console.log('Retire Button Clicked');
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    console.error('Retire Employee Error: Employee ID Missing');
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
                            console.log('Retire Employee Response:', data);
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
                console.log('Reactivate Button Clicked');
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    console.error('Reactivate Employee Error: Employee ID Missing');
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
                            console.log('Reactivate Employee Response:', data);
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
                console.log('Delete Employee Button Clicked');
                const id = document.getElementById('edit_employee_id')?.value;
                if (!id) {
                    console.error('Delete Employee Error: Employee ID Missing');
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
                            console.log('Delete Employee Response:', data);
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
            console.log('Update Pot Form Submitted');
            const salesDollars = document.getElementById('update_pot_sales_dollars');
            const bonusPercent = document.getElementById('update_pot_bonus_percent');
            if (!salesDollars?.value || !bonusPercent?.value) {
                console.error('Update Pot Form Error: Missing Required Fields', { salesDollars: salesDollars?.value, bonusPercent: bonusPercent?.value });
                alert('All fields are required.');
                return;
            }
            const formData = new FormData(updatePotForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Update Pot Form Data: ${key}=${value}`);
            }
            fetch('/admin/update_pot', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Update Pot Response:', data);
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
            console.log('Update Prior Year Sales Form Submitted');
            const priorYearSales = document.getElementById('update_prior_year_sales_prior_year_sales');
            if (!priorYearSales?.value) {
                console.error('Update Prior Year Sales Form Error: Prior Year Sales Missing');
                alert('Prior year sales is required.');
                return;
            }
            const formData = new FormData(updatePriorYearSalesForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Update Prior Year Sales Form Data: ${key}=${value}`);
            }
            fetch('/admin/update_prior_year_sales', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Update Prior Year Sales Response:', data);
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
            console.log('Set Point Decay Form Submitted');
            const roleName = document.getElementById('set_point_decay_role_name');
            const points = document.getElementById('set_point_decay_points');
            if (!roleName?.value || !points?.value) {
                console.error('Set Point Decay Form Error: Missing Required Fields', { roleName: roleName?.value, points: points?.value });
                alert('Role and points are required.');
                return;
            }
            const formData = new FormData(setPointDecayForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Set Point Decay Form Data: ${key}=${value}`);
            }
            fetch('/admin/set_point_decay', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Set Point Decay Response:', data);
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
            console.log('Add Role Form Submitted');
            const roleName = document.getElementById('add_role_role_name');
            const percentage = document.getElementById('add_role_percentage');
            if (!roleName?.value || !percentage?.value) {
                console.error('Add Role Form Error: Missing Required Fields', { roleName: roleName?.value, percentage: percentage?.value });
                alert('Role name and percentage are required.');
                return;
            }
            const formData = new FormData(addRoleForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Add Role Form Data: ${key}=${value}`);
            }
            fetch('/admin/add_role', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Add Role Response:', data);
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
            console.log('Edit Role Form Submitted');
            const newRoleName = form.querySelector('input[name="new_role_name"]');
            const percentage = form.querySelector('input[name="percentage"]');
            if (!newRoleName?.value || !percentage?.value) {
                console.error('Edit Role Form Error: Missing Required Fields', { newRoleName: newRoleName?.value, percentage: percentage?.value });
                alert('Role name and percentage are required.');
                return;
            }
            const formData = new FormData(form);
            for (let [key, value] of formData.entries()) {
                console.log(`Edit Role Form Data: ${key}=${value}`);
            }
            fetch('/admin/edit_role', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Edit Role Response:', data);
                    alert(data.message);
                    if (data.success) window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error editing role:', error);
                alert('Failed to edit role. Please try again.');
            });
        });
    });

    const removeRoleForms = document.querySelectorAll('.removeRoleFormUnique');
    removeRoleForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('Remove Role Form Submitted');
            if (confirm('Are you sure you want to remove this role?')) {
                const formData = new FormData(form);
                for (let [key, value] of formData.entries()) {
                    console.log(`Remove Role Form Data: ${key}=${value}`);
                }
                fetch('/admin/remove_role', { // Fixed endpoint from /admin/remove_rule to /admin/remove_role
                    method: 'POST',
                    body: formData
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Remove Role Response:', data);
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
            console.log('Update Admin Form Submitted');
            const oldUsername = document.getElementById('update_admin_old_username');
            const newUsername = document.getElementById('update_admin_new_username');
            const newPassword = document.getElementById('update_admin_new_password');
            if (!oldUsername?.value || !newUsername?.value || !newPassword?.value) {
                console.error('Update Admin Form Error: Missing Required Fields', { oldUsername: oldUsername?.value, newUsername: newUsername?.value, newPassword: newPassword?.value });
                alert('All fields are required.');
                return;
            }
            const formData = new FormData(updateAdminForm);
            for (let [key, value] of formData.entries()) {
                console.log(`Update Admin Form Data: ${key}=${value}`);
            }
            fetch('/admin/update_admin', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Update Admin Response:', data);
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
            console.log('Master Reset Form Submitted');
            const password = document.getElementById('master_reset_password');
            if (!password?.value) {
                console.error('Master Reset Form Error: Password Missing');
                alert('Master password is required.');
                return;
            }
            if (confirm('Reset all voting data and history? This cannot be undone.')) {
                const formData = new FormData(masterResetForm);
                for (let [key, value] of formData.entries()) {
                    console.log(`Master Reset Form Data: ${key}=${value}`);
                }
                fetch('/admin/master_reset', {
                    method: 'POST',
                    body: formData
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Master Reset Response:', data);
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
            console.log('Settings Form Submitted');
            const key = form.querySelector('input[name="key"]')?.value;
            const value = form.querySelector('input[name="value"]')?.value || form.querySelector('textarea[name="value"]')?.value;
            if (!key || !value) {
                console.error('Settings Form Error: Missing Required Fields', { key, value });
                alert('All fields are required.');
                return;
            }
            const formData = new FormData(form);
            for (let [key, value] of formData.entries()) {
                console.log(`Settings Form Data: ${key}=${value}`);
            }
            fetch('/admin/settings', {
                method: 'POST',
                body: formData
            })
            .then(handleResponse)
            .then(data => {
                if (data) {
                    console.log('Settings Response:', data);
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
        console.log('Initializing Sortable for RulesList');
        Sortable.create(rulesList, {
            animation: 150,
            onEnd: function () {
                console.log('Rules Reordered');
                const order = Array.from(rulesList.querySelectorAll('li')).map(li => li.getAttribute('data-description'));
                console.log('New Rule Order:', order);
                fetch('/admin/reorder_rules', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'order[]=' + order.map(encodeURIComponent).join('&order[]=')
                })
                .then(handleResponse)
                .then(data => {
                    if (data) {
                        console.log('Reorder Rules Response:', data);
                        if (!data.success) alert(data.message);
                    }
                })
                .catch(error => console.error('Error reordering rules:', error));
            }
        });
    } else if (rulesList) {
        console.warn('Sortable library not found for RulesList. Ensure Sortable.js is included in base.html.');
    }
});