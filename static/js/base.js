document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initReadyState();
    initAutoHideAlerts();
    initConfirmActions();
    initValidation();
    initSubmitState();
    initAutoSubmitControls();
    initPasswordToggles();
    initTooltips();
    initRowLinks();
    initAutofocus();
});

function initSidebar() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (!menuToggle || !sidebar || !sidebarOverlay) {
        return;
    }

    function closeSidebar() {
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
        menuToggle.setAttribute('aria-expanded', 'false');
        const icon = menuToggle.querySelector('i');
        if (icon) {
            icon.className = 'bi bi-list';
        }
    }

    menuToggle.addEventListener('click', function () {
        const opened = sidebar.classList.toggle('show');
        sidebarOverlay.classList.toggle('show', opened);
        menuToggle.setAttribute('aria-expanded', String(opened));
        const icon = menuToggle.querySelector('i');
        if (icon) {
            icon.className = opened ? 'bi bi-x' : 'bi bi-list';
        }
    });

    sidebarOverlay.addEventListener('click', closeSidebar);
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });
}

function initReadyState() {
    const loading = document.getElementById('globalLoading');
    document.body.classList.add('loaded');
    window.addEventListener('load', function () {
        document.body.classList.add('loaded');
        if (loading) {
            loading.classList.remove('show');
        }
    });
}

function initAutoHideAlerts() {
    document.querySelectorAll('.alert').forEach(function (alertEl) {
        setTimeout(function () {
            try {
                bootstrap.Alert.getOrCreateInstance(alertEl).close();
            } catch (error) {
                alertEl.remove();
            }
        }, 4500);
    });
}

function initConfirmActions() {
    document.addEventListener('click', function (event) {
        const confirmLink = event.target.closest('a[data-confirm], button[data-confirm]:not([type="submit"])');
        if (!confirmLink) {
            return;
        }
        const message = confirmLink.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });

    document.addEventListener('submit', function (event) {
        const form = event.target;
        const submitter = event.submitter;
        const message = (submitter && submitter.dataset.confirm) || form.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });
}

function initValidation() {
    document.addEventListener('submit', function (event) {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.classList.contains('needs-validation')) {
            return;
        }

        if (form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        form.classList.add('was-validated');

        const invalidField = form.querySelector(':invalid');
        if (invalidField && typeof invalidField.focus === 'function') {
            invalidField.focus({ preventScroll: true });
            if (typeof invalidField.scrollIntoView === 'function') {
                invalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    });
}

function initSubmitState() {
    document.addEventListener('submit', function (event) {
        if (event.defaultPrevented) {
            return;
        }

        const submitter = event.submitter;
        if (!submitter || submitter.dataset.skipBusy === 'true') {
            return;
        }
        if (submitter.disabled) {
            event.preventDefault();
            return;
        }

        const busyText = submitter.dataset.submitText;
        if (!busyText) {
            return;
        }

        submitter.dataset.originalHtml = submitter.innerHTML;
        submitter.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>' + busyText;
        submitter.disabled = true;
    });
}

function initAutoSubmitControls() {
    document.querySelectorAll('[data-auto-submit]').forEach(function (control) {
        const form = control.form || document.getElementById(control.dataset.autoSubmitForm || '');
        if (!form) {
            return;
        }

        const eventName = control.dataset.autoSubmitEvent || 'change';
        const delay = Number(control.dataset.autoSubmitDelay || 0);
        let timer = null;

        control.addEventListener(eventName, function () {
            window.clearTimeout(timer);
            timer = window.setTimeout(function () {
                form.requestSubmit();
            }, delay);
        });
    });
}

function initPasswordToggles() {
    document.querySelectorAll('.password-toggle').forEach(function (button) {
        button.addEventListener('click', function () {
            const input = this.closest('.input-group')?.querySelector('input');
            if (!input) {
                return;
            }
            const shown = input.type === 'text';
            input.type = shown ? 'password' : 'text';
            const icon = this.querySelector('i');
            if (icon) {
                icon.className = shown ? 'bi bi-eye' : 'bi bi-eye-slash';
            }
        });
    });
}

function initTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
        bootstrap.Tooltip.getOrCreateInstance(element);
    });
}

function shouldIgnoreRowLinkTrigger(target) {
    return Boolean(target && target.closest('a, button, form, input, select, textarea, label'));
}

function navigateToRowLink(row) {
    const target = row.dataset.rowLink;
    if (target) {
        window.location.href = target;
    }
}

function initRowLinks() {
    document.querySelectorAll('[data-row-link]').forEach(function (row) {
        if (!row.hasAttribute('tabindex')) {
            row.tabIndex = 0;
        }
        if (!row.hasAttribute('role')) {
            row.setAttribute('role', 'link');
        }

        row.addEventListener('click', function (event) {
            if (shouldIgnoreRowLinkTrigger(event.target)) {
                return;
            }
            navigateToRowLink(row);
        });

        row.addEventListener('keydown', function (event) {
            if (shouldIgnoreRowLinkTrigger(event.target)) {
                return;
            }
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                navigateToRowLink(row);
            }
        });
    });
}

function initAutofocus() {
    document.querySelectorAll('form[data-autofocus-first]').forEach(function (form) {
        const firstEditable = form.querySelector('input:not([readonly]):not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])');
        if (firstEditable && typeof firstEditable.focus === 'function') {
            firstEditable.focus();
        }
    });
}

function showLoading() {
    const loading = document.getElementById('globalLoading');
    if (loading) {
        loading.classList.add('show');
    }
}

function hideLoading() {
    const loading = document.getElementById('globalLoading');
    if (loading) {
        loading.classList.remove('show');
    }
}
