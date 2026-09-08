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

  for (const vp of widths) {
    for (const pg of pages) {
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await ctx.newPage();
      const errors = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://localhost:5173${pg.path}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `/tmp/t2w1-before/${pg.name}-${vp.label}.png`, fullPage: true });
      const bodyW = await page.evaluate(() => document.body.scrollWidth);
      console.log(`BEFORE ${pg.name} ${vp.label}: body=${bodyW} errors=${errors.length}`);
      await ctx.close();
    }
  }
  await browser.close();
  console.log('BEFORE capture complete.');
})();
