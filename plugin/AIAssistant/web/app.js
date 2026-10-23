/* STE AI Assistant — клиент чата.
 *
 * Контракт с Python-плагином:
 *   POST /api/message   {text, mode, attachments:[{name, mime, data(base64)}]}
 *   GET  /api/events?since=N  -> {events:[...], last:N}   (polling)
 *   GET  /api/settings        -> {base_url, model, has_key, explain}
 *   POST /api/settings        {base_url, api_key, model, explain}
 *   POST /api/export          {kind: "gcode" | "3mf"}
 *
 * Типы событий: assistant_text, tool_call, tool_result, setting_changed,
 *   scene, slice_progress, slice_result, decision, error, done.
 *
 * Если сервер недоступен (страница открыта как файл), включается демо-режим.
 */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var t = function () { return I18N.t.apply(null, arguments); };
  var els = {
    messages: $("messages"), welcome: $("welcome"), composer: $("composer"),
    input: $("input"), sendBtn: $("sendBtn"), fileInput: $("fileInput"),
    attachments: $("attachments"), objects: $("objects"), changes: $("changes"),
    changeCount: $("changeCount"), sliceCard: $("sliceCard"), sliceState: $("sliceState"),
    slicePct: $("slicePct"), sliceBar: $("sliceBar"), toast: $("toast"),
    exportGcode: $("exportGcode"), export3mf: $("export3mf")
  };

  var state = {
    demo: location.protocol === "file:",
    mode: "classic",
    modeFixed: false,
    files: [],
    busy: false,
    localUser: 0,
    lang: "ru",
    projects: null,
    lastEvent: 0,
    tools: {},
    changes: 0,
    assistantBubble: null
  };

  /* ---------- утилиты ---------- */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  // мини-markdown: **жирный**, `код`, списки, абзацы
  function md(text) {
    var html = esc(text)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
    return html.split(/\n{2,}/).map(function (block) {
      if (/^[-•] /m.test(block)) {
        return "<ul>" + block.split("\n").map(function (l) {
          return "<li>" + l.replace(/^[-•] /, "") + "</li>";
        }).join("") + "</ul>";
      }
      return "<p>" + block.replace(/\n/g, "<br>") + "</p>";
    }).join("");
  }
  function fmtSize(b) {
    if (b < 1024) return b + " " + t("b");
    if (b < 1048576) return (b / 1024).toFixed(0) + " " + t("kb");
    return (b / 1048576).toFixed(1) + " " + t("mb");
  }
  function ext(name) { return (name.split(".").pop() || "").toUpperCase(); }
  function scrollDown() { els.messages.scrollTop = els.messages.scrollHeight; }
  function toast(text) {
    els.toast.textContent = text;
    els.toast.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.remove("show"); }, 2600);
  }
  function api(path, body) {
    var opts = body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    };
    return fetch(path, opts).then(function (r) {
      if (r.ok) return r.json();
      return r.json().catch(function () { return {}; }).then(function (data) {
        var err = new Error(data.error || "HTTP " + r.status);
        err.status = r.status;
        throw err;
      });
    });
  }

  /* ---------- сообщения ---------- */
  function addMessage(role, html, extraNode) {
    if (els.welcome) { els.welcome.remove(); els.welcome = null; }
    var msg = document.createElement("div");
    msg.className = "msg " + role;
    msg.innerHTML =
      '<div class="msg-author">' + (role === "user" ? t("you") : t("assistant")) + "</div>" +
      '<div class="msg-body"></div>';
    var body = msg.querySelector(".msg-body");
    if (extraNode) body.appendChild(extraNode);
    if (html) {
      var b = document.createElement("div");
      b.className = "bubble";
      b.innerHTML = html;
      body.appendChild(b);
    }
    els.messages.appendChild(msg);
    scrollDown();
    return body;
  }

  // Ответ ассистента собирается в одну «ленту»: текст + карточки инструментов
  function assistantBody() {
    if (!state.assistantBubble) {
      state.assistantBubble = addMessage("assistant", "");
    }
    return state.assistantBubble;
  }
  function showTyping(on) {
    var t = document.getElementById("typing");
    if (on && !t) {
      t = document.createElement("div");
      t.id = "typing";
      t.className = "bubble typing";
      assistantBody().appendChild(t);
      scrollDown();
    } else if (!on && t) {
      t.remove();
    }
  }
  function appendAssistantText(text) {
    showTyping(false);
    var body = assistantBody();
    var last = body.lastElementChild;
    if (!last || !last.classList.contains("bubble") || last.dataset.kind !== "text") {
      last = document.createElement("div");
      last.className = "bubble";
      last.dataset.kind = "text";
      last.dataset.raw = "";
      body.appendChild(last);
    }
    last.dataset.raw += text;
    last.innerHTML = md(last.dataset.raw);
    scrollDown();
  }

  /* ---------- карточки инструментов ---------- */
  function summarizeArgs(args) {
    return Object.keys(args || {}).map(function (k) {
      var v = args[k];
      return k + "=" + (typeof v === "object" ? JSON.stringify(v) : v);
    }).join(", ");
  }
  function toolCall(ev) {
    showTyping(false);
    var card = document.createElement("div");
    card.className = "tool";
    card.dataset.status = "running";
    card.innerHTML =
      '<button class="tool-head" type="button">' +
        '<span class="tool-name">' + esc(ev.name) + "</span>" +
        '<span class="tool-summary">' + esc(summarizeArgs(ev.args)) + "</span>" +
        '<span class="tool-status"><span class="spinner"></span> ' + t("running") + "</span>" +
        '<span class="tool-chevron">' + t("details") + "</span>" +
      "</button>" +
      '<div class="tool-details">' +
        "<h4>" + t("arguments") + "</h4><pre>" + esc(JSON.stringify(ev.args || {}, null, 2)) + "</pre>" +
        "<h4>" + t("result") + '</h4><pre class="tool-result">…</pre>' +
      "</div>";
    card.querySelector(".tool-head").addEventListener("click", function () {
      card.classList.toggle("open");
    });
    assistantBody().appendChild(card);
    state.tools[ev.id] = card;
    scrollDown();
  }
  function toolResult(ev) {
    var card = state.tools[ev.id];
    if (!card) return;
    card.dataset.status = ev.ok === false ? "error" : "ok";
    card.querySelector(".tool-status").textContent = ev.ok === false ? t("failed") : t("ok");
    card.querySelector(".tool-result").textContent =
      typeof ev.result === "string" ? ev.result : JSON.stringify(ev.result, null, 2);
    if (ev.ok === false) card.classList.add("open");
  }

  /* ---------- правая панель ---------- */
  function settingChanged(ev) {
    if (state.changes === 0) els.changes.innerHTML = "";
    state.changes++;
    els.changeCount.textContent = state.changes;
    var li = document.createElement("li");
    li.className = "change";
    li.title = ev.reason || "";
    li.innerHTML =
      '<span class="change-key">' + esc(ev.label || ev.key) + "</span>" +
      '<span class="change-val">' + (ev.old !== undefined ? "<s>" + esc(ev.old) + "</s>" : "") +
      esc(ev.value) + "</span>";
    els.changes.prepend(li);

    var map = { quality: "kvQuality", material: "kvMaterial", infill_sparse_density: "kvInfill", support_enable: "kvSupport" };
    if (map[ev.key]) {
      var dd = $(map[ev.key]);
      dd.textContent = ev.value;
      dd.classList.remove("flash"); void dd.offsetWidth; dd.classList.add("flash");
    }
    if (ev.key === "print_mode") setMode(ev.raw || "classic", true);
  }
  function renderScene(objects) {
    if (!objects || !objects.length) {
      els.objects.innerHTML = '<li class="empty">' + t("no_models_yet") + "</li>";
      return;
    }
    els.objects.innerHTML = objects.map(function (o) {
      return '<li class="object"><div class="object-icon">' + esc(ext(o.name)) + "</div><div>" +
        '<div class="object-name">' + esc(o.name) + "</div>" +
        '<div class="object-dims">' + o.size.map(function (v) { return v.toFixed(1); }).join(" × ") + " " + t("mm") + "</div>" +
        "</div></li>";
    }).join("");
  }
  function sliceLabel(st) { return { idle: t("idle"), slicing: t("slicing_state"), done: t("done"), error: t("error") }[st]; }
  function sliceProgress(st, pct) {
    els.sliceCard.dataset.state = st;
    els.sliceState.innerHTML = (st === "slicing" ? '<span class="spinner"></span>' : "") + sliceLabel(st);
    var p = Math.round((pct || 0) * 100);
    els.slicePct.textContent = p + " %";
    els.sliceBar.style.width = p + "%";
  }
  function sliceResult(r) {
    sliceProgress("done", 1);
    $("mTime").textContent = r.time;
    $("mMat").textContent = r.length;
    $("mWeight").textContent = r.weight;
    $("mLayers").textContent = r.layers;
    els.exportGcode.disabled = false;
    els.export3mf.disabled = false;
  }
  function decision(ev) {
    var box = document.createElement("div");
    box.className = "decision";
    box.innerHTML = "<h4>" + esc(ev.title || t("decisions")) + "</h4><table>" +
      ev.rows.map(function (r) {
        return "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td><td>" + esc(r[2]) + "</td></tr>";
      }).join("") + "</table>";
    assistantBody().appendChild(box);
    scrollDown();
  }

  function normalize(raw) {
    var d = raw.data || {};
    var ev = { type: raw.type };
    Object.keys(d).forEach(function (k) { ev[k] = d[k]; });
    if (raw.type === "assistant_message") ev.type = "assistant_text";
    if (raw.type === "tool_call") { ev.id = d.call_id; ev.args = d.arguments; }
    if (raw.type === "tool_result") {
      ev.id = d.call_id;
      if (d.ok === false) ev.result = d.error;
    }
    return ev;
  }
  function separator() {
    var body = state.assistantBubble;
    var last = body && body.lastElementChild;
    return last && last.dataset && last.dataset.kind === "text" && last.dataset.raw ? "\n\n" : "";
  }

  function handleEvent(ev) {
    switch (ev.type) {
      case "user_message":
        if (state.localUser > 0) { state.localUser--; break; }
        state.assistantBubble = null;
        addMessage("user", md(ev.text || ""));
        break;
      case "assistant_text":
        if (ev.text) appendAssistantText(separator() + ev.text);
        break;
      case "tool_call":
        if (ev.name === "slice") sliceProgress("slicing", 0);
        toolCall(ev);
        break;
      case "tool_result":
        if (ev.name === "slice" && ev.ok === false) sliceProgress("error", 0);
        toolResult(ev);
        break;
      case "setting_changed": settingChanged(ev); break;
      case "scene": renderScene(ev.objects); break;
      case "slice_progress": sliceProgress(ev.state, ev.progress); break;
      case "slice_result": sliceResult(ev); break;
      case "decision": decision(ev); break;
      case "error":
        showTyping(false);
        var b = document.createElement("div");
        b.className = "bubble error";
        b.innerHTML = esc(t("error_prefix")) + esc(ev.message);
        assistantBody().appendChild(b);
        setBusy(false);
        break;
      case "done":
        showTyping(false);
        setBusy(false);
        if (!state.demo) loadProjects().catch(function () {});
        break;
    }
    if (ev.type === "tool_result" && state.busy) showTyping(true);
  }

  /* ---------- отправка ---------- */
  function setBusy(on) {
    state.busy = on;
    els.sendBtn.disabled = on;
    if (!on) state.assistantBubble = null;
  }

  function send(text) {
    text = (text || "").trim();
    if (state.busy || (!text && !state.files.length)) return;

    var files = state.files.slice();
    var preview = null;
    if (files.length) {
      preview = document.createElement("div");
      preview.className = "msg-files";
      files.forEach(function (f) {
        if (f.preview) {
          var img = document.createElement("img");
          img.src = f.preview;
          preview.appendChild(img);
        } else {
          preview.appendChild(chip(f, false));
        }
      });
    }
    addMessage("user", text ? md(text) : "", preview);
    state.localUser++;
    els.input.value = "";
    autoGrow();
    state.files = [];
    renderAttachments();
    setBusy(true);
    showTyping(true);

    if (state.demo) { runDemo(text, files); return; }

    api("/api/message", {
      text: text,
      mode: state.modeFixed ? state.mode : undefined,
      attachments: files.map(function (f) { return { name: f.name, mime: f.mime, data: f.data }; })
    }).catch(function () {
      state.demo = true;
      toast(t("demo_toast"));
      runDemo(text, files);
    });
  }

  function poll() {
    if (state.demo) return;
    api("/api/events?since=" + state.lastEvent).then(function (res) {
      (res.events || []).forEach(function (raw) { handleEvent(normalize(raw)); });
      state.lastEvent = res.last || state.lastEvent;
      setTimeout(poll, state.busy ? 300 : 1000);
    }).catch(function () { setTimeout(poll, 2000); });
  }

  /* ---------- вложения ---------- */
  function chip(f, removable) {
    var el = document.createElement("div");
    el.className = "chip";
    el.innerHTML =
      (f.preview ? '<img class="chip-thumb" src="' + f.preview + '">' : '<div class="chip-thumb">' + esc(ext(f.name)) + "</div>") +
      '<div class="chip-info"><div class="chip-name">' + esc(f.name) + '</div><div class="chip-size">' + fmtSize(f.size) + "</div></div>" +
      (removable ? '<button type="button" class="chip-x" title="Убрать">×</button>' : "");
    if (removable) {
      el.querySelector(".chip-x").addEventListener("click", function () {
        state.files.splice(state.files.indexOf(f), 1);
        renderAttachments();
      });
    }
    return el;
  }
  function renderAttachments() {
    els.attachments.innerHTML = "";
    state.files.forEach(function (f) { els.attachments.appendChild(chip(f, true)); });
  }
  var ALLOWED = /\.(stl|obj|3mf|jpe?g|png)$/i;
  function addFiles(list) {
    Array.prototype.forEach.call(list, function (file) {
      if (!ALLOWED.test(file.name)) { toast(t("format_unsupported", file.name)); return; }
      var reader = new FileReader();
      reader.onload = function () {
        var url = reader.result;
        var isImg = /^image\//.test(file.type);
        state.files.push({
          name: file.name, size: file.size, mime: file.type || "application/octet-stream",
          data: url.split(",")[1], preview: isImg ? url : null
        });
        renderAttachments();
      };
      reader.readAsDataURL(file);
    });
  }

  /* ---------- режим 3D/5D ---------- */
  function setMode(mode, fromAgent) {
    state.mode = mode;
    if (!fromAgent) state.modeFixed = true;
    document.querySelectorAll(".mode").forEach(function (b) {
      var on = b.dataset.mode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-checked", on);
    });
    if (!fromAgent) toast(t("mode_fixed", document.querySelector('.mode[data-mode="' + mode + '"]').textContent.trim().replace(/\s+/, " ")));
  }

  /* ---------- настройки ---------- */
  function openSettings() {
    var form = $("settingsForm");
    var dlg = $("settingsModal");
    if (!state.demo) {
      api("/api/settings").then(function (s) {
        form.base_url.value = s.base_url || "";
        form.model.value = s.model || "";
        form.api_key.placeholder = s.has_key ? t("key_saved") : "sk-…";
        form.explain.checked = s.explain !== false;
        form.auto_export.checked = s.auto_export !== false;
        form.results_dir.value = s.results_dir || "";
        form.language.value = s.language || "auto";
      }).catch(function () {});
    }
    dlg.showModal();
  }
  $("browseBtn").addEventListener("click", function () {
    var form = $("settingsForm");
    if (state.demo) return;
    api("/api/choose_folder", { start: form.results_dir.value }).then(function (r) {
      if (r.path) form.results_dir.value = r.path;
    }).catch(function () { toast(t("folder_failed")); });
  });
  $("settingsModal").addEventListener("close", function () {
    if (this.returnValue !== "save") return;
    var f = $("settingsForm");
    var data = {
      base_url: f.base_url.value.trim(), model: f.model.value.trim(), explain: f.explain.checked,
      auto_export: f.auto_export.checked, results_dir: f.results_dir.value.trim(), language: f.language.value
    };
    if (f.api_key.value) data.api_key = f.api_key.value;
    f.api_key.value = "";
    if (data.model) $("modelName").textContent = data.model.split("/").pop();
    if (state.demo) { toast(t("demo_no_save")); return; }
    api("/api/settings", data).then(function (s) {
      applyLanguage(s.language_effective);
      toast(t("settings_saved"));
    }).catch(function () { toast(t("settings_failed")); });
  });

  /* ---------- обработчики UI ---------- */
  function autoGrow() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 200) + "px";
  }
  els.input.addEventListener("input", autoGrow);
  els.input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(els.input.value); }
  });
  els.composer.addEventListener("submit", function (e) { e.preventDefault(); send(els.input.value); });
  els.fileInput.addEventListener("change", function () { addFiles(this.files); this.value = ""; });

  ["dragenter", "dragover"].forEach(function (t) {
    document.addEventListener(t, function (e) { e.preventDefault(); els.composer.classList.add("dragging"); });
  });
  ["dragleave", "drop"].forEach(function (t) {
    document.addEventListener(t, function (e) {
      e.preventDefault();
      if (t === "dragleave" && e.relatedTarget) return;
      els.composer.classList.remove("dragging");
      if (t === "drop" && e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    });
  });
  document.addEventListener("paste", function (e) {
    if (e.clipboardData && e.clipboardData.files.length) addFiles(e.clipboardData.files);
  });

  document.querySelectorAll(".mode").forEach(function (b) {
    b.addEventListener("click", function () { setMode(b.dataset.mode); });
  });
  $("quickPrompts").addEventListener("click", function (e) {
    var p = e.target.closest("button");
    if (!p) return;
    var text = t(p.dataset.tpl + "_text");
    var hadText = els.input.value.trim() !== "";
    els.input.value = hadText ? els.input.value.replace(/\s+$/, "") + "\n\n" + text : text;
    autoGrow();
    els.input.focus();
    var firstBreak = hadText ? els.input.value.lastIndexOf("\n\n") + 2 : 0;
    var lineEnd = els.input.value.indexOf("\n", firstBreak);
    var caret = lineEnd === -1 ? els.input.value.length : lineEnd;
    els.input.setSelectionRange(caret, caret);
    closeDrawers();
  });
  $("settingsBtn").addEventListener("click", openSettings);
  $("themeBtn").addEventListener("click", function () {
    var root = document.documentElement;
    var next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("ste-theme", next); } catch (e) {}
  });
  function applyLanguage(code) {
    state.lang = I18N.setLang(code || (navigator.language || "en").split("-")[0]);
    renderProjectTitle();
    if (!els.changeCount.textContent || state.changes === 0) {
      els.changes.innerHTML = '<li class="empty">' + t("no_changes") + "</li>";
    }
    if (!els.objects.querySelector(".object")) {
      els.objects.innerHTML = '<li class="empty">' + t("no_models") + "</li>";
    }
    sliceProgress(els.sliceCard.dataset.state, parseInt(els.slicePct.textContent, 10) / 100 || 0);
  }

  /* ---------- проекты ---------- */
  function projectError(err) {
    toast(err && err.status === 409 ? t("busy") : (err && err.message) || t("project_failed"));
  }
  function renderProjectTitle() {
    var current = state.projects && state.projects.current;
    $("projectTitle").textContent = current ? current.name : t("new_project");
    $("renameBtn").hidden = !current;
  }
  function loadProjects() {
    return api("/api/projects").then(function (data) {
      state.projects = data;
      renderProjectTitle();
      return data;
    });
  }
  function formatDate(ts) {
    var d = new Date(ts * 1000);
    return d.toLocaleDateString(I18N.get()) + " " + d.toLocaleTimeString(I18N.get(), { hour: "2-digit", minute: "2-digit" });
  }
  function renderProjectList() {
    var list = $("projectList");
    var data = state.projects || { projects: [], current: null };
    list.innerHTML = "";
    if (!data.projects.length) {
      list.innerHTML = '<li class="empty">' + t("projects_empty") + "</li>";
      return;
    }
    data.projects.forEach(function (p) {
      var isCurrent = data.current && data.current.id === p.id;
      var li = document.createElement("li");
      li.className = "project-item" + (isCurrent ? " current" : "");
      li.innerHTML =
        '<button type="button" class="project-open"><span class="project-name">' + esc(p.name) + "</span>" +
        '<span class="project-meta">' + esc(formatDate(p.updated)) + " · " + esc(t("messages", p.messages)) +
        (isCurrent ? " · " + esc(t("current")) : "") + "</span></button>" +
        '<span class="project-actions"><button type="button" class="btn btn-small" data-act="rename">' + esc(t("rename")) +
        '</button><button type="button" class="btn btn-small" data-act="delete">' + esc(t("delete")) + "</button></span>";
      li.querySelector(".project-open").addEventListener("click", function () {
        if (isCurrent) { showProjects(false); return; }
        projectAction({ action: "open", id: p.id }, true);
      });
      li.querySelector('[data-act="rename"]').addEventListener("click", function () { askRename(p); });
      li.querySelector('[data-act="delete"]').addEventListener("click", function () {
        if (!window.confirm(t("delete_confirm", p.name))) return;
        projectAction({ action: "delete", id: p.id }, false);
      });
      list.appendChild(li);
    });
  }
  function showProjects(on) {
    $("projectsScreen").hidden = !on;
    if (on) loadProjects().then(renderProjectList).catch(projectError);
  }
  function projectAction(body, enter) {
    if (state.demo) { toast(t("demo_no_save")); return; }
    api("/api/projects", body).then(function (data) {
      if (enter) {
        try { sessionStorage.setItem("ste-opened", "1"); } catch (e) {}
        location.reload();
        return;
      }
      state.projects = data;
      renderProjectTitle();
      renderProjectList();
    }).catch(projectError);
  }
  var renameTarget = null;
  function askRename(project) {
    renameTarget = project;
    var form = $("renameForm");
    form.name.value = project.name;
    $("renameModal").showModal();
    form.name.select();
  }
  $("renameModal").addEventListener("close", function () {
    if (this.returnValue !== "save" || !renameTarget) return;
    var name = $("renameForm").name.value.trim();
    var target = renameTarget;
    renameTarget = null;
    if (!name || name === target.name) return;
    projectAction({ action: "rename", id: target.id, name: name }, false);
  });
  $("renameBtn").addEventListener("click", function () {
    var current = state.projects && state.projects.current;
    if (current) askRename(current);
  });
  $("projectsBtn").addEventListener("click", function () { closeDrawers(); showProjects(true); });
  $("projectsCloseBtn").addEventListener("click", function () { showProjects(false); });
  $("newProjectBtn").addEventListener("click", function () { projectAction({ action: "create" }, true); });
  // выдвижные панели в узком окне: закрываются кнопкой, кликом по фону и Esc
  function openDrawer(id) {
    closeDrawers();
    $(id).classList.add("open");
    $("backdrop").classList.add("show");
  }
  function closeDrawers() {
    $("sidebar").classList.remove("open");
    $("statusPanel").classList.remove("open");
    $("backdrop").classList.remove("show");
  }
  $("menuBtn").addEventListener("click", function () { openDrawer("sidebar"); });
  $("statusToggle").addEventListener("click", function () { openDrawer("statusPanel"); });
  $("backdrop").addEventListener("click", closeDrawers);
  document.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", closeDrawers); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !$("settingsModal").open) closeDrawers();
  });
  window.addEventListener("resize", function () { if (innerWidth > 1180) closeDrawers(); });
  [els.exportGcode, els.export3mf].forEach(function (btn) {
    btn.addEventListener("click", function () {
      var kind = btn === els.exportGcode ? "gcode" : "3mf";
      if (state.demo) { toast(t("export_demo", kind.toUpperCase())); return; }
      btn.disabled = true;
      api("/api/export", { kind: kind }).then(function (r) { toast(t("export_saved", r.path || kind)); })
        .catch(function (err) { toast(t("export_failed", err.message)); })
        .then(function () { btn.disabled = false; });
    });
  });

  try {
    var saved = localStorage.getItem("ste-theme");
    if (saved) document.documentElement.dataset.theme = saved;
    else if (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) document.documentElement.dataset.theme = "dark";
  } catch (e) {}

  /* ---------- демо-сценарий ---------- */
  function runDemo(text, files) {
    var model = (files.filter(function (f) { return /\.(stl|obj|3mf)$/i.test(f.name); })[0] || {}).name || "bracket.stl";
    var steps = [
      [500, { type: "assistant_text", text: "Задача: деталь под нагрузку, PETG, без поддержек. Загружаю модель и проверяю геометрию." }],
      [500, { type: "tool_call", id: "t1", name: "load_model", args: { path: model } }],
      [700, { type: "tool_result", id: "t1", result: { object_id: 1, name: model } }],
      [0, { type: "scene", objects: [{ name: model, size: [62, 40, 35] }] }],
      [300, { type: "tool_call", id: "t2", name: "get_model_bounds", args: { object_id: 1 } }],
      [500, { type: "tool_result", id: "t2", result: { size_mm: [62, 40, 35], overhangs: "18% площади > 45°", flat_faces: 3 } }],
      [300, { type: "tool_call", id: "t3", name: "rotate_object", args: { object_id: 1, axis: "x", angle: 90 } }],
      [500, { type: "tool_result", id: "t3", result: { overhangs: "2% площади > 45°", lay_flat: true } }],
      [0, { type: "scene", objects: [{ name: model, size: [62, 35, 40] }] }],
      [300, { type: "tool_call", id: "t4", name: "set_print_mode", args: { mode: "classic" } }],
      [400, { type: "tool_result", id: "t4", result: "ok" }],
      [0, { type: "setting_changed", key: "print_mode", raw: "classic", label: "режим", value: "3D Classic" }],
      [300, { type: "tool_call", id: "t5", name: "set_material", args: { material: "PETG" } }],
      [400, { type: "tool_result", id: "t5", result: "ok" }],
      [0, { type: "setting_changed", key: "material", label: "material", old: "PLA", value: "PETG" }],
      [300, { type: "tool_call", id: "t6", name: "set_setting", args: { wall_line_count: 4, infill_sparse_density: 40, infill_pattern: "gyroid", support_enable: false } }],
      [500, { type: "tool_result", id: "t6", result: { changed: 4 } }],
      [0, { type: "setting_changed", key: "wall_line_count", label: "wall_line_count", old: 2, value: 4 }],
      [0, { type: "setting_changed", key: "infill_sparse_density", label: "infill_sparse_density", old: "20 %", value: "40 %" }],
      [0, { type: "setting_changed", key: "infill_pattern", label: "infill_pattern", old: "grid", value: "gyroid" }],
      [0, { type: "setting_changed", key: "support_enable", label: "support_enable", value: "нет" }],
      [300, { type: "tool_call", id: "t7", name: "slice", args: {} }],
      [200, { type: "slice_progress", state: "slicing", progress: 0.15 }],
      [300, { type: "slice_progress", state: "slicing", progress: 0.45 }],
      [300, { type: "slice_progress", state: "slicing", progress: 0.8 }],
      [300, { type: "tool_result", id: "t7", result: { time: "3 ч 12 мин", filament_m: 14.6, weight_g: 46 } }],
      [0, { type: "slice_result", time: "3 ч 12 м", length: "14.6 м", weight: "46 г", layers: "175" }],
      [400, { type: "decision", title: "Выбранные параметры", rows: [
        ["Режим", "3D Classic", "плоское основание, нет осевой симметрии — 5D не даёт выигрыша"],
        ["Ориентация", "X +90°", "слои поперёк нагрузки, свесы снижены с 18% до 2%"],
        ["Материал", "PETG", "по запросу; ударная вязкость выше PLA"],
        ["Стенки", "4 периметра", "основная прочность кронштейна — в периметрах"],
        ["Заполнение", "40 % gyroid", "изотропная прочность без перерасхода"],
        ["Поддержки", "выкл.", "после поворота свесы < 45°"]
      ] }],
      [200, { type: "assistant_text", text: "\n\nСлайсинг завершён. G-code и проект 3MF можно сохранить на панели справа. Если нужна большая жёсткость, можно поднять заполнение до 60 % — время печати вырастет примерно на 40 минут." }],
      [0, { type: "done" }]
    ];
    var i = 0;
    (function next() {
      if (i >= steps.length) return;
      var s = steps[i++];
      setTimeout(function () { handleEvent(s[1]); next(); }, s[0]);
    })();
  }

  /* ---------- старт ---------- */
  applyLanguage(null);
  if (!state.demo) {
    api("/api/settings").then(function (s) {
      if (s.model) $("modelName").textContent = s.model.split("/").pop();
      applyLanguage(s.language_effective);
      return loadProjects().then(function (data) {
        var opened = false;
        try { opened = sessionStorage.getItem("ste-opened") === "1"; } catch (e) {}
        if (!opened && data.projects.length) showProjects(true);
        poll();
      });
    }).catch(function () {
      state.demo = true;
      $("connPill").innerHTML = '<span class="dot dot-warn"></span>' + t("demo_pill");
    });
  } else {
    $("connPill").innerHTML = '<span class="dot dot-warn"></span>' + t("demo_pill");
  }
})();
