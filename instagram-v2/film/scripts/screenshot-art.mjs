import puppeteer from 'file:///C:/Users/hadzhee2K/AppData/Local/npm-cache/_npx/702923228c2ce1e6/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const b=await puppeteer.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--no-first-run','--no-sandbox']});
const p=await b.newPage();await p.setViewport({width:1620,height:960,deviceScaleFactor:1});
await p.goto(pathToFileURL(resolve('assets/art/artboard.html')).href,{waitUntil:'load'});
await p.screenshot({path:'assets/art/artboard.png'});await b.close();
