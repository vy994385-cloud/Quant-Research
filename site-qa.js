const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  
  const routes = [
    '/discover', '/discover/search', '/companies', '/companies/HDFCBANK',
    '/industries', '/themes', '/financial-intelligence', '/market-intelligence',
    '/technical', '/events', '/evidence', '/research-gaps', '/screener',
    '/compare', '/peer-research', '/my-research', '/watchlists',
    '/research-changes', '/evidence-alerts', '/calendar', '/reports',
    '/professional-report', '/evidence-package', '/asset-classes',
    '/timeline', '/profile', '/research-home',
  ];
  
  const widths = [
    { width: 1440, height: 900, label: '1440' },
    { width: 1280, height: 900, label: '1280' },
    { width: 1024, height: 900, label: '1024' },
    { width: 768, height: 900, label: '768' },
    { width: 390, height: 844, label: '390' },
  ];
  
  let total = 0, pass = 0, fail = 0;
  const failures = [];
  
  for (const vp of widths) {
    for (const path of routes) {
      total++;
      const name = path.replace(/\//g, '-').replace(/^-/, '') || 'root';
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await ctx.newPage();
      const errs = [];
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      page.on('pageerror', e => errs.push('PE:' + e.message));
      
      let status = 'PASS', issues = [];
      try {
        await page.goto(`http://localhost:5173${path}`, { waitUntil: 'networkidle', timeout: 10000 });
        await page.waitForTimeout(1500);
        const bodyW = await page.evaluate(() => document.body.scrollWidth);
        if (bodyW > vp.width + 5) { issues.push('overflow:' + bodyW); status = 'FAIL'; }
        const realErrs = errs.filter(e => !e.includes('React DevTools'));
        if (realErrs.length > 0) { issues.push('err:' + realErrs.length); status = 'FAIL'; }
      } catch (e) { issues.push('nav-fail'); status = 'FAIL'; }
      
      if (status === 'PASS') pass++; else { fail++; failures.push(`${name} ${vp.label}: ${issues.join(',')}`); }
      console.log(`${status} ${name} ${vp.label}${issues.length ? ' [' + issues.join(',') + ']' : ''}`);
      await ctx.close();
    }
  }
  
  console.log(`\nTOTAL: ${total} | PASS: ${pass} | FAIL: ${fail}`);
  if (failures.length > 0) { console.log('\nFailures:'); failures.forEach(f => console.log('  ' + f)); }
  else console.log('ALL PASS');
  
  await browser.close();
})();
