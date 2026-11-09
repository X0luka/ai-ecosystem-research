const fs = require('node:fs');
const path = require('node:path');
const {marked} = require('./vendor/marked.cjs');
const args = process.argv.slice(2), opts = {};
for(let i=0;i<args.length;i+=2){
 if(!['--input','--output','--theme','--title','--lang'].includes(args[i]) || args[i+1]===undefined) throw new Error('Usage: node render-report.cjs --input report.md --output report.html [--theme dark|light] [--title title]');
 opts[args[i].slice(2)]=args[i+1];
}
if(!opts.input || !opts.output) throw new Error('--input and --output are required');
if(opts.theme && !['dark','light'].includes(opts.theme)) throw new Error('--theme must be dark or light');
const input=path.resolve(opts.input), target=path.resolve(opts.output);
if(input===target) throw new Error('Output must not overwrite Markdown input');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const md=fs.readFileSync(input,'utf8');
const title=opts.title || (md.match(/^#\s+(.+)$/m)||[])[1] || path.basename(input,'.md');
marked.use({renderer:{html({text}){return /^<br\s*\/?\s*>$/i.test(text.trim()) ? "<br>" : esc(text);}},walkTokens(token){
 if(token.type==='link'||token.type==='image'){
  const url=token.href.trim();
  if(/^(?:javascript|vbscript|data):/i.test(url.replace(/[\x00-\x20]/g,''))) token.href='#';
  else if(!/^(?:[a-z][a-z0-9+.-]*:|#|\/\/)/i.test(url)){
   const [file,fragment]=url.split('#');
   token.href=path.relative(path.dirname(target),path.resolve(path.dirname(input),file)).split(path.sep).join('/')+(fragment?'#'+fragment:'');
  }
 }
}});
let html=marked.parse(md,{gfm:true});
let seq=0,toc=[];
html=html.replace(/<h([1-4])>([\s\S]*?)<\/h\1>/g,(_,lev,title)=>{
 const id='section-'+(++seq); if(lev==='2')toc.push(`<a href="#${id}">${title}</a>`);
 return `<h${lev} id="${id}">${title}</h${lev}>`;
});
html=html.replace(/<table>/g,'<div class="table-scroll" tabindex="0"><table>').replace(/<\/table>/g,'</table></div>');
html=html.replace(/(<h4[^>]*>[^<]+<\/h4>)\s*(<p>[\s\S]*?<\/p>)\s*(<p>[\s\S]*?<\/p>)/g,'<article class="project">$1$2$3</article>');
html=html.replace(/<div class="table-scroll" tabindex="0"><table>\s*<thead>\s*<tr>\s*<th>项目／类别<\/th>/g,'<p class="table-hint">按行看项目，按列作比较 · 窄窗口可横向滚动，首列与表头固定</p><div class="table-scroll comparison" tabindex="0" aria-label="项目横向比较"><table><thead><tr><th>项目／类别</th>');
html=html.replace(/<div class="table-scroll" tabindex="0"><table>([\s\S]*?)<\/table><\/div>/g,(all,body)=>body.includes('<th>项目介绍：具体做什么</th>')?'<div class="table-scroll discovery" tabindex="0" aria-label="榜单与项目导读"><table>'+body+'</table></div>':all);
const css=`
.project{margin:22px 0;padding:20px 0;border-bottom:1px solid #e2e8eb}.project h4{border:0;margin:0 0 10px;padding:0;font-size:21px}.project p{margin:8px 0;line-height:1.8}.project p:last-child{color:#425865}.followups{border:1px solid #dce4e8;background:#f7f9fa;padding:14px 20px;margin:24px 0 40px;border-radius:6px}.followups summary{cursor:pointer;font-weight:600;font-size:17px}.followups[open] summary{margin-bottom:18px}.followups li{line-height:1.8;margin:16px 0}
:root{color-scheme:light;--ink:#182a38;--blue:#155d87;--gold:#895b16}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f4ef;color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;font-size:18px;line-height:1.9}
.mast{background:#132e40;color:#fff;padding:20px 32px;font-size:14px;letter-spacing:.12em}.layout{display:grid;grid-template-columns:260px minmax(0,1080px);max-width:1420px;margin:auto;gap:34px;padding:36px 28px}
nav{position:sticky;top:24px;height:calc(100vh - 48px);overflow:auto;font-size:15px;line-height:1.6;padding:12px 12px 20px 0}nav strong{font-size:19px;display:block;margin-bottom:18px}nav a{display:block;padding:9px 10px;margin:4px 0;color:#284b61;border-radius:5px;text-decoration:none}nav a:hover{background:#e0e9ed}
main{min-width:0;background:#fff;padding:48px 54px;border:1px solid #e0e3e3;box-shadow:0 5px 20px #122c4007}
h1{font-size:42px;line-height:1.35;letter-spacing:-.02em;margin:0 0 28px;color:#123a54}h2{font-size:30px;line-height:1.45;margin:76px 0 28px;padding:22px 0 14px;border-top:4px solid #1d5a7a;color:#123a54;scroll-margin-top:20px}h3{font-size:23px;line-height:1.5;margin:44px 0 20px;padding-left:14px;border-left:4px solid #8b9faa;color:#21485f;scroll-margin-top:20px}h4{font-size:20px;line-height:1.5;margin:36px 0 14px;color:#152f42;border-bottom:1px solid #dfe7eb;padding-bottom:9px;scroll-margin-top:20px}
p{margin:16px 0}strong{font-weight:700}a{color:#14618c;text-underline-offset:3px;overflow-wrap:anywhere}li{margin:12px 0}code{font-size:.87em;background:#eef2f4;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}.fact,.analysis,.watch{padding:15px 18px;border-radius:4px;line-height:1.85}.fact{background:#eff7fb;border-left:4px solid var(--blue)}.analysis{background:#fcf7ec;border-left:4px solid var(--gold)}.watch{background:#f0f5f0;border-left:4px solid #57745e}
.table-scroll{overflow-x:auto;margin:24px 0;border:1px solid #dbe2e7;border-radius:5px}table{border-collapse:collapse;width:100%;font-size:18px;line-height:1.7;min-width:680px}th{background:#e8f0f4;text-align:left;color:#123a54;font-weight:700}td,th{padding:14px 16px;vertical-align:top;border-bottom:1px solid #dbe2e7}tbody tr:nth-child(even){background:#fafbfc}td:first-child{min-width:115px}td{overflow-wrap:anywhere}blockquote{border-left:4px solid #8398a5;padding-left:20px;margin-left:0;color:#465d6c}
.reading-tools{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}.reading-tools button{font:inherit;font-size:15px;border:1px solid #b8c8d3;background:#fff;border-radius:5px;padding:7px 10px;color:#1c4963;cursor:pointer}.note{font-size:14px;color:#647781}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:15px;border-bottom:1px solid #dce4e8;padding-bottom:20px;margin-bottom:28px}.legend span:nth-child(1){color:var(--blue)}.legend span:nth-child(2){color:var(--gold)}
@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:20px;gap:16px}nav{position:static;height:auto;max-height:290px;padding:12px;border:1px solid #d6e0e6}nav a{display:inline-block;margin-right:7px}main{padding:32px}h1{font-size:36px}}
@media(max-width:600px){.layout{padding:12px}main{padding:24px 20px}h1{font-size:34px}h2{font-size:29px;margin-top:54px}h3{font-size:23px}body{font-size:18px}.mast{padding:16px 22px}.fact,.analysis,.watch{padding:13px}}
@media print{body{background:#fff}nav,.mast,.reading-tools{display:none}.layout{display:block;padding:0;max-width:none}main{border:0;padding:0;box-shadow:none}h2{break-before:page}h2,h3,h4{break-after:avoid}.table-scroll{overflow:visible}table{min-width:0;font-size:11pt}body{font-size:12pt}.fact,.analysis,.watch{break-inside:avoid}a{color:inherit}h1{font-size:28pt}}
/* Comparison layout: preserve semantic columns and strong section hierarchy. */
.layout{grid-template-columns:220px minmax(0,1520px);max-width:1820px;gap:24px;padding:28px 22px}main{padding:40px 34px}h2{font-size:32px;border-top-width:5px}h3{font-size:24px;padding:14px 18px;background:#edf3f7;border-left:5px solid #245e7d}h4{font-size:22px;margin:34px 0 18px;border-bottom:2px solid #9fb2bf}
.table-hint{font-size:14px;color:#566d7b;margin-bottom:8px}.comparison{max-height:80vh;isolation:isolate}.comparison table{min-width:1240px;table-layout:fixed;border-collapse:separate;border-spacing:0}.comparison th:first-child{width:150px}.comparison th:nth-child(2){width:270px}.comparison th:nth-child(3){width:270px}.comparison th:nth-child(4){width:280px}.comparison th:nth-child(5){width:270px}.comparison th{position:sticky;top:0;z-index:2;background:#e9f1f7;border-bottom:2px solid #7895a8;font-size:18px}.comparison th:nth-child(3),.comparison th:nth-child(4){background:#f4eedf}.comparison th:nth-child(5){background:#e9f0e9}.comparison td:first-child{position:sticky;left:0;background:#f3f6f8;border-right:1px solid #ccd7de;z-index:1;font-size:16px;color:#516875}.comparison td:first-child strong{font-size:19px;color:#143b54}.comparison th:first-child{left:0;z-index:3}.comparison td{padding:18px;line-height:1.8}.comparison td a{font-size:15px}.comparison tbody tr:hover td{background:#f5f8fa}
@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:18px}main{padding:30px 22px}}@media(max-width:600px){.layout{padding:10px}main{padding:24px 14px}h2{font-size:29px}h3{font-size:23px}.comparison{max-height:75vh}}
`;
const themeCSS=`
.discovery{max-height:82vh}.discovery table{min-width:1260px;border-collapse:separate;border-spacing:0}.discovery th{position:sticky;top:0;z-index:2}.discovery th:first-child{width:65px}.discovery th:nth-child(2){min-width:160px}.discovery th:nth-last-child(2),.discovery th:last-child{width:32%}.discovery td:nth-child(2){min-width:160px;font-weight:600}.discovery td{padding:18px;line-height:1.85}.discovery td:first-child{min-width:60px}.discovery th:nth-last-child(2){background:#e9f1f7}.discovery th:last-child{background:#f4eedf}
html[data-theme="dark"]{color-scheme:dark;--ink:#e5e5e5;--blue:#b8b8b8;--gold:#c6c6c6}
html[data-theme="dark"] body{background:#181818;color:#e5e5e5}
html[data-theme="dark"] main{background:#212121;border-color:#424242;box-shadow:none}
html[data-theme="dark"] .mast{background:#161616;color:#cfcfcf}
html[data-theme="dark"] h1,html[data-theme="dark"] h2{color:#efefef;border-color:#9f9f9f}
html[data-theme="dark"] h3{color:#e8e8e8;background:#333333;border-color:#b0b0b0}
html[data-theme="dark"] h4{color:#e8e8e8;border-color:#737373}
html[data-theme="dark"] nav a{color:#d1d1d1}html[data-theme="dark"] nav a:hover{background:#383838}
html[data-theme="dark"] a{color:#c3c3c3}html[data-theme="dark"] .note,html[data-theme="dark"] .table-hint{color:#bdbdbd}
html[data-theme="dark"] .reading-tools button{background:#313131;color:#e8e8e8;border-color:#7e7e7e}
html[data-theme="dark"] code{background:#383838;color:#eaeaea}
html[data-theme="dark"] .table-scroll{border-color:#505050}
html[data-theme="dark"] th{background:#393939;color:#eeeeee;border-color:#626262}
html[data-theme="dark"] .discovery th:nth-last-child(2){background:#393939;color:#eeeeee}
.discovery th:first-child{width:100px;min-width:100px;white-space:nowrap;padding:14px 12px}
.discovery td:nth-child(3),.discovery table:has(th:nth-child(6)) td:nth-child(4){white-space:nowrap;min-width:85px}
html[data-theme="dark"] td{background:#212121;color:#e5e5e5;border-color:#494949}
html[data-theme="dark"] tbody tr:nth-child(even) td{background:#282828}
html[data-theme="dark"] .comparison th:nth-child(3),html[data-theme="dark"] .comparison th:nth-child(4),html[data-theme="dark"] .discovery th:last-child{background:#353535;color:#e4e4e4}
html[data-theme="dark"] .comparison th:nth-child(5){background:#383838;color:#e4e4e4}
html[data-theme="dark"] .comparison td:first-child{background:#313131;color:#cccccc;border-color:#626262}
html[data-theme="dark"] .comparison td:first-child strong{color:#eeeeee}
html[data-theme="dark"] .comparison tbody tr:hover td{background:#3b3b3b}
html[data-theme="dark"] blockquote{color:#cfcfcf;border-color:#848484}
html[data-theme="dark"] .fact{background:#333333}html[data-theme="dark"] .analysis{background:#333333}html[data-theme="dark"] .watch{background:#363636}
@media print{html[data-theme="dark"] body,html[data-theme="dark"] main,html[data-theme="dark"] td{background:white;color:#252525}.comparison,.discovery{max-height:none}}
`;

const discoveryCSS='/* Shorter discovery tables use semantic text columns, not the six-column metric layout. */\n.discovery table:has(th:nth-child(4):last-child){table-layout:fixed;min-width:1120px}\n.discovery table:has(th:nth-child(4):last-child) th:first-child{width:22%;white-space:normal}\n.discovery table:has(th:nth-child(4):last-child) th:nth-child(2){width:13%;min-width:0}\n.discovery table:has(th:nth-child(4):last-child) th:nth-child(3){width:32%}\n.discovery table:has(th:nth-child(4):last-child) th:nth-child(4){width:33%}\n.discovery table:has(th:nth-child(4):last-child) td{white-space:normal;min-width:0;font-weight:400}\n.discovery table:has(th:nth-child(3):last-child){table-layout:fixed;min-width:1000px}\n.discovery table:has(th:nth-child(3):last-child) th:first-child{width:22%;white-space:normal}\n.discovery table:has(th:nth-child(3):last-child) th:nth-child(2){width:38%;min-width:0}\n.discovery table:has(th:nth-child(3):last-child) th:nth-child(3){width:40%}\n.discovery table:has(th:nth-child(3):last-child) td{white-space:normal;min-width:0;font-weight:400}\n';
const printCSS='@media print{html[data-theme] h1,html[data-theme] h2,html[data-theme] h3,html[data-theme] h4,html[data-theme] th,html[data-theme] td,html[data-theme] td:first-child,html[data-theme] td:first-child strong,html[data-theme] a{color:#222!important;background:#fff!important}th,td:first-child{position:static!important}}';
const dark=(opts.theme||'dark')==='dark';
let output=`<!doctype html><html lang="${esc(opts.lang||'zh-CN')}" data-theme="${dark?'dark':'light'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${css}${themeCSS}${discoveryCSS}${printCSS}</style></head><body><div class="mast">${esc(title)}</div><div class="layout"><nav aria-label="报告目录"><strong>阅读目录</strong><div class="reading-tools"><button id="theme-toggle" aria-pressed="${dark}" onclick="const d=document.documentElement;d.dataset.theme=d.dataset.theme==='dark'?'light':'dark';this.textContent=d.dataset.theme==='dark'?'切换浅色':'切换深色';this.setAttribute('aria-pressed',String(d.dataset.theme==='dark'))">${dark?'切换浅色':'切换深色'}</button><button onclick="document.querySelector('main').style.fontSize='20px'">放大正文</button><button onclick="document.querySelector('main').style.fontSize='18px'">标准字号</button></div>${toc.join('')}<p class="note">项目按行、分析维度按列。比较表固定首列与表头，可横向滚动。</p></nav><main>${html}</main></div></body></html>`;
fs.mkdirSync(path.dirname(target),{recursive:true});
fs.writeFileSync(target,output,'utf8');
console.log(JSON.stringify({output:target,theme:dark?'dark':'light',sections:toc.length}));
