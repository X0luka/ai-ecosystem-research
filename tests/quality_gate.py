"""Record a task contract before editing, execute checks, and verify their receipts."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

AREAS = ('correctness', 'integration', 'effectiveness', 'regression')


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def start(folder):
    plan = read(folder / 'plan.json')
    for field in ('problem', 'limits', 'evidence'):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            raise ValueError('Missing '+field)
    if not plan.get('counterexamples') or not all(isinstance(x,str) and x.strip() for x in plan['counterexamples']) or not isinstance(plan['counterexamples'],list):
        raise ValueError('Missing failure cases')
    for field in ('criteria', 'methods'):
        for area in AREAS:
            if not isinstance(plan.get(field, {}).get(area), str) or not plan[field][area].strip():
                raise ValueError('Missing '+field+' / '+area)
    with (folder / 'contract').open('x', encoding='ascii') as f:
        f.write(hash_file(folder / 'plan.json'))


def check_contract(folder):
    if (folder / 'contract').read_text(encoding='ascii') != hash_file(folder / 'plan.json'):
        raise ValueError('Contract changed after start')


def source_hash():
    paths = subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z']).split(b'\0')
    digest = hashlib.sha256()
    for name in sorted(set(filter(None,paths))):
        p = Path(name.decode('utf-8'))
        digest.update(name+b'\0'+(hash_file(p) if p.is_file() else 'missing').encode())
    return digest.hexdigest()


def record(folder, area, command, artifacts):
    check_contract(folder)
    receipt = folder / (area+'.json')
    receipt.unlink(missing_ok=True)
    if not command:
        raise ValueError('Expected executable check')
    if area in ('effectiveness','integration') and not artifacts:
        raise ValueError('Expected observed artifacts')
    source = source_hash()
    log = folder / (area+'.log')
    with log.open('wb') as f:
        result = subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    files = {str(p.resolve()):hash_file(p) for p in [log,*artifacts]}
    write(receipt,dict(code=result.returncode,command=command,source=source,files=files,contract=hash_file(folder/'plan.json')))
    return result.returncode


def verify(folder):
    check_contract(folder)
    source = source_hash()
    for area in AREAS:
        receipt = read(folder/(area+'.json'))
        if receipt['code'] or receipt['source'] != source or receipt['contract'] != hash_file(folder/'plan.json'):
            raise ValueError('Failed or stale check: '+area)
        if any(hash_file(Path(p)) != h for p,h in receipt['files'].items()):
            raise ValueError('Changed evidence: '+area)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','run','check'])
    parser.add_argument('folder',type=Path)
    parser.add_argument('--area',choices=AREAS)
    parser.add_argument('--artifact',type=Path,action='append',default=[])
    args, command = parser.parse_known_args()
    try:
        if args.action == 'start':
            start(args.folder)
        elif args.action == 'check':
            verify(args.folder)
        else:
            if not args.area or not command or command[0] != '--':
                raise ValueError('Use --area AREA -- COMMAND')
            sys.exit(record(args.folder,args.area,command[1:],args.artifact))
    except (OSError,ValueError,KeyError) as error:
        sys.exit('Quality gate blocked: '+str(error))
