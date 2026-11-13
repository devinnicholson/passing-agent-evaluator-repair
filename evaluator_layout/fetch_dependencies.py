"""Download only public pinned research dependencies. No account or credentials."""

import ast
from hashlib import sha256
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
BASELINE_URL = 'https://raw.githubusercontent.com/iSEngLab/TEBench/5f607183bd9f29b6c740eae76b0489dd0c7556d5/update_evaluation/changed_method_extractor.py'
BASELINE_SHA256 = 'd62db60856a6ede6ecba67170678393c528d8b5f9c6d6cbf61ab58a29a6c42ca'
PREDICATE_SHA256 = 'ab234efdf0ef0a6b735ee588cea352e305256f95df8427474b9a1d0d086c92c2'


def download(url, maximum):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None
    with urllib.request.build_opener(NoRedirect()).open(url, timeout=30) as response:
        result = response.read(maximum + 1)
        if len(result) > maximum:
            raise ValueError('public artifact exceeds size bound')
        return result


def main():
    folder = HERE / 'dependencies'
    folder.mkdir(exist_ok=True)
    for entry in json.loads((HERE / 'DEPENDENCIES.json').read_text()).values():
        path = folder / entry['url'].rsplit('/', 1)[1]
        raw = path.read_bytes() if path.exists() else download(entry['url'], entry['bytes'])
        if len(raw) != entry['bytes'] or sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('dependency digest differs ' + path.name)
        if not path.exists():
            path.write_bytes(raw)
    source = download(BASELINE_URL, 100000)
    if sha256(source).hexdigest() != BASELINE_SHA256:
        raise ValueError('pinned released source digest differs')
    text = source.decode()
    tree = ast.parse(text)
    function = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                    and node.name == '_is_annotated_test_method')
    selected = ast.get_source_segment(text, function) + '\n'
    if sha256(selected.encode()).hexdigest() != PREDICATE_SHA256:
        raise ValueError('selected released predicate digest differs')
    (HERE / 'released_predicate.py').write_text(selected)
    print('Pinned public dependencies and baseline prepared')


if __name__ == '__main__':
    main()
