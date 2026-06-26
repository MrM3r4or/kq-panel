document.addEventListener('DOMContentLoaded', function() {
    'use strict';
    
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menuToggle');
    const themeToggle = document.getElementById('themeToggle');
    const refreshBtn = document.getElementById('refreshBtn');
    const dynamicContent = document.getElementById('dynamicContent');
    const pageTitle = document.getElementById('pageTitle');
    const toastContainer = document.getElementById('toastContainer');
    const navItems = document.querySelectorAll('.nav-item');
    
    let currentPage = 'status';
    let refreshInterval = null;
    
    function showToast(message, type = 'info') {
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `${icons[type]} ${message}`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideInToast 0.4s ease reverse';
            setTimeout(() => toast.remove(), 400);
        }, 3000);
    }
    
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        themeToggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    });
    
    menuToggle.addEventListener('click', () => sidebar.classList.toggle('closed'));
    
    refreshBtn.addEventListener('click', () => {
        refreshBtn.classList.add('spinning');
        setTimeout(() => refreshBtn.classList.remove('spinning'), 1000);
        loadPage(currentPage);
    });
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            navItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            currentPage = this.dataset.page;
            pageTitle.textContent = this.querySelector('span').textContent;
            loadPage(currentPage);
        });
    });
    
    function loadPage(page) {
        clearInterval(refreshInterval);
        dynamicContent.innerHTML = '<div style="text-align:center;padding:50px;"><i class="fas fa-spinner fa-spin" style="font-size:40px;color:var(--primary);"></i></div>';
        switch(page) {
            case 'status': loadStatus(); break;
            case 'messages': loadMessages(); break;
            case 'files': loadFiles(); break;
            case 'users': loadUsers(); break;
            case 'buttons': loadButtons(); break;
            case 'force_join': loadForceJoin(); break;
            case 'bans': loadBans(); break;
            case 'settings': loadSettings(); break;
        }
    }
    
    // ===== وضعیت =====
    function loadStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const isOnline = data.status === 'running';
                let html = `
                    <div class="card">
                        <div class="card-header">
                            <h3><span class="status-dot ${isOnline ? 'online' : 'offline'}"></span> وضعیت ربات</h3>
                            <div style="display:flex;gap:10px;align-items:center;">
                                <span class="status-badge ${isOnline ? 'online' : 'offline'}">${isOnline ? 'فعال ✅' : 'غیرفعال ❌'}</span>
                                <button class="btn ${isOnline ? 'btn-danger' : 'btn-success'}" id="toggleBtn" onclick="toggleBot('${isOnline ? 'stop' : 'start'}')">
                                    <i class="fas ${isOnline ? 'fa-stop' : 'fa-play'}"></i> ${isOnline ? 'خاموش' : 'روشن'}
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header"><h3><i class="fas fa-terminal"></i> لاگ‌های لحظه‌ای</h3></div>
                        <div class="terminal"><div class="terminal-log" id="logBox">${data.logs?.length ? data.logs.map(l => `<div>${l}</div>`).join('') : '<div>منتظر لاگ...</div>'}</div></div>
                    </div>`;
                dynamicContent.innerHTML = html;
                
                refreshInterval = setInterval(() => {
                    fetch('/api/status').then(r => r.json()).then(d => {
                        const box = document.getElementById('logBox');
                        if (box && d.logs) {
                            box.innerHTML = d.logs.map(l => `<div>${l}</div>`).join('');
                            box.parentElement.scrollTop = box.parentElement.scrollHeight;
                        }
                        const toggleBtn = document.getElementById('toggleBtn');
                        if (toggleBtn) {
                            if (d.status === 'running') {
                                toggleBtn.className = 'btn btn-danger';
                                toggleBtn.innerHTML = '<i class="fas fa-stop"></i> خاموش';
                                toggleBtn.setAttribute('onclick', "toggleBot('stop')");
                            } else {
                                toggleBtn.className = 'btn btn-success';
                                toggleBtn.innerHTML = '<i class="fas fa-play"></i> روشن';
                                toggleBtn.setAttribute('onclick', "toggleBot('start')");
                            }
                        }
                    });
                }, 2000);
            });
    }
    
    window.toggleBot = function(action) {
        fetch('/api/bot/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action})
        }).then(r => r.json()).then(data => {
            showToast(data.running ? 'ربات روشن شد ✅' : 'ربات خاموش شد ⏹️', 'success');
        });
    };
    
    // ===== پیام‌ها =====
    function loadMessages() {
        fetch('/api/messages').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-comment-dots"></i> پیام‌های سفارشی</h3><button class="btn btn-success" onclick="openMessageModal()"><i class="fas fa-plus"></i> افزودن</button></div><div class="table-container"><table><thead><tr><th>دستور</th><th>پاسخ</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;padding:30px;">پیامی ثبت نشده 📝</td></tr>';
            data.forEach(msg => {
                html += `<tr><td><strong>${msg.command}</strong></td><td>${msg.response_text.substring(0, 60)}...</td><td>
                    <button class="btn btn-primary btn-sm" onclick="openMessageModal(${msg.id}, '${msg.command.replace(/'/g, "\\'")}', \`${msg.response_text.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-danger btn-sm" onclick="deleteMessage(${msg.id})"><i class="fas fa-trash"></i></button></td></tr>`;
            });
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    
    window.openMessageModal = function(id = null, command = '', text = '') {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>${id ? '✏️ ویرایش' : '➕ افزودن'} پیام</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">دستور</label><input class="form-control" id="msgCommand" value="${command}"></div>
            <div class="form-group"><label class="form-label">پاسخ</label><textarea class="form-control" id="msgText" rows="5">${text}</textarea></div>
            <div class="modal-actions"><button class="btn btn-success" onclick="saveMessage(${id})"><i class="fas fa-save"></i> ذخیره</button><button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.saveMessage = function(id) {
        const command = document.getElementById('msgCommand').value;
        const text = document.getElementById('msgText').value;
        if (!command || !text) { showToast('فیلدها خالی است', 'error'); return; }
        fetch('/api/messages', { method: id ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(id ? {id, command, text} : {command, text}) })
        .then(r => r.json()).then(() => { document.querySelector('.modal-overlay').remove(); loadMessages(); showToast(id ? 'ویرایش شد ✏️' : 'اضافه شد ✅', 'success'); });
    };
    window.deleteMessage = function(id) {
        if (confirm('حذف شود؟')) fetch(`/api/messages?id=${id}`, {method: 'DELETE'}).then(() => { loadMessages(); showToast('حذف شد 🗑️', 'success'); });
    };
    
    // ===== فایل‌ها =====
    function loadFiles() {
        fetch('/api/files').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-folder-open"></i> فایل‌ها</h3><span>${data.length} فایل</span></div><div class="table-container"><table><thead><tr><th>نام</th><th>نوع</th><th>لینک</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">فایلی نیست 📁</td></tr>';
            data.forEach(f => html += `<tr><td>📄 ${f.file_name}</td><td>${f.file_type}</td><td><a href="/uploads/${f.file_name}" target="_blank" class="btn btn-primary btn-sm">مشاهده</a></td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    
    // ===== کاربران =====
    function loadUsers() {
        fetch('/api/users').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-users"></i> کاربران</h3><span>${data.length} کاربر</span></div><div class="table-container"><table><thead><tr><th>شناسه</th><th>نام</th><th>یوزرنیم</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">کاربری نیست 👥</td></tr>';
            data.forEach(u => html += `<tr><td>${u.user_id}</td><td>${u.first_name} ${u.last_name||''}</td><td>${u.username ? '@'+u.username : '---'}</td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    
    // ===== دکمه‌ها =====
    function loadButtons() {
        fetch('/api/buttons').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-th-large"></i> دکمه‌ها</h3><button class="btn btn-success" onclick="openButtonModal()"><i class="fas fa-plus"></i> افزودن</button></div><div class="table-container"><table><thead><tr><th>متن</th><th>نوع</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">دکمه‌ای نیست 🔘</td></tr>';
            data.forEach(b => html += `<tr><td><strong>${b.button_text}</strong></td><td>${b.menu_type === 'inline' ? 'شیشه‌ای' : 'منویی'}</td><td><button class="btn btn-danger btn-sm" onclick="deleteButton(${b.id})"><i class="fas fa-trash"></i></button></td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    window.openButtonModal = function() {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>➕ افزودن دکمه</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">متن</label><input class="form-control" id="btnText"></div>
            <div class="form-group"><label class="form-label">نوع</label><select class="form-control" id="btnType"><option value="inline">شیشه‌ای</option><option value="keyboard">منویی</option></select></div>
            <div class="form-group"><label class="form-label">عملیات</label><select class="form-control" id="btnAction"><option value="url">لینک</option><option value="callback">دستور</option></select></div>
            <div class="form-group"><label class="form-label">مقدار</label><input class="form-control" id="btnValue"></div>
            <div class="modal-actions"><button class="btn btn-success" onclick="saveButton()">💾 ذخیره</button><button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.saveButton = function() {
        const data = {text: document.getElementById('btnText').value, menu_type: document.getElementById('btnType').value, action_type: document.getElementById('btnAction').value, action_value: document.getElementById('btnValue').value, parent_command: 'main', priority: 0, requires_parent: 0};
        fetch('/api/buttons', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(() => { document.querySelector('.modal-overlay').remove(); loadButtons(); showToast('دکمه اضافه شد ✅', 'success'); });
    };
    window.deleteButton = function(id) { if (confirm('حذف شود؟')) fetch(`/api/buttons?id=${id}`, {method: 'DELETE'}).then(() => loadButtons()); };
    
    // ===== جوین اجباری =====
    function loadForceJoin() {
        fetch('/api/force_join').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-link"></i> جوین اجباری</h3><button class="btn btn-success" onclick="openForceJoinModal()"><i class="fas fa-plus"></i> افزودن</button></div><div class="table-container"><table><thead><tr><th>نام</th><th>یوزرنیم</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="4" style="text-align:center;">کانالی نیست 🔗</td></tr>';
            data.forEach(ch => html += `<tr><td>${ch.channel_name}</td><td>@${ch.channel_username}</td><td><span class="status-badge ${ch.enabled ? 'online' : 'offline'}">${ch.enabled ? 'فعال' : 'غیرفعال'}</span></td><td><button class="btn btn-warning btn-sm" onclick="toggleForceJoin(${ch.id}, ${ch.enabled})">${ch.enabled ? 'غیرفعال' : 'فعال'}</button> <button class="btn btn-danger btn-sm" onclick="deleteForceJoin(${ch.id})"><i class="fas fa-trash"></i></button></td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    window.openForceJoinModal = function() {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>➕ افزودن کانال</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">نام</label><input class="form-control" id="fjName"></div>
            <div class="form-group"><label class="form-label">یوزرنیم (بدون @)</label><input class="form-control" id="fjUsername"></div>
            <div class="form-group"><label class="form-label">پیام</label><textarea class="form-control" id="fjMessage" rows="3">لطفاً عضو شوید</textarea></div>
            <div class="modal-actions"><button class="btn btn-success" onclick="saveForceJoin()">💾 ذخیره</button><button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.saveForceJoin = function() {
        const data = {name: document.getElementById('fjName').value, username: document.getElementById('fjUsername').value, message: document.getElementById('fjMessage').value};
        fetch('/api/force_join', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(() => { document.querySelector('.modal-overlay').remove(); loadForceJoin(); });
    };
    window.toggleForceJoin = function(id, current) {
        fetch('/api/force_join', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, enabled: current ? 0 : 1})}).then(() => loadForceJoin());
    };
    window.deleteForceJoin = function(id) { if (confirm('حذف شود؟')) fetch(`/api/force_join?id=${id}`, {method: 'DELETE'}).then(() => loadForceJoin()); };
    
    // ===== بن =====
    function loadBans() {
        fetch('/api/bans').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-ban"></i> کاربران بن شده</h3><button class="btn btn-danger" onclick="openBanModal()"><i class="fas fa-plus"></i> بن کاربر</button></div><div class="table-container"><table><thead><tr><th>شناسه</th><th>نام</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">کاربری بن نشده ✅</td></tr>';
            data.forEach(b => html += `<tr><td>${b.user_id}</td><td>${b.first_name}</td><td><button class="btn btn-success btn-sm" onclick="unbanUser(${b.user_id})">✅ رفع بن</button></td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    window.openBanModal = function() {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>🚫 بن کاربر</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">شناسه</label><input type="number" class="form-control" id="banUserId"></div>
            <div class="form-group"><label class="form-label">نام</label><input class="form-control" id="banUserName"></div>
            <div class="modal-actions"><button class="btn btn-danger" onclick="banUser()">🚫 بن</button><button class="btn" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.banUser = function() {
        const data = {user_id: document.getElementById('banUserId').value, first_name: document.getElementById('banUserName').value};
        fetch('/api/bans', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        .then(() => { document.querySelector('.modal-overlay').remove(); loadBans(); });
    };
    window.unbanUser = function(userId) { fetch(`/api/bans?user_id=${userId}`, {method: 'DELETE'}).then(() => loadBans()); };
    
    // ===== تنظیمات =====
    function loadSettings() {
        fetch('/api/settings').then(r => r.json()).then(data => {
            let html = `
                <div class="card">
                    <div class="card-header"><h3><i class="fas fa-cog"></i> تنظیمات ربات</h3></div>
                    <div class="form-group"><label class="form-label">توکن فعلی (۱۰ کاراکتر آخر)</label><input class="form-control" value="${data.token ? '...' + data.token : '---'}" disabled></div>
                    <div class="form-group"><label class="form-label">توکن جدید</label><input class="form-control" id="newToken" placeholder="توکن جدید را وارد کنید"></div>
                    <div class="form-group"><label class="form-label">مسیر فعلی ذخیره‌سازی</label><input class="form-control" value="${data.upload_folder}" disabled></div>
                    <div class="form-group"><label class="form-label">مسیر جدید</label><input class="form-control" id="newPath" placeholder="مسیر جدید را وارد کنید"></div>
                    <button class="btn btn-primary" onclick="saveSettings()"><i class="fas fa-save"></i> ذخیره تغییرات</button>
                </div>
                <div class="card">
                    <div class="card-header"><h3><i class="fas fa-sign-out-alt"></i> خروج از پنل</h3></div>
                    <p>با خروج، تمام تنظیمات پاک شده و به صفحه ورود بازمی‌گردید.</p>
                    <button class="btn btn-danger" onclick="logout()"><i class="fas fa-power-off"></i> خروج</button>
                </div>`;
            dynamicContent.innerHTML = html;
        });
    }
    window.saveSettings = function() {
        const newToken = document.getElementById('newToken').value.trim();
        const newPath = document.getElementById('newPath').value.trim();
        if (!newToken && !newPath) { showToast('حداقل یک فیلد را پر کنید', 'error'); return; }
        fetch('/api/settings/update', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: newToken, upload_folder: newPath}) })
        .then(r => r.json()).then(data => {
            if (data.success) { showToast('تنظیمات ذخیره شد ✅', 'success'); loadSettings(); }
            else showToast('خطا: ' + data.error, 'error');
        });
    };
    window.logout = function() {
        if (confirm('آیا مطمئن هستید؟ تمام اطلاعات پاک می‌شود.')) {
            fetch('/api/logout', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) window.location.href = data.redirect;
            });
        }
    };
    
    // شروع
    loadPage('status');
});