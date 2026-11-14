import {mkdir,writeFile} from 'node:fs/promises';
import {shopBack,shopFront,owner,ribbon,looseReceipts,printer,receipt,svgScene,tidyPath} from './art.mjs';
await mkdir('assets/art',{recursive:true});
const drawings={
  'shop-chaos':svgScene('board-a',shopBack('ba')+ribbon('ba')+owner('ba')+shopFront('ba')+looseReceipts('ba')),
  'shop-clear':svgScene('board-b',shopBack('bb')+ribbon('bb',tidyPath)+owner('bb')+shopFront('bb')),
  'printer-close':svgScene('board-c',`<g transform="translate(540 1030) scale(2.9)">${printer('bc')}<g transform="translate(-72 -258)">${receipt('bc',{width:142,height:243})}</g></g>`)
};
for(const [name,svg] of Object.entries(drawings))await writeFile(`assets/art/${name}.svg`,svg);
await writeFile('assets/art/artboard.html',`<!doctype html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#fffdf7;display:flex;width:1620px;height:960px}section{position:relative;width:540px;height:960px;border-right:1px solid #ccc}img{position:absolute;width:540px;height:960px;inset:0}h1{position:absolute;left:45px;top:120px;font:900 55px/1.05 Impact,Arial,sans-serif;letter-spacing:-1px;margin:0;color:#1b2520}</style></head><body>${Object.keys(drawings).map((name,i)=>`<section><img src="${name}.svg"><h1>${['PAPER.<br>EVERYWHERE.','TAKE<br>CONTROL.','RUNNING<br>A SHOP?'][i]}</h1></section>`).join('')}</body></html>`);
console.log('Canonical artwork built as SVG and an artboard.');
