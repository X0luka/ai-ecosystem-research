"""SQLite-backed channel audit. A verified check describes a scoped observation only."""
import argparse
import html
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def defaults():
    path = Path(__file__).resolve().parents[1] / 'references/coverage-targets.json'
    return json.loads(path.read_text(encoding='utf-8'))


def make_plan(run):
    meta_file = run / 'run.json'
    meta = json.loads(meta_file.read_text(encoding='utf-8-sig')) if meta_file.exists() else {}
    targets = meta.get('coverage_targets', {} if meta.get('mode') == 'deep-dive' else defaults())
    if not isinstance(targets, dict) or any(not isinstance(x, str) or not x.strip()
                                             for pair in targets.items() for x in pair):
        raise ValueError('coverage_targets must map channel IDs to descriptions')
    routes = meta.get('coverage_routes', {})
    if not isinstance(routes, dict) or not routes.keys() <= targets.keys():
        raise ValueError('Routes must refer to declared targets')
    for prefixes in routes.values():
        if not isinstance(prefixes, list) or not all(isinstance(p, str) and urlsplit(p).scheme in ('http','https') and urlsplit(p).netloc and not urlsplit(p).query and not urlsplit(p).fragment for p in prefixes):
            raise ValueError('Expected HTTP(S) origin/path prefixes')
    return dict(targets=targets, routes=routes, run_id=meta.get('run_id', run.name),
                window=[meta.get('window_start'), meta.get('window_end', meta.get('window_end_exclusive'))])


def plan_for(db):
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='coverage_plan'").fetchone():
        return json.loads(db.execute('SELECT payload FROM coverage_plan').fetchone()[0])


def routed_targets(plan, url):
    actual = urlsplit(url)
    def matches(prefix):
        base = urlsplit(prefix)
        path = base.path.rstrip('/')
        return (actual.scheme == base.scheme and actual.netloc.lower() == base.netloc.lower()
                and (actual.path.rstrip('/') == path or actual.path.startswith(path+'/')))
    return [key for key, prefixes in (plan or {}).get('routes', {}).items() if any(matches(p) for p in prefixes)]


def window(value):
    if not isinstance(value, list) or len(value) != 2:
        return None
    try:
        start, end = map(datetime.fromisoformat, value)
        if (start.tzinfo is None) == (end.tzinfo is None) and start < end:
            return start, end
    except (ValueError, TypeError):
        pass
    return None


def is_search(c):
    query = c.get('query')
    if isinstance(query, str):
        try:
            query = json.loads(query)
        except ValueError:
            pass
    return ('search' in c['tool'].lower() or isinstance(query, dict) and 'search_query' in query
            or 'search' in urlsplit(c['url']).path.lower().split('/'))


def assess(c, review, expected):
    if c['status'] != 'ok':
        return 'unknown', c.get('error') or '请求尚未完成'
    if is_search(c) or review.get('material') == 'snippet':
        return 'partial', '搜索结果仅作发现线索'
    if not review:
        return 'partial', '尚无实际覆盖范围复核'
    if not window(expected):
        return 'unknown', '本期未定义可比较的时间窗口'
    if window(review.get('window')) != window(expected):
        return 'partial', '实际核查窗口与目标窗口不同'
    if review['material'] != 'original' or not review.get('complete'):
        return 'partial', '已记录部分材料或检查尚未完成'
    return 'verified', '原始响应已保存，研究者已复核目标及窗口'


def audit(db, run_name):
    plan = plan_for(db)
    targets = plan['targets'] if plan else defaults()
    records = {k: dict(label=v, attempts=[]) for k, v in targets.items()}
    def rows(table):
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM '+table+' ORDER BY id')]
    claims = rows('claims')
    evidence = rows('evidence')
    unassigned = []
    for c in rows('captures'):
        if 'coverage_targets' not in c:
            unassigned.append(c['id'])
        for key in c.get('coverage_targets', []):
            review = c.get('coverage_reviews', {}).get(key, {})
            state, reason = assess(c, review, plan['window'])
            if c['status'] == 'failed':
                state = 'failed'
            refs = {e['id'] for e in evidence if e['capture_id'] == c['id']}
            records[key]['attempts'].append(dict(capture=c['id'], started_at=c['started_at'], url=c.get('final_url') or c['url'],
                parent=c.get('parent_id'), status=state, reason=reason, review=review, purpose=c['purpose'],
                claims=[x['id'] for x in claims if x.get('active', True) and refs.intersection(x['evidence_ids'])]))
    for item in records.values():
        seen = {}
        item['attempts'].sort(key=lambda a: a['started_at'])
        for attempt in item['attempts']:
            url = attempt['url'].split('#', 1)[0]
            attempt['duplicate_of'] = seen.get(url)
            seen.setdefault(url, attempt['capture'])
        states = {a['status'] for a in item['attempts']}
        item['status'] = next((s for s in ('verified','partial','unknown','failed') if s in states),
                              'unknown' if not plan or unassigned else 'unattempted')
    return dict(schema=1, run_id=plan['run_id'] if plan else run_name, planned=plan is not None,
                window=plan['window'] if plan else None, targets=records, unassigned=unassigned)


def save_export(run, result):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=run, delete=False) as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    os.replace(out.name, run / 'discovery-audit.json')


def export(run):
    path = run / 'research.sqlite3'
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        result = audit(db, run.name)
    save_export(run, result)
    return result


def dashboard_shell(path, run_id):
    """Use the complete dashboard layout with this run's own records."""
    with closing(sqlite3.connect((path.parent / 'research.sqlite3').resolve().as_uri()+'?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        def records(table):
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM '+table+' ORDER BY id')]
        captures, candidates, evidence, claims = map(records, ('captures','candidates','evidence','claims'))
    data = dict(rows=[], caps={}, cand={}, ev={})
    for c in captures:
        key = c['id']
        url = c.get('final_url') or c['url']
        host = urlsplit(url).hostname or ''
        group = 2 if host in ('github.com','api.github.com','raw.githubusercontent.com') else 3 if host=='huggingface.co' else 4 if host=='arxiv.org' else 7
        mode = 2 if c['status']=='failed' else 3 if c['status']=='started' else int(not is_search(c))
        body = 'captures/'+key+'.bin'
        data['caps'][key] = dict(reason=c['purpose'], parent=c.get('parent_id'),error=c.get('error'),
                                 body=body if (path.parent/body).is_file() else None)
        data['rows'].append(dict(cap=key,url=url,title=c['purpose'],g=group,mode=mode,
                                 es=[e['id'] for e in evidence if e['capture_id']==key]))
    for c in candidates:
        data['cand'][c['id']] = dict(name=c['name'],decision=c['decision'],reason=c['reason'],
                                     origin=c.get('discovery_capture_ids',[]),url=c['canonical_url'])
    for e in evidence:
        data['ev'][e['id']] = dict(title=e['title'],kind=e['evidence_type'],fact=e['claim'],
                                   limit=e.get('limitations'),src=e['url'],
                                   cs=[c['id'] for c in claims if c.get('active',True) and e['id'] in c['evidence_ids']])
    links = [('trace.html','完整行为记录'),('report-dark.html','报告正文')]
    footer = '　'.join('<a href="'+url+'">'+label+'</a>' for url,label in links if (path.parent/url).is_file())
    template = Path(__file__).with_name('dashboard-template.html').read_text(encoding='utf-8')
    return template.replace('__RUN__',html.escape(run_id)).replace('__FOOT__',footer).replace(
        '__DATA__',json.dumps(data,ensure_ascii=False).replace('<',r'\u003c'))


def update_dashboard(path, result):
    """Install or refresh a scoped view inside the existing private dashboard."""
    original = path.read_text(encoding='utf-8') if path.exists() else ''
    if not original or 'id="stats"' not in original or 'data-run-dashboard' in original:
        original = dashboard_shell(path, result['run_id']).replace('<main>', '<main data-run-dashboard>')
    if 'id="tabs"' not in original or 'id="intro"' not in original:
        raise ValueError('Unsupported dashboard: expected existing review tabs')
    start, end = '<!-- discovery-audit:start -->', '<!-- discovery-audit:end -->'
    labels = dict(unknown='未知', unattempted='未尝试', failed='采集失败', partial='部分覆盖', verified='已核实')
    def safe(value):
        return html.escape(str(value))
    counts = {key: 0 for key in labels}
    for target in result['targets'].values():
        counts[target['status']] += 1
    summary = '　·　'.join(label+' '+str(counts[key]) for key, label in labels.items())
    note = ('历史数据无法核实。本期没有同期覆盖计划。' if not result['planned']
            else '按本期覆盖计划统计。')
    lines = ['<section id="coverage-home"><div class="line"><h2>渠道覆盖情况</h2>',
             '<button type="button" class="linkbtn">查看渠道明细 →</button></div>',
             '<p>'+safe(summary)+'</p><small>'+note+' 未关联目标的请求 '+str(len(result['unassigned']))+' 次。</small></section>',
             '<section id="coverage-panel" hidden><h2>研究来源覆盖审计</h2>',
             '<p>运行 '+safe(result['run_id'])+' · 未关联目标的请求 '+str(len(result['unassigned']))+' 次。</p>']
    if not result['planned']:
        lines.append('<p>历史数据无法核实。本期没有同期覆盖计划。</p>')
    for item in result['targets'].values():
        lines.append('<details class="row"><summary>'+safe(item['label'])+'　'+labels[item['status']]+'</summary>')
        attempts = item['attempts']
        state = item['status']
        target = item['label'] if result['planned'] else '未知（无同期计划）'
        actions = '；'.join(a['capture']+' · '+a.get('purpose','未知')+'　'+
                          ' '.join(parse_qs(urlsplit(a['url']).query).get('q', [])) for a in attempts)
        outcomes = '；'.join(a['capture']+' · '+(a['review'].get('impact') or a['reason']) for a in attempts)
        gaps = {'unattempted':'计划内检查尚无请求','partial':'；'.join(a['reason'] for a in attempts if a['status']=='partial'),'failed':'请求失败，未完成核查',
                'verified':'此项计划检查已完成','unknown':'未知'}
        next_step = ('执行计划中的检查：'+target if state=='unattempted' else '未知（没有登记后续动作）')
        fields = [('搜索目标',target),('执行了什么',actions or ('尚未执行' if state=='unattempted' else '未知')),
                  ('得到的结果',outcomes or ('尚无结果' if state=='unattempted' else '未知')),
                  ('尚未完成',gaps[state]),('下一步',next_step)]
        lines.extend('<p><b>'+label+'</b>　'+safe(value)+'</p>' for label,value in fields)
        if not item['attempts']:
            lines.append('<p>'+('没有关联请求，需执行计划中的检查。' if item['status']=='unattempted'
                               else '缺少同期计划或关联记录，无法核实。')+'</p>')
        elif item['status'] in ('failed', 'partial', 'unknown'):
            lines.append('<p>需要补查：核对以下请求的失败或范围限制，再读取能回答本期问题的原始材料。</p>')
        for a in item['attempts']:
            review = a['review']
            fields = [a['capture'], a['url'], a['reason'], '前序请求 '+str(a['parent'] or '无'),
                      '替代对象 '+str(review.get('alternative_for') or '无'),
                      '结论影响 '+str(review.get('impact') or '未登记'), '关联主张 '+(', '.join(a['claims']) or '无')]
            lines.append('<p>'+safe(' · '.join(fields))+'</p>')
            if a['status'] != 'failed':
                lines.append('<a href="captures/'+safe(a['capture'])+'.bin">查看导出的采集响应</a>' if
                             (path.parent/'captures'/(a['capture']+'.bin')).is_file() else '')
        lines.append('</details>')
    lines.append('</section>')
    script = Path(__file__).with_name('coverage-tab.js').read_text(encoding='utf-8')
    block = start+''.join(lines)+'<script>'+script+'</script>'+end
    if start in original:
        left, tail = original.split(start, 1)
        original = left+block+tail.split(end, 1)[1]
    else:
        original = original.replace('</html>', block+'</html>')
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as out:
        out.write(original)
    os.replace(out.name, path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--dashboard', action='store_true', help='Refresh existing research-dashboard.html in this run')
    args = parser.parse_args()
    result = export(args.run)
    if args.dashboard:
        dashboard = args.run / 'research-dashboard.html'
        update_dashboard(dashboard, result)
