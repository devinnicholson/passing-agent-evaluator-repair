"""Azure-only post-hoc coverage/semantic-adequacy diagnostic of one saved body."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import study

HERE = Path(__file__).resolve().parent
TARGET = 'org.jsoup.nodes.EntitiesTest#controlCharactersAreEscaped()'
CLASS = 'org/jsoup/nodes/Entities'


def production_debug(case, output, cp):
    result = {}
    project = case / 'project'
    for variant in ('developer','fault'):
        dest = output / ('production_' + variant)
        dest.mkdir()
        sources = []
        for path in sorted((project / 'src/main/java').rglob('*.java')):
            old = case / 'fault' / path.relative_to(project)
            sources.append(old if variant == 'fault' and old.exists() else path)
        receipt, _, _ = study.execute([study.JAVA/'javac','-J-Xmx384m','--release','8','-g','-proc:none','-encoding','UTF-8',
            '-cp',cp,'-d',dest,*sources],output,'production_'+variant,65)
        if receipt['returncode']: raise RuntimeError('debug production compilation failed '+variant)
        result[variant] = dest
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--units')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dependencies', type=Path, required=True)
    parser.add_argument('--responses', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()
    output = args.output
    report = {'completed':False,'exploratory_posthoc_single_case':True,'model_sample':'jsoup-2718',
              'exact_scope':CLASS,'training':False,'model_calls':0,'runs':[],'errors':[]}
    def save(): (output/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        dependencies = sorted(args.dependencies.glob('*.jar'))
        expected = json.loads((HERE/'DEPENDENCIES.json').read_text())
        if len(dependencies)!=8 or {study.sha256(p.read_bytes()).hexdigest() for p in dependencies}!={v['sha256'] for v in expected.values()}:
            raise ValueError('qualified dependency closure differs')
        tools = HERE.parent/'instrumentation'
        for name,spec in json.loads((tools/'MANIFEST.json').read_text()).items():
            if (tools/name).stat().st_size!=spec['bytes'] or sha256((tools/name).read_bytes()).hexdigest()!=spec['sha256']:
                raise ValueError('instrumentation artifact mismatch')
        cp=':'.join(map(str,dependencies))
        plan=json.loads((HERE/'PLAN.json').read_text());meta=plan['units']['jsoup'];case=HERE/'cases/jsoup'
        variants=production_debug(case,output,cp)
        production_map={k:study.filemap(v) for k,v in variants.items()}
        probe=study.probe(output,cp)
        dumper=output/'dumper';dumper.mkdir()
        receipt,_,_=study.execute([study.JAVA/'javac','-J-Xmx256m','--release','8','-proc:none','-cp',tools/'cli.jar',
            '-d',dumper,HERE/'ProbeDump.java'],output,'dumper_compile')
        if receipt['returncode']: raise RuntimeError('coverage dumper compilation failed')
        raw_model=json.loads(args.responses.read_text())['jsoup-2718']
        report['normalized_model_response_sha256']=sha256(raw_model.encode()).hexdigest()
        report['grades']={
            'gold':study.grade('jsoup',meta,(case/'GOLD_BODY.txt').read_text(),output/'gold',variants,probe,cp),
            'gemma':study.grade('jsoup',meta,raw_model,output/'gemma',variants,probe,cp,raw=True)}
        report['oracle_contrast']=(report['grades']['gold']['oracle_qualified'] and
            report['grades']['gemma'].get('oracle',{}).get('developer',{}).get('contract',{}).get('verdict')=='PASS' and
            report['grades']['gemma'].get('oracle',{}).get('fault',{}).get('contract',{}).get('verdict')=='PASS')
        for role in ('gold','gemma'):
            if report['grades'][role]['status']!='GRADED': raise RuntimeError('body was not admitted '+role)
            classes=output/role/'classes'
            for rep in range(2):
                folder=output/(role+'-coverage-'+str(rep));folder.mkdir()
                selectors=folder/'selectors.txt';selectors.write_text(TARGET+'\n')
                data=folder/'coverage.exec';origins=folder/'classload.log'
                runtime_cp=':'.join(map(str,[classes,variants['developer'],probe,cp]))
                receipt,stdout,_=study.execute([study.JAVA/'java','-Xmx256m','-ea','-Djava.awt.headless=true',
                    '-Xlog:class+load=info:file='+str(origins),
                    '-javaagent:'+str(tools/'agent.jar')+'=destfile='+str(data)+',append=false,includes=org.jsoup.*',
                    '-cp',runtime_cp,'SuiteProbe','execute',selectors],folder,'native',25)
                records,containers,skipped=study.native(stdout)
                contract=study.assess({TARGET:1},records,receipt['returncode'],containers,skipped)
                if contract['verdict']!='PASS': raise RuntimeError('instrumented target did not pass '+role)
                origin_text=origins.read_text()
                for class_name,expected_dir in [('org.jsoup.nodes.Entities',variants['developer']),('org.jsoup.nodes.EntitiesTest',classes)]:
                    hits=[line.split(' source: ',1)[1] for line in origin_text.splitlines() if '[class,load] '+class_name+' source: ' in line]
                    if hits!=['file:'+str(expected_dir)+'/']: raise ValueError('native class origin differs '+class_name)
                receipt,bits,_=study.execute([study.JAVA/'java','-Xmx256m','-cp',str(dumper)+':'+str(tools/'cli.jar'),
                    'ProbeDump',data,CLASS],folder,'probe_dump')
                if receipt['returncode']: raise RuntimeError('probe dump failed')
                fields=bits.strip().split('\t')
                if len(fields)!=3 or fields[0]!=CLASS or not fields[2] or set(fields[2])-{'0','1'} or '1' not in fields[2]:
                    raise ValueError('nonempty exact class probe record missing')
                xml=folder/'coverage.xml'
                receipt,_,_=study.execute([study.JAVA/'java','-Xmx256m','-jar',tools/'cli.jar','report',data,
                    '--classfiles',variants['developer'],'--xml',xml],folder,'xml_report',25)
                if receipt['returncode']: raise RuntimeError('coverage report failed')
                cls=ET.parse(xml).find('.//class[@name="'+CLASS+'"]')
                if cls is None: raise ValueError('changed class absent from XML')
                counters={n.attrib['type']:{'missed':int(n.attrib['missed']),'covered':int(n.attrib['covered'])} for n in cls.findall('counter')}
                methods={n.attrib['name']+n.attrib['desc']:{c.attrib['type']:{'missed':int(c.attrib['missed']),'covered':int(c.attrib['covered'])}
                    for c in n.findall('counter')} for n in cls.findall('method')}
                report['runs'].append({'role':role,'repetition':rep,'class_id':fields[1],'probe_bits':fields[2],
                    'covered_probes':fields[2].count('1'),'total_probes':len(fields[2]),'class_counters':counters,
                    'method_counters':methods,'native':contract,'class_origins_verified':True})
                if study.filemap(variants['developer'])!=production_map['developer']: raise ValueError('production classfiles changed')
                save()
        rows=report['runs']
        report['all_four_exact_vectors_equal']=len(rows)==4 and all((r['class_id'],r['probe_bits'])==(rows[0]['class_id'],rows[0]['probe_bits']) for r in rows)
        report['all_four_class_and_method_counters_equal']=len(rows)==4 and all((r['class_counters'],r['method_counters'])==(rows[0]['class_counters'],rows[0]['method_counters']) for r in rows)
        report['counterexample_admitted']=report['oracle_contrast'] and report['all_four_exact_vectors_equal'] and report['all_four_class_and_method_counters_equal']
        report['production_classfiles']=production_map
        report['completed']=True
    except Exception as error:
        report['errors'].append(type(error).__name__+' '+str(error))
    save()
    print(json.dumps({k:report.get(k) for k in ['completed','oracle_contrast','all_four_exact_vectors_equal','all_four_class_and_method_counters_equal','counterexample_admitted','errors']}))


if __name__=='__main__':main()
