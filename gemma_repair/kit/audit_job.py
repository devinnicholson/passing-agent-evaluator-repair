"""Bounded Azure entry point for saved-data provenance and descriptive analysis."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--units')
    parser.add_argument('--dependencies')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir()
    from audit_provenance import audit
    report={'completed':False,'training':False,'gpu_inference':False,'errors':[]}
    try:
        receipt=audit(args.evidence)
        (args.output/'PROVENANCE_AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n')
        report['provenance_audit']=receipt
        if (args.evidence/'FINAL.json').exists():
            run=subprocess.run([sys.executable,'-I','-S','-B',str(Path(__file__).with_name('analyze_study.py')),
                '--input',str(args.evidence),'--output',str(args.output/'analysis')],capture_output=True,text=True,timeout=90)
            (args.output/'analysis.stdout').write_text(run.stdout)
            (args.output/'analysis.stderr').write_text(run.stderr)
            if run.returncode:raise RuntimeError('descriptive analysis failed')
            report['summary']=json.loads((args.output/'analysis/SUMMARY.json').read_text())
        report['completed']=True
    except Exception as error:
        report['errors'].append(type(error).__name__+' '+str(error))
    (args.output/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'completed':report['completed'],'errors':report['errors']}))


if __name__=='__main__':main()
