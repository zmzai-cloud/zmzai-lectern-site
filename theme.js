
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── nav 滚动阴影 ── */
  var nav = document.querySelector('nav');
  if (nav && !reduce) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── scroll reveal ── */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('in'); });
  }

  /* ── 移动端汉堡菜单(≤760px 时显示;展开/收起 + 点链接自动收起) ── */
  var burger = document.querySelector('.nav-burger');
  var navLinks = document.querySelector('.nav-links');
  if (burger && navLinks) {
    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = navLinks.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    navLinks.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        navLinks.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });
  }
})();

/* Shared playback controls for the two interactive product demonstrations. */
window.LecternTimeline = function (options) {
  var track = options.track, button = options.button, icon = options.icon;
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var value = motion.matches ? 100 : 0, playing = !motion.matches;
  var frameId = null, last = null;
  track.tabIndex = 0;
  track.setAttribute('aria-valuemin', '0');
  track.setAttribute('aria-valuemax', '100');
  function render() {
    track.setAttribute('aria-valuenow', String(Math.round(value)));
    track.setAttribute('aria-valuetext', (value * options.duration / 100000).toFixed(1) + ' 秒，共 ' + options.duration / 1000 + ' 秒');
    button.setAttribute('aria-label', playing ? '暂停演示' : value >= 100 ? '重播演示' : '播放演示');
    icon.innerHTML = playing
      ? '<rect x="1" y="1" width="3" height="8"/><rect x="6" y="1" width="3" height="8"/>'
      : '<path d="M2 1 L9 5 L2 9 Z"/>';
    options.render(value, playing);
  }
  function stop() {
    playing = false;
    if (frameId !== null) cancelAnimationFrame(frameId);
    frameId = null;
    last = null;
  }
  function frame(time) {
    frameId = null;
    if (!playing) return;
    if (last !== null) value = Math.min(100, value + (time - last) / options.duration * 100);
    last = time;
    if (value >= 100) stop();
    render();
    if (playing) frameId = requestAnimationFrame(frame);
  }
  function seek(next) {
    stop();
    value = Math.max(0, Math.min(100, next));
    render();
  }
  button.addEventListener('click', function () {
    if (playing) stop();
    else {
      if (value >= 100) { value = 0; if (options.reset) options.reset(); }
      playing = true;
      frameId = requestAnimationFrame(frame);
    }
    render();
  });
  track.addEventListener('keydown', function (event) {
    var next;
    switch (event.key) {
      case 'ArrowLeft': case 'ArrowDown': next = value - 5; break;
      case 'ArrowRight': case 'ArrowUp': next = value + 5; break;
      case 'Home': next = 0; break;
      case 'End': next = 100; break;
      case 'PageDown': next = value - 10; break;
      case 'PageUp': next = value + 10; break;
      default: return;
    }
    event.preventDefault();
    seek(next);
  });
  function seekPointer(event) {
    var rect = track.getBoundingClientRect();
    seek((event.clientX - rect.left) / rect.width * 100);
  }
  track.addEventListener('pointerdown', function (event) {
    if (!event.isPrimary || event.button !== 0) return;
    track.focus();
    track.setPointerCapture(event.pointerId);
    seekPointer(event);
    event.preventDefault();
  });
  track.addEventListener('pointermove', function (event) {
    if (track.hasPointerCapture(event.pointerId)) seekPointer(event);
  });
  track.addEventListener('pointerup', function (event) {
    if (track.hasPointerCapture(event.pointerId)) {
      seekPointer(event);
      track.releasePointerCapture(event.pointerId);
    }
  });
  motion.addEventListener('change', function (event) {
    if (event.matches) seek(100);
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { stop(); render(); }
  });
  render();
  if (playing) frameId = requestAnimationFrame(frame);
};
