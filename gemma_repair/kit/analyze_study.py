"""Azure-only fixed-denominator descriptive analysis. No significance claims."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import tarfile


def reports(path, plan_sha):
    with tarfile.open(path) as archive:
        report = json.load(archive.extractfile('study/native/REPORT.json'))
        for unit in report['units']:
            control=json.load(archive.extractfile('study/native/'+unit+'/ASSERTION_CONTROL.json'))
            refusal=archive.extractfile('study/native/'+unit+'/assertion_disabled_refusal.stderr').read().decode()
            if control['verdict']!='FAIL' or 'Java assertions must be enabled with -ea' not in refusal:
                raise ValueError('assertion configuration lacks independent controls')
    if not report['completed'] or report['plan_sha256'] != plan_sha:
        raise ValueError('incomplete or unrelated native grading')
    result = {}
    for unit, row in report['units'].items():
        if row['errors']:
            raise ValueError('native grading operational errors ' + unit)
        for label, candidate in row['candidates'].items():
            if label in result:
                raise ValueError('duplicate candidate label')
            result[label] = candidate
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()
    root = args.input
    payload = json.loads((root / 'payload.json').read_text())
    initial = json.loads((root / 'INITIAL.json').read_text())
    final = json.loads((root / 'FINAL.json').read_text())
    feedback = json.loads((root / 'FEEDBACK.json').read_text())
    plan = json.loads((root / 'PLAN.json').read_text())
    if sha256((root / 'PLAN.json').read_bytes()).hexdigest() != payload['plan_sha256']:
        raise ValueError('plan identity')
    if not final['complete'] or initial['weights'] != payload['weights'] or final['weights'] != payload['weights']:
        raise ValueError('incomplete inference or model mismatch')
    if set(initial['initial']) != set(payload['order']) or set(final['repairs']) != set(feedback['tasks']):
        raise ValueError('fixed inference denominator mismatch')
    for row in [*initial['initial'].values(), *final['repairs'].values()]:
        if row.get('model_output_status'):
            if row['response'].get('content') != '' or not row.get('request_attempted'):
                raise ValueError('invalid typed missing-response record')
            continue
        if not row.get('native_token_ids_match') or row['input_tokens'] + 2048 > 8192:
            raise ValueError('native input token qualification')
    initial_grades, final_grades = {}, {}
    for label, target in [('initial_a', initial_grades), ('initial_b', initial_grades), ('final_a', final_grades), ('final_b', final_grades)]:
        values = reports(root / (label + '.tar.gz'), payload['plan_sha256'])
        if set(values) & set(target):
            raise ValueError('grading split duplicate')
        target.update(values)
    expected_final = {name + '-' + arm for name, arms in feedback['routing'].items() for arm in arms}
    if set(initial_grades) != set(payload['order']) or set(final_grades) != expected_final:
        raise ValueError('fixed grading denominator mismatch')
    rows = []
    totals = Counter()
    for name in payload['order']:
        unit, seed = name.rsplit('-', 1)
        meta = plan['units'][unit]
        baseline = initial_grades[name]
        row = {'sample': name, 'unit': unit, 'seed': int(seed), 'commit_cluster': meta['instance'],
               'initial_output_status': initial['initial'][name].get('model_output_status', 'available'),
               'initial_grade_status': baseline['status'],
               'initial_feedback_verdicts': {a:f['verdict'] for a,f in baseline['feedback'].items()},
               'initial_oracle_qualified': baseline['oracle_qualified'], 'arms': {}}
        totals['initial_status_'+baseline['status']] += 1
        totals['initial_model_outputs_available'] += row['initial_output_status'] == 'available'
        totals['initial_responses_missing'] += row['initial_output_status'] != 'available'
        totals['initial_qualified'] += bool(baseline['oracle_qualified'])
        totals['initial_nonempty_source_false_pass'] += (baseline.get('arms',{}).get('released',{}).get('verdict') == 'PASS'
            and baseline.get('arms',{}).get('repaired',{}).get('verdict') == 'FAIL')
        for arm in feedback['routing'][name]:
            candidate = final_grades[name + '-' + arm]
            route = feedback['routing'][name][arm]
            final_feedback = candidate['feedback'][('released' if arm != 'repaired' else 'repaired')]
            row['arms'][arm] = {'status': candidate['status'], 'oracle_qualified': candidate['oracle_qualified'],
                'model_output_status': (initial['initial'][name] if route['retained_initial'] else final['repairs'][route['request']]).get('model_output_status', 'available'),
                'retained_initial': route['retained_initial'], 'request': route.get('request'),
                'final_own_verdict': final_feedback['verdict'],
                'native': {key: value for key,value in candidate.get('arms',{}).get('released' if arm != 'repaired' else 'repaired',{}).items()
                           if key in ('selected','started','failed','contract','native_exit')},
                'oracle': {key: {'verdict': value['contract']['verdict'], 'started': value['started'], 'failed': value['failed']}
                           for key,value in candidate.get('oracle',{}).items()}}
            totals[arm + '_qualified'] += bool(candidate['oracle_qualified'])
            totals[arm + '_status_'+candidate['status']] += 1
            totals[arm + '_outputs_available'] += row['arms'][arm]['model_output_status']=='available'
            totals[arm + '_observations'] += 1
            totals[arm + '_accepted_unqualified'] += final_feedback['verdict'] == 'PASS' and not candidate['oracle_qualified']
            totals[arm + '_accepted_developer_failure'] += (final_feedback['verdict'] == 'PASS' and
                candidate.get('oracle',{}).get('developer',{}).get('contract',{}).get('verdict') == 'FAIL')
            totals[arm + '_crossgraded_source_false_pass'] += (candidate.get('arms',{}).get('released',{}).get('verdict') == 'PASS'
                and candidate.get('arms',{}).get('repaired',{}).get('verdict') == 'FAIL')
        a, b = row['arms']['released']['oracle_qualified'], row['arms']['repaired']['oracle_qualified']
        totals['both_qualified'] += a and b
        totals['repaired_only'] += b and not a
        totals['released_only'] += a and not b
        totals['neither_qualified'] += not a and not b
        if 'matched_released' in row['arms']:
            matched = row['arms']['matched_released']['oracle_qualified']
            totals['matched_repaired_only'] += b and not matched
            totals['matched_released_only'] += matched and not b
            totals['matched_both'] += matched and b
            totals['matched_neither'] += not matched and not b
        rows.append(row)
    primary_calls = {arm: sum(not feedback['routing'][name][arm]['retained_initial'] for name in payload['order']) for arm in ('released','repaired')}
    summary = {'completed': True, 'model': payload['weights'], 'backend': payload['inference_backend'],
        'paired_seed_observations': len(rows), 'repair_units': len({r['unit'] for r in rows}),
        'historical_commit_clusters': len({r['commit_cluster'] for r in rows}),
        'counts': dict(totals), 'initial_calls': len(initial['initial']), 'distinct_repair_calls': len(final['repairs']),
        'actual_repair_outputs':sum(not r.get('model_output_status') for r in final['repairs'].values()),
        'activated_initial_grader_feedback_contrasts':sum(
            r['initial_feedback_verdicts']['released']!=r['initial_feedback_verdicts']['repaired'] for r in rows),
        'java_language_assertions_enabled':True,
        'primary_policy_extra_calls': primary_calls, 'rows': rows,
        'limits': ['All historical tasks were source-exposed. Public-source memorization is not excluded.',
                   'Two Codec units share a commit. Seeds, layouts, invocations and methods are not independent tasks.',
                   'Qualification is a finite one-fault test-adequacy oracle, not exhaustive semantic correctness.',
                   'Missing model responses are explicit availability failures. They are not fabricated patches or demonstrated semantic code errors.',
                   'Primary policy changes feedback and stopping jointly. Matched ablation is conditional on initial developer-grader discordance.',
                   'The conservative admission policy rejects Java Unicode escapes and method-scaffold escapes. Admission failure does not establish semantically incorrect Java.',
                   'No post-training, swarm improvement, population accuracy, significance, leaderboard rank or competition-winning effect is established.']}
    (args.output / 'SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
    text = ['Gemma 4 E4B paired repair study', '', 'Five source-exposed repair units, four historical commits, two seeds per unit.',
            'Oracle qualification requires developer PASS and complete native fault FAIL.', '',
            'Unit | Seed | Initial qualified | Released final | Repaired final | Matched released',
            '--- | --- | --- | --- | --- | ---']
    for row in rows:
        text.append(' | '.join([row['unit'], str(row['seed']), str(row['initial_oracle_qualified']),
            str(row['arms']['released']['oracle_qualified']), str(row['arms']['repaired']['oracle_qualified']),
            str(row['arms'].get('matched_released',{}).get('oracle_qualified','not applicable'))]))
    text += ['', json.dumps(dict(totals), indent=2), '', *summary['limits']]
    (args.output / 'RESULTS.txt').write_text('\n'.join(text) + '\n')
    print(json.dumps({k: summary[k] for k in ('completed','paired_seed_observations','repair_units','historical_commit_clusters','counts')}))


if __name__ == '__main__':
    main()
