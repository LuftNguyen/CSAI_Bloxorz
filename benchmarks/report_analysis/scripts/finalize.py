"""Offline delivery validation, cross-replays, source snapshot and file manifest."""
from common import BASE, ROOT, digest, git, read_csv, write_json
from run_supplement import load_jsonl, new_problem, replay
from pathlib import Path
from gameModel.block import Direction
from search.contracts import SearchResult
import json
import zipfile


def main():
    survey=load_jsonl(BASE/'cost_sensitivity/raw/survey.jsonl')
    cases=load_jsonl(BASE/'cost_sensitivity/raw/cases_additional.jsonl')
    cross=[]
    for lv,source_lambda,target_lambda,cfg in [(2,.25,0.,'ucs'),(4,1.5,1.,'ucs'),(4,3.,2.,'ucs')]:
        r=next(r for r in survey if r['level']==lv and r['lambda']==source_lambda and r['config']==cfg)
        p=new_problem(lv,target_lambda)
        actions=tuple(Direction[a] for a in r['actions'])
        # Build cost by actual target-mode engine replay before validator checks it.
        state=p.initial.copy(); cost=0.
        for a in actions:
            child=p.result(state,a)
            assert child is not None
            cost+=p.step_cost(state,a,child);state=child
        result=SearchResult('solved',actions,cost,r['expanded_nodes'],r['generated_nodes'])
        x=replay(p,result)
        baseline=next(b for b in survey if b['level']==lv and b['lambda']==target_lambda and b['config']=='ucs')
        assert x['replay_verified'] and cost==baseline['total_cost']
        cross.append({'level':lv,'source_lambda':source_lambda,'evaluated_lambda':target_lambda,
                      'measurement_type':'cross-replay of stored solution; no new solve and no timing claim',
                      'N':x['solution_length'],'F':x['fragile_penalty_count'],'C':cost,'actions':x['actions'],
                      'baseline_ucs_N':baseline['solution_length'],'baseline_ucs_F':baseline['fragile_penalty_count'],
                      'baseline_ucs_C':baseline['total_cost'],'replay_verified':True})
    write_json(BASE/'cost_sensitivity/case_studies/equal_cost_paths.json',cross)
    preserve=BASE/'metadata/preservation'
    manifest=json.loads((preserve/'manifest.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(preserve/'preintegration_evidence.zip') as archive:
        for name,info in manifest['files'].items():
            b=archive.read(name)
            assert digest(b)==info['sha256']
            if name.startswith('benchmarks/audit_'):
                assert (ROOT/name).read_bytes()==b,'Original untracked audit changed'
        for name in ['sweep_lambda.csv','examples/sweep_lambda.py']:
            dst=preserve/'legacy'/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            b=archive.read(name)
            if dst.exists():assert dst.read_bytes()==b
            else:dst.write_bytes(b)
    assert not git('ls-files','-u'),'Unresolved merge entries'
    assert not git('diff','origin/main','--','gameModel','search','runner.py','benchmarks/benchmark_all.py'),'Core or official measurement code changed beyond upstream'
    test_result=json.loads((BASE/'metadata/unit_tests.json').read_text())
    assert test_result['successful'] and test_result['tests_run']==208
    assert len(read_csv(BASE/'main_comparison/summary/per_level.csv'))==70
    assert len(read_csv(BASE/'main_comparison/summary/overall.csv'))==7
    assert len(read_csv(BASE/'main_comparison/summary/direct_verification.csv'))==350
    charts=json.loads((BASE/'metadata/chart_manifest.json').read_text())
    for c in charts:
        assert digest((BASE/c['chart']).read_bytes())==c['sha256']
        assert digest((BASE/c['script']).read_bytes())==c['script_sha256']
        for p,h in c['inputs'].items():assert digest((BASE/p).read_bytes())==h
    # Exact integrated source snapshot, independent of whether merge is committed.
    paths=sorted(set(list(ROOT.glob('*.py'))+list((ROOT/'gameModel').glob('*.py'))+list((ROOT/'search').glob('*.py'))+
                     list((ROOT/'levels').glob('*.py'))+list((ROOT/'levels').glob('*.json'))+
                     list((ROOT/'tests').rglob('*.py'))+list((ROOT/'tests/fixtures').rglob('*.json'))+
                     list((BASE/'scripts').glob('*.py'))+list((ROOT/'assets').rglob('*'))+
                     list((ROOT/'docs').glob('*.json'))+
                     [ROOT/'runner.py',ROOT/'requirements.txt',ROOT/'benchmarks/benchmark_all.py',ROOT/'benchmarks/plot_benchmark.py']))
    paths=[p for p in paths if p.is_file()]
    snap=BASE/'metadata/integrated_source.zip'
    source_hash={p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in paths}
    if not snap.exists():
        with zipfile.ZipFile(snap,'x',zipfile.ZIP_DEFLATED) as z:
            for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    else:
        with zipfile.ZipFile(snap) as z:
            assert {p:digest(z.read(p)) for p in z.namelist()}==source_hash,'Snapshot changed: create versioned output instead'
    with zipfile.ZipFile(snap) as z:
        assert all(digest(z.read(p))==h for p,h in source_hash.items())
    write_json(BASE/'metadata/integrated_source_manifest.json',source_hash)
    write_json(BASE/'metadata/git_integration.json',{
        'branch':git('branch','--show-current'),'HEAD':git('rev-parse','HEAD'),'origin_main':git('rev-parse','origin/main'),
        'merge_head':git('rev-parse','MERGE_HEAD') if (ROOT/'.git/MERGE_HEAD').exists() else None,'unmerged_entries':git('ls-files','-u'),
        'integration_status':'Merged working tree and staged conflict resolution; merge commit intentionally not created.',
        'conflict_resolution':'test_loader_replay_cost_and_reset uses the actual Problem with unit_cost=True explicitly.',
        'new_local_core_edits':False,'pushed':False,'committed':False,'old_files_preserved':len(manifest['files']),
        'restoration':'Read metadata/preservation/manifest.json and restore selected paths from ZIP into a NEW directory. Do not overwrite current source.',
        'git_status':git('status','--porcelain')})
    write_json(BASE/'metadata/delivery_validation.json',{'status':'READY WITH CAVEATS','preservation_archive_hashes':'PASS',
        'untracked_old_audit_unchanged':'PASS','integrated_core_matches_origin_main':'PASS','merge_conflicts_resolved':'PASS',
        'unit_tests':test_result,'charts_manifest':'PASS','source_snapshot':'PASS','cross_replays_valid':len(cross),
        'caveats':['Merge intentionally not committed; exact source snapshot and two-parent provenance supplied.',
                   'Historical macOS CPU model/dependency freeze unavailable.',
                   'Separate phase tracemalloc peaks are not combined memory or RSS.',
                   'Observed deadline policy differs across solvers; no failure in campaign runs.',
                   'Survey one repetition; cases three; no exact global lambda threshold claim.']})
    write_json(BASE/'metadata/file_manifest.json',{
        p.relative_to(BASE).as_posix():{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size}
        for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='file_manifest.json' and '__pycache__' not in p.parts})
    print('Delivery checks PASS; 35 preserved files; exact source snapshot; 3 equal-cost cross-replays; no commit/push.')


if __name__=='__main__':main()
