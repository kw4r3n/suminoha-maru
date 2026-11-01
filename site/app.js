(() => {
  'use strict';
  const families = {
    prose: { label: '本文', css: 'Suminoha prose' },
    code12: { label: 'Code12', css: 'Suminoha code12' },
    code35: { label: 'Code35', css: 'Suminoha code35' },
  };
  const form = document.querySelector('.tester-controls');
  const area = document.querySelector('.specimen-area');
  const specimen = document.querySelector('#specimen');
  const size = document.querySelector('#font-size');
  const sizeValue = document.querySelector('#size-value');
  const ligatures = document.querySelector('#ligatures');
  const glyphs = document.querySelector('#glyphs');
  const hint = document.querySelector('#feature-hint');
  const status = document.querySelector('#font-status');
  const retry = document.querySelector('#retry-font');
  const download = document.querySelector('#selected-download');
  let current = 'prose';
  const unavailableDownloads = new Set();
  let loadRequest = 0;
  let typingTimer;
  form.addEventListener('submit', event => event.preventDefault());

  function fitText() {
    specimen.style.height = '0px';
    specimen.style.height = `${Math.min(380, specimen.scrollHeight + 2)}px`;
  }

  function updateDownload() {
    const source = document.querySelector(`[data-download="${current}"]`);
    if (unavailableDownloads.has(current)) {
      download.removeAttribute('href');
      download.setAttribute('aria-disabled', 'true');
      download.textContent = `${families[current].label}の配布ファイルを準備中`;
    } else {
      download.href = source.href;
      download.removeAttribute('aria-disabled');
      download.textContent = `${families[current].label}用TTFをダウンロード（ZIP）`;
    }
  }

  async function verifyDownloads() {
    await Promise.all([...document.querySelectorAll('[data-download]')].map(async link => {
      try {
        const response = await fetch(link.href, { method: 'HEAD' });
        if (!response.ok) throw new Error('Download unavailable');
      } catch {
        unavailableDownloads.add(link.dataset.download);
        link.removeAttribute('href');
        link.setAttribute('aria-disabled', 'true');
        link.textContent = `${families[link.dataset.download].label}の配布ファイルを準備中`;
        document.querySelector('#download-status').hidden = false;
      }
    }));
    updateDownload();
  }

  function updateFeatures() {
    const settings = current === 'prose' ? 'normal' :
      `"calt" ${ligatures.checked ? 1 : 0}, "${glyphs.value === 'default' ? 'zero' : glyphs.value}" ${glyphs.value === 'default' ? 0 : 1}`;
    specimen.style.fontFeatureSettings = settings;
    document.querySelector('#hero-title').style.fontFeatureSettings = settings;
  }

  async function loadFont() {
    const request = ++loadRequest;
    const family = families[current];
    status.textContent = `${family.label}の見本フォントを読み込んでいます…`;
    retry.hidden = true;
    try {
      const loaded = await document.fonts.load(`400 ${size.value}px "${family.css}"`, specimen.value || 'あA');
      if (request !== loadRequest) return;
      if (!loaded.length) throw new Error('Font unavailable');
      fitText();
      status.textContent = `${family.label}を表示中。未収録文字は代替書体になります。`;
    } catch {
      if (request !== loadRequest) return;
      status.textContent = '見本フォントを読み込めませんでした。通信を確認し、再試行してください。';
      retry.hidden = false;
    }
  }

  function selectFamily(value) {
    if (!families[value]) return;
    current = value;
    area.dataset.family = value;
    form.elements.family.value = value;
    const isProse = value === 'prose';
    ligatures.disabled = isProse;
    glyphs.disabled = isProse;
    hint.textContent = isProse ? '本文ではコード用の合字・字形操作は使用できません。' :
      '合字の見本：!= === -> =>　字形の見本：Q @ a i <= >=';
    updateDownload();
    document.querySelector('#package-note').textContent = `${families[value].label}（Regular・横組み）のTTF、補助漢字3書体、各種ライセンスを同梱しています。`;
    updateFeatures();
    loadFont();
  }

  form.addEventListener('change', event => {
    if (event.target.name === 'family') selectFamily(event.target.value);
  });
  size.addEventListener('input', () => {
    specimen.style.setProperty('--sample-size', `${size.value}px`);
    sizeValue.value = `${size.value} px`;
    fitText();
  });
  ligatures.addEventListener('change', updateFeatures);
  glyphs.addEventListener('change', updateFeatures);
  specimen.addEventListener('input', () => {
    fitText();
    clearTimeout(typingTimer);
    typingTimer = setTimeout(loadFont, 250);
  });
  retry.addEventListener('click', () => {
    // Failed FontFace objects stay failed; refresh their stylesheet before retrying.
    const sheet = document.querySelector('link[href^="fonts/fonts.css"]');
    retry.hidden = true;
    status.textContent = '見本フォントを再読み込みしています…';
    sheet.onload = loadFont;
    sheet.onerror = () => {
      status.textContent = '見本フォントを読み込めませんでした。通信を確認し、再試行してください。';
      retry.hidden = false;
    };
    sheet.href = `fonts/fonts.css?retry=${Date.now()}`;
  });
  window.addEventListener('resize', fitText);
  document.querySelectorAll('[data-try]').forEach(button => {
    button.addEventListener('click', () => {
      selectFamily(button.dataset.try);
      document.querySelector('#tester').scrollIntoView({ block: 'start' });
      specimen.focus({ preventScroll: true });
    });
  });
  if (window.matchMedia('(max-width: 600px)').matches) {
    size.value = '32';
    size.dispatchEvent(new Event('input'));
  }
  selectFamily(current);
  verifyDownloads();
})();
