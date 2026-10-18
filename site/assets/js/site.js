/* Anki Dictionary Add-on — shared site behaviour.
   No framework, no build step. Everything degrades to readable HTML. */

(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;

  /* ── ground: ink / paper ─────────────────────────────────────── */

  const themeButtons = [...document.querySelectorAll("[data-theme-set]")];
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  function applyTheme(name, persist) {
    const theme = name === "paper" ? "paper" : "ink";
    root.dataset.theme = theme;
    themeButtons.forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.themeSet === theme));
    });
    if (themeMeta) themeMeta.setAttribute("content", theme === "paper" ? "#efece5" : "#17171a");
    if (persist) {
      try { localStorage.setItem("akd-theme", theme); } catch (_) { /* private mode */ }
    }
  }

  themeButtons.forEach((btn) => {
    btn.addEventListener("click", () => applyTheme(btn.dataset.themeSet, true));
  });
  applyTheme(root.dataset.theme || "ink", false);

  /* ── mobile sheet ────────────────────────────────────────────── */

  const menu = document.querySelector(".menu");
  const sheet = document.getElementById("site-sheet");
  if (menu && sheet) {
    const close = () => {
      sheet.classList.remove("is-open");
      menu.setAttribute("aria-expanded", "false");
    };
    menu.addEventListener("click", () => {
      const open = !sheet.classList.contains("is-open");
      sheet.classList.toggle("is-open", open);
      menu.setAttribute("aria-expanded", String(open));
    });
    sheet.querySelectorAll("a").forEach((a) => a.addEventListener("click", close));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  }

  /* ── copy buttons ────────────────────────────────────────────── */

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "-1000px";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
      area.remove();
      return ok;
    }
  }

  document.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-copy], .copy");
    if (!btn) return;

    let text = btn.dataset.copy;
    if (!text) {
      const holder = btn.closest(".install-card, pre");
      const code = holder && holder.querySelector("code");
      text = code ? code.textContent.trim() : "";
    }
    if (!text) return;

    const ok = await writeClipboard(text);
    const previous = btn.textContent;
    btn.textContent = ok ? "copied" : "failed";
    btn.classList.toggle("is-done", ok);
    window.setTimeout(() => {
      btn.textContent = previous;
      btn.classList.remove("is-done");
    }, 1600);
  });

  /* ── count-up numbers ────────────────────────────────────────── */

  function formatNumber(el, value) {
    const decimals = Number.parseInt(el.dataset.decimals || "0", 10);
    let text;
    if (el.dataset.format === "plain") {
      text = String(Math.round(value));
    } else {
      text = value.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    }
    return text + (el.dataset.suffix || "");
  }

  function animateCount(el, force) {
    const target = Number.parseFloat(el.dataset.count);
    if (!Number.isFinite(target)) return;
    if (el.dataset.counted === "1" && !force) return;
    el.dataset.counted = "1";

    if (reduceMotion) {
      el.textContent = formatNumber(el, target);
      return;
    }

    const started = performance.now();
    const duration = 1350;
    el.textContent = formatNumber(el, 0);

    const tick = (now) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = formatNumber(el, target * eased);
      if (progress < 1) window.requestAnimationFrame(tick);
      else el.textContent = formatNumber(el, target);
    };
    window.requestAnimationFrame(tick);
  }

  function inView(el) {
    const rect = el.getBoundingClientRect();
    return rect.top < window.innerHeight * 0.92 && rect.bottom > 0;
  }

  const counters = [...document.querySelectorAll("[data-count]")];
  if (counters.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animateCount(entry.target, false);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.35 });
    counters.forEach((el) => observer.observe(el));
  } else {
    counters.forEach((el) => animateCount(el, false));
  }

  /* ── GitHub stars: live, with a quiet fallback ───────────────── */

  const REPO = "Alexander-Nilsson/Anki-Dictionary-Addon";
  const starNodes = [...document.querySelectorAll("[data-github-stars]")];
  if (starNodes.length) {
    fetch(`https://api.github.com/repos/${REPO}`, {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((response) => {
        if (!response.ok) throw new Error(`GitHub ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (typeof data.stargazers_count !== "number") throw new Error("no count");
        starNodes.forEach((el) => {
          el.dataset.count = String(data.stargazers_count);
          el.classList.remove("is-fallback");
          el.textContent = formatNumber(el, data.stargazers_count);
          if (el.classList.contains("stat-num") && inView(el)) {
            animateCount(el, true);
          }
        });
      })
      .catch(() => {
        starNodes.forEach((el) => {
          el.classList.add("is-fallback");
          el.textContent = "\u2014";
          el.setAttribute("title", "Live star count unavailable");
        });
      });
  }

  /* ── reveal on scroll ────────────────────────────────────────── */

  const reveals = [...document.querySelectorAll("[data-reveal]")];
  if (reveals.length && !reduceMotion && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach((el) => revealObserver.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("is-in"));
  }

  /* ── docs scrollspy ──────────────────────────────────────────── */

  const tocLinks = [...document.querySelectorAll(".toc nav a[href^='#']")];
  if (tocLinks.length) {
    const sections = tocLinks
      .map((link) => document.getElementById(link.hash.slice(1)))
      .filter(Boolean);

    let scheduled = false;
    const highlight = () => {
      scheduled = false;
      let active = sections[0];
      for (const section of sections) {
        if (section.getBoundingClientRect().top <= 128) active = section;
      }
      // Near the bottom of the page the final section wins even if its
      // heading has not crossed the line yet.
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 60) {
        active = sections[sections.length - 1];
      }
      tocLinks.forEach((link) => {
        const on = active && link.hash === `#${active.id}`;
        link.classList.toggle("is-active", Boolean(on));
        if (on) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      });
    };

    window.addEventListener("scroll", () => {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(highlight);
    }, { passive: true });
    highlight();
  }

  /* ── motion preferences for autoplaying captures ────────────── */

  if (reduceMotion) {
    document.querySelectorAll("video[autoplay]").forEach((video) => {
      video.removeAttribute("autoplay");
      video.pause();
    });
  }

  /* ── footer year ─────────────────────────────────────────────── */

  document.querySelectorAll("[data-year]").forEach((el) => {
    el.textContent = String(new Date().getFullYear());
  });
})();
