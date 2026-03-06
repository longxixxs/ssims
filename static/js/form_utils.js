(function () {
    function readTrimmed(input) {
        return input ? input.value.trim() : '';
    }

    function setText(target, value, emptyText) {
        if (!target) {
            return;
        }
        target.textContent = value || emptyText;
    }

    function validatePattern(input, regex, message, options) {
        if (!input) {
            return;
        }

        const settings = options || {};
        if (typeof settings.skip === 'function' && settings.skip(input)) {
            input.setCustomValidity('');
            return;
        }

        const value = readTrimmed(input);
        if (!value && settings.allowEmpty !== false) {
            input.setCustomValidity('');
            return;
        }

        input.setCustomValidity(regex.test(value) ? '' : message);
    }

    function validateRange(input, min, max, message) {
        if (!input) {
            return;
        }

        if (!input.value) {
            input.setCustomValidity('');
            return;
        }

        const value = Number(input.value);
        input.setCustomValidity(Number.isNaN(value) || value < min || value > max ? message : '');
    }

    function bindTextPreview(input, target, emptyText, transform) {
        function update() {
            const rawValue = readTrimmed(input);
            const nextValue = typeof transform === 'function' ? transform(rawValue, input) : rawValue;
            setText(target, nextValue, emptyText);
        }

        if (input) {
            input.addEventListener('input', update);
        }

        return update;
    }

    function bindSelectPreview(select, target, emptyText, transform) {
        function update() {
            const rawValue = readTrimmed(select);
            const nextValue = typeof transform === 'function' ? transform(rawValue, select) : rawValue;
            setText(target, nextValue, emptyText);
        }

        if (select) {
            select.addEventListener('change', update);
        }

        return update;
    }

    function bindRadioPreview(selector, target, emptyText, transform) {
        const radios = Array.from(document.querySelectorAll(selector));

        function update() {
            const selected = radios.find(function (radio) {
                return radio.checked;
            });
            const value = selected ? selected.value : '';
            const nextValue = typeof transform === 'function' ? transform(value, selected) : value;
            setText(target, nextValue, emptyText);
        }

        radios.forEach(function (radio) {
            radio.addEventListener('change', update);
        });

        return update;
    }

    window.SSIMSFormUtils = {
        bindRadioPreview: bindRadioPreview,
        bindSelectPreview: bindSelectPreview,
        bindTextPreview: bindTextPreview,
        readTrimmed: readTrimmed,
        setText: setText,
        validatePattern: validatePattern,
        validateRange: validateRange
    };
})();
