(function () {
    const form = document.querySelector('[data-shop-binding-form]');
    if (!form) return;

    const disableForm = window.SHOP_BINDING_DISABLE_FORM === true;
    const submitBtn = form.querySelector('[data-submit-btn]');
    const saveDraftBtn = form.querySelector('[data-save-draft-btn]');
    const resetBtn = form.querySelector('[data-reset-btn]');
    const intentInput = form.querySelector('input[name="intent"]');
    const draftKey = 'shop-binding-form-draft-v1';
    let isDraftSubmit = false;

    const summary = document.createElement('div');
    summary.className = 'error-summary';
    summary.style.display = 'none';
    summary.setAttribute('aria-expanded', 'true');
    summary.innerHTML = '<button type="button" class="error-summary-toggle" data-error-summary-toggle>请修正以下问题后再提交</button><ul></ul>';
    form.prepend(summary);

    const identityInputs = form.querySelectorAll('[name="identity_type"]');
    const authorizationInput = form.querySelector('#id_authorization_note');
    const authorizationHint = authorizationInput
        ? authorizationInput.closest('.mb-3').querySelector('.form-hint')
        : null;

    function identityNeedsAuthorization() {
        const checked = form.querySelector('[name="identity_type"]:checked');
        return checked && checked.value !== 'OWNER';
    }

    function syncAuthorizationState() {
        if (!authorizationInput) return;
        const required = identityNeedsAuthorization();
        authorizationInput.required = required;
        authorizationInput.setAttribute('aria-required', required ? 'true' : 'false');
        if (authorizationHint) {
            authorizationHint.textContent = required
                ? '当前身份必须填写授权说明，后续请补充授权证明材料。'
                : '若你是店主可不填写；其他身份建议填写授权说明。';
        }
    }

    const fieldMap = {
        requested_shop_name: {
            el: form.querySelector('#id_requested_shop_name'),
            message: '请填写真实店铺名称',
            validate: (value) => {
                const trimmed = (value || '').trim();
                if (!trimmed) return false;
                if (trimmed.length < 2 || trimmed.length > 120) return false;
                return !(/[<>\/\\]/.test(trimmed));
            },
        },
        mall_name: {
            el: form.querySelector('#id_mall_name'),
            message: '请填写所在商场/园区/区域',
            validate: (value) => Boolean((value || '').trim()),
        },
        contact_name: {
            el: form.querySelector('#id_contact_name'),
            message: '请填写联系人姓名',
            validate: (value) => Boolean((value || '').trim()),
        },
        contact_phone: {
            el: form.querySelector('#id_contact_phone'),
            message: '手机号格式不正确',
            validate: (value) => {
                if (!value) return false;
                const normalized = value.replace(/[\s-]/g, '').replace(/^\+/, '');
                return /^[0-9]+$/.test(normalized) && normalized.length >= 7 && normalized.length <= 15;
            },
        },
        role_requested: {
            el: form.querySelector('#id_role_requested'),
            message: '请选择期望绑定角色',
            validate: (value) => Boolean(value),
        },
        authorization_note: {
            el: form.querySelector('#id_authorization_note'),
            message: '非店主身份需填写授权说明',
            validate: (value) => {
                if (!identityNeedsAuthorization()) return true;
                return Boolean((value || '').trim());
            },
        },
    };

    function setFieldState(field, isValid) {
        if (!field || !field.el) return;
        if (isValid) {
            field.el.classList.remove('is-invalid');
            field.el.setAttribute('aria-invalid', 'false');
            return;
        }
        field.el.classList.add('is-invalid');
        field.el.setAttribute('aria-invalid', 'true');
    }

    function bindA11yDescriptors() {
        Object.keys(fieldMap).forEach((name) => {
            const field = fieldMap[name];
            if (!field.el) return;
            const hint = document.getElementById(`hint_${name}`);
            const err = document.getElementById(`error_${name}`);
            const ids = [];
            if (hint) ids.push(hint.id);
            if (err) ids.push(err.id);
            if (ids.length) field.el.setAttribute('aria-describedby', ids.join(' '));
            field.el.setAttribute('aria-invalid', err ? 'true' : 'false');
        });
        if (authorizationInput) {
            const hint = document.getElementById('hint_authorization_note');
            const err = document.getElementById('error_authorization_note');
            const ids = [];
            if (hint) ids.push(hint.id);
            if (err) ids.push(err.id);
            if (ids.length) authorizationInput.setAttribute('aria-describedby', ids.join(' '));
        }
    }

    function validateForm() {
        const errors = [];
        Object.values(fieldMap).forEach((field) => {
            const value = field.el ? field.el.value : '';
            const isValid = field.validate(value);
            setFieldState(field, isValid);
            if (!isValid) errors.push(field.message);
        });

        const list = summary.querySelector('ul');
        list.innerHTML = '';
        errors.forEach((msg) => {
            const li = document.createElement('li');
            li.textContent = msg;
            list.appendChild(li);
        });
        summary.style.display = errors.length ? 'block' : 'none';
        summary.setAttribute('aria-expanded', errors.length ? 'true' : 'false');
        if (errors.length) {
            const firstInvalid = form.querySelector('.is-invalid');
            if (firstInvalid) firstInvalid.focus();
        }
        return errors.length === 0;
    }

    if (disableForm) {
        form.querySelectorAll('input, textarea, select, button').forEach((el) => {
            if (el.type !== 'hidden') el.disabled = true;
        });
        return;
    }

    identityInputs.forEach((input) => input.addEventListener('change', syncAuthorizationState));
    syncAuthorizationState();

    const shopNameInput = form.querySelector('#id_requested_shop_name');
    const mallInput = form.querySelector('#id_mall_name');
    const shopSearchResults = document.getElementById('shopSearchResults');
    const shopSearchUrl = document.getElementById('shopSearchUrl');
    let searchTimer = null;

    function renderSearchResults(results) {
        shopSearchResults.innerHTML = '';
        if (!results.length) {
            shopSearchResults.innerHTML = '<div class="text-muted small">未找到匹配店铺，请手动填写。</div>';
            return;
        }
        const list = document.createElement('div');
        list.className = 'list-group';
        results.forEach((item) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'list-group-item list-group-item-action';
            const title = document.createElement('div');
            title.className = 'fw-semibold';
            title.textContent = item.name || '-';
            const meta = document.createElement('div');
            meta.className = 'text-muted small';
            const parts = [];
            if (item.id) parts.push(`ID: ${item.id}`);
            if (item.contact_person) parts.push(`联系人：${item.contact_person}`);
            if (item.contact_phone) parts.push(`电话：${item.contact_phone}`);
            if (item.address) parts.push(item.address);
            meta.textContent = parts.join(' · ');
            btn.appendChild(title);
            btn.appendChild(meta);
            btn.addEventListener('click', () => {
                shopNameInput.value = item.name || '';
                if (mallInput && item.address) mallInput.value = item.address;
                const requestedId = form.querySelector('#id_requested_shop_id');
                if (requestedId && item.id) requestedId.value = item.id;
                const contactName = form.querySelector('#id_contact_name');
                if (contactName && !contactName.value && item.contact_person) {
                    contactName.value = item.contact_person;
                }
                const contactPhone = form.querySelector('#id_contact_phone');
                if (contactPhone && !contactPhone.value && item.contact_phone) {
                    contactPhone.value = item.contact_phone;
                }
                shopSearchResults.innerHTML = '';
            });
            list.appendChild(btn);
        });
        shopSearchResults.appendChild(list);
    }

    if (shopNameInput && shopSearchResults && shopSearchUrl) {
        shopNameInput.addEventListener('input', () => {
            const q = shopNameInput.value.trim();
            if (searchTimer) clearTimeout(searchTimer);
            if (q.length < 2) {
                shopSearchResults.innerHTML = '';
                return;
            }
            searchTimer = setTimeout(() => {
                fetch(`${shopSearchUrl.value}?q=${encodeURIComponent(q)}`)
                    .then((res) => res.json())
                    .then((data) => renderSearchResults(data.results || []))
                    .catch(() => {
                        shopSearchResults.innerHTML = '<div class="text-danger small">店铺搜索失败，请稍后重试。</div>';
                    });
            }, 280);
        });
    }

    const attachmentInput = form.querySelector('#id_attachments');
    const attachmentPreview = document.getElementById('attachmentPreview');
    const attachmentStore = [];

    function syncAttachmentInput() {
        const dataTransfer = new DataTransfer();
        attachmentStore.forEach((file) => dataTransfer.items.add(file));
        attachmentInput.files = dataTransfer.files;
    }

    function renderAttachmentList() {
        attachmentPreview.innerHTML = '';
        if (!attachmentStore.length) return;
        attachmentStore.forEach((file, index) => {
            const row = document.createElement('div');
            row.className = 'd-flex align-items-center justify-content-between text-muted small mb-1';
            const name = document.createElement('span');
            name.textContent = `${file.name} (${Math.round(file.size / 1024)}KB)`;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'btn btn-sm btn-outline-danger';
            remove.textContent = '移除';
            remove.addEventListener('click', () => {
                attachmentStore.splice(index, 1);
                syncAttachmentInput();
                renderAttachmentList();
            });
            row.appendChild(name);
            row.appendChild(remove);
            attachmentPreview.appendChild(row);
        });
    }

    if (attachmentInput && attachmentPreview) {
        attachmentInput.addEventListener('change', () => {
            const incoming = Array.from(attachmentInput.files || []);
            const allowed = ['jpg', 'jpeg', 'png', 'pdf'];

            for (const file of incoming) {
                const ext = (file.name.split('.').pop() || '').toLowerCase();
                if (!allowed.includes(ext)) {
                    attachmentPreview.innerHTML = '<div class="text-danger small">仅支持 JPG / PNG / PDF 文件。</div>';
                    attachmentInput.value = '';
                    return;
                }
                if (file.size > 5 * 1024 * 1024) {
                    attachmentPreview.innerHTML = '<div class="text-danger small">单个文件不得超过 5MB。</div>';
                    attachmentInput.value = '';
                    return;
                }
            }

            attachmentStore.push(...incoming);
            if (attachmentStore.length > 5) {
                attachmentStore.splice(5);
                attachmentPreview.innerHTML = '<div class="text-danger small">最多上传 5 个文件。</div>';
            }
            syncAttachmentInput();
            renderAttachmentList();
        });
    }

    function collectDraft() {
        const payload = {};
        form.querySelectorAll('input, textarea, select').forEach((el) => {
            if (!el.name || el.type === 'file' || el.type === 'hidden') return;
            if (el.type === 'radio') {
                if (el.checked) payload[el.name] = el.value;
                return;
            }
            payload[el.name] = el.value;
        });
        return payload;
    }

    function restoreDraft() {
        const raw = localStorage.getItem(draftKey);
        if (!raw) return;
        try {
            const data = JSON.parse(raw);
            Object.keys(data).forEach((name) => {
                const nodes = form.querySelectorAll(`[name="${name}"]`);
                if (!nodes.length) return;
                if (nodes[0].type === 'radio') {
                    nodes.forEach((node) => {
                        node.checked = node.value === data[name];
                    });
                    return;
                }
                nodes[0].value = data[name];
            });
            syncAuthorizationState();
        } catch (e) {
            localStorage.removeItem(draftKey);
        }
    }

    if (saveDraftBtn) {
        saveDraftBtn.addEventListener('click', (event) => {
            event.preventDefault();
            isDraftSubmit = true;
            if (intentInput) intentInput.value = 'draft';
            if (typeof form.requestSubmit === 'function') {
                form.requestSubmit();
            } else {
                form.submit();
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (!window.confirm('确定要重置当前表单内容吗？')) return;
            form.reset();
            summary.style.display = 'none';
            form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
            shopSearchResults.innerHTML = '';
            attachmentStore.splice(0, attachmentStore.length);
            attachmentPreview.innerHTML = '';
            syncAuthorizationState();
        });
    }

    form.addEventListener('submit', (event) => {
        if (!isDraftSubmit && !validateForm()) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        if (intentInput && !intentInput.value) {
            intentInput.value = isDraftSubmit ? 'draft' : 'submit';
        }
        if (!isDraftSubmit) {
            localStorage.removeItem(draftKey);
        }
        const targetBtn = isDraftSubmit ? saveDraftBtn : submitBtn;
        if (targetBtn) {
            targetBtn.disabled = true;
            const text = targetBtn.getAttribute('data-loading-text') || targetBtn.textContent;
            targetBtn.textContent = text;
            targetBtn.setAttribute('aria-busy', 'true');
        }
        isDraftSubmit = false;
    });

    restoreDraft();
    bindA11yDescriptors();
    const summaryToggle = form.querySelector('[data-error-summary-toggle]');
    if (summaryToggle) {
        summaryToggle.addEventListener('click', () => {
            const expanded = summary.getAttribute('aria-expanded') === 'true';
            summary.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        });
    }
    const firstServerError = form.querySelector('.field-error');
    if (firstServerError) {
        const host = firstServerError.closest('.mb-3');
        const target = host ? host.querySelector('input,textarea,select') : null;
        if (target) target.focus();
    }
})();
