document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('classForm');
    const submitBtn = document.getElementById('submitBtn');
    const classnoInput = document.getElementById('classno');
    const classnameInput = document.getElementById('classname');
    const dnoSelect = document.getElementById('dno');

    // 实时预览更新
    function updatePreview() {
        document.getElementById('previewClassNo').textContent =
            classnoInput.value.trim() || '未填写';

        document.getElementById('previewClassName').textContent =
            classnameInput.value.trim() || '未填写';

        if (dnoSelect.value) {
            const selectedOption = dnoSelect.options[dnoSelect.selectedIndex];
            document.getElementById('previewDepart').textContent =
                selectedOption.text.split(' - ')[1] || selectedOption.text;
        } else {
            document.getElementById('previewDepart').textContent = '未选择';
        }
    }

    // 表单提交验证
    form.addEventListener('submit', function(event) {
        if (!classnoInput.value.trim()) {
            alert('请输入班级编号');
            classnoInput.focus();
            event.preventDefault();
            return false;
        }

        if (!classnameInput.value.trim()) {
            alert('请输入班级名称');
            classnameInput.focus();
            event.preventDefault();
            return false;
        }

        if (!dnoSelect.value) {
            alert('请选择所属系部');
            dnoSelect.focus();
            event.preventDefault();
            return false;
        }

        // 防止重复提交
        if (submitBtn.disabled) {
            event.preventDefault();
            return false;
        }

        // 显示加载状态
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';
        submitBtn.disabled = true;

        // 超时恢复
        setTimeout(function() {
            if (submitBtn.disabled) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                alert('保存时间过长，请检查网络连接后重试。');
            }
        }, 10000);

        return true;
    });

    // 强制修复下拉菜单（确保可点击）
    dnoSelect.style.pointerEvents = 'auto';
    dnoSelect.style.cursor = 'pointer';

    // 初始化预览
    updatePreview();

    // 如果有编辑模式，确保预览正确显示
    {% if cl and cl.dno %}
    setTimeout(function() {
        updatePreview();
    }, 100);
    {% endif %}
});
