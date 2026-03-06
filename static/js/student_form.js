document.addEventListener('DOMContentLoaded', function () {
    const utils = window.SSIMSFormUtils;
    const form = document.getElementById('studentForm');
    if (!utils || !form) {
        return;
    }

    const snoInput = document.getElementById('sno');
    const snameInput = document.getElementById('sname');
    const ageInput = document.getElementById('age');
    const semesterInput = document.getElementById('semester');
    const telephoneInput = document.getElementById('telephone');
    const previewSno = document.getElementById('preview-sno');
    const previewSname = document.getElementById('preview-sname');

    function validatePhone() {
        if (!telephoneInput || !telephoneInput.value) {
            if (telephoneInput) {
                telephoneInput.setCustomValidity('');
            }
            return;
        }
        telephoneInput.setCustomValidity(/^[0-9\-]{7,15}$/.test(telephoneInput.value) ? '' : '请输入有效的电话号码');
    }

    function validateSno() {
        utils.validatePattern(snoInput, /^[A-Za-z0-9]{1,10}$/, '学号只能包含字母和数字，最多 10 个字符', {
            skip: function (input) {
                return input.readOnly;
            }
        });
    }

    const updateSno = utils.bindTextPreview(snoInput, previewSno, '未填写');
    const updateSname = utils.bindTextPreview(snameInput, previewSname, '未填写');

    if (snoInput) {
        snoInput.addEventListener('input', validateSno);
    }
    if (ageInput) {
        ageInput.addEventListener('input', function () {
            utils.validateRange(ageInput, 0, 100, '年龄必须在 0-100 之间');
        });
    }
    if (semesterInput) {
        semesterInput.addEventListener('input', function () {
            utils.validateRange(semesterInput, 1, 12, '学期必须在 1-12 之间');
        });
    }
    if (telephoneInput) {
        telephoneInput.addEventListener('input', validatePhone);
    }

    updateSno();
    updateSname();
    validateSno();
    validatePhone();
    if (ageInput) {
        utils.validateRange(ageInput, 0, 100, '年龄必须在 0-100 之间');
    }
    if (semesterInput) {
        utils.validateRange(semesterInput, 1, 12, '学期必须在 1-12 之间');
    }
});
