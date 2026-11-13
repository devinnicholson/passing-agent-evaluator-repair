"""Azure-only provenance and feedback audit, independent of model collection."""
from hashlib import sha256
import json
from pathlib import Path
import tarfile


def read_grades(path):
    with tarfile.open(path) as archive:
        report = json.load(archive.extractfile('study/native/REPORT.json'))
    if not report['completed']:
        raise ValueError('incomplete native grading')
    rows = {}
    for unit in report['units'].values():
        if unit['errors'] or set(rows).intersection(unit['candidates']):
            raise ValueError('grading errors or duplicate observations')
        rows.update(unit['candidates'])
    return rows


def normalized(row):
    text = row['response'].get('content', '').strip()
    return text[:-7].rstrip() if text.endswith('<turn|>') else text


def audit(root):
    root = Path(root)
    payload = json.loads((root/'payload.json').read_text())
    initial = json.loads((root/'INITIAL.json').read_text())
    feedback = json.loads((root/'FEEDBACK.json').read_text())
    parent_bytes = (root/'PARENT_FINAL.json').read_bytes()
    parent = json.loads(parent_bytes)
    if sha256(parent_bytes).hexdigest() != payload['retained_source_worker_record_sha256']:
        raise ValueError('parent collection identity differs')
    original, corrected = {}, {}
    for side in ('a','b'):
        original.update(read_grades(root/('provisional_initial_'+side+'.tar.gz')))
        corrected.update(read_grades(root/('initial_'+side+'.tar.gz')))
    expected = set(payload['order'])
    if not (set(original) == set(corrected) == set(initial['initial']) == set(feedback['routing']) == expected):
        raise ValueError('initial denominator differs')
    if sha256((root/'INITIAL.json').read_bytes()).hexdigest() != feedback['initial_sha256']:
        raise ValueError('feedback not bound to actual initial receipt')
    retained = payload['retained_initial']
    if 'INITIAL_RESPONSES.json' in {p.name for p in root.iterdir()}:
        saved=json.loads((root/'INITIAL_RESPONSES.json').read_text())
        if saved!={n:normalized(r) for n,r in initial['initial'].items()}:
            raise ValueError('initial normalization differs from preserved bytes')
    if set(retained).union(payload['pending_order']) != expected or set(retained).intersection(payload['pending_order']):
        raise ValueError('resumption partition differs')
    origins, checked_requests = {}, set()
    for name in payload['order']:
        row = initial['initial'][name]
        if row.get('name')!=name or row.get('seed')!=payload['tasks'][name]['seed']:
            raise ValueError('initial sample identity differs '+name)
        if not row.get('model_output_status') and row['prompt']!=payload['tasks'][name]['prompt']:
            raise ValueError('initial prompt differs '+name)
        if name in parent['initial']:
            if row != parent['initial'][name] or row != retained[name]:
                raise ValueError('retained raw response changed '+name)
            origins[name] = {'phase':'parent_collection','available':True}
        elif name in retained:
            if row != retained[name] or row.get('model_output_status') != 'timeout_no_response' or not row.get('request_attempted'):
                raise ValueError('retained missing observation changed '+name)
            if parent.get('error') != row.get('error'):
                raise ValueError('missing observation not joined to parent failure')
            origins[name] = {'phase':'parent_collection','available':False,'status':row['model_output_status']}
        else:
            if name not in payload['pending_order']:
                raise ValueError('unassigned resumed sample')
            origins[name] = {'phase':'resumed_collection','available':not bool(row.get('model_output_status'))}
        # The assertion-setting correction cannot retroactively alter feedback.
        if corrected[name]['feedback'] != original[name]['feedback']:
            raise ValueError('assertion-enabled feedback differs from delivered feedback '+name)
        allowed = corrected[name]['feedback']
        if row.get('model_output_status'):
            if corrected[name]['status'] != 'REJECTED':
                raise ValueError('missing response treated as generated code')
            message = {'verdict':'NO_RESPONSE','error':'The initial model request returned no patch before the fixed request deadline. This is response absence, not a demonstrated Java assertion error. Produce one replacement within the same generation budget.'}
            allowed = {arm:dict(message) for arm in ('released','repaired')}
        expected_arms = {'released','repaired'}
        if allowed['released']['verdict']=='PASS' and allowed['repaired']['verdict']!='PASS':
            expected_arms.add('matched_released')
        routes = feedback['routing'][name]
        if set(routes) != expected_arms:
            raise ValueError('conditional policy route differs '+name)
        for arm,route in routes.items():
            f = allowed['released' if arm=='matched_released' else arm]
            should_stop = f['verdict']=='PASS' and arm!='matched_released'
            if route['retained_initial'] != should_stop:
                raise ValueError('stopping policy differs '+name)
            if should_stop:
                continue
            prompt = (payload['tasks'][name]['prompt']+'\nPrevious answer as a JSON string\n'+
                json.dumps(normalized(row)).replace('<','\\u003c')+'\nDeveloper-production grader feedback\n'+
                json.dumps(f,sort_keys=True).replace('<','\\u003c')+
                '\nThis is the only allowed repair opportunity. Return the complete replacement method body in the same JSON format. Preserve meaningful coverage.')
            task = feedback['tasks'][route['request']]
            if task != {'prompt':prompt,'seed':payload['tasks'][name]['seed']+1}:
                raise ValueError('actual callback differs from corrected permitted feedback '+name)
            checked_requests.add(route['request'])
    if checked_requests != set(feedback['tasks']):
        raise ValueError('unassigned callback request')
    final_checked=False
    if (root/'FINAL.json').exists():
        final=json.loads((root/'FINAL.json').read_text())
        if (not final['complete'] or final['initial']!=initial['initial'] or
                final.get('feedback_packet')!=feedback or set(final['repairs'])!=checked_requests):
            raise ValueError('final collection or feedback identity differs')
        for name,row in final['repairs'].items():
            task=feedback['tasks'][name]
            if row['name']!=name or row['prompt']!=task['prompt'] or row['seed']!=task['seed']:
                raise ValueError('callback prompt or identity differs '+name)
        expected_final={}
        for name,arms in feedback['routing'].items():
            for arm,route in arms.items():
                row=initial['initial'][name] if route['retained_initial'] else final['repairs'][route['request']]
                expected_final[name+'-'+arm]=normalized(row)
        if json.loads((root/'FINAL_RESPONSES.json').read_text())!=expected_final:
            raise ValueError('final normalization or routing differs from preserved bytes')
        final_checked=True
    return {'verified':True,'initial_slots':len(expected),'origins':origins,
        'retained_actual_responses':len(parent['initial']),
        'parent_error':parent.get('error'), 'resumed_initial_requests':len(payload['pending_order']),
        'assertion_enabled_feedback_exactly_matches_delivered':True,
        'verified_distinct_callback_requests':len(checked_requests),
        'final_raw_prompts_routing_and_normalization_verified':final_checked,
        'matched_control_eligible_slots':sum('matched_released' in v for v in feedback['routing'].values()),
        'no_raw_response_regeneration_or_researcher_code_correction':True}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.input)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
