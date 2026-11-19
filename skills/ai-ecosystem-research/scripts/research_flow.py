"""Transactional research records and pre-writing gate. Python standard library only.

Local records are evidence of recorded actions, not proof of source truth.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import urllib.request
import urllib.parse
import discovery_audit
from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path

EXPORTS = {'candidates': 'candidates.json', 'evidence': 'evidence.json',
           'claims': 'report-claims.json', 'captures': 'captures.json'}
TYPES = {'primary_artifact', 'official_claim', 'independent_test',
         'community_feedback', 'discovery_only', 'analysis'}


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def need(value, keys):
    if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or
                                         not value[k].strip() for k in keys):
        raise ValueError('Required nonempty strings: ' + ', '.join(keys))


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,79}', value):
        raise ValueError('Invalid record ID')
    return value


class Store:
    def __init__(self, run):
        self.run = Path(run)
        if not (self.run / 'research.sqlite3').is_file():
            raise ValueError('Initialize a new research directory first')
        self.db = sqlite3.connect(self.run / 'research.sqlite3', timeout=30)
        self.db.execute('PRAGMA synchronous=FULL')

    def close(self):
        self.db.close()

    def rows(self, table):
        return [json.loads(r[0]) for r in self.db.execute(
            'SELECT payload FROM ' + table + ' ORDER BY id')]

    def get(self, table, key):
        row = self.db.execute('SELECT payload FROM ' + table + ' WHERE id=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Unknown ' + table + ' ID: ' + str(key))
        return json.loads(row[0])

    def save(self, table, record, update=False):
        ident(record['id'])
        if update:
            self.db.execute('UPDATE ' + table + ' SET payload=? WHERE id=?',
                            (encode(record), record['id']))
        else:
            self.db.execute('INSERT INTO ' + table + ' VALUES (?,?)',
                            (record['id'], encode(record)))

    def event(self, kind, record):
        self.db.execute('INSERT INTO events(kind,at,payload) VALUES (?,?,?)',
                        (kind, now(), encode(record)))

    def apply(self, action, data, content=None):
        """Serialize validation and mutation; retain old candidate states in events."""
        self.db.execute('BEGIN IMMEDIATE')
        try:
            result = self._apply(action, dict(data), content)
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def _apply(self, action, d, content):
        need(d, ['id'])
        ident(d['id'])
        if action == 'begin':
            need(d, ['tool', 'purpose', 'url'])
            explicitly_scoped = 'coverage_targets' in d
            targets = d.get('coverage_targets', [])
            if not isinstance(targets, list) or any(not isinstance(k, str) for k in targets):
                raise ValueError('coverage_targets must be a list of channel IDs')
            if targets:
                plan = discovery_audit.plan_for(self.db)
                if not plan or not set(targets) <= plan['targets'].keys():
                    raise ValueError('Unknown coverage target')
            if d.get('parent_id'):
                self.get('captures', d['parent_id'])
            if d.get('candidate_id'):
                self.get('candidates', d['candidate_id'])
            d = {k: d.get(k) for k in ['id', 'tool', 'purpose', 'url', 'query',
                                      'parent_id', 'candidate_id', 'version']}
            d.update(status='started', started_at=now(), finished_at=None)
            if explicitly_scoped:
                d['coverage_targets'] = sorted(set(targets))
            self.save('captures', d)
        elif action == 'coverage-review':
            capture = self.get('captures', d['id'])
            need(d, ['target', 'material', 'impact'])
            if d['target'] not in capture.get('coverage_targets', []) or capture['status'] == 'started':
                raise ValueError('Review requires a finished capture associated with this target')
            if d['material'] not in ('original', 'snippet', 'incomplete') or not isinstance(d.get('complete'), bool):
                raise ValueError('Expected material and boolean complete')
            if d['material'] == 'original':
                need(d, ['excerpt'])
                body = self.db.execute('SELECT content FROM bodies WHERE id=?', (d['id'],)).fetchone()
                if capture['status'] != 'ok' or not body or d['excerpt'].encode() not in body[0]:
                    raise ValueError('Excerpt missing from original saved response')
            if d.get('alternative_for'):
                other = self.get('captures', d['alternative_for'])
                if other['id'] == capture['id'] or d['target'] not in other.get('coverage_targets', []):
                    raise ValueError('Alternative must reference another attempt for this target')
            capture.setdefault('coverage_reviews', {})[d['target']] = {
                k: d.get(k) for k in ('material', 'complete', 'window', 'excerpt', 'alternative_for', 'impact')}
            self.save('captures', capture, update=True)
        elif action == 'finish':
            capture = self.get('captures', d['id'])
            if capture['status'] != 'started':
                raise ValueError('Capture already finished; use a new ID for a retry')
            if d.get('status') not in ('ok', 'failed'):
                raise ValueError('Finish status must be ok or failed')
            if d['status'] == 'ok' and not content:
                raise ValueError('Successful capture requires saved content')
            if d['status'] == 'failed':
                need(d, ['error'])
            capture.update(status=d['status'], finished_at=now(), error=d.get('error'),
                           final_url=d.get('final_url'), http_status=d.get('http_status'))
            if content:
                capture.update(sha256=digest(content), bytes=len(content))
                self.db.execute('INSERT INTO bodies VALUES (?,?)', (d['id'], content))
            d = capture
            self.save('captures', d, update=True)
        elif action == 'candidate':
            need(d, ['entity_id', 'canonical_url', 'event_key', 'name', 'event_type',
                     'decision', 'reason'])
            if d['decision'] not in ('selected', 'watch', 'deferred', 'excluded'):
                raise ValueError('Unknown candidate decision')
            refs = d.get('discovery_capture_ids')
            if not isinstance(refs, list) or not refs:
                raise ValueError('Candidate needs discovery capture IDs')
            for key in refs:
                if self.get('captures', key)['status'] != 'ok':
                    raise ValueError('Discovery must reference a successful capture')
            old = next((x for x in self.rows('candidates') if x['id'] == d['id']), None)
            identity = ('entity_id', 'canonical_url', 'event_key')
            for x in self.rows('candidates'):
                if x['entity_id'] == d['entity_id'] and x['canonical_url'] != d['canonical_url']:
                    raise ValueError('Use the existing canonical URL for this entity')
                if x['id'] != d['id'] and x['event_key'] == d['event_key'] and (
                        x['canonical_url'] == d['canonical_url'] or x['entity_id'] == d['entity_id']):
                    raise ValueError('Duplicate entity event; update existing candidate ' + x['id'])
            if old and any(old[k] != d[k] for k in identity):
                raise ValueError('Candidate identity cannot change')
            d['discovery_capture_ids'] = sorted(set(refs + (old['discovery_capture_ids'] if old else [])))
            d['first_seen'] = old['first_seen'] if old else now()
            d['updated_at'] = now()
            self.save('candidates', d, update=bool(old))
        elif action == 'evidence':
            need(d, ['candidate_id', 'capture_id', 'claim', 'title', 'publisher',
                     'evidence_type', 'locator'])
            self.get('candidates', d['candidate_id'])
            c = self.get('captures', d['capture_id'])
            if c['status'] != 'ok' or d['evidence_type'] not in TYPES:
                raise ValueError('Evidence needs successful capture and known type')
            d.update(url=c.get('final_url') or c['url'], retrieved_at=c['finished_at'],
                     capture_started_at=c['started_at'], access_status='ok')
            for key in ('published_at', 'event_at', 'version', 'limitations'):
                d.setdefault(key, None)
            self.save('evidence', d)
        elif action == 'claim':
            need(d, ['claim', 'support_review', 'kind'])
            if d['kind'] not in ('fact', 'analysis'):
                raise ValueError('Claim kind must be fact or analysis')
            refs = d.get('evidence_ids')
            if not isinstance(refs, list) or not refs:
                raise ValueError('Claim needs evidence IDs')
            candidates = set()
            for key in refs:
                e = self.get('evidence', key)
                if e['evidence_type'] == 'discovery_only':
                    raise ValueError('Discovery-only material cannot support report claims')
                candidates.add(e['candidate_id'])
            d['candidate_ids'] = sorted(candidates)
            if d.get('quantitative') is not False:
                need(d, ['metric_scope'])
            d['recorded_at'] = now()
            d['active'] = True
            old = next((x for x in self.rows('claims') if x['id'] == d['id']), None)
            d['revision'] = old.get('revision', 1) + 1 if old else 1
            self.save('claims', d, update=bool(old))
        elif action == 'withdraw-claim':
            need(d, ['reason'])
            old = self.get('claims', d['id'])
            d = dict(old, active=False, withdrawal_reason=d['reason'],
                     revision=old['revision'] + 1, recorded_at=now())
            self.save('claims', d, update=True)
        else:
            raise ValueError('Unknown action')
        self.event(action, d)
        return d

    def state(self):
        return {table: self.rows(table) for table in EXPORTS}

    def public_rows(self, table):
        rows = self.rows(table)
        return [r for r in rows if r.get('active', True)] if table == 'claims' else rows

    def problems(self):
        errors = []
        candidates = {x['id']: x for x in self.rows('candidates')}
        claims = self.public_rows('claims')
        if not claims:
            errors.append('No report claims registered')
        for c in self.rows('captures'):
            if c['status'] == 'started':
                errors.append('Unfinished capture ' + c['id'])
            if c['status'] == 'ok':
                body = self.db.execute('SELECT content FROM bodies WHERE id=?', (c['id'],)).fetchone()
                if not body or digest(body[0]) != c['sha256']:
                    errors.append('Missing/changed capture body ' + c['id'])
        used = set()
        for c in claims:
            for key in c['candidate_ids']:
                used.add(key)
                if candidates[key]['decision'] != 'selected':
                    errors.append('Claim refers to non-selected candidate ' + key)
        for c in candidates.values():
            if c['decision'] == 'selected' and c['id'] not in used:
                errors.append('Selected candidate has no report claim ' + c['id'])
        return errors

    def export(self):
        if discovery_audit.plan_for(self.db):
            discovery_audit.save_export(self.run, discovery_audit.audit(self.db, self.run.name))
        for table, filename in EXPORTS.items():
            (self.run / filename).write_text(encode(self.public_rows(table)) + '\n', encoding='utf-8')
        events = [{'sequence': i, 'action': k, 'at': t, 'record': json.loads(p)}
                  for i, k, t, p in self.db.execute('SELECT seq,kind,at,payload FROM events ORDER BY seq')]
        (self.run / 'acquisition-log.jsonl').write_text(
            ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in events), encoding='utf-8')
        folder = self.run / 'captures'
        folder.mkdir(exist_ok=True)
        for key, body in self.db.execute('SELECT id,content FROM bodies'):
            (folder / (ident(key) + '.bin')).write_bytes(body)

    def prewrite(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            errors = self.problems()
            if errors:
                raise ValueError('; '.join(errors))
            self.export()
            receipt = {'schema_version': 1, 'checked_at': now(),
                       'state_sha256': digest(encode(self.state()).encode()),
                       'exports': {f: digest((self.run / f).read_bytes()) for f in EXPORTS.values()},
                       'note': 'Structural check only; support_review is a researcher assertion.'}
            (self.run / 'prewrite.json').write_text(encode(receipt), encoding='utf-8')
        finally:
            self.db.rollback()  # Read transaction; exports can be rebuilt from authoritative DB.
        return receipt


def initialize(run):
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    # Refuse historical or partially initialized runs. Never overwrite old records.
    if any((run / f).exists() for f in ['research.sqlite3', 'report.md', 'prewrite.json', *EXPORTS.values()]):
        raise ValueError('Use a new run directory; existing research records are preserved')
    plan = discovery_audit.make_plan(run)
    with closing(sqlite3.connect(run / 'research.sqlite3')) as db:
        db.execute('BEGIN')
        db.execute('CREATE TABLE coverage_plan(payload TEXT NOT NULL)')
        db.execute('INSERT INTO coverage_plan VALUES (?)', (encode(plan),))
        for table in EXPORTS:
            db.execute('CREATE TABLE ' + table + '(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('CREATE TABLE bodies(id TEXT PRIMARY KEY,content BLOB NOT NULL)')
        db.execute('CREATE TABLE events(seq INTEGER PRIMARY KEY,kind TEXT,at TEXT,payload TEXT)')
        db.commit()


def fetch(store, data):
    """Record start before network I/O. Repeated IDs never repeat a request."""
    url = urllib.parse.urlsplit(data['url'])
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials')
    data = dict(data, tool='http')
    store.apply('begin', data)
    try:
        with urllib.request.urlopen(urllib.request.Request(data['url'], headers={
                'User-Agent': 'EcosystemResearch/1.0'}), timeout=30) as response:
            content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise ValueError('Response exceeds 8 MiB; use external capture for larger artifacts')
            return store.apply('finish', {'id': data['id'], 'status': 'ok',
                               'final_url': response.url, 'http_status': response.status}, content)
    except Exception as exc:
        store.apply('finish', {'id': data['id'], 'status': 'failed',
                              'error': type(exc).__name__ + ': ' + str(exc)})
        raise


def check_writing(run):
    """Fail closed for new delivery; historical files are not silently migrated."""
    store = None
    try:
        store = Store(run)
        store.db.execute('BEGIN')
        errors = store.problems()
        receipt = json.loads((Path(run) / 'prewrite.json').read_text(encoding='utf-8'))
        if receipt['state_sha256'] != digest(encode(store.state()).encode()):
            errors.append('Research changed after pre-writing check; check again')
        for table, filename in EXPORTS.items():
            raw = (Path(run) / filename).read_bytes()
            if digest(raw) != receipt['exports'][filename] or json.loads(raw) != store.public_rows(table):
                errors.append('Export differs from checked records: ' + filename)
        report = (Path(run) / 'report.md').read_text(encoding='utf-8-sig')
        markers = re.findall(r'<!--\s*claim:([A-Za-z][A-Za-z0-9_-]*)\s*-->', report)
        closing_markers = re.findall(r'<!--\s*/claim:([A-Za-z][A-Za-z0-9_-]*)\s*-->', report)
        ids = {c['id'] for c in store.public_rows('claims')}
        if set(markers) != ids or len(markers) != len(ids) or sorted(closing_markers) != sorted(markers):
            errors.append('Report claim markers must match registered claims')
        for c in store.public_rows('claims'):
            pair = re.search(r'<!--\s*claim:' + re.escape(c['id']) + r'\s*-->(.*?)<!--\s*/claim:'
                             + re.escape(c['id']) + r'\s*-->', report, re.S)
            if not pair or pair[1].strip() != c['claim'].strip():
                errors.append('Report text differs from registered claim ' + c['id'])
        return errors
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        return ['Research workflow check failed: ' + str(exc)]
    finally:
        if store:
            store.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init', 'begin', 'finish', 'fetch', 'candidate',
                                     'evidence', 'claim', 'withdraw-claim', 'export', 'prewrite', 'check', 'coverage-review'])
    p.add_argument('run', type=Path)
    p.add_argument('--input', type=Path, help='UTF-8 JSON record')
    p.add_argument('--content', type=Path, help='Raw response or external tool result saved immediately')
    args = p.parse_args()
    store = None
    try:
        if args.action == 'init':
            initialize(args.run)
            result = {'initialized': True}
        elif args.action == 'check':
            errors = check_writing(args.run)
            print(encode({'ok': not errors, 'errors': errors}))
            return bool(errors)
        else:
            store = Store(args.run)
            if args.action in ('export', 'prewrite'):
                result = getattr(store, args.action)()
            else:
                if not args.input:
                    raise ValueError('--input is required')
                data = json.loads(args.input.read_text(encoding='utf-8-sig'))
                result = fetch(store, data) if args.action == 'fetch' else store.apply(
                    args.action, data, args.content.read_bytes() if args.content else None)
        print(encode({'ok': True, 'result': result}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(encode({'ok': False, 'error': str(exc)}))
        return 1
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    sys.exit(main())
