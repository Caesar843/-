(function () {
    var doc = document.documentElement;
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    var iconEl = toggle.querySelector('.theme-toggle-icon');
    var icons = {
        light: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
            '<circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.6"/>' +
            '<path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
        '</svg>',
        dark: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
            '<path d="M20 14.5A7.5 7.5 0 0 1 9.5 4a6.5 6.5 0 1 0 10.5 10.5z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' +
        '</svg>'
    };

    function systemTheme() {
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function resolveTheme() {
        var stored = localStorage.getItem('theme');
        if (stored === 'light' || stored === 'dark') return stored;
        return systemTheme();
    }

    function setToggleState(theme) {
        var next = theme === 'dark' ? 'light' : 'dark';
        var label = next === 'dark' ? '\u5207\u6362\u5230\u591C\u95F4\u6A21\u5F0F' : '\u5207\u6362\u5230\u65E5\u95F4\u6A21\u5F0F';
        toggle.setAttribute('aria-label', label);
        if (iconEl) {
            iconEl.innerHTML = theme === 'dark' ? icons.dark : icons.light;
        }
    }

    function applyTheme(theme) {
        doc.setAttribute('data-theme', theme);
        setToggleState(theme);
    }

    toggle.addEventListener('click', function () {
        var current = resolveTheme();
        var next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', next);
        applyTheme(next);
    });

    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
            if (!localStorage.getItem('theme')) {
                applyTheme(systemTheme());
            }
        });
    }

    applyTheme(resolveTheme());
})();
