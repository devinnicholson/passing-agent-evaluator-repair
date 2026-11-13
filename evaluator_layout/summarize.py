"""Verify saved native transcripts and summarize the finite layout study."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from execution_contract import assess
from run_study import native_records

HERE = Path(__file__).resolve().parent


def summarize(paths):
    plan = json.loads((HERE / 'PLAN.json').read_text())
    result = {'scope': plan['scope'], 'candidate_origin': plan['candidate_origin'],
              'independent_tasks': 2, 'compiled_fixtures': 0, 'nonoriginal_fixtures': 0,
              'native_executions': 0, 'cases': [], 'strategies': {}}
    counters = {name: Counter() for name in plan['strategies']}
    for case_name in ('jsoup', 'codec'):
        path = paths[case_name]
        with tarfile.open(path) as archive:
            wrapper = json.load(archive.extractfile('REPORT.json'))
            assert wrapper['completed'] and wrapper['admitted']
            report_bytes = archive.extractfile('study/REPORT.json').read()
            report = json.loads(report_bytes)
            assert report['case'] == case_name and report['completed']
            assert report['plan_sha256'] == sha256((HERE / 'PLAN.json').read_bytes()).hexdigest()
            assert report['all_variants_qualified'] and report['all_complete_controls_match']
            assert report['errors'] == [] and report['native_execution_count'] == 42
            assert len(report['variants']) == 14
            assert [(row['layout'], row['role']) for row in report['variants']] == [
                (layout, role) for layout in plan['layouts'] for role in ('gold', 'candidate')]
            baseline = {row['role']: row['classfiles'] for row in report['variants'] if row['layout'] == 'original'}
            rows = []
            complete_failure_messages = None
            for row in report['variants']:
                assert row['qualified'] and row['classfiles'] == baseline[row['role']]
                assert not row['errors'] and row['complete_control_matches']
                assert [arm['strategy'] for arm in row['arms']] == plan['strategies']
                inventory_path = 'study/' + row['layout'] + '-' + row['role'] + '/inventory.stdout'
                inventory = archive.extractfile(inventory_path).read().decode()
                assert [line.split('\t', 1)[1] for line in inventory.splitlines()] == row['compiled_inventory']
                for arm in row['arms']:
                    prefix = 'study/' + row['layout'] + '-' + row['role'] + '/' + arm['strategy']
                    stdout = archive.extractfile(prefix + '/native.stdout').read().decode()
                    records, containers, skipped = native_records(stdout)
                    assert records == arm['records'] and containers == arm['containers'] and skipped == arm['skipped']
                    command = json.load(archive.extractfile(prefix + '/native.json'))
                    assert not command['timed_out'] and not command['output_limited']
                    assert command['returncode'] == arm['native_exit']
                    contract = assess(report['required_invocations'], records, command['returncode'], containers, skipped)
                    assert contract == arm['contract']
                    assert len(records) == arm['started']
                    assert sum(record['status'] == 'FAILED' for record in records) == arm['failed']
                    assert sum(record['status'] == 'SUCCESSFUL' for record in records) == arm['passed']
                    assert arm['native_verdict'] == (
                        'EMPTY' if not records else 'INVALID' if containers or skipped else
                        'FAIL' if arm['failed'] else 'PASS')
                    if arm['strategy'] == 'compiled_inventory':
                        assert arm['started'] == sum(report['required_invocations'].values())
                        expected_failed = plan['cases'][case_name]['expected_' + row['role'] + '_failures']
                        assert arm['failed'] == expected_failed
                        assert contract['verdict'] == ('PASS' if row['role'] == 'gold' else 'FAIL')
                        if row['role'] == 'candidate':
                            messages = sorted(record['message'] for record in records if record['status'] == 'FAILED')
                            assert all(message.startswith('org.opentest4j.AssertionFailedError: ') for message in messages)
                            if complete_failure_messages is None:
                                complete_failure_messages = messages
                            assert messages == complete_failure_messages
                    # Role-paired selection comparisons are counted once per task-layout.
                    count = counters[arm['strategy']]
                    if row['role'] == 'candidate':
                        count['task_layouts'] += 1
                        count['complete_task_layouts'] += contract['verdict'] != 'INCOMPLETE'
                        count['false_native_passes'] += arm['native_verdict'] == 'PASS'
                        count['empty_selections'] += arm['native_verdict'] == 'EMPTY'
                        count['correct_native_rejections'] += arm['native_verdict'] == 'FAIL'
                        count['contract_incomplete_candidates'] += contract['verdict'] == 'INCOMPLETE'
                        count['false_contract_passes'] += contract['verdict'] == 'PASS'
                    else:
                        count['gold_layouts'] += 1
                        count['complete_gold_passes'] += contract['verdict'] == 'PASS'
                        count['gold_failures'] += arm['native_verdict'] == 'FAIL'
                    rows.append({'case': case_name, 'layout': row['layout'], 'role': row['role'],
                                 'strategy': arm['strategy'], 'selected_methods': len(arm['selected']),
                                 'started': arm['started'], 'passed': arm['passed'], 'failed': arm['failed'],
                                 'native_verdict': arm['native_verdict'], 'contract_verdict': contract['verdict']})
                result['compiled_fixtures'] += 1
                result['nonoriginal_fixtures'] += row['layout'] != 'original'
            result['native_executions'] += report['native_execution_count']
            result['cases'].append({'case': case_name, 'source_exposed': True,
                'instance_id': plan['cases'][case_name]['instance_id'],
                'archive_sha256': sha256(path.read_bytes()).hexdigest(),
                'report_sha256': sha256(report_bytes).hexdigest(), 'rows': rows,
                'required_invocations': report['required_invocations'],
                'complete_candidate_failure_messages': complete_failure_messages})
    result['strategies'] = {name: dict(counts) for name, counts in counters.items()}
    result['all_contract_false_passes_zero'] = all(counts['false_contract_passes'] == 0 for counts in counters.values())
    result['training'] = result['gpu_inference'] = 'paused'
    result['submitted'] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jsoup', type=Path, required=True)
    parser.add_argument('--codec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize({'jsoup': args.jsoup, 'codec': args.codec})
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['strategies'], indent=2))


if __name__ == '__main__':
    main()
