document.addEventListener('DOMContentLoaded', function() {
    var menuBtn = document.getElementById('adminMenuBtn');
    var sidebar = document.getElementById('adminSidebar');
    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    document.querySelectorAll('.chart-bar').forEach(function(bar) {
        var h = bar.style.height;
        bar.style.height = '0';
        setTimeout(function() { bar.style.height = h; }, 200);
    });

    document.querySelectorAll('.freq-bar-row .bar-fill').forEach(function(el, i) {
        var w = el.style.width;
        el.style.width = '0';
        setTimeout(function() { el.style.width = w; }, 250 + i * 60);
    });
});
