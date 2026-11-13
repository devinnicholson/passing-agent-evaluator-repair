"""Explicit finite invocation-count contract. Unknown counts cannot be certified."""

from collections import Counter


def assess(required_counts, records, native_exit, containers=(), skipped=()):
    observed = Counter(row['method'] for row in records)
    reasons = []
    if not required_counts or any(type(n) is not int or n <= 0 for n in required_counts.values()):
        reasons.append('missing_or_unknown_required_counts')
    for method, expected in required_counts.items():
        if observed[method] != expected:
            reasons.append('invocation_count:' + method)
    if set(observed) - set(required_counts):
        reasons.append('unexpected_method')
    if containers or skipped or any(row['status'] not in ('SUCCESSFUL', 'FAILED') for row in records):
        reasons.append('container_error_skip_or_abort')
    failures = sum(row['status'] == 'FAILED' for row in records)
    if native_exit != (1 if failures else 0):
        reasons.append('native_exit_inconsistent')
    verdict = 'INCOMPLETE' if reasons else ('FAIL' if failures else 'PASS')
    return {'verdict': verdict, 'reasons': reasons,
            'expected_invocations': dict(required_counts), 'observed_invocations': dict(observed),
            'passed': sum(row['status'] == 'SUCCESSFUL' for row in records), 'failed': failures}
