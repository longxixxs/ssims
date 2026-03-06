document.addEventListener('DOMContentLoaded', function () {
    const utils = window.SSIMSFormUtils;
    const form = document.getElementById('courseForm');
    if (!utils || !form) {
        return;
    }

    const inputs = {
        cno: document.getElementById('cno'),
        cname: document.getElementById('cname'),
        lecture: document.getElementById('lecture'),
        semester: document.getElementById('semester'),
        credit: document.getElementById('credit')
    };

    const previews = {
        cno: document.getElementById('preview-cno'),
        cname: document.getElementById('preview-cname'),
        lecture: document.getElementById('preview-lecture'),
        semester: document.getElementById('preview-semester'),
        credit: document.getElementById('preview-credit'),
        type: document.getElementById('preview-type')
    };

    const courseTypeMap = {
        crc: '公共课',
        bcim: '专业基础课',
        spc: '专业课',
        ocos: '选修课'
    };

    function validateLecture() {
        if (!inputs.lecture.value) {
            inputs.lecture.setCustomValidity('');
            return;
        }
        const value = Number(inputs.lecture.value);
        inputs.lecture.setCustomValidity(Number.isNaN(value) || value < 0 || value > 200 ? '学时应在 0-200 之间' : '');
    }

    function validateCredit() {
        if (!inputs.credit.value) {
            inputs.credit.setCustomValidity('');
            return;
        }
        const value = Number(inputs.credit.value);
        if (Number.isNaN(value) || value < 0 || value > 10) {
            inputs.credit.setCustomValidity('学分应在 0-10 之间');
            return;
        }
        inputs.credit.setCustomValidity((value * 2) % 1 !== 0 ? '学分应为 0.5 的倍数' : '');
    }

    function validateCno() {
        utils.validatePattern(inputs.cno, /^[A-Za-z0-9]+$/, '课程号只能包含字母和数字', {
            skip: function (input) {
                return input.disabled;
            }
        });
    }

    const updateCno = utils.bindTextPreview(inputs.cno, previews.cno, '未填写');
    const updateCname = utils.bindTextPreview(inputs.cname, previews.cname, '未填写');
    const updateLecture = utils.bindTextPreview(inputs.lecture, previews.lecture, '未填写', function (value) {
        return value ? value + ' 小时' : '';
    });
    const updateSemester = utils.bindTextPreview(inputs.semester, previews.semester, '未填写');
    const updateCredit = utils.bindTextPreview(inputs.credit, previews.credit, '未填写', function (value) {
        return value ? value + ' 学分' : '';
    });
    const updateType = utils.bindRadioPreview('input[name="type"]', previews.type, '公共课', function (value) {
        return courseTypeMap[value] || '公共课';
    });

    inputs.lecture.addEventListener('input', validateLecture);
    inputs.credit.addEventListener('input', validateCredit);
    if (inputs.cno && !inputs.cno.disabled) {
        inputs.cno.addEventListener('input', validateCno);
    }

    updateCno();
    updateCname();
    updateLecture();
    updateSemester();
    updateCredit();
    updateType();
    validateLecture();
    validateCredit();
    validateCno();
});
