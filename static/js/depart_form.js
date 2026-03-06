document.addEventListener('DOMContentLoaded', function () {
    const utils = window.SSIMSFormUtils;
    const form = document.getElementById('departForm');
    const dnoInput = document.getElementById('dno');
    const dnameInput = document.getElementById('dname');
    const telephoneInput = document.getElementById('telephone');
    const previewDno = document.getElementById('preview-dno');
    const previewDname = document.getElementById('preview-dname');
    const previewTelephone = document.getElementById('preview-telephone');

    if (!utils || !form || !dnoInput || !dnameInput || !telephoneInput) {
        return;
    }

    function validateDno() {
        utils.validatePattern(dnoInput, /^[A-Za-z0-9]{1,6}$/, '系部编号只能包含字母和数字，最多 6 位');
    }

    const updateDno = utils.bindTextPreview(dnoInput, previewDno, '未填写');
    const updateDname = utils.bindTextPreview(dnameInput, previewDname, '未填写');
    const updateTelephone = utils.bindTextPreview(telephoneInput, previewTelephone, '未登记');

    dnoInput.addEventListener('input', validateDno);

    updateDno();
    updateDname();
    updateTelephone();
    validateDno();
});
