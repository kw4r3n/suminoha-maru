module.exports = async (page) => {
  const results = [];
  function check(condition, name) {
    if (!condition) throw new Error(name);
    results.push(name);
  }
  const root = process.env.SITE_URL || 'http://127.0.0.1:8765';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto(root);
  await page.locator('#font-status').filter({ hasText: '本文を表示中' }).waitFor();
  check(await page.locator('#ligatures').isDisabled(), '本文ではコード専用操作を無効化');
  const value = '日本語 <script>alert(1)</script>\nconst a = x => x != null; Q @ ai <= >=';
  await page.locator('#specimen').fill(value);
  for (const family of ['code12', 'code35', 'prose']) {
    await page.locator(`input[name="family"][value="${family}"]`).check();
    await page.waitForFunction(f => document.querySelector('.specimen-area').dataset.family === f, family);
    check(await page.locator('#specimen').inputValue() === value, `${family}: 入力保持`);
    check(await page.locator('#ligatures').isDisabled() === (family === 'prose'), `${family}: 操作の可否`);
    check((await page.locator('#selected-download').getAttribute('href')).includes(family === 'prose' ? 'Gothic' : family === 'code12' ? 'Code12' : 'Code35'), `${family}: 配布先切替`);
  }
  await page.locator('input[value="code12"]').check();
  await page.locator('#specimen').fill('!= === -> => <= >= ai Q @');
  await page.locator('#font-status').filter({ hasText: 'Code12を表示中' }).waitFor();
  const on = await page.locator('#specimen').screenshot();
  await page.locator('#ligatures').uncheck();
  const off = await page.locator('#specimen').screenshot();
  check(!on.equals(off), '合字のON/OFFで実際の描画が変わる');
  await page.locator('#ligatures').check();
  await page.locator('#glyphs').selectOption('cv02');
  const alternate = await page.locator('#specimen').screenshot();
  check(!on.equals(alternate), 'cv02で実際の字形が変わる');
  check(await page.locator('#specimen').evaluate(el => getComputedStyle(el).fontFeatureSettings.includes('cv02')), '選択した機能を適用');
  await page.locator('#font-size').fill('96');
  check((await page.locator('#size-value').innerText()).includes('96'), 'サイズ値を更新');
  check(await page.locator('#specimen').evaluate(el => getComputedStyle(el).fontSize === '96px'), 'サイズを実描画に反映');
  await page.locator('#specimen').fill('');
  await page.locator('#font-status').filter({ hasText: 'Code12を表示中' }).waitFor();
  check(await page.locator('#specimen').inputValue() === '', '空入力でも操作可能');
  await page.locator('#specimen').fill('あ'.repeat(2000));
  check(await page.locator('#specimen').evaluate(el => el.scrollHeight > el.clientHeight), '長文をスクロールで閲覧可能');
  await page.locator('[data-try="code35"]').click();
  check(await page.locator('#specimen').evaluate(el => document.activeElement === el), '下部の試すボタンから入力欄へフォーカス');
  for (const family of ['prose', 'code12', 'code35']) {
    const pending = page.waitForEvent('download');
    await page.locator(`[data-download="${family}"]`).click();
    const download = await pending;
    check(download.suggestedFilename().endsWith('-TTF.zip') && !await download.failure(), `${family}: ZIPを実ダウンロード`);
  }
  const details = page.locator('.installation');
  await details.locator('summary').click();
  check(await details.getAttribute('open') !== null, '利用案内を展開');
  await page.keyboard.press('Tab');
  check(await page.evaluate(() => document.activeElement.tagName !== 'BODY'), 'キーボード操作のフォーカス');
  for (const width of [1536, 1440, 1280, 900, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 960 });
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${width}px: ページの横はみ出しなし`);
  }
  check(errors.length === 0, '通常操作でJavaScriptエラーなし');

  const backgrounds = [];
  for (const colorScheme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme });
    backgrounds.push(await page.locator('html').evaluate(el => getComputedStyle(el).backgroundColor));
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 960 });
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${colorScheme}・${width}px: 横はみ出しなし`);
    }
    const contrastFailures = await page.evaluate(() => {
      function luminance(color) {
        const rgb = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => v / 255);
        const linear = rgb.map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
        return linear[0] * .2126 + linear[1] * .7152 + linear[2] * .0722;
      }
      return ['#specimen', '.family-meta', '.input-hint', '.control-hint', '.primary', '.secondary', '.family-options small'].filter(selector => {
        const el = document.querySelector(selector);
        let parent = el;
        while (parent.parentElement && getComputedStyle(parent).backgroundColor === 'rgba(0, 0, 0, 0)') parent = parent.parentElement;
        const foreground = luminance(getComputedStyle(el).color);
        const background = luminance(getComputedStyle(parent).backgroundColor);
        return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05) < 4.5;
      });
    });
    check(contrastFailures.length === 0, `${colorScheme}: 本文・補足・配布ボタンの文字コントラスト4.5以上 (${contrastFailures.join(', ')})`);
  }
  check(backgrounds[0] !== backgrounds[1], 'システムの配色変更にページが再読み込みなしで追従');

  const browser = page.context().browser();
  for (const [character, part] of [['𠀋', 'HanJP'], ['𠀁', 'HanRareA'], ['𪑓', 'HanRareB']]) {
    const context = await browser.newContext();
    const samplePage = await context.newPage();
    const requested = [];
    samplePage.on('request', request => {
      if (request.url().includes('GothicHan') && request.url().endsWith('.woff2')) requested.push(request.url());
    });
    await samplePage.goto(root);
    await samplePage.locator('#font-status').filter({ hasText: '本文を表示中' }).waitFor();
    const response = samplePage.waitForResponse(r => r.url().includes(`Gothic${part}-Regular.woff2`) && r.ok());
    await samplePage.locator('#specimen').fill(character);
    await response;
    await samplePage.evaluate(() => document.fonts.ready);
    check(requested.length === 1 && requested[0].includes(part), `${part}: 必要な補助漢字だけを実際にロード`);
    await context.close();
  }
  const failureContext = await browser.newContext();
  const failurePage = await failureContext.newPage();
  await failurePage.route('**/*.woff2', route => route.abort());
  await failurePage.goto(root);
  await failurePage.locator('#retry-font').waitFor({ state: 'visible' });
  check((await failurePage.locator('#font-status').innerText()).includes('読み込めません'), 'フォント失敗時に再試行を提示');
  await failurePage.unroute('**/*.woff2');
  await failurePage.locator('#retry-font').click();
  // A failed FontFace stays failed in the font set; recovery must replace it or reload.
  await failurePage.locator('#font-status').filter({ hasText: '本文を表示中' }).waitFor({ timeout: 5000 });
  check(await failurePage.locator('#retry-font').isHidden(), 'フォント通信復旧後の再試行に成功');
  await failureContext.close();

  const missingContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const missingPage = await missingContext.newPage();
  await missingPage.route('**/*Code35*-TTF.zip', route => route.fulfill({ status: 404, body: '' }));
  await missingPage.goto(root);
  await missingPage.locator('[data-download="code35"][aria-disabled="true"]').waitFor();
  await missingPage.locator('input[value="code35"]').check();
  check(await missingPage.locator('#selected-download').getAttribute('href') === null, 'ZIP欠落時に無効リンクを出さない');
  check(await missingPage.locator('#download-status').isVisible(), 'ZIP欠落の案内を表示');
  await missingContext.close();

  const noJsContext = await browser.newContext({ javaScriptEnabled: false, colorScheme: 'dark' });
  const noJsPage = await noJsContext.newPage();
  await noJsPage.goto(root);
  check(await noJsPage.locator('noscript').isVisible(), 'JavaScript無効時の案内');
  check(await noJsPage.locator('[data-download]').count() === 3, 'JavaScriptなしでも用途別配布リンクがある');
  const darkBackground = await noJsPage.locator('html').evaluate(el => getComputedStyle(el).backgroundColor);
  check(darkBackground === backgrounds[1], 'JavaScriptなしでもダーク配色を適用');
  await noJsPage.locator('a[href="licenses/index.html"]').click();
  check(await noJsPage.locator('html').evaluate(el => getComputedStyle(el).backgroundColor) === darkBackground, 'ライセンス一覧も同じダーク配色');
  await noJsPage.locator('.license-face summary').first().click();
  check(await noJsPage.locator('.license-face pre').first().isVisible(), 'ダーク配色・JavaScriptなしでライセンス原文を展開');
  await noJsContext.close();
  return { browser: browser.browserType().name(), passed: results.length, checks: results };
};

if (require.main === module) {
  (async () => {
    const { firefox } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
    const browser = await firefox.launch({ headless: true });
    try {
      const page = await browser.newPage();
      console.log(JSON.stringify(await module.exports(page), null, 2));
    } finally {
      await browser.close();
    }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
