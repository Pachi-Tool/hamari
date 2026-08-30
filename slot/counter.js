/* パチスロ レア役カウンター */
(function () {
  var root = document.querySelector('.counter');
  if (!root) return;

  var slug = root.dataset.slug || 'general';
  var machineName = root.dataset.name || '';
  var storeKey = 'slot-counter:' + slug;

  var gamesInput = document.getElementById('games');
  var roleEls = Array.prototype.slice.call(root.querySelectorAll('.role'));
  var totalCountEl = root.querySelector('.t-count');
  var totalProbEl = root.querySelector('.t-prob');
  var resetBtn = document.getElementById('reset');
  var shareBtn = document.getElementById('share');

  var state = { games: 0, counts: {} };
  roleEls.forEach(function (el) { state.counts[el.dataset.role] = 0; });

  /* ---------- 保存・復元 ---------- */
  function save() {
    try { localStorage.setItem(storeKey, JSON.stringify(state)); } catch (e) {}
  }
  function load() {
    try {
      var raw = localStorage.getItem(storeKey);
      if (!raw) return;
      var d = JSON.parse(raw);
      if (typeof d.games === 'number' && isFinite(d.games)) state.games = Math.max(0, Math.round(d.games));
      if (d.counts) {
        Object.keys(state.counts).forEach(function (k) {
          var v = d.counts[k];
          if (typeof v === 'number' && isFinite(v)) state.counts[k] = Math.max(0, Math.round(v));
        });
      }
    } catch (e) {}
  }

  /* ---------- 確率表示 ---------- */
  function probText(count) {
    if (!count || !state.games) return '1/－';
    var d = state.games / count;
    return '1/' + (d >= 1000 ? Math.round(d) : d.toFixed(1));
  }
  function totalCount() {
    return Object.keys(state.counts).reduce(function (s, k) { return s + state.counts[k]; }, 0);
  }

  /* ---------- 描画 ---------- */
  function render() {
    if (document.activeElement !== gamesInput) gamesInput.value = state.games;
    roleEls.forEach(function (el) {
      var key = el.dataset.role;
      el.querySelector('.count').textContent = state.counts[key];
      el.querySelector('.prob').textContent = probText(state.counts[key]);
    });
    var t = totalCount();
    totalCountEl.textContent = t;
    totalProbEl.textContent = probText(t);
    disarmReset();
  }

  /* ---------- 操作 ---------- */
  root.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.arrow');
    if (!btn) return;
    var li = btn.closest('.role');
    var key = li.dataset.role;
    var delta = btn.classList.contains('up') ? 1 : -1;
    state.counts[key] = Math.max(0, state.counts[key] + delta);
    save(); render();
  });

  Array.prototype.forEach.call(document.querySelectorAll('.step'), function (btn) {
    btn.addEventListener('click', function () {
      var step = parseInt(btn.dataset.step, 10) || 0;
      state.games = Math.max(0, state.games + step);
      save(); render();
    });
  });

  gamesInput.addEventListener('input', function () {
    var v = parseInt(gamesInput.value, 10);
    state.games = isFinite(v) && v > 0 ? v : 0;
    save();
    roleEls.forEach(function (el) {
      el.querySelector('.prob').textContent = probText(state.counts[el.dataset.role]);
    });
    totalProbEl.textContent = probText(totalCount());
  });

  /* ---------- リセット（2回押しで確定） ---------- */
  var armTimer = null;
  function disarmReset() {
    if (!resetBtn) return;
    resetBtn.dataset.armed = '0';
    resetBtn.textContent = 'リセット';
    if (armTimer) { clearTimeout(armTimer); armTimer = null; }
  }
  if (resetBtn) {
    resetBtn.addEventListener('click', function () {
      if (resetBtn.dataset.armed === '1') {
        state.games = 0;
        Object.keys(state.counts).forEach(function (k) { state.counts[k] = 0; });
        save(); render();
        return;
      }
      resetBtn.dataset.armed = '1';
      resetBtn.textContent = 'もう一度押すと消去';
      armTimer = setTimeout(disarmReset, 4000);
    });
  }

  /* ---------- Xに投稿 ---------- */
  if (shareBtn) {
    shareBtn.addEventListener('click', function () {
      var lines = [];
      lines.push(machineName + ' レア役カウンター');
      lines.push('総ゲーム数 ' + state.games + 'G');
      roleEls.forEach(function (el) {
        var key = el.dataset.role;
        lines.push(key + ' ' + state.counts[key] + '回 (' + probText(state.counts[key]) + ')');
      });
      var t = totalCount();
      lines.push('レア役合算 ' + t + '回 (' + probText(t) + ')');
      var url = 'https://twitter.com/intent/tweet?text=' +
        encodeURIComponent(lines.join('\n') + '\n') +
        '&url=' + encodeURIComponent(location.href) +
        '&hashtags=' + encodeURIComponent('パチスロ,レア役カウンター');
      window.open(url, '_blank', 'noopener');
    });
  }

  load();
  render();
})();
