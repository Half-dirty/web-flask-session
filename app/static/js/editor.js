document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.markdown-editor').forEach(function (element) {
        new EasyMDE({
            element: element,
            spellChecker: false,
            status: false,
            autosave: false
        });
    });
});
