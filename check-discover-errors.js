const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://localhost:5173/discover', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  console.log('Discover errors:');
  errors.forEach((e, i) => console.log(`  ${i+1}. ${e.slice(0, 120)}`));
  await browser.close();
})();
