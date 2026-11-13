"""Azure-only native qualification and paired grading of constrained Gemma patches."""
import argparse
import ast
import base64
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

from source_tools import admit_body, decode_answer, replace, span
from execution_contract import assess
from offline_network import disable_child_network

HERE = Path(__file__).resolve().parent
JAVA = Path('/usr/lib/jvm/java-17-openjdk-amd64/bin')


def identity(method):
    return method['class'] + '#' + method['name'] + '(' + ','.join(method['parameters']) + ')'


def execute(argv, folder, stem, timeout=30):
    process = subprocess.Popen(list(map(str, argv)), cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True, env={'PATH': str(JAVA) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8'},
        preexec_fn=disable_child_network)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    result = {'returncode': process.returncode, 'timed_out': timed_out, 'output_limited': len(stdout) + len(stderr) > 500000}
    (folder / (stem + '.stdout')).write_text(stdout[:250000])
    (folder / (stem + '.stderr')).write_text(stderr[:250000])
    (folder / (stem + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    if timed_out or result['output_limited']:
        raise RuntimeError(stem + ' operational failure')
    return result, stdout, stderr


def native(stdout):
    records, containers, skipped = [], [], []
    seen = set()
    for line in stdout.splitlines():
        fields = line.split('\t')
        if fields[0] == 'RESULT' and len(fields) == 5:
            uid = base64.b64decode(fields[3], validate=True).decode()
            if uid in seen:
                raise ValueError('duplicate native invocation')
            seen.add(uid)
            records.append({'method': fields[1], 'status': fields[2], 'uid': uid,
                            'message': base64.b64decode(fields[4], validate=True).decode()})
        elif fields[0] == 'CONTAINER':
            containers.append(fields[1:])
        elif fields[0] == 'SKIP':
            skipped.append(fields[1:])
        elif line.strip():
            raise ValueError('unexpected runner output ' + line[:100])
    return records, containers, skipped


def filemap(folder):
    return {str(p.relative_to(folder)): sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*.class'))}


def production(case, output, cp):
    result = {}
    project = case / 'project'
    for variant in ('developer', 'fault'):
        dest = output / ('production_' + variant)
        dest.mkdir()
        sources = []
        for path in sorted((project / 'src/main/java').rglob('*.java')):
            fault = case / 'fault' / path.relative_to(project)
            sources.append(fault if variant == 'fault' and fault.exists() else path)
        receipt, _, _ = execute([JAVA / 'javac', '-J-Xmx384m', '--release', '8', '-g:none', '-proc:none', '-encoding', 'UTF-8',
             '-cp', cp, '-d', dest, *sources], output, 'production_' + variant, 65)
        if receipt['returncode']:
            raise RuntimeError('production compilation failed ' + variant)
        result[variant] = dest
    return result


def probe(output, cp):
    dest = output / 'probe'
    dest.mkdir()
    receipt, _, _ = execute([JAVA / 'javac', '-J-Xmx256m', '--release', '8', '-g:none', '-proc:none', '-cp', cp,
                             '-d', dest, HERE / 'SuiteProbe.java', HERE / 'JavaAssertionControl.java'], output, 'probe_compile')
    if receipt['returncode']:
        raise RuntimeError('probe compilation failed')
    selector = output / 'assertion_control.selectors.txt'
    selector.write_text('JavaAssertionControl#deliberatelyFalse()\n')
    receipt, stdout, _ = execute([JAVA / 'java', '-Xmx256m', '-ea', '-cp', str(dest) + ':' + cp,
        'SuiteProbe', 'execute', selector], output, 'assertion_control')
    records, containers, skipped = native(stdout)
    contract = assess({'JavaAssertionControl#deliberatelyFalse()': 1}, records, receipt['returncode'], containers, skipped)
    if (contract['verdict'] != 'FAIL' or len(records) != 1 or
            'java.lang.AssertionError: AUTHORED_JAVA_ASSERTION_CONTROL' not in records[0]['message']):
        raise RuntimeError('Java assertion positive control was not observed as a native failure')
    (output / 'ASSERTION_CONTROL.json').write_text(json.dumps(contract, indent=2) + '\n')
    receipt, _, stderr = execute([JAVA / 'java', '-Xmx256m', '-cp', str(dest) + ':' + cp,
        'SuiteProbe', 'inventory', 'JavaAssertionControl'], output, 'assertion_disabled_refusal')
    if receipt['returncode'] == 0 or 'Java assertions must be enabled with -ea' not in stderr:
        raise RuntimeError('misconfigured assertion-disabled runner was not refused')
    return dest


def run_native(folder, selectors, required, classes, production_dir, probe_dir, cp, testroot, stem):
    selected = folder / (stem + '.selectors.txt')
    selected.write_text(''.join(s + '\n' for s in selectors))
    runtime_cp = ':'.join(map(str, [classes, production_dir, probe_dir, cp]))
    receipt, stdout, _ = execute([JAVA / 'java', '-Xmx256m', '-ea', '-Djava.awt.headless=true', '-cp', runtime_cp,
                                  'SuiteProbe', 'execute', selected], folder, stem, 20)
    records, containers, skipped = native(stdout)
    contract = assess(required, records, receipt['returncode'], containers, skipped)
    return {'selected': selectors, 'started': len(records), 'failed': sum(r['status'] == 'FAILED' for r in records),
            'records': records, 'containers': containers, 'skipped': skipped, 'native_exit': receipt['returncode'],
            'contract': contract}


def grade(unit, meta, value, folder, variants, probe_dir, cp, raw=False):
    folder.mkdir()
    result = {'unit': unit, 'status': 'ungraded', 'oracle_qualified': False}
    try:
        answer = decode_answer(value) if raw else admit_body(value)
    except Exception as error:
        result.update(status='REJECTED', error=type(error).__name__ + ' ' + str(error))
        result['feedback'] = {arm: {'verdict': 'REJECTED', 'error': result['error']} for arm in ('released', 'repaired')}
        return result
    case = HERE / 'cases' / unit
    text = replace((case / 'scaffold.java').read_text(), meta['target']['name'], answer)
    source = folder / Path(meta['test_source']).name
    source.write_text(text)
    classes = folder / 'classes'
    classes.mkdir()
    project = case / 'project'
    paths = [source]
    for method in meta['controls']:
        relative = 'src/test/java/' + method['class'].replace('.', '/') + '.java'
        if relative != meta['test_source']:
            paths.append(project / relative)
    receipt, _, stderr = execute([JAVA / 'javac', '-J-Xmx384m', '--release', '8', '-g:none', '-proc:none', '-encoding', 'UTF-8',
        '-cp', str(variants['developer']) + ':' + cp, '-sourcepath', project / 'src/test/java', '-d', classes, *paths], folder, 'test_compile', 40)
    result['compile'] = receipt
    if receipt['returncode']:
        result.update(status='COMPILE_ERROR', error=stderr[-6000:])
        result['feedback'] = {arm: {'verdict': 'COMPILE_ERROR', 'error': result['error']} for arm in ('released', 'repaired')}
        return result
    required_methods = [meta['target'], *meta['controls']]
    required = {identity(m): m['count'] for m in required_methods}
    cls_names = sorted({m['class'] for m in required_methods})
    runtime_cp = ':'.join(map(str, [classes, variants['developer'], probe_dir, cp]))
    inventory_receipt, stdout, _ = execute([JAVA / 'java', '-Xmx256m', '-ea', '-Djava.awt.headless=true', '-cp', runtime_cp,
                                           'SuiteProbe', 'inventory', *cls_names], folder, 'inventory')
    inventory = [line.split('\t', 1)[1] for line in stdout.splitlines() if line.startswith('METHOD\t')]
    if inventory_receipt['returncode'] or set(required) - set(inventory):
        raise RuntimeError('compiled inventory failed or lost a required method')
    tree = ast.parse((HERE / 'released_predicate.py').read_text())
    namespace = {'re': re, 'Dict': dict}
    exec(compile(tree, '<pinned predicate>', 'exec'), namespace)
    released = []
    for method in required_methods:
        relative = 'src/test/java/' + method['class'].replace('.', '/') + '.java'
        src = text if relative == meta['test_source'] else (project / relative).read_text()
        start, _ = span(src, method['name'])
        index = src[:start].count('\n') + 1
        if namespace['_is_annotated_test_method'](None, src, {'start_line': index}):
            released.append(identity(method))
    result['arms'] = {}
    for arm, selectors in [('released', sorted(released)), ('repaired', sorted(required))]:
        observed = run_native(folder, selectors, required, classes, variants['developer'], probe_dir, cp, project, arm)
        own_required = {k: required[k] for k in selectors}
        own_contract = assess(own_required, observed['records'], observed['native_exit'], observed['containers'], observed['skipped'])
        verdict = ('EMPTY' if not selectors else own_contract['verdict']) if arm == 'released' else observed['contract']['verdict']
        observed['verdict'] = verdict
        result['arms'][arm] = observed
    target_required = {identity(meta['target']): meta['target']['count']}
    oracle = {v: run_native(folder, list(target_required), target_required, classes, variants[v], probe_dir, cp, project, 'oracle_' + v)
              for v in ('developer', 'fault')}
    result['oracle'] = oracle
    result['oracle_qualified'] = oracle['developer']['contract']['verdict'] == 'PASS' and oracle['fault']['contract']['verdict'] == 'FAIL'
    result['status'] = 'GRADED'
    result['feedback'] = {arm: {'verdict': row['verdict'], 'selected': row['selected'], 'started': row['started'], 'failed': row['failed'],
                               'failures': [{'method': r['method'], 'message': r['message'][:2000]} for r in row['records'] if r['status'] != 'SUCCESSFUL']}
                          for arm, row in result['arms'].items()}
    result['classfiles'] = filemap(classes)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--units', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--dependencies', required=True, type=Path)
    parser.add_argument('--responses', type=Path)
    args = parser.parse_args()
    args.output.mkdir()
    plan = json.loads((HERE / 'PLAN.json').read_text())
    receipts = json.loads((HERE / 'DEPENDENCIES.json').read_text())
    jars = sorted(args.dependencies.glob('*.jar'))
    if {sha256(p.read_bytes()).hexdigest() for p in jars} != {r['sha256'] for r in receipts.values()} or len(jars) != len(receipts):
        raise ValueError('dependency closure mismatch')
    cp = ':'.join(map(str, jars))
    report = {'completed': False, 'mode': 'grading' if args.responses else 'qualification', 'units': {},
              'plan_sha256': sha256((HERE / 'PLAN.json').read_bytes()).hexdigest(), 'training': False}
    responses = json.loads(args.responses.read_text()) if args.responses else None
    def save():
        (args.output / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    for unit in args.units.split(','):
        dest = args.output / unit
        dest.mkdir()
        row = {'qualified': False, 'errors': [], 'candidates': {}}
        report['units'][unit] = row
        save()
        try:
            meta = plan['units'][unit]
            variants = production(HERE / 'cases' / unit, dest, cp)
            probe_dir = probe(dest, cp)
            values = ({k: v for k,v in responses.items() if k.startswith(unit + '-')}
                      if responses is not None else {'gold': (HERE / 'cases' / unit / 'GOLD_BODY.txt').read_text(),
                        'stale': (HERE / 'cases' / unit / 'STALE_BODY.txt').read_text(), 'vacuous': '\n'})
            for label, value in values.items():
                row['candidates'][label] = grade(unit, meta, value, dest / label, variants, probe_dir, cp, raw=responses is not None)
                save()
            if responses is None:
                c = row['candidates']
                row['qualified'] = (c['gold']['oracle_qualified'] and not c['vacuous']['oracle_qualified'] and
                    c['vacuous']['oracle']['developer']['contract']['verdict'] == 'PASS' and
                    c['vacuous']['oracle']['fault']['contract']['verdict'] == 'PASS' and not c['stale']['oracle_qualified'])
            row['production_classfiles'] = {k: filemap(v) for k,v in variants.items()}
        except Exception as error:
            row['errors'].append(type(error).__name__ + ' ' + str(error))
        save()
    report['completed'] = True
    save()
    print(json.dumps({'completed': True, 'units': {k: {'qualified': v['qualified'], 'errors': v['errors']} for k,v in report['units'].items()}}))


if __name__ == '__main__':
    main()
