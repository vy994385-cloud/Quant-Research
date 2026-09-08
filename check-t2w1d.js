const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const pages = [
    { path: '/financial-intelligence', name: 'financials' },
    { path: '/market-intelligence', name: 'market' },
    { path: '/technical', name: 'technical' },
  ];
  const widths = [
    { width: 1440, height: 900, label: '1440' },
    { width: 390, height: 844, label: '390' },
  ];
  const allIssues = [];

  for (const vp of widths) {
    for (const pg of pages) {
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await ctx.newPage();
      const errors = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://localhost:5173${pg.path}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `/tmp/t2w1-d/${pg.name}-${vp.label}.png`, fullPage: true });
      const bodyW = await page.evaluate(() => document.body.scrollWidth);
      const overflow = bodyW > vp.width + 5;
      if (errors.length > 0 || overflow) allIssues.push(`${pg.name} ${vp.label}: errors=${errors.length} overflow=${overflow}`);
      console.log(`${pg.name} ${vp.label}: body=${bodyW} errors=${errors.length} overflow=${overflow}`);
      await ctx.close();
    }
  }

  // Check canonical states render
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://localhost:5173/financial-intelligence', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Check Section components exist
  const sectionCount = await page.evaluate(() => document.querySelectorAll('.section').length);
  console.log(`Financial: ${sectionCount} Section components`);

  // Check page-kicker exists
  const kicker = await page.evaluate(() => {
    const el = document.querySelector('.page-kicker');
    return el ? el.textContent.trim() : null;
  });
  console.log(`Financial kicker: ${kicker}`);

  // Check no SCREAMING_SNAKE in section titles
  const snakeCheck = await page.evaluate(() => {
    const titles = document.querySelectorAll('.section-title, .section-subtitle, .page-kicker');
    const snakes = Array.from(titles).filter(el => /[A-Z]{2,}\s[A-Z]{2,}/.test(el.textContent));
    return snakes.map(el => el.textContent.trim());
  });
  console.log(`SCREAMING_SNAKE in sections: ${snakeCheck.length === 0 ? 'PASS' : snakeCheck.join(', ')}`);

  await ctx.close();

  console.log(`\n${allIssues.length === 0 ? 'ALL PASS' : 'ISSUES: ' + allIssues.join(' | ')}`);
  await browser.close();
})();
