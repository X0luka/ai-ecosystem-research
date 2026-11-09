"""Fail-closed structural gate; not a truth verifier."""
import json,sys
from pathlib import Path
REQUIRED={'source_support','time_scope','reader_value','semantic_review','visual_review'}
def check(run):
 errors=[]
 def read(name):
  try:return json.loads((run/name).read_text(encoding='utf-8-sig'))
  except (OSError,ValueError):errors.append('Missing/invalid '+name)
 a,evidence,claims=[read(n) for n in ('acceptance.json','evidence.json','report-claims.json')]
 mode=None
 if not isinstance(a,dict) or not a:errors.append('Acceptance must be a nonempty object')
 else:
  mode=a.get('mode')
  if mode not in ('weekly','monthly','deep-dive'):errors.append('Unknown mode')
  if a.get('artifact_status')!='ready' or a.get('delivery_ready') is not True:errors.append('Research not ready')
  req=a.get('requirements');needed=REQUIRED|({'nine_layers','rankings'} if mode in ('weekly','monthly') else {'research_question'})
  if mode=='monthly':needed|={'longitudinal_review','judgment_revision'}
  if not isinstance(req,list) or not all(isinstance(x,dict) for x in req):errors.append('Invalid requirements')
  else:
   if not needed<={x.get('id') for x in req}:errors.append('Required reviews missing')
   for x in req:
    if x.get('status') not in ('pass','source_limited') or not x.get('evidence'):errors.append('Incomplete requirement '+str(x.get('id')))
    if x.get('status')=='source_limited' and not x.get('reason'):errors.append('Source limitation lacks reason')
  unresolved=a.get('unresolved')
  if not isinstance(unresolved,list):errors.append('Explicit unresolved list required')
  else:
   for x in unresolved:
    if not isinstance(x,dict) or x.get('blocking',True) or x.get('type') in ('not_read','not_attempted'):errors.append('Unfinished research')
    elif not x.get('attempts') or not x.get('impact'):errors.append('Source limitation lacks attempts/impact')
 ids=set()
 if not isinstance(evidence,list) or not evidence:errors.append('Evidence must be a nonempty list')
 else:
  for e in evidence:
   if not isinstance(e,dict):errors.append('Invalid evidence record');continue
   if not all(e.get(k) for k in ('id','claim','url','title','publisher','retrieved_at','evidence_type','locator')):errors.append('Incomplete evidence '+str(e.get('id')))
   eid=e.get('id')
   if not isinstance(eid,str) or eid in ids:errors.append('Invalid/duplicate evidence ID')
   else:ids.add(eid)
 if not isinstance(claims,list) or not claims:errors.append('Missing claim mapping')
 else:
  for c in claims:
   if not isinstance(c,dict):errors.append('Invalid claim');continue
   refs=c.get('evidence_ids')
   if not c.get('claim') or not isinstance(refs,list) or not refs or not all(isinstance(i,str) and i in ids for i in refs):errors.append('Unsupported claim mapping')
 for name in ('report.md','report-dark.html','coverage.md'):
  if not (run/name).is_file() or (run/name).stat().st_size==0:errors.append('Missing/empty '+name)
 if mode=='monthly':
  review=read('review.json')
  if not isinstance(review,(dict,list)) or not review:errors.append('Monthly review index missing/empty')
 return errors
if __name__=='__main__':
 issues=check(Path(sys.argv[1]));print(json.dumps({'structural_gate':'fail' if issues else 'pass','errors':issues,'note':'Semantic/source and visual review are separately required.'},ensure_ascii=False));sys.exit(bool(issues))
