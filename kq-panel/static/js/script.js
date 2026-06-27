document.addEventListener('DOMContentLoaded', function() {
    'use strict';
    
    // تابع نمایش/مخفی کردن فیلدهای هوش مصنوعی
    window.toggleAiFields = function() {
        const type = document.getElementById('newBotType').value;
        const aiFields = document.getElementById('aiFields');
        if (type === 'assistant') {
            aiFields.style.display = 'block';
        } else {
            aiFields.style.display = 'none';
        }
    };

    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menuToggle');
    const themeToggle = document.getElementById('themeToggle');
    const refreshBtn = document.getElementById('refreshBtn');
    const dynamicContent = document.getElementById('dynamicContent');
    const pageTitle = document.getElementById('pageTitle');
    const toastContainer = document.getElementById('toastContainer');
    const brandClickable = document.getElementById('brandClickable');
    const botsOverlay = document.getElementById('botsOverlay');
    const botList = document.getElementById('botList');
    const addBotModal = document.getElementById('addBotModal');

    let currentBotId = null;
    let currentBotType = 'uploader';
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

    function getTypeLabel(type) {
        const labels = { 'uploader': '📁 آپلودر', 'anonymous': '👻 پیام ناشناس', 'buy_sell': '🛒 خرید و فروش', 'assistant': '🧠 دستیار' };
        return labels[type] || type;
    }

    // Theme
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

    // Fetch current bot
    function fetchCurrentBot() {
        return fetch('/api/current_bot')
            .then(r => r.json())
            .then(bot => {
                if (bot && bot.id) {
                    currentBotId = bot.id;
                    currentBotType = bot.type;
                    document.getElementById('currentBotType').textContent = getTypeLabel(bot.type);
                } else {
                    currentBotId = null;
                    document.getElementById('currentBotType').textContent = 'بدون بات';
                }
            })
            .catch(() => {
                currentBotId = null;
                document.getElementById('currentBotType').textContent = 'خطا';
            });
    }

    // Build sidebar
    function buildSidebar(type) {
        const nav = document.getElementById('sidebarNav');
        const commonItems = [
            { page: 'status', icon: 'fa-chart-line', text: 'وضعیت ربات', badge: 'pulse' },
            { page: 'messages', icon: 'fa-comment-dots', text: 'تنظیمات پیام‌ها' },
            { page: 'users', icon: 'fa-users', text: 'کاربران' },
            { page: 'buttons', icon: 'fa-th-large', text: 'مدیریت دکمه‌ها' },
            { page: 'force_join', icon: 'fa-link', text: 'جوین اجباری' },
            { page: 'bans', icon: 'fa-ban', text: 'مدیریت بن' },
            { page: 'broadcast', icon: 'fa-bullhorn', text: 'پیام همگانی' },
            { page: 'settings', icon: 'fa-cog', text: 'تنظیمات' }
        ];

        let typeSpecific = [];
        if (type === 'uploader') {
            typeSpecific = [{ page: 'files', icon: 'fa-folder-open', text: 'فایل‌ها' }];
        } else if (type === 'assistant') {
            typeSpecific = [
                { page: 'ai_commands', icon: 'fa-scroll', text: 'دستورات به ربات' },
                { page: 'ai_settings', icon: 'fa-robot', text: 'تنظیمات هوش مصنوعی' },
                { page: 'ai_forbidden', icon: 'fa-ban', text: 'نبایدها' },
                { page: 'ai_dnd', icon: 'fa-clock', text: 'مزاحم نشوید' }
            ];
        }

        const allItems = [...commonItems];
        if (typeSpecific.length > 0) {
            allItems.splice(2, 0, ...typeSpecific);
        }

        nav.innerHTML = allItems.map(item => `
            <a href="#" class="nav-item" data-page="${item.page}">
                <i class="fas ${item.icon}"></i><span>${item.text}</span>
                ${item.badge ? '<span class="badge pulse"></span>' : ''}
            </a>
        `).join('');

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                currentPage = this.dataset.page;
                pageTitle.textContent = this.querySelector('span').textContent;
                loadPage(currentPage);
            });
        });

        const firstItem = nav.querySelector('.nav-item');
        if (firstItem) firstItem.classList.add('active');
    }

    // Page loader
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
            case 'broadcast': loadBroadcast(); break;
            case 'settings': loadSettings(); break;
            case 'ai_commands': loadAiCommands(); break;
            case 'ai_settings': loadAiSettings(); break;
            case 'ai_forbidden': loadAiForbidden(); break;
            case 'ai_dnd': loadAiDnd(); break;
            default: dynamicContent.innerHTML = '<div class="card">صفحه‌ای یافت نشد.</div>';
        }
    }

    // ========== 1. Status ==========
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
        fetch('/api/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action})
        }).then(r => r.json()).then(data => {
            showToast(data.running ? 'ربات روشن شد ✅' : 'ربات خاموش شد ⏹️', 'success');
        });
    };

    // ========== 2. Messages ==========
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

    // ========== 3. Files ==========
    function loadFiles() {
        fetch('/api/files').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-folder-open"></i> فایل‌ها</h3><span>${data.length} فایل</span></div><div class="table-container"><table><thead><tr><th>نام</th><th>نوع</th><th>لینک</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">فایلی نیست 📁</td></tr>';
            data.forEach(f => html += `<tr><td>📄 ${f.file_name}</td><td>${f.file_type}</td><td><a href="/uploads/${f.file_name}" target="_blank" class="btn btn-primary btn-sm">مشاهده</a></td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }

    // ========== 4. Users ==========
    function loadUsers() {
        fetch('/api/users').then(res => res.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-users"></i> کاربران</h3><span>${data.length} کاربر</span></div><div class="table-container"><table><thead><tr><th>شناسه</th><th>نام</th><th>یوزرنیم</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">کاربری نیست 👥</td></tr>';
            data.forEach(u => html += `<tr><td>${u.user_id}</td><td>${u.first_name} ${u.last_name||''}</td><td>${u.username ? '@'+u.username : '---'}</td></tr>`);
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }

    // ========== 5. Buttons ==========
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

    // ========== 6. Force Join ==========
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

    // ========== 7. Bans ==========
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

    // ========== 8. Broadcast ==========
    function loadBroadcast() {
        const timezones = moment.tz.names();
        let html = `
            <div class="card">
                <div class="card-header"><h3><i class="fas fa-bullhorn"></i> پیام همگانی</h3></div>
                <div class="form-group">
                    <label class="form-label">منطقه زمانی</label>
                    <select class="form-control" id="timezoneSelect">${timezones.map(tz => `<option value="${tz}">${tz}</option>`).join('')}</select>
                </div>
                <div class="form-group">
                    <label class="form-label">متن پیام</label>
                    <textarea class="form-control" id="broadcastMessage" rows="4" placeholder="پیام خود را بنویسید..."></textarea>
                </div>
                <div class="form-group">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="scheduleCheck" onchange="toggleSchedule()">
                        <span>زمان‌بندی ارسال</span>
                    </label>
                    <input type="datetime-local" class="form-control" id="scheduleTime" style="display:none;">
                </div>
                <button class="btn btn-primary" onclick="sendBroadcast()"><i class="fas fa-paper-plane"></i> ارسال</button>
                <div id="broadcastStatus" style="margin-top:10px;"></div>
            </div>`;
        dynamicContent.innerHTML = html;
    }
    window.toggleSchedule = function() {
        document.getElementById('scheduleTime').style.display = document.getElementById('scheduleCheck').checked ? 'block' : 'none';
    };
    window.sendBroadcast = function() {
        const tz = document.getElementById('timezoneSelect').value;
        const message = document.getElementById('broadcastMessage').value;
        const scheduled = document.getElementById('scheduleCheck').checked;
        const timeVal = document.getElementById('scheduleTime').value;
        if (!message) { showToast('متن پیام نباید خالی باشد', 'error'); return; }
        fetch('/api/broadcast', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message, timezone: tz, scheduled_time: scheduled ? timeVal : null}) })
        .then(r => r.json()).then(data => {
            if (data.success) showToast('پیام همگانی با موفقیت ثبت شد ✅', 'success');
            else showToast('خطا در ارسال پیام', 'error');
        });
    };

    // ========== 9. Settings ==========
    function loadSettings() {
        fetch('/api/settings').then(r => r.json()).then(data => {
            let html = `
                <div class="card">
                    <div class="card-header"><h3><i class="fas fa-cog"></i> تنظیمات ربات</h3></div>
                    <div class="form-group"><label class="form-label">توکن فعلی (۱۰ کاراکتر آخر)</label><input class="form-control" value="${data.token ? '...' + data.token : '---'}" disabled></div>
                    <div class="form-group"><label class="form-label">توکن جدید</label><input class="form-control" id="newToken" placeholder="توکن جدید را وارد کنید"></div>
                    <div class="form-group"><label class="form-label">مسیر فعلی ذخیره‌سازی</label><input class="form-control" value="${data.folder}" disabled></div>
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
        fetch('/api/settings/update', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: newToken, folder: newPath}) })
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

    // ========== AI Commands ==========
    function loadAiCommands() {
        fetch('/api/ai/commands').then(r => r.json()).then(data => {
            let html = `<div class="card"><div class="card-header"><h3><i class="fas fa-scroll"></i> دستورات به ربات</h3><button class="btn btn-success" onclick="openAiCommandModal()"><i class="fas fa-plus"></i> افزودن</button></div><div class="table-container"><table><thead><tr><th>دستور</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="3" style="text-align:center;">دستوری ثبت نشده</td></tr>';
            data.forEach(cmd => {
                html += `<tr><td>${cmd.text}</td><td><button class="btn ${cmd.enabled ? 'btn-success' : 'btn-warning'} btn-sm" onclick="toggleAiCommand('${cmd.id}')">${cmd.enabled ? 'فعال' : 'غیرفعال'}</button></td><td><button class="btn btn-danger btn-sm" onclick="deleteAiCommand('${cmd.id}')"><i class="fas fa-trash"></i></button></td></tr>`;
            });
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    window.openAiCommandModal = function() {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>➕ افزودن دستور</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">دستور (متن کامل)</label><textarea class="form-control" id="cmdText" rows="4" placeholder="مثال: تو یک دستیار خندق هستی..."></textarea></div>
            <div class="modal-actions"><button class="btn btn-success" onclick="saveAiCommand()">💾 ذخیره</button><button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.saveAiCommand = function() {
        const text = document.getElementById('cmdText').value.trim();
        if (!text) { showToast('متن خالی', 'error'); return; }
        fetch('/api/ai/commands', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text}) })
            .then(() => { document.querySelector('.modal-overlay').remove(); loadAiCommands(); showToast('دستور اضافه شد ✅', 'success'); });
    };
    window.toggleAiCommand = function(id) {
        fetch('/api/ai/commands/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) })
            .then(() => loadAiCommands());
    };
    window.deleteAiCommand = function(id) {
        if (confirm('حذف شود؟')) fetch(`/api/ai/commands?id=${id}`, { method: 'DELETE' }).then(() => loadAiCommands());
    };

    // ========== AI Settings ==========
    function loadAiSettings() {
        fetch('/api/ai/settings').then(r => r.json()).then(data => {
            let html = `
                <div class="card">
                    <div class="card-header"><h3><i class="fas fa-robot"></i> تنظیمات هوش مصنوعی</h3></div>
                    <div class="form-group"><label class="form-label">توکن فعلی (نمایش ۱۰ کاراکتر آخر)</label><input class="form-control" value="${data.ai_token ? '...' + data.ai_token.slice(-10) : '---'}" disabled></div>
                    <div class="form-group"><label class="form-label">توکن جدید</label><input class="form-control" id="aiToken" placeholder="توکن جدید"></div>
                    <div class="form-group"><label class="form-label">مدل فعلی</label><input class="form-control" value="${data.ai_model || ''}" disabled></div>
                    <div class="form-group"><label class="form-label">مدل جدید</label><input class="form-control" id="aiModel" placeholder="مثال: openai/gpt-4o"></div>
                    <button class="btn btn-primary" onclick="saveAiSettings()"><i class="fas fa-save"></i> ذخیره</button>
                </div>`;
            dynamicContent.innerHTML = html;
        });
    }
    window.saveAiSettings = function() {
        const token = document.getElementById('aiToken').value.trim();
        const model = document.getElementById('aiModel').value.trim();
        if (!token && !model) { showToast('تغییری وارد نشده', 'error'); return; }
        const payload = {};
        if (token) payload.ai_token = token;
        if (model) payload.ai_model = model;
        fetch('/api/ai/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
            .then(r => r.json()).then(() => { loadAiSettings(); showToast('تنظیمات ذخیره شد ✅', 'success'); });
    };

    // ========== AI Forbidden ==========
    function loadAiForbidden() {
        fetch('/api/ai/forbidden').then(r => r.json()).then(data => {
            let allEnabled = data.length ? data.every(f => f.enabled) : false;
            let html = `<div class="card">
                <div class="card-header">
                    <h3><i class="fas fa-ban"></i> نبایدها</h3>
                    <div>
                        <button class="btn btn-success" onclick="openAiForbiddenModal()"><i class="fas fa-plus"></i> افزودن</button>
                        <button class="btn btn-warning" onclick="toggleAllForbidden()">${allEnabled ? 'غیرفعال کردن همه' : 'فعال کردن همه'}</button>
                    </div>
                </div>
                <div class="table-container"><table><thead><tr><th>عبارت</th><th>پاسخ</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>`;
            if (!data.length) html += '<tr><td colspan="4" style="text-align:center;">موردی ثبت نشده</td></tr>';
            data.forEach(f => {
                html += `<tr>
                    <td>${f.phrase}</td><td>${f.response}</td>
                    <td><button class="btn ${f.enabled ? 'btn-success' : 'btn-danger'} btn-sm" onclick="toggleAiForbidden('${f.id}')">${f.enabled ? 'فعال' : 'غیرفعال'}</button></td>
                    <td><button class="btn btn-danger btn-sm" onclick="deleteAiForbidden('${f.id}')"><i class="fas fa-trash"></i></button></td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
            dynamicContent.innerHTML = html;
        });
    }
    window.openAiForbiddenModal = function() {
        const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
        overlay.innerHTML = `<div class="modal"><div class="modal-header"><h3>➕ افزودن عبارت ممنوع</h3><button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button></div>
            <div class="form-group"><label class="form-label">دستور (عبارت)</label><input class="form-control" id="forbiddenPhrase" placeholder="مثال: یک کد بنویس که..."></div>
            <div class="form-group"><label class="form-label">پاسخ پیش‌فرض</label><textarea class="form-control" id="forbiddenResponse" rows="2">ببخشید اجازه پردازش این درخواست رو ندارم.</textarea></div>
            <div class="modal-actions"><button class="btn btn-success" onclick="saveAiForbidden()">💾 ذخیره</button><button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove()">لغو</button></div></div>`;
        document.body.appendChild(overlay);
    };
    window.saveAiForbidden = function() {
        const phrase = document.getElementById('forbiddenPhrase').value.trim();
        const response = document.getElementById('forbiddenResponse').value.trim();
        if (!phrase) { showToast('عبارت خالی', 'error'); return; }
        fetch('/api/ai/forbidden', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({phrase, response}) })
            .then(() => { document.querySelector('.modal-overlay').remove(); loadAiForbidden(); showToast('اضافه شد ✅', 'success'); });
    };
    window.toggleAiForbidden = function(id) {
        fetch('/api/ai/forbidden/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) })
            .then(() => loadAiForbidden());
    };
    window.toggleAllForbidden = function() {
        fetch('/api/ai/forbidden/toggle', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) })
            .then(() => loadAiForbidden());
    };
    window.deleteAiForbidden = function(id) {
        if (confirm('حذف شود؟')) fetch(`/api/ai/forbidden?id=${id}`, { method: 'DELETE' }).then(() => loadAiForbidden());
    };

    // ========== AI DND ==========
    function loadAiDnd() {
        fetch('/api/ai/dnd').then(r => r.json()).then(data => {
            let html = `<div class="card">
                <div class="card-header"><h3><i class="fas fa-clock"></i> مزاحم نشوید</h3>
                <button class="btn ${data.enabled ? 'btn-danger' : 'btn-success'}" onclick="toggleDnd()">${data.enabled ? 'غیرفعال کردن' : 'فعال کردن'} کلی</button></div>
                <div class="form-group"><label class="form-label">پیام خودکار</label><textarea class="form-control" id="dndMessage" rows="3">${data.message || ''}</textarea></div>
                <div class="form-group">
                    <label style="display:flex;align-items:center;gap:8px;"><input type="checkbox" id="dndTimerCheck" ${data.timer_enabled ? 'checked' : ''} onchange="toggleDndTimer()"> فعال‌سازی تایمر</label>
                    <div id="dndTimerSection" style="display:${data.timer_enabled ? 'block' : 'none'}; margin-top:10px;">
                        <label class="form-label">از ساعت</label><input type="time" class="form-control" id="dndStartTime" value="${data.start_time || ''}">
                        <label class="form-label">تا ساعت</label><input type="time" class="form-control" id="dndEndTime" value="${data.end_time || ''}">
                        <label style="display:flex;align-items:center;gap:8px; margin-top:10px;"><input type="checkbox" id="dndDateCheck" ${data.start_date ? 'checked' : ''} onchange="toggleDndDate()"> محدودیت تاریخ</label>
                        <div id="dndDateSection" style="display:${data.start_date ? 'block' : 'none'}; margin-top:10px;">
                            <label class="form-label">از تاریخ</label><input type="date" class="form-control" id="dndStartDate" value="${data.start_date || ''}">
                            <label class="form-label">تا تاریخ</label><input type="date" class="form-control" id="dndEndDate" value="${data.end_date || ''}">
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="saveDnd()">💾 ذخیره</button>
            </div>`;
            dynamicContent.innerHTML = html;
        });
    }
    window.toggleDnd = function() {
        fetch('/api/ai/dnd', { method: 'GET' }).then(r => r.json()).then(data => {
            data.enabled = !data.enabled;
            fetch('/api/ai/dnd', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
                .then(() => { loadAiDnd(); showToast('تغییر وضعیت', 'success'); });
        });
    };
    window.toggleDndTimer = function() {
        document.getElementById('dndTimerSection').style.display = document.getElementById('dndTimerCheck').checked ? 'block' : 'none';
    };
    window.toggleDndDate = function() {
        document.getElementById('dndDateSection').style.display = document.getElementById('dndDateCheck').checked ? 'block' : 'none';
    };
    window.saveDnd = function() {
        fetch('/api/ai/dnd', { method: 'GET' }).then(r => r.json()).then(data => {
            data.message = document.getElementById('dndMessage').value;
            data.timer_enabled = document.getElementById('dndTimerCheck').checked;
            if (data.timer_enabled) {
                data.start_time = document.getElementById('dndStartTime').value;
                data.end_time = document.getElementById('dndEndTime').value;
            }
            const dateCheck = document.getElementById('dndDateCheck');
            if (dateCheck && dateCheck.checked) {
                data.start_date = document.getElementById('dndStartDate').value;
                data.end_date = document.getElementById('dndEndDate').value;
            } else {
                data.start_date = '';
                data.end_date = '';
            }
            fetch('/api/ai/dnd', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
                .then(() => { showToast('ذخیره شد ✅', 'success'); });
        });
    };

    // ========== Bot Management (Overlay & Modal) ==========
    brandClickable.addEventListener('click', () => {
        botsOverlay.style.display = 'flex';
        loadBotList();
    });
    window.closeBotsOverlay = function() { botsOverlay.style.display = 'none'; };
    function loadBotList() {
        fetch('/api/bots').then(r => r.json()).then(bots => {
            botList.innerHTML = bots.map(bot => `
                <div class="bot-item ${bot.id === currentBotId ? 'active' : ''}" onclick="switchToBot(${bot.id})">
                    <span class="bot-token">${bot.token.substring(0,12)}...</span>
                    <span class="bot-type-badge">${getTypeLabel(bot.type)}</span>
                </div>
            `).join('');
        });
    }
    window.switchToBot = function(botId) {
        fetch('/api/switch_bot', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({bot_id: botId}) })
            .then(() => window.location.reload());
    };
    window.openAddBotModal = function() { addBotModal.style.display = 'flex'; };
    window.closeAddBotModal = function() { addBotModal.style.display = 'none'; };
    // تابع افزودن ربات (بدون تعریف تکراری)
    window.addNewBot = function() {
        const token = document.getElementById('newBotToken').value.trim();
        const type = document.getElementById('newBotType').value;
        if (!token) { showToast('توکن ربات نمی‌تواند خالی باشد', 'error'); return; }
        if (type !== 'uploader' && type !== 'assistant') {
            showToast('این نوع ربات فعلاً در دسترس نیست', 'error');
            return;
        }
        
        const payload = { token, type };
        
        if (type === 'assistant') {
            const aiToken = document.getElementById('newAiToken').value.trim();
            const aiModel = document.getElementById('newAiModel').value.trim();
            if (!aiToken) { showToast('توکن هوش مصنوعی الزامی است', 'error'); return; }
            if (!aiModel) { showToast('مدل هوش مصنوعی الزامی است', 'error'); return; }
            payload.ai_token = aiToken;
            payload.ai_model = aiModel;
        }
        
        fetch('/api/add_bot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('ربات جدید اضافه شد!', 'success');
                closeAddBotModal();
                loadBotList();
                // پاک کردن فیلدها
                document.getElementById('newBotToken').value = '';
                if (type === 'assistant') {
                    document.getElementById('newAiToken').value = '';
                    document.getElementById('newAiModel').value = '';
                }
                document.getElementById('aiFields').style.display = 'none';
                document.getElementById('newBotType').value = 'uploader';
            } else {
                showToast('خطا: ' + (data.error || 'مشکل در افزودن ربات'), 'error');
            }
        });
    };

    // Initialize
    fetchCurrentBot().then(() => {
        buildSidebar(currentBotType);
        loadPage('status');
    });
});