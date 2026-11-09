// Email clients need inline styles and real HTML tables, not Markdown or browser UI.
const fs = require('node:fs');
const {marked} = require('./vendor/marked.cjs');
const [input, output] = process.argv.slice(2);
if (!input || !output || input === output) throw Error('Usage: node render-email.cjs input.md output.html');
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
marked.use({renderer: {
  html({text}) { return /^<br\s*\/?\s*>$/i.test(text.trim()) ? '<br>' : esc(text); },
  link({href, tokens}) {
    const label = this.parser.parseInline(tokens);
    return /^https?:\/\//i.test(href) ? `<a href="${esc(href)}">${label}</a>` : label;
  },
  image({text}) { return esc(text); }
}});
const styles = {
 h1:'font-size:32px;line-height:1.4;margin:0 0 28px;color:#f5f5f5;',
 h2:'font-size:26px;line-height:1.5;margin:48px 0 20px;padding:16px 0 12px;border-top:3px solid #888888;color:#f5f5f5;',
 h3:'font-size:22px;line-height:1.5;margin:32px 0 16px;color:#eeeeee;',
 h4:'font-size:20px;margin:24px 0 12px;color:#eeeeee;',
 p:'margin:14px 0;line-height:1.85;',
 table:'border-collapse:collapse;width:100%;margin:20px 0;font-size:18px;line-height:1.7;',
 th:'background-color:#393939;color:#f5f5f5;border:1px solid #666666;padding:12px;text-align:left;vertical-align:top;',
 td:'background-color:#242424;color:#e5e5e5;border:1px solid #555555;padding:12px;text-align:left;vertical-align:top;word-break:break-word;',
 a:'color:#dddddd;text-decoration:underline;word-break:break-all;',
 li:'margin:10px 0;',
 code:'background-color:#383838;color:#eeeeee;padding:2px 4px;',
 pre:'white-space:pre-wrap;background-color:#303030;padding:16px;',
 blockquote:'border-left:3px solid #888888;margin:16px 0;padding-left:16px;color:#cccccc;'
};
let body = marked.parse(fs.readFileSync(input,'utf8'),{gfm:true});
for (const [tag,style] of Object.entries(styles)) body=body.replace(new RegExp(`<${tag}(?=[ >])`,'g'), `<${tag} style="${style}"`);
fs.writeFileSync(output,`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0;background-color:#212121;color:#e5e5e5;font-family:Arial,'Microsoft YaHei',sans-serif;font-size:18px;line-height:1.85;"><div style="background-color:#212121;color:#e5e5e5;padding:24px;max-width:1120px;margin:auto;"><p style="color:#cccccc;font-size:15px;">本邮件含完整报告和表格。若邮箱折叠长正文或手机显示宽表不便，请下载 report-dark.html 附件，用浏览器阅读。</p>${body}</div></body></html>`,'utf8');
