"""Mechanical Java method-body substitution. Does not change model answers."""
import json
import re

TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)


def masked(source):
    return TOKEN.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), source)


def span(source, name, parameter_hint=None):
    clean = masked(source)
    pattern = r'\b(?:void|boolean|byte\[\]|OrderedProperties)\s+' + re.escape(name) + r'\s*\(([^)]*)\)\s*(?:throws\s+[^{};]+)?\{'
    hits = [m for m in re.finditer(pattern, clean) if parameter_hint is None or parameter_hint in m[1]]
    if len(hits) != 1:
        raise ValueError('ambiguous method declaration ' + name)
    hit = hits[0]
    opening = hit.end() - 1
    depth = 1
    for closing in range(opening + 1, len(clean)):
        depth += (clean[closing] == '{') - (clean[closing] == '}')
        if depth == 0:
            return opening + 1, closing
    raise ValueError('unclosed method body')


def body(source, name, parameter_hint=None):
    start, end = span(source, name, parameter_hint)
    return source[start:end]


def replace(source, name, value, parameter_hint=None):
    start, end = span(source, name, parameter_hint)
    return source[:start] + value + source[end:]


def admit_body(value):
    if not isinstance(value, str) or len(value.encode()) > 24000 or '\\u' in value:
        raise ValueError('body type, size or Unicode escape rejected')
    clean = masked(value)
    depth = 0
    for char in clean:
        depth += (char == '{') - (char == '}')
        if depth < 0:
            raise ValueError('method-body scaffold escape')
    if depth:
        raise ValueError('unbalanced method body')
    # A type literal such as NoSuchMethodException.class is legitimate assertion
    # syntax. Declarations remain forbidden, as do loading and introspection.
    forbidden = r'(?<![.\w])class\b|\b(?:interface|package|import|enum|record|System|Runtime|ProcessBuilder|Thread|ClassLoader|SecurityManager|getClass|forName|getenv|getProperty|setProperty|Files|Paths|File|FileReader|FileWriter|URL|Socket|ServerSocket|Unsafe|ServiceLoader|loadLibrary|exit|halt)\b|\bjava\s*\.\s*(?:io|nio|net|security)\b|\bjava\s*\.\s*lang\s*\.\s*reflect\b'
    if re.search(forbidden, clean):
        raise ValueError('body outside test-only execution policy')
    return value


def decode_answer(text):
    text = text.strip()
    for prefix in ('```json\n', '```\n'):
        if text.startswith(prefix) and text.endswith('\n```'):
            text = text[len(prefix):-4]
            break
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(text, object_pairs_hook=pairs)
    if not isinstance(value, dict) or set(value) != {'body'}:
        raise ValueError('answer must have exactly the body key')
    return admit_body(value['body'])
