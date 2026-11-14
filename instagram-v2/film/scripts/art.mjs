// Canonical original vector artwork. All scenes share these exact silhouettes.
// Units match the 1080 x 1920 composition; the drawing uses round ink contours.
export const C={ink:'#1b2520',green:'#27755d',deep:'#153e30',paper:'#fffdf7',orange:'#f3693b',lime:'#d9ed9c',skin:'#e6a17d'};
export const ink=`stroke="${C.ink}" stroke-width="5.5" stroke-linejoin="round" stroke-linecap="round"`;

export function receipt(prefix,{width=142,height=230}={}){
  const w=width,h=height;
  let teeth=`M0 0 H${w} V${h-12}`;
  for(let i=0;i<10;i++)teeth+=` l${-w/20} 12 l${-w/20} -12`;
  teeth+=' Z';
  return `<g id="${prefix}-receipt"><path d="${teeth}" fill="${C.paper}" ${ink}/><path d="M22 32 H${w-22}" stroke="${C.ink}" stroke-width="9"/><path d="M22 55 H${w-37} M22 80 H${w-22} M22 100 H${w-45} M22 ${h-68} H${w-22}" stroke="${C.ink}" stroke-width="4"/><path d="M22 ${h-43} H${w-42}" stroke="${C.green}" stroke-width="10"/></g>`;
}

export function printer(prefix){
 return `<g id="${prefix}-printer" ${ink}>
  <path d="M-116 -60 L96 -60 L132 -16 L132 94 L-116 94Z" fill="${C.deep}"/>
  <path d="M-116 -60 L-85 -112 L69 -112 L96 -60Z" fill="${C.green}"/>
  <rect x="-116" y="-60" width="212" height="154" rx="17" fill="${C.green}"/>
  <rect x="-91" y="-25" width="164" height="32" rx="6" fill="${C.ink}"/>
  <path d="M-74 -10 H57" stroke="${C.paper}" stroke-width="4"/>
  <circle cx="68" cy="-77" r="7" fill="${C.lime}" stroke="none"/>
  <path d="M-86 49 H-37 M-86 62 H-37 M-86 75 H-37" stroke="${C.deep}" stroke-width="5"/>
  <rect x="29" y="40" width="42" height="27" rx="6" fill="${C.lime}"/>
 </g>`;
}

export const GRIP={x:650,y:1010};
export const chaosPath='M400 1130 C400 970 230 1010 270 860 C300 710 680 850 720 700 C750 560 390 610 480 810 C570 1010 830 800 650 1010';
export const tidyPath='M400 1130 C400 1080 400 1020 400 970 C400 920 470 910 520 910 C570 910 610 910 650 930 C670 950 670 980 650 1010';

export function armTo(x=GRIP.x,y=GRIP.y){
 const sx=694,sy=960,upper=57,lower=65,wx=x+22,wy=y+13;
 const dx=wx-sx,dy=wy-sy,d=Math.hypot(dx,dy),ux=dx/d,uy=dy/d;
 const a=(upper*upper-lower*lower+d*d)/(2*d),h=Math.sqrt(Math.max(0,upper*upper-a*a));
 const ex=sx+ux*a+uy*h,ey=sy+uy*a-ux*h;
 return `M${sx} ${sy} L${ex.toFixed(3)} ${ey.toFixed(3)} L${wx} ${wy}`;
}
export function pathToGrip(path,x=GRIP.x,y=GRIP.y){return path.replace(/650 1010$/,`${x} ${y}`);}

export function pinchHand(prefix,mirror=false){
 return `<g id="${prefix}-hand"${mirror?' transform="scale(-1 1)"':''} stroke="${C.ink}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"><path d="M5 -9 L-6 -12 L-15 -22 Q-20 -26 -24 -21 Q-28 -17 -22 -10 L-19 -7 L-28 -13 Q-33 -15 -35 -9 L-37 -2 Q-39 4 -32 9 L-20 18 Q-9 25 3 13 L9 5Z" fill="${C.skin}"/><path d="M-19 -7 L-8 2 M-29 -5 L-21 3 M-25 4 L-17 11" fill="none" stroke-width="2.5"/></g>`;
}

export function bagReceipt(){
 return `<g stroke="${C.ink}" stroke-width="2.5" stroke-linejoin="round"><path d="M531 1060 H551 V1100 L547 1104 L543 1100 L539 1104 L535 1100 L531 1104Z" fill="${C.paper}"/><path d="M536 1068 H546 M536 1076 H546 M536 1084 H542" fill="none"/></g>`;
}

export function frontHand(prefix){
 return `<g class="${prefix}-grip"><g transform="translate(${GRIP.x+22} ${GRIP.y+13})">${pinchHand(prefix+'-front')}</g></g>`;
}

export function printerPaper(prefix){
 const edge=Array.from({length:10},()=> ' l7.1 -12 l7.1 12').join('');
 return `<g id="${prefix}-printer-paper" ${ink}><path d="M-72 -10 V-192${edge} V-10Z" fill="${C.paper}"/><path d="M-50 -168 H46" stroke-width="8"/><path d="M-50 -145 H35 M-50 -124 H46 M-50 -103 H17 M-50 -65 H46" stroke-width="4"/><path d="M-50 -39 H25" stroke="${C.green}" stroke-width="9"/></g>`;
}

export function ribbon(prefix,path=chaosPath){
 return `<g id="${prefix}-ribbon" fill="none" stroke-linecap="butt" stroke-linejoin="round">
  <path class="${prefix}-ribbon-edge" d="${path}" stroke="${C.ink}" stroke-width="91" data-layout-ignore/>
  <path class="${prefix}-ribbon-paper" d="${path}" stroke="${C.paper}" stroke-width="80" data-layout-ignore/>
  <path class="${prefix}-ribbon-print" d="${path}" stroke="${C.ink}" stroke-width="36" stroke-dasharray="3 17" data-layout-ignore/>
 </g>`;
}

export function owner(prefix,{frontHandVisible=true}={}){
 return `<g id="${prefix}-owner" ${ink}>
  <g class="${prefix}-legs"><path d="M684 1134 L676 1254 L714 1254 L730 1156 L750 1254 L789 1254 L774 1134Z" fill="${C.deep}"/><path d="M676 1249 L662 1270 L713 1270 L715 1249 M750 1249 L749 1270 L806 1270 L789 1249" fill="${C.ink}"/></g>
  <path d="M690 931 Q733 913 774 937 L792 1148 Q735 1166 677 1148 L673 999Z" fill="${C.green}"/>
  <path d="M710 940 H755 L757 1015 H765 L774 1145 Q731 1154 691 1145 L699 1015 H707Z" fill="${C.paper}"/>
  <path d="M705 1070 H757 V1118 H705Z" fill="${C.lime}"/>
  <g class="${prefix}-head"><path d="M716 916 L717 940 Q735 950 751 935 L748 906Z" fill="${C.skin}"/>
   <path d="M678 847 Q677 796 722 788 Q775 787 783 827 L780 877 Q775 919 735 924 Q692 924 682 886Z" fill="${C.skin}"/>
   <path d="M680 862 Q660 839 671 812 Q681 779 717 777 Q748 768 771 789 Q792 798 789 830 Q766 842 749 816 Q720 839 689 828 L688 864Z" fill="${C.ink}"/>
   <path d="M680 857 Q663 850 665 868 Q665 884 685 887" fill="${C.skin}"/>
   <path d="M735 854 L731 873 L742 874" fill="none" stroke-width="4"/>
   <ellipse class="${prefix}-eye-left" cx="712" cy="851" rx="4" ry="7" fill="${C.ink}" stroke="none"/><ellipse class="${prefix}-eye-right" cx="760" cy="849" rx="4" ry="7" fill="${C.ink}" stroke="none"/>
   <path class="${prefix}-brow-left" d="M698 833 Q709 830 720 827" fill="none" stroke-width="4"/><path class="${prefix}-brow-right" d="M750 827 Q761 830 772 834" fill="none" stroke-width="4"/>
   <path class="${prefix}-mouth" d="M722 894 Q735 881 749 891" fill="none" stroke-width="4"/>
   <path d="M694 878 L704 881 M760 877 L770 875" stroke="#ce7958" stroke-width="5"/>
  </g>
  <g class="${prefix}-rear-arm" fill="none" stroke-linecap="butt"><path d="M774 956 L797 998 L777 1038" stroke="${C.ink}" stroke-width="31"/><path d="M774 956 L797 998 L777 1038" stroke="${C.green}" stroke-width="20"/></g>
  <g transform="translate(777 1038) rotate(-90)">${pinchHand(prefix+'-rest')}</g>
  <g class="${prefix}-front-arm" fill="none" stroke-linecap="butt"><path class="${prefix}-arm-edge" d="${armTo()}" stroke="${C.ink}" stroke-width="31"/><path class="${prefix}-arm-shirt" d="${armTo()}" stroke="${C.green}" stroke-width="20"/></g>
  ${frontHandVisible?frontHand(prefix):''}
 </g>`;
}

export function shopBack(prefix){
 return `<g id="${prefix}-shop-back" ${ink}>
  <path d="M175 1255 H903" stroke="#d3d7ca" stroke-width="22"/>
  <path d="M230 748 H850 V1244 H230Z" fill="${C.paper}"/>
  <path d="M230 748 H850 V797 H230Z" fill="${C.deep}"/>
  <rect x="257" y="832" width="290" height="300" rx="5" fill="#e5eadb"/>
  <path d="M257 975 H547 M277 1113 H526" fill="none" stroke-width="10"/>
  <path d="M283 932 L295 867 H397 L409 932Z M278 939 H416" fill="${C.green}"/>
  <path d="M306 881 H386 L392 921 H299Z" fill="${C.lime}" stroke-width="3"/>
  <path d="M451 924 V879 Q451 851 477 851 Q503 851 503 879 V924 M448 896 H460 V925 H448Z M494 896 H506 V925 H494Z" fill="none" stroke-width="8"/>
  <rect x="290" y="1008" width="67" height="75" rx="5" fill="${C.orange}"/><path d="M310 1008 V1083 M290 1044 H357" stroke="${C.paper}" stroke-width="5"/>
  <rect x="389" y="1018" width="104" height="64" rx="4" fill="${C.paper}"/><path d="M408 1040 H474 M408 1058 H449" stroke-width="4"/>
  <rect x="582" y="830" width="223" height="390" rx="5" fill="#e5eadb"/>
  <path d="M203 750 L243 668 H834 L876 750Z" fill="${C.paper}"/>
  <path d="M243 668 H325 L308 750 H203Z M407 668 H489 L487 750 H390Z M571 668 H653 L667 750 H571Z M735 668 H817 L876 750 H764Z" fill="${C.green}" stroke="none"/>
  <path d="M203 750 H876 V781 Q846 808 820 781 Q794 808 768 781 Q742 808 716 781 Q690 808 664 781 Q638 808 612 781 Q586 808 560 781 Q534 808 508 781 Q482 808 456 781 Q430 808 404 781 Q378 808 352 781 Q326 808 300 781 Q274 808 248 781 Q222 808 203 781Z" fill="${C.green}"/>
  <path d="M230 645 H847 V590 H230Z" fill="${C.lime}"/>
  <text x="539" y="630" text-anchor="middle" fill="${C.ink}" stroke="none" font-family="League Gothic" font-size="44" letter-spacing="2">YOUR SHOP</text>
 </g>`;
}

export function shopFront(prefix){
 return `<g id="${prefix}-shop-front" ${ink}>
  <rect x="261" y="1126" width="557" height="120" rx="8" fill="${C.deep}"/>
  <path d="M251 1121 H830 V1145 H251Z" fill="${C.green}"/>
  <path d="M285 1174 H538" stroke="#3a6652" stroke-width="5"/>
  <path d="M856 1161 L914 1142 L952 1163 L895 1183Z" fill="#dfb78b"/>
  <path d="M856 1161 V1235 L895 1260 L895 1183Z" fill="#c99765"/>
  <path d="M895 1183 L952 1163 V1238 L895 1260Z" fill="#ebc89c"/>
  <path d="M878 1154 L917 1175 V1248" fill="none" stroke="${C.paper}" stroke-width="9"/>
  <g transform="translate(400 1130) scale(.62)">${printer(prefix+'-counter')}</g>
 </g>`;
}

export function looseReceipts(prefix){
 const poses=[[255,680,-18],[610,650,14],[340,890,-23],[740,860,24],[220,1050,10],[465,990,-15],[580,1135,9],[760,1085,-20]];
 return `<defs><clipPath id="${prefix}-leaf-region"><rect x="0" y="565" width="1080" height="745"/></clipPath></defs><g clip-path="url(#${prefix}-leaf-region)">`+poses.map(([x,y,r],i)=>`<g transform="translate(${x} ${y})"><g class="${prefix}-leaf-${i}" data-prop="receipt-leaf"><g transform="rotate(${r}) scale(.68)">${receipt(prefix+'-leaf-'+i,{width:142,height:218})}</g></g></g>`).join('')+'</g>';
}

export function svgScene(prefix,content){
 return `<svg id="${prefix}-drawing" class="drawing" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg" aria-label="Original illustration of a shop and its runaway receipt" role="img">${content}</svg>`;
}

export function customerHand(prefix){
 return `<g class="${prefix}-customer" ${ink}>
  <g class="${prefix}-customer-leg-a"><path d="M325 1100 L321 1249 L354 1249 L372 1110Z" fill="${C.deep}"/><path d="M321 1245 L305 1268 H354 V1245Z" fill="${C.ink}"/></g>
  <g class="${prefix}-customer-leg-b"><path d="M366 1100 L380 1249 H415 L401 1100Z" fill="${C.deep}"/><path d="M380 1245 V1268 H433 L415 1245Z" fill="${C.ink}"/></g>
  <path d="M323 943 Q365 928 394 949 L416 1120 Q366 1142 309 1117 L301 988Z" fill="${C.orange}"/>
  <path d="M365 923 V947 Q377 959 392 945 L387 920Z" fill="${C.skin}"/>
  <path d="M326 850 Q343 815 380 827 Q412 837 412 876 L426 891 L412 898 Q412 930 384 936 Q345 935 334 905Z" fill="${C.skin}"/>
  <path d="M327 889 Q307 861 327 836 Q352 805 383 821 Q405 822 413 846 L384 852 L367 839 L358 868 L339 872 L341 895Z" fill="${C.ink}"/>
  <path d="M338 879 Q322 872 325 890 Q328 905 345 905" fill="${C.skin}"/>
  <path d="M392 862 L407 864 M401 912 Q408 917 413 911" fill="none" stroke-width="4"/><ellipse cx="404" cy="879" rx="3.5" ry="6" fill="${C.ink}" stroke="none"/>
  <path d="M389 963 L436 1018" fill="none" stroke="${C.ink}" stroke-width="30"/><path d="M389 963 L436 1018" fill="none" stroke="${C.orange}" stroke-width="19"/>
  <path d="M436 1018 L532 1002" fill="none" stroke="${C.ink}" stroke-width="25" stroke-linecap="butt"/><path d="M436 1018 L532 1002" fill="none" stroke="${C.skin}" stroke-width="16" stroke-linecap="butt"/>
  <g transform="translate(532 1002)">${pinchHand(prefix+'-customer',true)}</g>
 </g>`;
}
