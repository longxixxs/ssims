document.addEventListener('DOMContentLoaded', function () {
    const utils = window.SSIMSFormUtils;
    const form = document.getElementById('classForm');
    const classnoInput = document.getElementById('classno');
    const classnameInput = document.getElementById('classname');
    const departSelect = document.getElementById('dno');
    const previewClassNo = document.getElementById('previewClassNo');
    const previewClassName = document.getElementById('previewClassName');
    const previewDepart = document.getElementById('previewDepart');

    if (!utils || !form || !classnoInput || !classnameInput || !departSelect) {
        return;
    }

    function validateClassNo() {
        utils.validatePattern(classnoInput, /^[A-Za-z0-9]+$/, '班级编号只能包含字母和数字', {
            skip: function (input) {
                return input.readOnly;
            }
        });
    }

    const updateClassNo = utils.bindTextPreview(classnoInput, previewClassNo, '未填写');
    const updateClassName = utils.bindTextPreview(classnameInput, previewClassName, '未填写');
    const updateDepart = utils.bindSelectPreview(departSelect, previewDepart, '未选择', function (value, select) {
        if (!value) {
            return '';
        }
        const option = select.options[select.selectedIndex];
        return option ? (option.text.split(' - ')[1] || option.text).trim() : '';
    });

    classnoInput.addEventListener('input', validateClassNo);

    updateClassNo();
    updateClassName();
    updateDepart();
    validateClassNo();
});
