document.addEventListener('DOMContentLoaded', function() {
    // Mobile sidebar toggle
    const menuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('userSidebar');
    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    // Upload drag-and-drop
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('videoFile') || document.getElementById('imageFile');
    if (uploadZone && fileInput) {
        uploadZone.addEventListener('click', function() { fileInput.click(); });
        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', function() {
            uploadZone.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileLabel(e.dataTransfer.files[0].name);
            }
        });
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length) updateFileLabel(fileInput.files[0].name);
        });
    }

    function updateFileLabel(name) {
        const label = document.getElementById('fileNameLabel');
        if (label) label.textContent = name;
    }

    // Animate confidence meters
    document.querySelectorAll('.meter-fill').forEach(function(el) {
        const w = el.style.width;
        el.style.width = '0';
        setTimeout(function() { el.style.width = w; }, 200);
    });

    // Animate frequency bars
    document.querySelectorAll('.freq-bar-row .bar-fill').forEach(function(el, i) {
        const w = el.style.width;
        el.style.width = '0';
        setTimeout(function() { el.style.width = w; }, 300 + i * 80);
    });
});
