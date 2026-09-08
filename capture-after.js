const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const pages = [
    { path: '/discover', name: 'discover' },
    { path: '/companies/HDFCBANK', name: 'company' },
    { path: '/financial-intelligence', name: 'financials' },
    { path: '/screener', name: 'screener' },
    { path: '/evidence', name: 'evidence' },
  ];
  const widths = [
    { width: 1440, height: 900, label: '1440' },
    { width: 390, height: 844, label: '390' },
  ];
  const allErrors = [];

  for (const vp of widths) {
    for (const pg of pages) {
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await ctx.newPage();
      const errors = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://localhost:5173${pg.path}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `/tmp/t2w1-after/${pg.name}-${vp.label}.png`, fullPage: true });
      const bodyW = await page.evaluate(() => document.body.scrollWidth);
      const overflow = bodyW > vp.width + 5;
      const status = errors.length === 0 && !overflow ? 'PASS' : 'ISSUES';
      if (errors.length > 0 || overflow) allErrors.push(`${pg.name} ${vp.label}: errors=${errors.length} overflow=${overflow}`);
      console.log(`AFTER ${pg.name} ${vp.label}: body=${bodyW} errors=${errors.length} overflow=${overflow} [${status}]`);
      await ctx.close();
    }
  }

  // Check SCREAMING_SNAKE is gone
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://localhost:5173/discover', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const snakeCheck = await page.evaluate(() => {
    const dividers = document.querySelectorAll('.section-divider-label, .page-kicker');
    const snakes = Array.from(dividers).filter(el => /[A-Z]{2,}\s[A-Z]{2,}/.test(el.textContent));
    return snakes.map(el => el.textContent.trim());
  });
  console.log('SCREAMING_SNAKE in section labels:', snakeCheck.length === 0 ? 'PASS (0)' : `FAIL: ${snakeCheck.join(', ')}`);

  // Check page-kicker exists on key pages
  const kickerCheck = await page.evaluate(() => {
    const kickers = document.querySelectorAll('.page-kicker');
    return Array.from(kickers).map(k => k.textContent.trim());
  });
  console.log('Page kickers found:', kickerCheck);

  // Check typography tokens are being used
  const tokenCheck = await page.evaluate(() => {
    const el = document.querySelector('h1');
    if (!el) return null;
    const style = getComputedStyle(el);
    return { fontSize: style.fontSize, fontFamily: style.fontFamily.slice(0, 30) };
  });
  console.log('H1 typography:', tokenCheck);

  await ctx.close();

  console.log('\n=== SUMMARY ===');
  console.log(allErrors.length === 0 ? 'ALL PASS' : `ISSUES: ${allErrors.join(' | ')}`);
  await browser.close();
})();
