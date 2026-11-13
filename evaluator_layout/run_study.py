"""CPU-only source-layout audit. Requires Python 3.12, Java 17 and pinned JARs."""

import argparse
import ast
import base64
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import subprocess
import time

from execution_contract import assess

HERE = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def classmap(folder):
    return {str(path.relative_to(folder)): digest(path) for path in sorted(folder.rglob('*.class'))}


def identity(method):
    return method['class'] + '#' + method['name'] + '(' + ','.join(method['parameters']) + ')'


def method_path(method):
    return 'src/test/java/' + method['class'].replace('.', '/') + '.java'


def declaration(source, method):
    lines = source.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if re.search(r'\bvoid\s+' + re.escape(method['name']) + r'\s*\(', line)]
    if len(hits) != 1:
        raise ValueError('ambiguous frozen declaration ' + method['name'])
    index = hits[0]
    return lines, index


def transform(source, methods, layout):
    if layout == 'original':
        return source
    replacements = []
    for method in methods:
        lines, index = declaration(source, method)
        line = lines[index].strip()
        if line.startswith('@Test '):
            start = index
            method_line = line[len('@Test '):]
        else:
            method_line = line
            annotation = '@ParameterizedTest' if method['parameters'] else '@Test'
            matches = [i for i in range(max(0, index - 28), index)
                       if lines[i].strip() == annotation]
            if not matches:
                raise ValueError('frozen annotation prefix absent')
            start = matches[-1]
        annotations = ['@Test']
        if method['parameters']:
            values = ', '.join(json.dumps(value) for value in method['values'])
            annotations = ['@ParameterizedTest', '@ValueSource(strings = {' + values + '})']
        if layout == 'qualified':
            mapping = {'@Test': '@org.junit.jupiter.api.Test',
                       '@ParameterizedTest': '@org.junit.jupiter.params.ParameterizedTest',
                       '@ValueSource': '@org.junit.jupiter.params.provider.ValueSource'}
            annotations = [next(full + a[len(short):] for short, full in mapping.items()
                                if a == short or a.startswith(short + '(')) for a in annotations]
        if layout == 'multiline':
            annotations = [a + '(\n    )' if '(' not in a else a.replace('{', '{\n        ').replace('})', '\n    })')
                           for a in annotations]
        prefix = '\n    '.join(annotations)
        if layout == 'inline':
            replacement = '    ' + ' '.join(annotations) + ' ' + method_line + '\n'
        else:
            gap = '\n' * 21 if layout == 'gap20' else '\n'
            middle = '    /* evaluator layout control */\n' if layout == 'block_comment' else ''
            replacement = '    ' + prefix + gap + middle + '    ' + method_line + '\n'
        replacements.append((start, index + 1, replacement))
    lines = source.splitlines(keepends=True)
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = [replacement]
    return ''.join(lines)


def owned(path):
    path.mkdir(parents=True, exist_ok=False)
    path.chmod(0o755)
    if os.geteuid() == 0:
        os.chown(path, 65534, 65534)


def freeze(path):
    for entry in (path, *path.rglob('*')):
        entry.chmod(0o555 if entry.is_dir() else 0o444)


def execute(argv, folder, stem, java_home, seconds=20, allowed=(0,)):
    disable_network = runpy.run_path(str(HERE / 'offline_network.py'))['disable_child_network']
    kwargs = {'preexec_fn': disable_network}
    if os.geteuid() == 0:
        kwargs.update(user=65534, group=65534, extra_groups=[])
    process = subprocess.Popen(argv, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
        env={'PATH': str(java_home / 'bin') + ':/usr/bin:/bin', 'LANG': 'C.UTF-8'}, **kwargs)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    (folder / (stem + '.stdout')).write_text(stdout[:250000])
    (folder / (stem + '.stderr')).write_text(stderr[:250000])
    result = {'argv': list(map(str, argv)), 'returncode': process.returncode,
              'timed_out': timed_out, 'output_limited': len(stdout) + len(stderr) > 500000}
    (folder / (stem + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    if timed_out or result['output_limited'] or process.returncode not in allowed:
        raise RuntimeError(stem + ' operational failure ' + str(process.returncode))
    return result, stdout


def native_records(stdout):
    records, containers, skipped = [], [], []
    seen = set()
    for line in stdout.splitlines():
        fields = line.split('\t')
        if fields[0] == 'RESULT' and len(fields) == 5:
            uid = base64.b64decode(fields[3], validate=True).decode()
            if uid in seen:
                raise ValueError('duplicate native invocation identity')
            seen.add(uid)
            records.append({'method': fields[1], 'status': fields[2], 'uid': uid,
                            'message': base64.b64decode(fields[4], validate=True).decode()})
        elif fields[0] == 'CONTAINER':
            containers.append(fields[1:])
        elif fields[0] == 'SKIP':
            skipped.append(fields[1:])
        elif line.strip():
            raise ValueError('unexpected native output ' + line[:100])
    return records, containers, skipped


def check_origins(path, expected):
    log = path.read_text()
    from urllib.parse import unquote, urlsplit
    for name, folder in expected.items():
        marker = '[class,load] ' + name + ' source: '
        matches = [line.split(' source: ', 1)[1] for line in log.splitlines() if marker in line]
        if len(matches) != 1:
            raise ValueError('missing or duplicate class origin ' + name)
        uri = urlsplit(matches[0])
        if uri.scheme != 'file' or uri.netloc or uri.query or uri.fragment or Path(unquote(uri.path)).resolve() != folder.resolve():
            raise ValueError('incorrect class origin ' + name)


def study(case_name, output, dependencies, java_home, deadline_seconds=220):
    start_time = time.monotonic()
    plan = json.loads((HERE / 'PLAN.json').read_text())
    case = plan['cases'][case_name]
    output.mkdir(mode=0o755)
    report = {'completed': False, 'case': case_name, 'plan_sha256': digest(HERE / 'PLAN.json'),
              'candidate_origin': plan['candidate_origin'], 'scope': plan['scope'],
              'debug_tables': 'disabled equally with -g:none', 'variants': [], 'errors': []}
    def save():
        (output / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    tree = ast.parse((HERE / 'released_predicate.py').read_text())
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError('released predicate scope differs')
    namespace = {'re': re, 'Dict': dict}
    exec(compile(tree, '<pinned released predicate>', 'exec'), namespace)
    predicate = namespace['_is_annotated_test_method']
    project = HERE / 'cases' / case_name / 'project'
    project_map = {str(path.relative_to(project)): digest(path) for path in sorted(project.rglob('*')) if path.is_file()}
    (output / 'SOURCE_FILES.json').write_text(json.dumps(project_map, indent=2) + '\n')
    deps = sorted(dependencies.glob('*.jar'))
    receipts = json.loads((HERE / 'DEPENDENCIES.json').read_text())
    if len(deps) != len(receipts):
        raise ValueError('dependency count differs')
    if {digest(path) for path in deps} != {entry['sha256'] for entry in receipts.values()}:
        raise ValueError('dependency artifact digest differs')
    dep_cp = ':'.join(map(str, deps))
    javac, java = str(java_home / 'bin/javac'), str(java_home / 'bin/java')
    execute([java, '-version'], output, 'java_version', java_home)
    production = output / 'production'
    owned(production)
    production_sources = sorted((project / 'src/main/java').rglob('*.java'))
    execute([javac, '-J-Xmx384m', '--release', '8', '-g:none', '-proc:none', '-encoding', 'UTF-8',
             '-cp', dep_cp, '-d', str(production), *map(str, production_sources)],
            output, 'production_compile', java_home, seconds=35)
    production_map = classmap(production)
    freeze(production)
    probe = output / 'probe'
    owned(probe)
    execute([javac, '-J-Xmx256m', '--release', '8', '-g:none', '-proc:none', '-cp', dep_cp,
             '-d', str(probe), str(HERE / 'SuiteProbe.java')], output, 'probe_compile', java_home)
    freeze(probe)
    required = {identity(method): method['expected_invocations'] for method in case['methods']}
    classes = sorted({method['class'] for method in case['methods']})
    originals = {}
    for layout in plan['layouts']:
        for role in ('gold', 'candidate'):
            if time.monotonic() - start_time > deadline_seconds:
                report['errors'].append('study deadline reached before ' + layout + '/' + role)
                save()
                return report
            folder = output / (layout + '-' + role)
            folder.mkdir(mode=0o755)
            row = {'layout': layout, 'role': role, 'qualified': False, 'arms': [], 'errors': []}
            report['variants'].append(row)
            save()
            try:
                src = folder / 'src'
                src.mkdir(mode=0o755)
                sources = {}
                for relative in sorted({method_path(method) for method in case['methods']}):
                    original = (project / relative).read_text()
                    candidate_file = HERE / 'cases' / case_name / 'candidate' / Path(relative).name
                    if role == 'candidate' and candidate_file.exists():
                        original = candidate_file.read_text()
                    methods = [method for method in case['methods'] if method_path(method) == relative]
                    changed = transform(original, methods, layout)
                    path = src / Path(relative).name
                    path.write_text(changed)
                    sources[relative] = changed
                row['transformed_source_sha256'] = {name: sha256(text.encode()).hexdigest() for name, text in sources.items()}
                tests = folder / 'classes'
                owned(tests)
                execute([javac, '-J-Xmx384m', '--release', '8', '-g:none', '-proc:none', '-encoding', 'UTF-8',
                         '-cp', str(production) + ':' + dep_cp,
                         '-sourcepath', str(project / 'src/test/java'), '-d', str(tests),
                         *map(str, sorted(src.glob('*.java')))], folder, 'test_compile', java_home, seconds=30)
                fixed = classmap(tests)
                freeze(tests)
                if layout == 'original':
                    originals[role] = fixed
                row['classfiles'] = fixed
                row['qualified'] = fixed == originals[role]
                if not row['qualified']:
                    row['errors'].append('compiled classfiles differ; variant excluded from invariance claims')
                    save()
                    continue
                cp = ':'.join([str(tests), str(production), str(probe), dep_cp,
                               str(project / 'src/test/resources'), str(project / 'src/main/resources')])
                cmd, stdout = execute([java, '-Xmx256m', '-cp', cp, 'SuiteProbe', 'inventory', *classes],
                                      folder, 'inventory', java_home)
                discovered = [line.split('\t', 1)[1] for line in stdout.splitlines() if line.startswith('METHOD\t')]
                if len(discovered) != len(set(discovered)) or set(required) - set(discovered):
                    raise ValueError('compiled inventory does not contain each frozen required method')
                helper_names = ('validateScriptContents', 'validateXmlScriptContents') if case_name == 'jsoup' else ('assertBase64DecodingOfTrailingBits', 'testDecodeEncode')
                if any(re.search('#' + name + r'\(', item) for item in discovered for name in helper_names):
                    raise ValueError('unannotated helper entered test inventory')
                row['compiled_inventory'] = discovered
                released, same_line = [], []
                for method in case['methods']:
                    source = sources[method_path(method)]
                    lines, index = declaration(source, method)
                    retained = predicate(None, source, {'start_line': index + 1})
                    if retained:
                        released.append(identity(method))
                    on_line = bool(re.match(r'^\s*@(Test|ParameterizedTest|RepeatedTest)\b', lines[index]))
                    if retained or on_line:
                        same_line.append(identity(method))
                strategies = {'released': sorted(released), 'same_line_patch': sorted(same_line),
                              'compiled_inventory': sorted(set(required) & set(discovered))}
                for strategy in plan['strategies']:
                    arm = folder / strategy
                    arm.mkdir(mode=0o755)
                    selectors = strategies[strategy]
                    (arm / 'selectors.txt').write_text(''.join(item + '\n' for item in selectors))
                    origin_path = arm / 'classload.log'
                    owned(arm / 'native')
                    # The class log is written by the unprivileged child.
                    origin_path = arm / 'native/classload.log'
                    command, stdout = execute([java, '-Xmx256m', '-Xlog:class+load=info:file=' + str(origin_path),
                        '-cp', cp, 'SuiteProbe', 'execute', str(arm / 'selectors.txt')],
                        arm, 'native', java_home, seconds=15, allowed=(0, 1))
                    records, containers, skipped = native_records(stdout)
                    if records:
                        expected_origins = {name: tests for name in {item['method'].split('#')[0] for item in records}}
                        expected_origins['org.jsoup.Jsoup' if case_name == 'jsoup' else 'org.apache.commons.codec.binary.Base64'] = production
                        check_origins(origin_path, expected_origins)
                    failed = sum(item['status'] == 'FAILED' for item in records)
                    native_verdict = ('EMPTY' if not records else
                        ('INVALID' if containers or skipped or any(x['status'] == 'ABORTED' for x in records)
                         else ('FAIL' if failed else 'PASS')))
                    contract = assess(required, records, command['returncode'], containers, skipped)
                    row['arms'].append({'strategy': strategy, 'selected': selectors, 'native_verdict': native_verdict,
                        'native_exit': command['returncode'], 'started': len(records), 'failed': failed,
                        'passed': sum(item['status'] == 'SUCCESSFUL' for item in records),
                        'records': records, 'containers': containers, 'skipped': skipped, 'contract': contract})
                    if classmap(tests) != fixed or classmap(production) != production_map:
                        raise ValueError('compiled fixture changed during native execution')
                full = row['arms'][-1]
                row['complete_control_matches'] = (
                    full['contract']['verdict'] == ('PASS' if role == 'gold' else 'FAIL')
                    and full['started'] == sum(required.values())
                    and full['failed'] == case['expected_' + role + '_failures'])
            except Exception as error:
                row['errors'].append(type(error).__name__ + ': ' + str(error))
            save()
    report['production_classfiles'] = production_map
    report['required_invocations'] = required
    report['completed'] = True
    report['all_variants_qualified'] = len(report['variants']) == 14 and all(row['qualified'] for row in report['variants'])
    report['all_complete_controls_match'] = all(row.get('complete_control_matches', False) for row in report['variants'])
    report['native_execution_count'] = sum(len(row['arms']) for row in report['variants'])
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=('jsoup', 'codec'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dependencies', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    args = parser.parse_args()
    report = study(args.case, args.output.resolve(), args.dependencies.resolve(), args.java_home.resolve())
    print(json.dumps({key: report.get(key) for key in ('case', 'completed', 'all_variants_qualified',
        'all_complete_controls_match', 'native_execution_count', 'errors')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
