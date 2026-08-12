const puppeteer = require('puppeteer');
const path = require('path');

const wireframes = [
  { file: 'dashboard.html', output: 'dashboard.png' },
  { file: 'cliente-ficha.html', output: 'cliente-ficha.png' },
  { file: 'agenda-tecnicos.html', output: 'agenda-tecnicos.png' },
];

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  
  for (const wf of wireframes) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    const filePath = 'file://' + path.resolve(__dirname, 'wireframes', wf.file);
    await page.goto(filePath, { waitUntil: 'networkidle0', timeout: 15000 });
    await page.screenshot({ path: path.resolve(__dirname, 'wireframes', wf.output), fullPage: true });
    console.log(`Screenshot saved: ${wf.output}`);
    await page.close();
  }
  
  await browser.close();
  console.log('All screenshots done.');
})();
