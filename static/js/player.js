/* SOLO BEATS — shared player / theme / share logic */
(function () {
  "use strict";

  function formatTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  /* ---------------- Now playing bar (shared across pages) ---------------- */
  var nowPlaying = document.getElementById("nowPlaying");
  var npName = nowPlaying ? document.getElementById("npName") : null;
  var npToggle = nowPlaying ? document.getElementById("npToggle") : null;
  var npIconPause = nowPlaying ? document.getElementById("npIconPause") : null;
  var npIconPlay = nowPlaying ? document.getElementById("npIconPlay") : null;
  var npEqBars = nowPlaying ? nowPlaying.querySelectorAll(".np-eq span") : [];
  var activeAudio = null;
  var countedTracks = new Set();

  function setNpIcon(isPlaying) {
    if (!npIconPause || !npIconPlay) return;
    npIconPause.style.display = isPlaying ? "" : "none";
    npIconPlay.style.display = isPlaying ? "none" : "";
  }

  /* ---------------- Equalizer (lightweight visual animation) ----------------
     Note: this no longer routes audio through the Web Audio API
     (createMediaElementSource/AnalyserNode). That routing was forcing the
     browser to re-process every uploaded track's audio in JS, which caused
     crackling/noise during playback on some devices. The bars now animate
     with a simple timer instead of reading live audio data, so playback
     stays on the browser's native (clean) audio path. */
  var eqIntervalId = null;

  function startEq() {
    if (!npEqBars || !npEqBars.length) return;
    if (eqIntervalId) clearInterval(eqIntervalId);
    eqIntervalId = setInterval(function () {
      npEqBars.forEach(function (bar) {
        var scale = 0.18 + Math.random() * 1.0;
        bar.style.transform = "scaleY(" + scale.toFixed(2) + ")";
      });
    }, 120);
  }

  function stopEq() {
    if (eqIntervalId) { clearInterval(eqIntervalId); eqIntervalId = null; }
    npEqBars.forEach(function (bar) { bar.style.transform = "scaleY(0.18)"; });
  }

  /* ---------------- Swipe on now-playing bar ---------------- */
  function playableCards() {
    return Array.from(document.querySelectorAll(".music-box")).filter(function (c) {
      return c.style.display !== "none" && c.querySelector("audio");
    });
  }

  function playRelative(dir) {
    if (!activeAudio) return;
    var cards = playableCards();
    var currentCard = activeAudio.closest(".music-box");
    var idx = cards.indexOf(currentCard);
    if (idx === -1 || cards.length === 0) return;
    var nextIdx = (idx + dir + cards.length) % cards.length;
    var nextAudio = cards[nextIdx].querySelector("audio");
    if (nextAudio) nextAudio.play();
  }

  if (nowPlaying) {
    var touchStartX = null;
    nowPlaying.addEventListener("touchstart", function (e) {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });
    nowPlaying.addEventListener("touchend", function (e) {
      if (touchStartX === null) return;
      var dx = e.changedTouches[0].clientX - touchStartX;
      touchStartX = null;
      if (Math.abs(dx) < 45) return;
      playRelative(dx < 0 ? 1 : -1);
    });
  }

  /* ---------------- Global play/pause delegation ---------------- */
  document.addEventListener("play", function (e) {
    if (e.target.tagName !== "AUDIO") return;
    document.querySelectorAll("audio").forEach(function (a) {
      if (a !== e.target) a.pause();
    });
    document.querySelectorAll(".music-box").forEach(function (c) { c.classList.remove("playing"); });
    var card = e.target.closest(".music-box");
    if (card) card.classList.add("playing");

    activeAudio = e.target;
    if (nowPlaying) {
      var displayName = card ? card.getAttribute("data-display") : (document.body.getAttribute("data-track-display") || "");
      if (npName) npName.textContent = displayName || "";
      nowPlaying.classList.add("show");
      setNpIcon(true);
      startEq(e.target);
    }

    var name = card ? card.getAttribute("data-name") : document.body.getAttribute("data-track-name");
    if (name && !countedTracks.has(name)) {
      countedTracks.add(name);
      fetch("/track_play/" + encodeURIComponent(name), { method: "POST" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var els = document.querySelectorAll('.music-box[data-name="' + CSS.escape(name) + '"] .plays-count, .plays-count[data-track="' + CSS.escape(name) + '"]');
          els.forEach(function (el) { if (typeof data.plays !== "undefined") el.textContent = data.plays; });
        }).catch(function () {});
    }
  }, true);

  document.addEventListener("pause", function (e) {
    if (e.target.tagName !== "AUDIO") return;
    if (e.target === activeAudio) {
      var card = e.target.closest(".music-box");
      if (card) card.classList.remove("playing");
      setNpIcon(false);
      stopEq();
    }
  }, true);

  if (npToggle) {
    npToggle.addEventListener("click", function () {
      if (!activeAudio) return;
      if (activeAudio.paused) { activeAudio.play(); } else { activeAudio.pause(); }
    });
  }

  /* ---------------- Custom per-track player controls ---------------- */
  function initPlayer(playerEl) {
    var audio = playerEl.querySelector("audio");
    if (!audio) return;
    var playBtn = playerEl.querySelector(".play-pause-btn");
    var iconPlay = playerEl.querySelector(".icon-play");
    var iconPause = playerEl.querySelector(".icon-pause");
    var seekBar = playerEl.querySelector(".seek-bar");
    var progressFill = playerEl.querySelector(".progress-fill");
    var timeEl = playerEl.querySelector(".player-time");
    var muteBtn = playerEl.querySelector(".mute-btn");
    var iconVol = playerEl.querySelector(".icon-vol");
    var iconMute = playerEl.querySelector(".icon-mute");
    var volumeBar = playerEl.querySelector(".volume-bar");
    var volumePop = playerEl.querySelector(".volume-pop");
    var seeking = false;

    if (playBtn) {
      playBtn.addEventListener("click", function () {
        if (audio.paused) { audio.play(); } else { audio.pause(); }
      });
    }
    audio.addEventListener("play", function () {
      if (iconPlay) iconPlay.style.display = "none";
      if (iconPause) iconPause.style.display = "";
    });
    audio.addEventListener("pause", function () {
      if (iconPlay) iconPlay.style.display = "";
      if (iconPause) iconPause.style.display = "none";
    });
    audio.addEventListener("timeupdate", function () {
      if (seeking) return;
      if (timeEl) timeEl.textContent = formatTime(audio.currentTime);
      if (audio.duration) {
        var pct = (audio.currentTime / audio.duration) * 100;
        if (seekBar) seekBar.value = pct;
        if (progressFill) progressFill.style.width = pct + "%";
      }
    });
    audio.addEventListener("ended", function () {
      if (progressFill) progressFill.style.width = "0%";
      if (seekBar) seekBar.value = 0;
      if (timeEl) timeEl.textContent = "0:00";
    });
    if (seekBar) {
      seekBar.addEventListener("input", function () {
        seeking = true;
        if (progressFill) progressFill.style.width = seekBar.value + "%";
        if (timeEl && audio.duration) {
          timeEl.textContent = formatTime((seekBar.value / 100) * audio.duration);
        }
      });
      seekBar.addEventListener("change", function () {
        if (audio.duration) {
          audio.currentTime = (seekBar.value / 100) * audio.duration;
        }
        seeking = false;
      });
    }
    if (volumeBar) {
      volumeBar.addEventListener("input", function () {
        audio.volume = parseFloat(volumeBar.value);
        audio.muted = false;
        if (iconVol && iconMute) {
          iconVol.style.display = audio.volume > 0 ? "" : "none";
          iconMute.style.display = audio.volume > 0 ? "none" : "";
        }
      });
    }
    if (muteBtn) {
      muteBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        if (volumePop) {
          var isOpen = volumePop.classList.contains("show");
          document.querySelectorAll(".volume-pop.show").forEach(function (p) { p.classList.remove("show"); });
          if (!isOpen) volumePop.classList.add("show");
        } else {
          audio.muted = !audio.muted;
          if (iconVol && iconMute) {
            iconVol.style.display = audio.muted ? "none" : "";
            iconMute.style.display = audio.muted ? "" : "none";
          }
        }
      });
    }
    if (volumePop) {
      volumePop.addEventListener("click", function (e) { e.stopPropagation(); });
    }
  }

  document.addEventListener("click", function () {
    document.querySelectorAll(".volume-pop.show").forEach(function (p) { p.classList.remove("show"); });
  });

  /* ---------------- Share (Web Share API with copy fallback) ---------------- */
  window.sbShare = function (title, url, btn) {
    var shareText = title + " — SOLO BEATS";
    if (navigator.share) {
      navigator.share({ title: title, text: shareText, url: url }).catch(function () {});
    } else {
      navigator.clipboard.writeText(url).then(function () {
        if (btn) {
          var original = btn.textContent;
          btn.textContent = "لینک کپی شد ✓";
          setTimeout(function () { btn.textContent = original; }, 1500);
        }
      });
    }
  };

  /* ---------------- Theme toggle (day / night mirror) ---------------- */
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var moon = document.getElementById("themeIconMoon");
    var sun = document.getElementById("themeIconSun");
    var label = document.getElementById("themeLabel");
    if (moon && sun) {
      moon.style.display = theme === "light" ? "none" : "";
      sun.style.display = theme === "light" ? "" : "none";
    }
    if (label) label.textContent = theme === "light" ? "حالت روز" : "حالت شب";
  }

  window.sbInitThemeToggle = function () {
    var btn = document.getElementById("themeToggle");
    if (!btn) return;
    var saved = "dark";
    try { saved = localStorage.getItem("sb_theme") || "dark"; } catch (e) {}
    applyTheme(saved);
    btn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
      var next = current === "light" ? "dark" : "light";
      try { localStorage.setItem("sb_theme", next); } catch (e) {}
      applyTheme(next);
    });
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".player").forEach(initPlayer);
    window.sbInitThemeToggle();
  });
})();
