"""Fetch checksum-pinned TEBench source directly from its upstream repository."""
import ast
from hashlib import sha256
from pathlib import Path
from typing import Dict, Set, Tuple
import urllib.request

REVISION = '5f607183bd9f29b6c740eae76b0489dd0c7556d5'
SOURCES = {
    'identification': ('evaluate_user_identification.py', 18723, 'e0d03cb23dc915be300b6f77b22fe4dba88d6d56cea9964e1033664ce3911497'),
    'selection': ('update_evaluation/changed_method_extractor.py', 18793, 'd62db60856a6ede6ecba67170678393c528d8b5f9c6d6cbf61ab58a29a6c42ca'),
}
FUNCTIONS = {
    'extract_user_identified_tests': 'aef826628a2722e13fa6e6dd1c7e850f9c27b4037569d2683ff2e3446c95054a',
    'calculate_metrics': 'ac76d07cc67576bc7bfad8606906830973434f41218e03d079c2ebe6ee0ff2ae',
    '_is_annotated_test_method': 'ab234efdf0ef0a6b735ee588cea352e305256f95df8427474b9a1d0d086c92c2',
}


def source_bytes(label, cache=Path('.tebench-upstream')):
    relative, size, expected = SOURCES[label]
    cache = Path(cache)
    path = cache / relative.replace('/', '__')
    if path.exists():
        raw = path.read_bytes()
    else:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        url = 'https://raw.githubusercontent.com/iSEngLab/TEBench/' + REVISION + '/' + relative
        with urllib.request.build_opener(NoRedirect()).open(url, timeout=30) as response:
            raw = response.read(size + 1)
    if len(raw) != size or sha256(raw).hexdigest() != expected:
        raise ValueError('Pinned TEBench source differs: ' + relative)
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return raw


def selected_function(label, name, cache=Path('.tebench-upstream')):
    source = source_bytes(label, cache).decode('utf-8')
    matches = [node for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError('Expected one upstream function: ' + name)
    selected = ast.get_source_segment(source, matches[0]) + '\n'
    if sha256(selected.encode()).hexdigest() != FUNCTIONS[name]:
        raise ValueError('Pinned upstream function differs: ' + name)
    return selected


def load_identification_functions(cache=Path('.tebench-upstream')):
    namespace = {'Dict': Dict, 'Set': Set, 'Tuple': Tuple}
    for name in ('extract_user_identified_tests', 'calculate_metrics'):
        selected = selected_function('identification', name, cache)
        exec(compile(selected, '<checksum-verified-upstream>', 'exec'), namespace)
    return namespace


def prepare_predicate(path, cache=Path('.tebench-upstream')):
    selected = selected_function('selection', '_is_annotated_test_method', cache)
    Path(path).write_text(selected)
    return sha256(selected.encode()).hexdigest()


if __name__ == '__main__':
    load_identification_functions()
    prepare_predicate(Path('.tebench-upstream/released_predicate.py'))
    print('Pinned upstream functions verified and cached locally')
