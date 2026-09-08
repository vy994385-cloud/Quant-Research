const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const pages = [
    { path: '/discover', name: 'discover' },
    { path: '/companies/HDFCBANK', name: 'company' },
    { path: '/financial-intelligence', name: 'financials' },
    { path: '/market-intelligence', name: 'market' },
    { path: '/technical', name: 'technical' },
    { path: '/events', name: 'events' },
    { path: '/compare', name: 'compare' },
    { path: '/reports', name: 'reports' },
    { path: '/my-research', name: 'my-research' },
    { path: '/screener', name: 'screener' },
    { path: '/evidence', name: 'evidence' },
    { path: '/themes', name: 'themes' },
    { path: '/industries', name: 'industries' },
    { path: '/peer-research', name: 'peer-research' },
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
      try {
        await page.goto(`http://localhost:5173${pg.path}`, { waitUntil: 'networkidle', timeout: 15000 });
        await page.waitForTimeout(2000);
        await page.screenshot({ path: `/tmp/t2w1-final/${pg.name}-${vp.label}.png`, fullPage: true });
        const bodyW = await page.evaluate(() => document.body.scrollWidth);
        const overflow = bodyW > vp.width + 5;
        const status = errors.length === 0 && !overflow ? 'PASS' : 'ISSUES';
        if (errors.length > 0 || overflow) allIssues.push(`${pg.name} ${vp.label}: errors=${errors.length} overflow=${overflow}`);
        console.log(`${pg.name} ${vp.label}: body=${bodyW} errors=${errors.length} overflow=${overflow} [${status}]`);
      } catch (e) {
        allIssues.push(`${pg.name} ${vp.label}: NAVIGATION FAILED`);
        console.log(`${pg.name} ${vp.label}: NAVIGATION FAILED`);
      }
      await ctx.close();
    }
  }

  // SCREAMING_SNAKE check
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://localhost:5173/discover', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const snakeCheck = await page.evaluate(() => {
    const els = document.querySelectorAll('.section-divider-label, .page-kicker, .section-title, .tech-obs-group-head strong');
    const snakes = Array.from(els).filter(el => /[A-Z]{2,}\s[A-Z]{2,}/.test(el.textContent));
    return snakes.map(el => el.textContent.trim());
  });
  console.log(`\nSCREAMING_SNAKE: ${snakeCheck.length === 0 ? 'PASS (0)' : 'FAIL: ' + snakeCheck.join(', ')}`);

  // Typography token check
  const tokenCheck = await page.evaluate(() => {
    const h1 = document.querySelector('h1');
    const section = document.querySelector('.section-title');
    const body = document.querySelector('.page-subtitle');
    return {
      h1: h1 ? getComputedStyle(h1).fontSize : null,
      section: section ? getComputedStyle(section).fontSize : null,
      body: body ? getComputedStyle(body).fontSize : null,
    };
  });
  console.log('Typography tokens:', tokenCheck);

  // Check page-kickers on all pages
  const kickerPages = [
    { path: '/discover', expected: 'Research home' },
    { path: '/financial-intelligence', expected: 'Research' },
    { path: '/market-intelligence', expected: 'Research' },
    { path: '/technical', expected: 'Research' },
    { path: '/events', expected: 'Research' },
    { path: '/compare', expected: 'Screen' },
    { path: '/reports', expected: 'Output' },
    { path: '/my-research', expected: 'Monitor' },
    { path: '/screener', expected: 'Screen' },
    { path: '/themes', expected: 'Discover' },
  ];
  
  for (const kp of kickerPages) {
    await page.goto(`http://localhost:5173${kp.path}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    const kicker = await page.evaluate(() => {
      const el = document.querySelector('.page-kicker');
      return el ? el.textContent.trim() : null;
    });
    const ok = kicker === kp.expected;
    if (!ok) allIssues.push(`Kicker ${kp.path}: expected "${kp.expected}", got "${kicker}"`);
    console.log(`Kicker ${kp.path}: ${ok ? 'PASS' : 'FAIL'} ("${kicker}" vs "${kp.expected}")`);
  }

  await ctx.close();

  console.log(`\n=== FINAL RESULT ===`);
  console.log(allIssues.length === 0 ? 'ALL PASS' : `ISSUES (${allIssues.length}): ${allIssues.join(' | ')}`);
  await browser.close();
})();
