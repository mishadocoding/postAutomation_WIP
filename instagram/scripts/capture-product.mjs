import puppeteer from 'file:///C:/Users/hadzhee2K/AppData/Local/npm-cache/_npx/702923228c2ce1e6/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
import {mkdir, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const output = resolve('assets/product');
await mkdir(output, {recursive:true});
const browser = await puppeteer.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless:true, args:['--no-first-run','--disable-background-networking','--disable-features=msEdgeSidebarV2','--no-sandbox']});
const page = await browser.newPage();
await page.setViewport({width:1440,height:1100,deviceScaleFactor:2});
await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
const errors=[];
page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(resolve('../../SampleERP/index.html')).href, {waitUntil:'load'});
await page.evaluate(()=>{localStorage.clear(); db=structuredClone(seed);db.sellerPermissions={...sellerDefaults};setLanguage('en');close();go('dashboard');});
await page.screenshot({path:resolve(output,'workspace.png')});
await (await page.$('.brand')).screenshot({path:resolve(output,'brand.png'),omitBackground:true});
await (await page.$('.logo')).screenshot({path:resolve(output,'logo.png'),omitBackground:true});
async function captureModal(name,short=false) {
  const box=await (await page.$('.modal')).boundingBox();
  if(short){
    const end=await (await page.$('.modal .detail-grid')).boundingBox();
    box.height=end.y+end.height-box.y+28;
  }
  await page.screenshot({path:resolve(output,name+'.png'),clip:box});
}
await page.evaluate(()=>{go('inventory');detail('CM-1001');});
await captureModal('stock-before',true);
const before=await page.evaluate(()=>product('CM-1001').stock);
await page.evaluate(()=>{close();newOrder();});
await captureModal('order-empty');
await page.type('#order-form [name="customer"]','Demo Customer');
await captureModal('order-filled');
await page.click('#order-form button[type="submit"]');
const sale=await page.evaluate(()=>({order:{...db.orders[0]},stock:product('CM-1001').stock}));
if(sale.stock!==before-1||sale.order.qty!==1)throw Error('Actual order did not deduct exactly one unit');
await page.evaluate(()=>detail('CM-1001'));
await captureModal('stock-after',true);
await page.evaluate(()=>{close();orderDetail(db.orders[0].id);});
await captureModal('processing',true);
for(const status of ['Shipped','Completed']){
  await page.evaluate(status=>{const f=document.querySelector('#status-form');f.querySelector('[name="status"]').value=status;f.requestSubmit();orderDetail(db.orders[0].id);},status);
  await captureModal(status.toLowerCase(),true);
}
await page.evaluate(()=>{close();go('orders');});
await page.screenshot({path:resolve(output,'workspace-result.png')});
await writeFile(resolve(output,'capture.json'),JSON.stringify({source:'../../SampleERP/index.html',language:'en',isolatedBrowser:true,before,...sale,finalStatus:await page.evaluate(()=>db.orders[0].status),errors},null,2));
console.log(JSON.stringify({captured:10,before,...sale,errors}));
await browser.close();
