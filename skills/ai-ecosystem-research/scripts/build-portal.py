"""Build a private, relocatable report home. Standard library only."""
import argparse
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

LABELS = {'weekly': '周报', 'monthly': '月报', 'deep-dive': '专题'}

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def records(root):
    legacy_path = root / 'portal-legacy.json'
    legacy = read_json(legacy_path) if legacy_path.exists() else {}
    found, warnings = [], []
    for report in sorted((root / 'runs').rglob('report-dark.html')):
        if not report.resolve().is_relative_to(root.resolve()):
            warnings.append('Skipped report outside research root'); continue
        rel = report.relative_to(root).as_posix()
        folder = report.parent
        try:
            run = read_json(folder / 'run.json') if (folder / 'run.json').exists() else {}
            old = legacy.get(rel, {})
            data = {**old, **run}
            mode = data.get('mode')
            if mode not in LABELS:
                warnings.append('Unclassified: ' + rel); continue
            acceptance = folder / 'acceptance.json'
            # Explicit modern draft/failure always wins over a legacy registration.
            if acceptance.exists():
                a = read_json(acceptance)
                ready = a.get('artifact_status') == 'ready' and a.get('delivery_ready') is True
                status = '已交付' if ready else '草稿／未通过验收'
            else:
                ready = old.get('delivered') is True
                status = old.get('label', '未登记交付') if ready else '草稿／未通过验收'
            start = str(data.get('window_start', ''))[:10]
            end = str(data.get('window_end', data.get('window_end_exclusive', '')))[:10]
            period = start + ' — ' + (datetime.fromisoformat(end) - timedelta(days=1)).date().isoformat() if start and end else '原报告所示研究窗口'
            created = str(data.get('revision_at') or data.get('created_at') or data.get('retrieved_date') or old.get('date') or end)
            found.append({'path': rel, 'href': quote(rel, safe='/'), 'mode': mode,
                          'period': period, 'window_end': end, 'created_at': created,
                          'date': created[:10], 'status': status, 'ready': ready,
                          'title': old.get('title') or ('AI 生态' + LABELS[mode]),
                          'revision_of': data.get('revision_of')})
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.append('Invalid metadata: ' + rel + ' (' + type(exc).__name__ + ')')
    found.sort(key=lambda r: (r['window_end'], r['created_at'], r['path']), reverse=True)
    return found, warnings

def render(items):
    esc = html.escape
    cards = []
    for mode in ('weekly', 'monthly'):
        latest = next((r for r in items if r['mode'] == mode and r['ready']), None)
        if latest:
            cards.append(f'<article><p class="eyebrow">最新{LABELS[mode]}</p><h2>{esc(latest["period"])}</h2><p>{esc(latest["title"])}</p><p class="muted">报告日期 {esc(latest["date"])} · {esc(latest["status"])}</p><a class="button" href="{latest["href"]}">阅读{LABELS[mode]} <span aria-hidden="true">→</span></a></article>')
        else:
            cards.append(f'<article><p class="eyebrow">最新{LABELS[mode]}</p><h2>尚无已交付报告</h2><p>完成研究与验收后，这里会出现阅读入口。</p></article>')
    def table(rows):
        if not rows: return '<p class="muted">暂无记录。</p>'
        body = ''.join(f'<tr><td>{LABELS[r["mode"]]}</td><td>{esc(r["period"])}</td><td>{esc(r["date"])}</td><td>{esc(r["status"])}</td><td><a href="{r["href"]}">{esc(r["title"])} →</a></td></tr>' for r in rows)
        return '<div class="scroll" tabindex="0" aria-label="历史报告，可横向滚动"><table><thead><tr><th>类型</th><th>研究窗口</th><th>报告日期</th><th>版本说明</th><th>阅读</th></tr></thead><tbody>'+body+'</tbody></table></div>'
    delivered = table([r for r in items if r['ready']])
    drafts = table([r for r in items if not r['ready']])
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI 生态报告中心</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#181818;color:#ececec;font:18px/1.8 "Microsoft YaHei",system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:48px 32px 80px}h1{font-size:42px;line-height:1.3;margin:12px 0 18px}h2{font-size:26px;line-height:1.45;margin:12px 0}h3{font-size:28px;margin:52px 0 16px}p{margin:10px 0}.muted{color:#bcbcbc}.intro{max-width:850px}.cards{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:32px 0}article{background:#242424;border:1px solid #494949;border-radius:14px;padding:28px;display:flex;flex-direction:column;align-items:start}.eyebrow{font-size:19px;font-weight:bold;color:#cfcfcf}a{color:#efefef;text-underline-offset:5px}a:focus-visible,summary:focus-visible{outline:3px solid white;outline-offset:4px}.button{display:inline-block;margin-top:auto;padding:12px 22px;background:#e3e3e3;color:#202020;border-radius:8px;text-decoration:none;font-weight:bold}.scroll{overflow-x:auto;border:1px solid #484848;border-radius:10px}table{border-collapse:collapse;width:100%;min-width:850px}th,td{padding:16px;text-align:left;vertical-align:top;border-bottom:1px solid #464646}th{background:#333333}tbody tr:nth-child(even){background:#242424}details{margin-top:32px;padding:20px;background:#222;border-radius:10px}summary{cursor:pointer;font-size:19px}footer{margin-top:36px;color:#aaa;font-size:15px}@media(max-width:720px){main{padding:28px 18px}.cards{grid-template-columns:1fr}h1{font-size:34px}h2{font-size:24px}article{padding:22px}}@media print{body{background:white;color:black}.button,a{color:black}article,th,details{background:white}}
</style></head><body><main><p class="eyebrow">你的固定阅读入口</p><h1>AI 生态报告中心</h1><p class="intro muted">周报发现新变化，月报回访与修正判断。以后从这里打开最新报告，也可以按研究窗口查阅历史版本。</p><div class="cards">'''+''.join(cards)+'''</div><p class="muted">“最新”指已生成并交付的最近一期，不代表今天的新报告。新报告完成后首页更新；如果一直开着此页，请刷新。</p><h3>历史报告</h3><p class="muted">保留每期原文和修订版；窄窗口可左右滚动表格。</p>'''+delivered+'''<details><summary>草稿与未通过验收的版本</summary><p class="muted">保留作为研究记录，不作为最新报告推荐。</p>'''+drafts+'''</details><footer>本机私人报告入口 · 可收藏此页。网页与报告使用相对链接；迁移时复制整个 research 文件夹。本入口不会将私人报告发布到 GitHub，也不会自动成为 ChatGPT 网页中的云端页面。</footer></main></body></html>'''

def build(root):
    root = Path(root).resolve()
    items, warnings = records(root)
    root.mkdir(parents=True, exist_ok=True)
    output = root / 'index.html'
    temp = root / 'index.html.tmp'
    temp.write_text(render(items), encoding='utf-8'); temp.replace(output)
    (root / 'portal-index.json').write_text(json.dumps({'reports':items,'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8')
    return items, warnings

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-dir', type=Path, required=True)
    args=parser.parse_args()
    rows,warnings=build(args.research_dir)
    print(json.dumps({'reports':len(rows),'delivered':sum(r['ready'] for r in rows),'warnings':warnings},ensure_ascii=False))
