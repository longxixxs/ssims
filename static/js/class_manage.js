document.addEventListener('DOMContentLoaded', function() {
    // 删除确认
    function confirmDelete(link) {
        const className = link.getAttribute('data-classname') || '该班级';
        return confirm(`确定要删除"${className}"吗？此操作不可撤销！`);
    }

    // 绑定删除按钮点击事件
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirmDelete(this)) {
                e.preventDefault();
            }
        });
    });

    // 统计卡片动画
    const statCards = document.querySelectorAll('.card');
    statCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.style.animation = 'fadeInUp 0.5s ease-out forwards';
        card.style.opacity = '0';
    });

    // 为表格行添加悬停效果
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
            this.style.transition = 'transform 0.3s ease';
        });

        row.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
});

// CSS动画
const style = document.createElement('style');
style.textContent = `
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
`;
document.head.appendChild(style);
