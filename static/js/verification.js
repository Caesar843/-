(function () {
    function getCookie(name) {
        const value = document.cookie || "";
        const parts = value.split(";").map(part => part.trim());
        for (const part of parts) {
            if (part.startsWith(name + "=")) {
                return decodeURIComponent(part.slice(name.length + 1));
            }
        }
        return "";
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            credentials: "same-origin",
            body: JSON.stringify(payload || {}),
        }).then(res => res.json().then(data => ({ ok: res.ok, data })));
    }

    function getChannelFromSource(sourceName) {
        if (!sourceName) return "";
        const el = document.querySelector(`[name="${sourceName}"]:checked`);
        return el ? el.value : "";
    }

    function getInputValueById(id) {
        if (!id) return "";
        const el = document.getElementById(id);
        return el ? el.value.trim() : "";
    }

    function setMessage(targetId, message, isError) {
        const el = targetId ? document.getElementById(targetId) : null;
        if (!el) return;
        el.textContent = message || "";
        el.classList.toggle("text-danger", !!isError);
        el.classList.toggle("text-muted", !isError);
    }

    function cooldownKey(scene, channel, destination) {
        return `verificationCooldown:${scene}:${channel}:${destination}`;
    }

    function saveCooldown(key, seconds) {
        if (!key || !seconds) return;
        const until = Date.now() + seconds * 1000;
        localStorage.setItem(key, String(until));
    }

    function loadCooldown(key) {
        if (!key) return 0;
        const raw = localStorage.getItem(key);
        if (!raw) return 0;
        const until = parseInt(raw, 10);
        if (Number.isNaN(until)) return 0;
        const remaining = Math.floor((until - Date.now()) / 1000);
        if (remaining <= 0) {
            localStorage.removeItem(key);
            return 0;
        }
        return remaining;
    }

    function startCountdown(button, seconds, key) {
        if (!button || !seconds) return;
        saveCooldown(key, seconds);
        button.disabled = true;
        const defaultText = button.dataset.defaultText || button.textContent;
        button.dataset.defaultText = defaultText;
        let remaining = seconds;
        button.textContent = `重新发送(${remaining}s)`;
        const timer = setInterval(() => {
            remaining -= 1;
            if (remaining <= 0) {
                clearInterval(timer);
                button.disabled = false;
                button.textContent = defaultText;
                if (key) localStorage.removeItem(key);
                return;
            }
            button.textContent = `重新发送(${remaining}s)`;
        }, 1000);
    }

    function resolveDestination(button, channel) {
        const emailId = button.dataset.destinationEmail;
        const smsId = button.dataset.destinationSms;
        if (channel === "EMAIL") return getInputValueById(emailId);
        if (channel === "SMS") return getInputValueById(smsId);
        return getInputValueById(button.dataset.destinationInput);
    }

    function restoreCooldown(button) {
        const scene = button.dataset.scene;
        const channel = button.dataset.channel || getChannelFromSource(button.dataset.channelSource);
        if (!scene || !channel) return;
        if (scene === "RESET_PASSWORD") {
            const identifier = button.dataset.identifierInput
                ? getInputValueById(button.dataset.identifierInput)
                : "";
            if (!identifier) return;
            const key = cooldownKey(scene, channel, identifier);
            const remaining = loadCooldown(key);
            if (remaining > 0) {
                startCountdown(button, remaining, key);
            }
            return;
        }
        const destination = resolveDestination(button, channel);
        if (!destination) return;
        const key = cooldownKey(scene, channel, destination);
        const remaining = loadCooldown(key);
        if (remaining > 0) {
            startCountdown(button, remaining, key);
        }
    }

    function initSendButtons() {
        const buttons = document.querySelectorAll("[data-verification-send]");
        buttons.forEach(button => {
            restoreCooldown(button);
            button.addEventListener("click", () => {
                const scene = button.dataset.scene;
                const channel = button.dataset.channel || getChannelFromSource(button.dataset.channelSource);
                const destination = resolveDestination(button, channel);
                const messageTarget = button.dataset.messageTarget;
                const payload = {
                    scene,
                    channel,
                    destination,
                };
                if (button.dataset.identifierInput) {
                    payload.identifier = getInputValueById(button.dataset.identifierInput);
                }
                if (!scene || !channel) {
                    setMessage(messageTarget, "请选择接收方式。", true);
                    return;
                }
                if (scene !== "RESET_PASSWORD" && !destination) {
                    setMessage(messageTarget, "请先填写接收地址。", true);
                    return;
                }
                if (scene === "RESET_PASSWORD" && !payload.identifier) {
                    setMessage(messageTarget, "请先填写账号标识。", true);
                    return;
                }
                postJson(button.dataset.sendUrl, payload).then(({ data }) => {
                    setMessage(messageTarget, data.message || "", !data.success);
                    if (data.cooldown_seconds) {
                        const key = scene === "RESET_PASSWORD" && payload.identifier
                            ? cooldownKey(scene, channel, payload.identifier)
                            : cooldownKey(scene, channel, destination);
                        startCountdown(button, data.cooldown_seconds, key);
                    }
                    if (data.success && button.dataset.redirectUrl) {
                        if (payload.identifier) {
                            sessionStorage.setItem("reset_identifier", payload.identifier);
                            const target = `${button.dataset.redirectUrl}?identifier=${encodeURIComponent(payload.identifier)}`;
                            window.location.href = target;
                        } else {
                            window.location.href = button.dataset.redirectUrl;
                        }
                    }
                }).catch(() => {
                    setMessage(messageTarget, "发送失败，请稍后重试。", true);
                });
            });
        });
    }

    function initVerifyButtons() {
        const buttons = document.querySelectorAll("[data-verification-verify]");
        buttons.forEach(button => {
            button.addEventListener("click", () => {
                const scene = button.dataset.scene;
                const channel = button.dataset.channel || getChannelFromSource(button.dataset.channelSource);
                const destination = resolveDestination(button, channel);
                const code = getInputValueById(button.dataset.codeInput);
                const messageTarget = button.dataset.messageTarget;
                if (!scene || !channel) {
                    setMessage(messageTarget, "请选择接收方式。", true);
                    return;
                }
                if (scene !== "RESET_PASSWORD" && !destination) {
                    setMessage(messageTarget, "请先填写接收地址。", true);
                    return;
                }
                if (scene === "RESET_PASSWORD") {
                    const identifier = button.dataset.identifierInput
                        ? getInputValueById(button.dataset.identifierInput)
                        : "";
                    if (!identifier) {
                        setMessage(messageTarget, "请先填写账号标识。", true);
                        return;
                    }
                }
                if (!code) {
                    setMessage(messageTarget, "请输入验证码。", true);
                    return;
                }
                const payload = {
                    scene,
                    channel,
                    destination,
                    code,
                };
                if (button.dataset.identifierInput) {
                    payload.identifier = getInputValueById(button.dataset.identifierInput);
                }
                postJson(button.dataset.verifyUrl, payload).then(({ data }) => {
                    setMessage(messageTarget, data.message || "", !data.success);
                    if (data.verification_token && button.dataset.tokenOutput) {
                        const tokenEl = document.getElementById(button.dataset.tokenOutput);
                        if (tokenEl) tokenEl.value = data.verification_token;
                    }
                    if (data.reset_token && button.dataset.redirectUrl) {
                        sessionStorage.setItem("reset_token", data.reset_token);
                        const target = `${button.dataset.redirectUrl}?token=${encodeURIComponent(data.reset_token)}`;
                        window.location.href = target;
                    }
                }).catch(() => {
                    setMessage(messageTarget, "校验失败，请稍后重试。", true);
                });
            });
        });
    }

    function initResetForm() {
        const form = document.querySelector("[data-reset-form]");
        if (!form) return;
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            const resetToken = form.querySelector("[name='reset_token']");
            const password1 = form.querySelector("[name='password1']");
            const password2 = form.querySelector("[name='password2']");
            const messageTarget = form.dataset.messageTarget;
            const payload = {
                reset_token: resetToken ? resetToken.value.trim() : "",
                password1: password1 ? password1.value.trim() : "",
                password2: password2 ? password2.value.trim() : "",
            };
            postJson(form.dataset.actionUrl, payload).then(({ data }) => {
                setMessage(messageTarget, data.message || "", !data.success);
                if (data.success && form.dataset.redirectUrl) {
                    window.location.href = form.dataset.redirectUrl;
                }
            }).catch(() => {
                setMessage(messageTarget, "重置失败，请稍后重试。", true);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initSendButtons();
        initVerifyButtons();
        initResetForm();
    });
})();
