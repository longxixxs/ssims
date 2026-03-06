document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-password-meter-form]').forEach(initPasswordMeter);
});

function initPasswordMeter(form) {
    const primary = form.querySelector('[data-password-primary]');
    const confirmInput = form.querySelector('[data-password-confirm]');
    const bar = form.querySelector('[data-password-bar]');
    const label = form.querySelector('[data-password-label]');
    const badge = form.querySelector('[data-password-match]');

    if (!primary || !confirmInput || !bar || !label || !badge) {
        return;
    }

    function scorePassword(value) {
        let score = 0;
        if (value.length >= 8) score += 30;
        if (/[a-z]/i.test(value)) score += 20;
        if (/\d/.test(value)) score += 20;
        if (/[^A-Za-z0-9]/.test(value)) score += 20;
        if (value.length >= 12) score += 10;
        return Math.min(score, 100);
    }

    function updateStrength() {
        const score = scorePassword(primary.value);
        bar.style.width = score + '%';

        if (!primary.value) {
            bar.className = 'progress-bar';
            label.textContent = '密码强度：待输入';
            return;
        }

        if (score < 45) {
            bar.className = 'progress-bar bg-danger';
            label.textContent = '密码强度：弱';
        } else if (score < 75) {
            bar.className = 'progress-bar bg-warning';
            label.textContent = '密码强度：中';
        } else {
            bar.className = 'progress-bar bg-success';
            label.textContent = '密码强度：强';
        }
    }

    function updateMatch() {
        if (!confirmInput.value) {
            badge.className = 'badge bg-secondary';
            badge.textContent = '未匹配';
            return;
        }

        if (primary.value === confirmInput.value) {
            badge.className = 'badge bg-success';
            badge.textContent = '已匹配';
        } else {
            badge.className = 'badge bg-danger';
            badge.textContent = '不匹配';
        }
    }

    primary.addEventListener('input', function () {
        updateStrength();
        updateMatch();
    });
    confirmInput.addEventListener('input', updateMatch);

    updateStrength();
    updateMatch();
}
