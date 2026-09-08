const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  
  // All routes from App.tsx inventory
  const routes = [
    { path: '/discover', name: 'discover' },
    { path: '/discover/search', name: 'global-search' },
    { path: '/companies', name: 'companies' },
    { path: '/companies/HDFCBANK', name: 'company-workspace' },
    { path: '/industries', name: 'industries' },
    { path: '/themes', name: 'themes' },
    { path: '/financial-intelligence', name: 'financials' },
    { path: '/market-intelligence', name: 'market' },
    { path: '/technical', name: 'technical' },
    { path: '/events', name: 'events' },
    { path: '/evidence', name: 'evidence' },
    { path: '/research-gaps', name: 'research-gaps' },
    { path: '/screener', name: 'screener' },
    { path: '/compare', name: 'compare' },
    { path: '/peer-research', name: 'peer-research' },
    { path: '/my-research', name: 'my-research' },
    { path: '/watchlists', name: 'watchlists' },
    { path: '/research-changes', name: 'research-changes' },
    { path: '/evidence-alerts', name: 'evidence-alerts' },
    { path: '/calendar', name: 'calendar' },
    { path: '/reports', name: 'reports' },
    { path: '/professional-report', name: 'professional-report' },
    { path: '/evidence-package', name: 'evidence-package' },
    { path: '/asset-classes', name: 'asset-classes' },
    { path: '/timeline', name: 'timeline-redirect' },
    { path: '/profile', name: 'profile-redirect' },
    { path: '/research-home', name: 'research-home-redirect' },
  ];
  
  const widths = [
    { width: 1440, height: 900, label: '1440' },
    { width: 1280, height: 900, label: '1280' },
    { width: 1024, height: 900, label: '1024' },
    { width: 768, height: 900, label: '768' },
    { width: 390, height: 844, label: '390' },
  ];
  
  const results = [];
  let totalTests = 0;
  let passedTests = 0;
  let failedTests = 0;
  
  for (const vp of widths) {
    for (const pg of routes) {
      totalTests++;
      const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await ctx.newPage();
      const consoleErrors = [];
      const pageErrors = [];
      page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
      page.on('pageerror', e => pageErrors.push(e.message));
      
      let status = 'PASS';
      let issues = [];
      
      try {
        await page.goto(`http://localhost:5173${pg.path}`, { waitUntil: 'networkidle', timeout: 15000 });
        await page.waitForTimeout(2000);
        
        const bodyW = await page.evaluate(() => document.body.scrollWidth);
        const overflow = bodyW > vp.width + 5;
        if (overflow) {
          issues.push(`overflow:${bodyW}`);
          status = 'ISSUES';
        }
        
        if (consoleErrors.length > 0) {
          // Filter out known pre-existing warnings (React DevTools)
          const realErrors = consoleErrors.filter(e => !e.includes('React DevTools'));
          if (realErrors.length > 0) {
            issues.push(`console:${realErrors.length}`);
            status = 'ISSUES';
          }
        }
        
        if (pageErrors.length > 0) {
          issues.push(`pageerror:${pageErrors.length}`);
          status = 'ISSUES';
        }
        
        // Check primary structure present
        const hasHero = await page.evaluate(() => !!document.querySelector('.page-hero, .page-header'));
        const hasContent = await page.evaluate(() => {
          const el = document.querySelector('.page-content, .fi-layout, .ei-layout, .compare-grid, .reports-layout, .screener-layout');
          return !!el || document.body.innerText.length > 200;
        });
        
        if (!hasHero && !hasContent && pg.name !== 'timeline-redirect' && pg.name !== 'profile-redirect' && pg.name !== 'research-home-redirect') {
          issues.push('no-structure');
          status = 'ISSUES';
        }
        
      } catch (e) {
        issues.push('nav-failed');
        status = 'ISSUES';
      }
      
      if (status === 'PASS') passedTests++;
      else failedTests++;
      
      results.push({ route: pg.name, width: vp.label, status, issues: issues.join(',') });
      console.log(`${pg.name} ${vp.label}: ${status}${issues.length > 0 ? ' [' + issues.join(',') + ']' : ''}`);
      
      await ctx.close();
    }
  }
  
  console.log(`\n=== SUMMARY ===`);
  console.log(`Total: ${totalTests} | Pass: ${passedTests} | Fail: ${failedTests}`);
  console.log(failedTests === 0 ? 'ALL PASS' : `FAILURES: ${failedTests}`);
  
  if (failedTests > 0) {
    console.log('\nFailed tests:');
    results.filter(r => r.status !== 'PASS').forEach(r => {
      console.log(`  ${r.route} ${r.width}: ${r.issues}`);
    });
  }
  
  await browser.close();
})();
