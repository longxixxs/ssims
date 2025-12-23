// ==================== 页面加载完成 ====================
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initSidebar();
    initPageLoad();
    initLinkAnimations();
    initCardHover();
    initAutoHideMessages();
});

// ==================== 侧边栏切换 ====================
function initSidebar() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    if (!menuToggle || !sidebar) return;

    menuToggle.addEventListener('click', function() {
        const isExpanded = sidebar.classList.toggle('show');
        sidebarOverlay.classList.toggle('show');

        // 更新 ARIA 属性
        this.setAttribute('aria-expanded', isExpanded);

        // 切换图标
        const icon = this.querySelector('i');
        icon.className = isExpanded ? 'bi bi-x' : 'bi bi-list';
    });

    // 点击遮罩关闭
    sidebarOverlay.addEventListener('click', function() {
        sidebar.classList.remove('show');
        this.classList.remove('show');
        menuToggle.setAttribute('aria-expanded', 'false');
        menuToggle.querySelector('i').className = 'bi bi-list';
    });

    // ESC 键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            sidebarOverlay.classList.remove('show');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.querySelector('i').className = 'bi bi-list';
        }
    });
}

// ==================== 页面加载动画 ====================
function initPageLoad() {
    const loading = document.getElementById('globalLoading');

    window.addEventListener('load', function() {
        document.body.classList.add('loaded');

        // 隐藏加载动画
        if (loading) {
            loading.classList.remove('show');
        }
    });
}

// ==================== 链接点击动画 ====================
function initLinkAnimations() {
    document.querySelectorAll('a:not(.no-animation)').forEach(link => {
        link.addEventListener('click', function(e) {
            // 跳过登出和外部链接
            if (this.href.includes('logout') || this.target === '_blank') return;

            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

// ==================== 卡片悬停效果 ====================
function initCardHover() {
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// ==================== 自动隐藏消息提示 ====================
function initAutoHideMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // 5 秒后自动关闭
    });
}

// ==================== 全局 Toast 通知（可选） ====================
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now();
    const iconMap = {
        success: 'check-circle',
        error: 'exclamation-triangle',
        warning: 'exclamation-circle',
        info: 'info-circle'
    };

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${iconMap[type]} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();

    // 移除 DOM
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// ==================== 全局加载状态 ====================
function showLoading() {
    const loading = document.getElementById('globalLoading');
    if (loading) loading.classList.add('show');
}

function hideLoading() {
    const loading = document.getElementById('globalLoading');
    if (loading) loading.classList.remove('show');
}

// ==================== AJAX 请求拦截（可选） ====================
// 为所有 fetch 请求添加加载动画
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        showLoading();
        return originalFetch.apply(this, args).finally(() => {
            hideLoading();
        });
    };
})();
