/* パチスロ レア役カウンター（機種切替つき） */
(function () {
  var root = document.querySelector('.counter');
  if (!root) return;

  var DATA = window.SLOT_MACHINES || [];
  var gamesInput = document.getElementById('games');
  var select = document.getElementById('machine-select');
  var titleEl = document.getElementById('machine-title');
  var tagsEl = document.getElementById('machine-tags');
  var noteEl = document.getElementById('machine-note');
  var rolesEl = root.querySelector('.roles');
  var refEl = document.getElementById('ref-area');
  var totalCountEl = root.querySelector('.t-count');
  var totalProbEl = root.querySelector('.t-prob');
  var resetBtn = document.getElementById('reset');
  var shareBtn = document.getElementById('share');

  var machine = null;
  var state = { games: 0, counts: {} };

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function bySlug(slug) {
    for (var i = 0; i < DATA.length; i++) if (DATA[i].slug === slug) return DATA[i];
    return null;
  }
  function storeKey() { return 'slot-counter:' + machine.slug; }

  /* ---------- 保存・復元 ---------- */
  function save() {
    try { localStorage.setItem(storeKey(), JSON.stringify(state)); } catch (e) {}
  }
  function load() {
    state = { games: 0, counts: {} };
    machine.roles.forEach(function (r) { state.counts[r.name] = 0; });
    try {
      var raw = localStorage.getItem(storeKey());
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

  /* ---------- 計算 ---------- */
  function probText(count) {
    if (!count || !state.games) return '1/－';
    var d = state.games / count;
    return '1/' + (d >= 1000 ? Math.round(d) : d.toFixed(1));
  }
  function totalCount() {
    return machine.roles.reduce(function (s, r) { return s + (state.counts[r.name] || 0); }, 0);
  }

  /* ---------- 描画：カード ---------- */
  function buildCards() {
    var h = '';
    machine.roles.forEach(function (r) {
      var n = esc(r.name);
      h += '<li class="role" data-role="' + n + '">' +
        '<div class="role-name">' + n + '</div>' +
        (r.alias ? '<div class="role-alias">＝' + esc(r.alias) + '</div>' : '') +
        '<button type="button" class="arrow up" aria-label="' + n + ' を1回足す">▲</button>' +
        '<div class="count">0</div>' +
        '<button type="button" class="arrow down" aria-label="' + n + ' を1回減らす">▼</button>' +
        '<div class="prob">1/－</div></li>';
    });
    rolesEl.innerHTML = h;
  }

  /* ---------- 描画：設定差の表 ---------- */
  function buildRef() {
    if (!refEl) return;
    var diffRoles = machine.roles.filter(function (r) { return r.diff && r.probs; });
    var headEl = document.getElementById('ref-heading');
    if (headEl) headEl.textContent = diffRoles.length ? '設定推測に使えるレア役' : 'レア役の出現率';
    var h = '';
    if (!diffRoles.length) {
      h += '<p class="note">この機種は、レア役の出現率に設定差が確認されていません。' +
        'カウントは実戦データの記録用としてお使いください。</p>';
    } else {
      var settings = [];
      diffRoles.forEach(function (r) {
        Object.keys(r.probs).forEach(function (k) { if (settings.indexOf(k) < 0) settings.push(k); });
      });
      settings.sort();
      h += '<div class="tablewrap"><table class="ref"><tr><th>レア役</th>';
      settings.forEach(function (s) { h += '<th>設定' + esc(s) + '</th>'; });
      h += '</tr>';
      diffRoles.forEach(function (r) {
        h += '<tr><td class="rolecell hit">' + esc(r.name) + '</td>';
        settings.forEach(function (s) {
          h += '<td>' + (r.probs[s] ? '1/' + esc(r.probs[s]) : '－') + '</td>';
        });
        h += '</tr>';
      });
      h += '</table></div><p class="note">設定差が確認されているのはこのレア役です。' +
        'ここが伸びているかどうかが設定推測の手がかりになります。</p>';
    }

    var others = machine.roles.filter(function (r) { return !(r.diff && r.probs); });
    if (others.length) {
      h += '<h3 class="sub-h">そのほかのレア役</h3>' +
        '<div class="tablewrap"><table class="ref"><tr><th>レア役</th><th>出現率</th></tr>';
      others.forEach(function (r) {
        var v;
        if (r.common) v = '1/' + esc(r.common) + '<span class="cap">全設定共通</span>';
        else if (r.probs && r.probs['1']) v = '1/' + esc(r.probs['1']) + '<span class="cap">設定1の値</span>';
        else v = '<span class="cap">調査中</span>';
        h += '<tr><td class="rolecell">' + esc(r.name) + '</td><td>' + v + '</td></tr>';
      });
      h += '</table></div>';
    }

    if (machine.sources && machine.sources.length) {
      h += '<p class="note src">確率の出典：' + machine.sources.map(function (u) {
        return '<a href="' + esc(u) + '" target="_blank" rel="nofollow noopener">' +
          esc(u.split('/')[2]) + '</a>';
      }).join('、') + '</p>';
    }
    refEl.innerHTML = h;
  }

  /* ---------- 描画：数値 ---------- */
  function renderCounts() {
    if (document.activeElement !== gamesInput) gamesInput.value = state.games;
    Array.prototype.forEach.call(rolesEl.querySelectorAll('.role'), function (el) {
      var key = el.dataset.role;
      el.querySelector('.count').textContent = state.counts[key] || 0;
      el.querySelector('.prob').textContent = probText(state.counts[key] || 0);
    });
    var t = totalCount();
    totalCountEl.textContent = t;
    totalProbEl.textContent = probText(t);
    disarmReset();
  }

  /* ---------- 機種の切替 ---------- */
  function applyMachine(m, pushUrl) {
    machine = m;
    root.dataset.slug = m.slug;
    root.dataset.name = m.name;
    var title = m.name + ' レア役合算・レア役カウンター';
    if (titleEl) titleEl.textContent = title;
    document.title = title;
    if (noteEl) noteEl.textContent = m.note || '';
    if (tagsEl) {
      tagsEl.innerHTML = [m.maker, m.type, m.intro].filter(Boolean)
        .map(function (c) { return '<span class="tag">' + esc(c) + '</span>'; }).join('');
    }
    if (select) select.value = m.slug;
    buildCards();
    buildRef();
    load();
    renderCounts();
    if (pushUrl && window.history && history.pushState) {
      try { history.pushState({ slug: m.slug }, '', m.slug + '.html'); } catch (e) {}
    }
  }

  if (select) {
    select.addEventListener('change', function () {
      var m = bySlug(select.value);
      if (m) { applyMachine(m, true); window.scrollTo({ top: 0, behavior: 'smooth' }); }
    });
  }
  window.addEventListener('popstate', function () { location.reload(); });

  /* ---------- 操作 ---------- */
  root.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.arrow');
    if (!btn) return;
    var key = btn.closest('.role').dataset.role;
    state.counts[key] = Math.max(0, (state.counts[key] || 0) + (btn.classList.contains('up') ? 1 : -1));
    save(); renderCounts();
  });

  Array.prototype.forEach.call(document.querySelectorAll('.step'), function (btn) {
    btn.addEventListener('click', function () {
      state.games = Math.max(0, state.games + (parseInt(btn.dataset.step, 10) || 0));
      save(); renderCounts();
    });
  });

  gamesInput.addEventListener('input', function () {
    var v = parseInt(gamesInput.value, 10);
    state.games = isFinite(v) && v > 0 ? v : 0;
    save(); renderCounts();
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
        save(); renderCounts();
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
      var lines = [machine.name + ' レア役カウンター', '総ゲーム数 ' + state.games + 'G'];
      machine.roles.forEach(function (r) {
        lines.push(r.name + ' ' + (state.counts[r.name] || 0) + '回 (' + probText(state.counts[r.name] || 0) + ')');
      });
      var t = totalCount();
      lines.push('レア役合算 ' + t + '回 (' + probText(t) + ')');
      window.open('https://twitter.com/intent/tweet?text=' +
        encodeURIComponent(lines.join('\n') + '\n') +
        '&url=' + encodeURIComponent(location.href) +
        '&hashtags=' + encodeURIComponent('パチスロ,レア役カウンター'), '_blank', 'noopener');
    });
  }

  /* ---------- 起動 ---------- */
  var initial = bySlug(root.dataset.slug) || DATA[0];
  if (initial) applyMachine(initial, false);
})();
