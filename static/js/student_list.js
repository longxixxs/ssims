document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.delete-form').forEach(function (form) {
        form.addEventListener('submit', function () {
            const studentName = form.dataset.studentName || '该学生';
            const actionField = form.querySelector('select[name="account_action"]');
            const actionLabel = actionField ? actionField.options[actionField.selectedIndex].text : '归档账号';
            form.dataset.confirm = '确定要归档“' + studentName + '”吗？账号动作：' + actionLabel + '。';
        });
    });
});
