document.addEventListener('DOMContentLoaded', function () {
    function initSort(triggerSelector, tableSelector) {
        document.querySelectorAll(triggerSelector).forEach(function (trigger) {
            trigger.addEventListener('click', function (event) {
                event.preventDefault();
                const sortBy = trigger.dataset.sort;
                const tbody = document.querySelector(tableSelector);
                if (!tbody) {
                    return;
                }
                const rows = Array.from(tbody.querySelectorAll('tr'));
                rows.sort(function (left, right) {
                    const leftName = (left.dataset.sortName || '').toLowerCase();
                    const rightName = (right.dataset.sortName || '').toLowerCase();
                    const leftValue = Number(left.dataset.sortValue || 0);
                    const rightValue = Number(right.dataset.sortValue || 0);
                    if (sortBy === 'name') {
                        return leftName.localeCompare(rightName, 'zh-Hans-CN');
                    }
                    return rightValue - leftValue;
                });
                rows.forEach(function (row) {
                    tbody.appendChild(row);
                });
            });
        });
    }

    initSort('.sort-depart', '#depart-table');
    initSort('.sort-course', '#course-table');
});
