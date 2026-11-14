import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import {C,GRIP,ink,printer,printerPaper,shopBack,shopFront,owner,frontHand,ribbon,looseReceipts,svgScene,chaosPath,tidyPath,armTo,pathToGrip,receipt,customerHand,bagReceipt} from './art.mjs';

const timing=JSON.parse(await readFile('timing.json','utf8'));
const fps=timing.fps,cuts=timing.cutsFrames.map(f=>f/fps),total=cuts.at(-1);
await mkdir('compositions',{recursive:true});
const base=`
@font-face{font-family:'Receipt Sans';src:url('assets/fonts/Inter-700.woff2') format('woff2');font-weight:700;font-display:swap}
@font-face{font-family:'Receipt Sans';src:url('assets/fonts/Inter-400.woff2') format('woff2');font-weight:400;font-display:swap}
#root{position:absolute;inset:0;background:${C.paper};color:${C.ink};font-family:'Receipt Sans',Inter,sans-serif;overflow:hidden}
.drawing{position:absolute;inset:0;width:1080px;height:1920px;overflow:visible}
.headline{position:absolute;left:90px;top:226px;margin:0;font-family:'League Gothic';font-size:146px;font-weight:400;line-height:.96;letter-spacing:-1px;z-index:2}
.support{position:absolute;left:94px;font-size:34px;line-height:1.3;margin:0;font-weight:700}
.world{position:absolute;inset:0}
`;
const scene=async(id,html,css,js)=>{
 const n=timing.sceneIds.indexOf(id),duration=cuts[n+1]-cuts[n];
 await writeFile(`compositions/${id}.html`,`<template>\n<style>${base}\n${css}\n</style>\n<div id="root" data-composition-id="${id}" data-width="1080" data-height="1920">\n<div id="${id}-clip" class="clip" data-start="0" data-duration="${duration}" data-track-index="0" data-beat="${id}">\n${html}\n</div>\n</div>\n<script>\nconst tl=gsap.timeline({paused:true});\n${js}\nwindow.__timelines["${id}"]=tl;\n</script>\n</template>\n`);
};
const wipe=(id)=>`<div class="${id}-paper-wipe" data-layout-allow-overflow data-layout-allow-occlusion><svg viewBox="0 0 1080 2040" width="1080" height="2040"><path d="M0 60L60 0L120 60L180 0L240 60L300 0L360 60L420 0L480 60L540 0L600 60L660 0L720 60L780 0L840 60L900 0L960 60L1020 0L1080 60V2040H0Z" fill="${C.paper}" ${ink}/></svg></div>`;
const wipeCSS=(id)=>`.${id}-paper-wipe{position:absolute;left:0;top:0;width:1080px;height:2040px;transform-origin:0 0;opacity:0;z-index:10}`;
const zoomPaper=(id,{x,y,sx,sy,at,dur=.44})=>`tl.to('.${id}-paper-wipe',{opacity:1,duration:.001},${at});\ntl.fromTo('.${id}-paper-wipe',{x:${x},y:${y},scaleX:${sx},scaleY:${sy}},{x:-25,y:-60,scaleX:1.05,scaleY:1.05,duration:${dur},ease:'power4.inOut'},${at});`;
const stage=(prefix,opts={})=>svgScene(prefix,shopBack(prefix)+ribbon(prefix,opts.path||chaosPath)+owner(prefix,{frontHandVisible:opts.frontHandVisible!==false})+shopFront(prefix)+(opts.leaves?looseReceipts(prefix):''));
const morphRibbon=(prefix,path,at,duration=1)=>['edge','paper','print'].map(part=>`tl.to('.${prefix}-ribbon-${part}',{attr:{d:${JSON.stringify(path)}},duration:${duration},ease:'power3.inOut'},${at});`).join('\n');
const grip=(prefix,x,y,at,duration=.35)=>`tl.to('.${prefix}-grip',{x:${x-GRIP.x},y:${y-GRIP.y},duration:${duration},ease:'power3.inOut'},${at});\ntl.to('.${prefix}-arm-edge,.${prefix}-arm-shirt',{attr:{d:${JSON.stringify(armTo(x,y))}},duration:${duration},ease:'power3.inOut'},${at});`;
const happy=(prefix,at)=>`tl.to('.${prefix}-mouth',{attr:{d:'M718 886 Q735 907 753 885'},duration:.35,ease:'power2.inOut'},${at});\ntl.to('.${prefix}-brow-left',{attr:{d:'M699 829 Q709 825 720 830'},duration:.3},${at});\ntl.to('.${prefix}-brow-right',{attr:{d:'M750 830 Q761 825 772 830'},duration:.3},${at+.07});`;

// 1. The printer is a real illustrated object with paper exiting its slot.
await scene('burst',`<h1 class="headline burst-title">RUNNING<br>A SHOP?</h1>
<div class="bu-camera" data-layout-allow-overflow data-layout-allow-occlusion>${svgScene('bu',`<g transform="translate(540 1070) scale(2.3)"><g class="bu-machine">${printer('bu')}<defs><clipPath id="bu-slot-mask"><rect x="-85" y="-250" width="170" height="240"/></clipPath></defs><g clip-path="url(#bu-slot-mask)"><g class="bu-feed">${printerPaper('bu')}</g></g><path d="M-88 -9 H69" stroke="${C.ink}" stroke-width="6" stroke-linecap="round"/></g></g>`)}</div>`,
`#root{background:${C.orange}}.bu-camera{position:absolute;inset:0;transform-origin:540px 947.525px;z-index:3}.burst-title{font-size:154px}`,
`tl.fromTo('.bu-feed',{y:142},{y:0,duration:.48,ease:'power4.out'},.12);
tl.fromTo('.bu-machine',{rotation:-2},{rotation:0,duration:.24,ease:'back.out(1.6)',svgOrigin:'0 70'},.05);
tl.to('.bu-feed',{y:-15,duration:.12,ease:'power2.in'},.68);
tl.to('.bu-feed',{y:0,duration:.2,ease:'power3.out'},.8);
tl.to('.bu-camera',{scale:50,y:12.475,duration:.42,ease:'power3.in'},${cuts[1]-.42});`);

// 2. Same shop and owner: paper grows out of the printer, then rains over them.
const tugPath=pathToGrip(chaosPath,620,1000);
const anticipateAt=cuts[2]-cuts[1]-.6;
const leavesB=Array.from({length:8},(_,i)=>`tl.to('.av-leaf-${i}',{opacity:1,duration:.001},${1.65+i*.25});\ntl.fromTo('.av-leaf-${i}',{y:${-360-i*35},x:${i%2?70:-65},rotation:${i%2?16:-12}},{y:0,x:0,rotation:0,duration:.48,ease:'power2.in'},${1.65+i*.25});`).join('\n');
await scene('avalanche',`<h1 class="headline avalanche-title">PAPER.<br>EVERYWHERE.</h1><div class="world av-world">${stage('av',{path:tidyPath,leaves:true})}</div>`,
`.av-world{transform-origin:735px 930px}.av-world [data-prop="receipt-leaf"]{opacity:0}`,
`${morphRibbon('av',chaosPath,.12,1.35)}
${leavesB}
tl.fromTo('.av-head',{rotation:0},{rotation:-6,svgOrigin:'735 917',duration:.42,ease:'power3.inOut'},2.6);
tl.to('.av-head',{rotation:-9,duration:.16,ease:'power2.in'},4.1);
tl.to('.av-head',{rotation:-6,duration:.3,ease:'power3.out'},4.26);
tl.to('.av-eye-left',{ry:3,duration:.12,yoyo:true,repeat:1},4.9);
tl.to('.av-eye-right',{ry:3,duration:.12,yoyo:true,repeat:1},4.93);
${grip('av',620,1000,anticipateAt,.3)}
${morphRibbon('av',tugPath,anticipateAt,.3)}`);

// 3. A shared grip drives both the hand and paper. The system clears on the drop.
const controlDur=cuts[3]-cuts[2];
const leavesC=Array.from({length:8},(_,i)=>`tl.to('.co-leaf-${i}',{x:${(400-[255,610,340,740,220,465,580,760][i])},y:${(1130-[680,650,890,860,1050,990,1135,1085][i])},scale:.05,opacity:0,duration:.42,ease:'power3.in'},${i*.065});`).join('\n');
await scene('control',`<h1 class="headline control-title">TAKE<br>CONTROL.</h1><div class="world co-world">${stage('co',{path:tugPath,leaves:true})}</div>${wipe('co')}`,
`${wipeCSS('co')}`,
`tl.fromTo('.co-head',{rotation:-6},{rotation:0,svgOrigin:'735 917',duration:.75,ease:'power3.out'},0);
${morphRibbon('co',tidyPath,0,1.05)}
tl.fromTo('.co-grip',{x:-30,y:-10},{x:0,y:0,duration:1.05,ease:'power3.inOut'},0);
tl.fromTo('.co-arm-edge,.co-arm-shirt',{attr:{d:${JSON.stringify(armTo(620,1000))}}},{attr:{d:${JSON.stringify(armTo(650,1010))}},duration:1.05,ease:'power3.inOut'},0);
${leavesC}
${happy('co',.65)}
${zoomPaper('co',{x:610,y:970,sx:.0741,sy:.075,at:controlDur-.44})}`);

// 4. Brief real proof. Source crops are captured in an isolated browser with focus blurred.
const proofDur=cuts[4]-cuts[3];
const proofCard=`<svg class="drawing" viewBox="0 0 1080 1920" data-layout-ignore><path d="M130 565 H910 V1190 L871 1220 L832 1190 L793 1220 L754 1190 L715 1220 L676 1190 L637 1220 L598 1190 L559 1220 L520 1190 L481 1220 L442 1190 L403 1220 L364 1190 L325 1220 L286 1190 L247 1220 L208 1190 L169 1220 L130 1190Z" fill="white" ${ink}/><path d="M173 776 H866 M173 1090 H866" stroke="${C.ink}" stroke-width="3" stroke-dasharray="9 8"/></svg>`;
await scene('proof',`<div class="proof-underlay" data-layout-ignore></div><h1 class="headline proof-title">ONE SALE.<br>STOCK UPDATED.</h1>${proofCard}
<div class="proof-product"><img id="proof-product-title" class="clip proof-header" src="assets/product/product-title.png" data-start="0" data-duration="${proofDur}" alt="Actual product: MacBook Air M3, CM-1001"></div>
<div class="proof-value"><img id="proof-stock-before" class="clip stock-crop" src="assets/product/stock-24.png" data-start="0" data-duration="1.55" alt="Actual available stock before sale: 24"><img id="proof-stock-after" class="clip stock-crop" src="assets/product/stock-23.png" data-start="1.55" data-duration="${proofDur-1.55}" alt="Actual available stock after one sale: 23"></div>
<p class="support proof-note">SampleERP · One demo sale</p><div class="proof-stamp">1 SOLD</div>
${wipe('pf')}`,
`#root{background:${C.lime}}${wipeCSS('pf')}.proof-underlay{position:absolute;inset:0;background:${C.paper};transform-origin:540px 900px}.proof-title{font-size:135px}.proof-product{position:absolute;left:170px;top:605px;width:700px;height:151px;overflow:hidden}.proof-header{position:absolute;left:0;top:0;width:700px;height:auto}.proof-value{position:absolute;left:177px;top:812px;width:530px;height:241px;overflow:hidden}.stock-crop{position:absolute;left:0;top:0;width:530px;height:auto}.proof-note{top:1123px;font-size:34px;left:177px}.proof-stamp{position:absolute;left:655px;top:917px;color:${C.green};border:5px solid ${C.green};padding:10px 18px;font:62px/.95 'League Gothic';transform-origin:center}`,
`tl.fromTo('.proof-stamp',{scale:1.8,rotation:-17,opacity:0},{scale:1,rotation:-7,opacity:1,duration:.22,ease:'power4.out'},1.55);
tl.fromTo('.proof-underlay',{scaleX:1,scaleY:1},{scaleX:.7,scaleY:.32,duration:.36,ease:'power3.inOut'},0);
tl.to('.proof-underlay',{opacity:0,duration:.01},.36);
${zoomPaper('pf',{x:130,y:565,sx:.7222,sy:.3211,at:proofDur-.4,dur:.4})}`);

// 5. Return to exactly the same illustrated shop. Owner releases the paper and smiles.
const payoffDur=cuts[5]-cuts[4];
await scene('payoff',`<h1 class="headline payoff-title">RUN THE SHOP.<br>NOT THE CHAOS.</h1><div class="world pa-world">${stage('pa',{path:tidyPath,frontHandVisible:false})}<svg class="drawing" viewBox="0 0 1080 1920"><g class="pa-bag" ${ink}><path d="M530 1011 H629 L640 1120 H520Z" fill="${C.lime}"/><path d="M554 1011 V989 Q578 964 604 989 V1011" fill="none" stroke-width="7"/><image href="assets/product/logo.png" x="556" y="1043" width="48" height="48"/>${bagReceipt()}</g>${customerHand('pa')}${frontHand('pa')}</svg></div>${wipe('pa')}`,
`.payoff-title{font-size:130px}${wipeCSS('pa')}.pa-customer{opacity:0}`,
`${happy('pa',0)}
tl.fromTo('.pa-head',{rotation:0},{rotation:4,svgOrigin:'735 917',duration:.3,ease:'power3.out'},.15);
tl.fromTo('.pa-bag',{y:-52,opacity:0},{y:0,opacity:1,duration:.38,ease:'power3.out'},.38);
${morphRibbon('pa','M400 1130 C400 1100 400 1090 400 1080 C400 1070 410 1060 420 1050 C430 1040 440 1040 450 1050 C460 1060 460 1080 460 1100',.15,.6)}
${grip('pa',604,989,.15,.6)}
tl.to('.pa-customer',{opacity:1,duration:.001},1);
tl.fromTo('.pa-customer',{x:-320,y:0},{x:0,y:0,duration:.8,ease:'power2.inOut'},1);
tl.fromTo('.pa-customer-leg-a',{rotation:-6},{rotation:6,svgOrigin:'340 1120',duration:.18,yoyo:true,repeat:3,ease:'sine.inOut'},1);
tl.fromTo('.pa-customer-leg-b',{rotation:5},{rotation:-5,svgOrigin:'380 1120',duration:.18,yoyo:true,repeat:3,ease:'sine.inOut'},1.04);
tl.to('.pa-customer-leg-a,.pa-customer-leg-b',{rotation:0,duration:.12,ease:'power2.out'},1.76);
${grip('pa',650,1010,2.25,.3)}
tl.to('.pa-customer,.pa-bag',{x:-130,y:0,duration:.65,ease:'power3.inOut'},2.55);
tl.to('.pa-customer-leg-a',{rotation:7,svgOrigin:'340 1120',duration:.15,yoyo:true,repeat:3,ease:'sine.inOut'},2.55);
tl.to('.pa-customer-leg-b',{rotation:-6,svgOrigin:'380 1120',duration:.15,yoyo:true,repeat:3,ease:'sine.inOut'},2.58);
${zoomPaper('pa',{x:401,y:1060,sx:.01852,sy:.01961,at:payoffDur-.6,dur:.6})}`);

// 6. A shop poster / receipt, not an unrelated corporate title card.
const finishDur=cuts[6]-cuts[5];
await scene('finish',`<div class="finish-paper"><svg class="drawing" viewBox="0 0 1080 1920" data-layout-ignore><path d="M125 270 H935 V1247 L890 1285 L845 1247 L800 1285 L755 1247 L710 1285 L665 1247 L620 1285 L575 1247 L530 1285 L485 1247 L440 1285 L395 1247 L350 1285 L305 1247 L260 1285 L215 1247 L170 1285 L125 1247Z" fill="${C.paper}" ${ink}/><path d="M176 955 H883" stroke="${C.ink}" stroke-width="3" stroke-dasharray="8 9"/></svg><img id="finish-logo" class="clip finish-logo" src="assets/product/logo.png" data-start="0" data-duration="${finishDur}" alt="Original Circuit Market logo"><h1 class="finish-brand" data-var-text="brand">SAMPLE ERP</h1><p class="finish-line">A little clarity<br>for a busy day.</p><p class="finish-cta" data-var-text="cta">EXPLORE THE DEMO ↗</p><p class="finish-demo">Circuit Market demo</p><p class="finish-credit">“Electro Cabello” · Kevin MacLeod<br>incompetech.com · CC BY 4.0</p></div>`,
`#root{background:${C.green}}.finish-paper{position:absolute;inset:0}.finish-logo{position:absolute;left:177px;top:330px;width:102px;height:102px}.finish-brand{position:absolute;left:175px;top:481px;font:116px/.95 'League Gothic';margin:0;letter-spacing:-1px}.finish-line{position:absolute;left:178px;top:655px;margin:0;font:700 52px/1.12 'Receipt Sans';letter-spacing:-2px}.finish-cta{position:absolute;left:178px;top:848px;font:62px/1 'League Gothic';margin:0}.finish-demo{position:absolute;left:178px;top:989px;font-size:30px;margin:0}.finish-credit{position:absolute;left:178px;top:1110px;font-size:28px;line-height:1.4;margin:0}`,
`tl.fromTo('.finish-paper',{scale:3,y:0},{scale:1,y:0,transformOrigin:'540px 900px',duration:.55,ease:'power4.out'},0);
tl.fromTo('.finish-brand,.finish-line,.finish-cta,.finish-demo,.finish-credit,.finish-logo',{opacity:0},{opacity:1,duration:.18},.3);`);

let music=false;try{await access(timing.musicFile);music=true}catch{}
const audio=music?`<audio id="music-bed" class="clip" src="${timing.musicFile}" data-start="0" data-duration="${total}" data-media-start="${timing.musicOffset}" data-volume="1" data-timeline-role="music" data-track-index="3"></audio>`:'';
const sfx=[['paper-burst','whoosh-short.mp3',.15,.4,.38],['grip-hit','impact-bass-1.mp3',cuts[2]+.03,.65,.22],['sale-tick','click-soft.mp3',cuts[3]+1.56,.3,.4],['bag-land','click-soft.mp3',cuts[4]+.7,.3,.35]].map(([id,file,t,d,v])=>`<audio id="${id}" class="clip" src="assets/sfx/${file}" data-start="${t}" data-duration="${d}" data-volume="${v}" data-track-index="4"></audio>`).join('\n');
await writeFile('index.html',`<!doctype html>\n<html lang="en" data-resolution="portrait" data-composition-variables='[{"id":"brand","type":"string","label":"Brand name","default":"SAMPLE ERP"},{"id":"cta","type":"string","label":"Call to action","default":"EXPLORE THE DEMO ↗"}]'>\n<head><meta charset="utf-8"><meta name="viewport" content="width=1080,height=1920"><title>Receipt Avalanche — Circuit Market</title><script src="assets/vendor/gsap.min.js"></script><style>*{box-sizing:border-box}html,body{width:1080px;height:1920px;margin:0;overflow:hidden;background:${C.paper}}#root,.clip{position:absolute;inset:0}</style></head>\n<body><div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-fps="30" data-width="1080" data-height="1920">\n${timing.sceneIds.map((id,i)=>`<div id="${id}" class="clip" data-composition-id="${id}" data-composition-src="compositions/${id}.html" data-start="${cuts[i]}" data-duration="${cuts[i+1]-cuts[i]}" data-width="1080" data-height="1920" data-track-index="1" data-track-kind="graphics"></div>`).join('\n')}\n${audio}\n${sfx}\n</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>\n`);
console.log(`Built six editable scenes / ${total}s. Music on disk: ${music}. Timing status: ${timing.status}.`);
