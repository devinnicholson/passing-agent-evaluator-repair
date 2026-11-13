"""Fetch only the eight public, hash-pinned native grading dependencies."""
import argparse
from hashlib import sha256
import json
import runpy
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((Path(__file__).parent / 'DEPENDENCIES.json').read_text())
    for name, spec in manifest.items():
        path = args.output / (name + '.jar')
        if path.exists():
            raw = path.read_bytes()
        else:
            if not spec['url'].startswith('https://repo.maven.apache.org/maven2/'):
                raise ValueError('unexpected dependency host')
            with urllib.request.urlopen(spec['url'], timeout=30) as response:
                raw = response.read(spec['bytes'] + 1)
        if len(raw) != spec['bytes'] or sha256(raw).hexdigest() != spec['sha256']:
            raise ValueError('dependency size or digest mismatch ' + name)
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(raw)
        print(name + ' verified')
    helper = runpy.run_path(str(Path(__file__).with_name('fetch_tebench.py')))
    helper['prepare_predicate'](Path(__file__).with_name('released_predicate.py'))


if __name__ == '__main__':
    main()
