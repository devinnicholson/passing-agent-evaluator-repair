"""Export recorded llama.cpp completion inputs without making model requests."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir()
    initial=json.loads((args.evidence/'INITIAL.json').read_text())
    final=json.loads((args.evidence/'FINAL.json').read_text())
    rows={**initial['initial'],**final['repairs']}
    manifest={}
    for name,row in rows.items():
        if row.get('model_output_status'):
            manifest[name]={'status':row['model_output_status'],'exported':False,
                'reason':'No complete input/output record for this timed-out request. Do not substitute a fresh response into the saved study.'}
            continue
        if not row.get('native_token_ids_match') or len(row['input_ids'])!=row['input_tokens']:
            raise ValueError('unqualified recorded token inputs '+name)
        packet={**row['settings'],'prompt':row['input_ids']}
        raw=(json.dumps(packet,indent=2)+'\n').encode()
        (args.output/(name+'.request.json')).write_bytes(raw)
        (args.output/(name+'.prompt.txt')).write_text(row['prompt'])
        manifest[name]={'exported':True,'request_sha256':sha256(raw).hexdigest(),
            'saved_response_content_sha256':sha256(row['response']['content'].encode()).hexdigest(),
            'input_tokens':row['input_tokens'],'seed':row['seed']}
    (args.output/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'exported_requests':sum(r.get('exported',False) for r in manifest.values()),
        'missing_observations_retained':sum(not r.get('exported',False) for r in manifest.values()),'model_calls':0}))


if __name__=='__main__':main()
