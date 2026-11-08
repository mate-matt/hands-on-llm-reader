(function () {
  "use strict";

  var KEY = "hollm-reader-v1";

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      var data = raw ? JSON.parse(raw) : {};
      return data && typeof data === "object" ? data : {};
    } catch (err) {
      return {};
    }
  }

  function save(data) {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
    } catch (err) {
      /* private mode or a full disk; reading still works */
    }
  }

  function entry(data, id) {
    var cur = data[id];
    if (!cur || typeof cur !== "object") cur = {};
    return cur;
  }

  function fitNav() {
    var nav = document.querySelector(".chrome");
    if (!nav) return;
    var fixed = window.getComputedStyle(nav).position === "fixed";
    var space = fixed ? nav.offsetHeight + "px" : "0px";
    document.documentElement.style.setProperty("--nav-space", space);
  }

  function paint() {
    var data = load();
    var doneCount = 0;
    document.querySelectorAll("[data-done]").forEach(function (btn) {
      var id = btn.getAttribute("data-done");
      var cur = entry(data, id);
      var on = !!cur.done;
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.textContent = on ? "已读" : "标为已读";
    });
    document.querySelectorAll("[data-pct]").forEach(function (el) {
      var id = el.getAttribute("data-pct");
      var cur = entry(data, id);
      if (cur.done) doneCount += 1;
      var pct = Math.max(0, Math.min(100, cur.pct || 0));
      el.textContent = cur.done ? "已读" : "进度 " + pct + "%";
    });
    document.querySelectorAll("[data-meter]").forEach(function (el) {
      var id = el.getAttribute("data-meter");
      var cur = entry(data, id);
      var pct = cur.done ? 100 : Math.max(0, Math.min(100, cur.pct || 0));
      var bar = el.querySelector("span");
      if (bar) bar.style.width = pct + "%";
    });
    var summary = document.getElementById("progress-summary");
    if (summary) {
      var total = summary.getAttribute("data-total") || "12";
      var marked = 0;
      var seen = {};
      document.querySelectorAll("[data-pct]").forEach(function (el) {
        var id = el.getAttribute("data-pct");
        if (seen[id]) return;
        seen[id] = true;
        if (entry(data, id).done) marked += 1;
      });
      summary.textContent = "已读 " + marked + " / " + total;
    }
    fitNav();
  }

  function scrollRatio() {
    var el = document.documentElement;
    var max = el.scrollHeight - el.clientHeight;
    if (max <= 8) return null;
    return Math.min(1, Math.max(0, el.scrollTop / max));
  }

  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-done]");
    if (!btn) return;
    var id = btn.getAttribute("data-done");
    var data = load();
    var cur = entry(data, id);
    cur.done = !cur.done;
    if (cur.done) cur.pct = 100;
    data[id] = cur;
    save(data);
    paint();
  });

  var chapter = document.body.getAttribute("data-chapter");
  var line = document.getElementById("scrollline");
  var resume = document.getElementById("resume");

  if (chapter && resume) {
    var saved = entry(load(), chapter).pct || 0;
    if (saved >= 4 && saved <= 96) {
      resume.hidden = false;
      resume.textContent = "回到上次位置（" + saved + "%）";
      resume.addEventListener("click", function (event) {
        event.preventDefault();
        var max = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        window.scrollTo({ top: (saved / 100) * Math.max(0, max), behavior: "smooth" });
      });
    }
  }

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      ticking = false;
      var ratio = scrollRatio();
      if (ratio === null) {
        if (line) line.style.width = "0%";
        return;
      }
      var pct = Math.round(ratio * 100);
      if (line) line.style.width = pct + "%";
      if (!chapter) return;
      if (window.scrollY < 48 && pct < 97) return;
      var data = load();
      var cur = entry(data, chapter);
      var prev = cur.pct || 0;
      if (pct > prev) cur.pct = pct;
      if (pct >= 97) cur.done = true;
      if ((cur.pct || 0) !== prev || (pct >= 97 && !entry(load(), chapter).done)) {
        data[chapter] = cur;
        save(data);
        paint();
      }
    });
  }

  document.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", fitNav);
  window.addEventListener("orientationchange", fitNav);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(fitNav);
  }
  fitNav();
  paint();
  onScroll();
})();
