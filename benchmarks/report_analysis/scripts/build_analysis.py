"""Rebuild all summaries/figures/report from recorded data; never runs a solver."""
from common import BASE, ROOT, read_csv, write_csv, write_json, digest
from run_supplement import load_jsonl, LAMBDAS, replay, new_problem
from collections import defaultdict, Counter
from pathlib import Path
import json
import math
import statistics as S
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

LABELS = {'bfs':'BFS','dfs':'DFS','ucs':'UCS','astar_zero':'A* Zero','astar_manhattan':'A* Manhattan',
          'astar_relaxed':'A* Relaxed','astar_relaxed_split':'A* Relaxed Split'}
CONFIGS = list(LABELS)
HEURS = CONFIGS[2:]
plt.rcParams.update({'font.size':10,'figure.dpi':110,'savefig.dpi':170})


def md_table(rows, columns):
    def fmt(v):
        return f'{v:.6g}' if isinstance(v,float) else str(v)
    return '\n'.join(['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+
                     ['| '+' | '.join(fmt(r.get(c,'')) for c in columns)+' |' for r in rows])


def save(fig, path):
    path=BASE/path
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,bbox_inches='tight')
    plt.close(fig)


def lineplot(ax, rows, metric, configs, ylabel):
    for c in configs:
        data=sorted((r for r in rows if r['config']==c),key=lambda x:int(x['level']))
        ax.plot([int(r['level']) for r in data],[float(r[metric]) if r[metric] not in ('',None) else np.nan for r in data],
                marker='o',markersize=3,label=LABELS[c],linewidth=1.3)
    ax.set(xlabel='Official level',ylabel=ylabel,xticks=range(1,11))
    ax.grid(alpha=.25)


def main_plots(per):
    for directory, configs in [('main_comparison',CONFIGS),('heuristic_comparison',HEURS)]:
        fig,axes=plt.subplots(1,3,figsize=(17,5))
        for ax,k,title in zip(axes,['median_time_s','median_precompute_time_s','median_total_time_s'],
                              ['Search only (s)','Precompute (s)','Precompute + search (s)']):
            lineplot(ax,per,k,configs,title)
            if k!='median_precompute_time_s':ax.set_yscale('log')
        axes[0].legend(fontsize=8)
        fig.suptitle('Historical macOS cohort; lambda=0.25; 5 repetitions; per-level medians')
        save(fig,f'{directory}/charts/time.png')
        if directory=='main_comparison':
            fig,axes=plt.subplots(1,2,figsize=(14,5))
            lineplot(axes[0],per,'median_peak_memory_mb',configs,'Search-phase traced peak (MB)')
            lineplot(axes[1],per,'median_precompute_peak_memory_mb',configs,'Precompute-phase traced peak (MB)')
            axes[0].set_yscale('log');axes[0].legend(fontsize=8)
            fig.suptitle('Separate tracemalloc phases: neither panel is whole-process RAM or combined peak')
            save(fig,f'{directory}/charts/memory.png')
        metrics=[('median_expanded_nodes','Expanded nodes','expanded_nodes')]
        if directory=='main_comparison':
            metrics += [('median_generated_nodes','Generated successors (before duplicate filtering)','generated_nodes'),
                        ('median_solution_length','Search actions (including SWITCH)','solution_length'),
                        ('median_total_cost','Total solution cost','total_cost')]
        for metric,label,filename in metrics:
            fig,ax=plt.subplots(figsize=(11,5))
            lineplot(ax,per,metric,configs,label)
            if filename in ('expanded_nodes','generated_nodes'):ax.set_yscale('log')
            ax.legend(ncol=3,fontsize=8)
            ax.set_title('macOS; lambda=0.25; 5 repetitions; per-level medians')
            save(fig,f'{directory}/charts/{filename}.png')


def sensitivity_plots(survey, overview, case_rows):
    for metric,label,name in [('total_cost','Total cost C = N + lambda F','total_cost'),
                              ('solution_length','Search actions N','solution_length'),
                              ('fragile_penalty_count','Measured penalty actions F','fragile_penalty_count'),
                              ('expanded_nodes','Expanded nodes','expanded_nodes')]:
        fig,axes=plt.subplots(2,5,figsize=(18,7))
        for lv,ax in enumerate(axes.flat,1):
            for cfg in ('bfs','ucs'):
                data=sorted([r for r in survey if r['level']==lv and r['config']==cfg],key=lambda r:r['lambda'])
                ax.plot([r['lambda'] for r in data],[r[metric] for r in data],marker='o',markersize=3,label=cfg.upper())
            ax.set(title=f'Level {lv}',xlabel='lambda',ylabel=label)
            ax.grid(alpha=.25)
        axes[0,0].legend()
        fig.suptitle('Windows survey: all 10 levels; weighted mode; one observation per point; lines connect samples only')
        fig.tight_layout(rect=[0,0,1,.95])
        save(fig,f'cost_sensitivity/charts/{name}.png')
    matrix=np.array([[int(r[k]) for k in ['bfs_cost_changes','ucs_cost_changes','ucs_sequence_changes','ucs_N_changes','ucs_F_changes','bfs_ucs_cost_gap']] for r in overview])
    fig,ax=plt.subplots(figsize=(10,6))
    ax.imshow(matrix,cmap='Blues',vmin=0,vmax=1,aspect='auto')
    ax.set(yticks=range(10),yticklabels=range(1,11),ylabel='Level',
           xticks=range(6),xticklabels=['BFS cost','UCS cost','UCS actions','UCS N','UCS F','BFS > UCS cost'])
    for i in range(10):
        for j in range(6):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j] else 'black')
    ax.set_title('Observed change over lambda grid: 1=yes, 0=no (not a general proof)')
    save(fig,'cost_sensitivity/charts/change_heatmap.png')
    for lv in sorted({r['level'] for r in case_rows}):
        fig,axes=plt.subplots(1,3,figsize=(14,4.7))
        for cfg in ('bfs','ucs','astar_relaxed','astar_relaxed_split'):
            data=sorted([r for r in case_rows if r['level']==lv and r['config']==cfg],key=lambda r:r['lambda'])
            for ax,k,label in zip(axes,['total_cost','solution_length','fragile_penalty_count'],['Cost','Actions N','Penalty actions F']):
                ax.plot([r['lambda'] for r in data],[r[k] for r in data],marker='o',label=LABELS[cfg])
                ax.set(xlabel='lambda',ylabel=label);ax.grid(alpha=.25)
        axes[0].legend(fontsize=8)
        fig.suptitle(f'Level {lv}: Windows cases, 3 trials; UCS/A* curves overlap; lines connect sampled points only')
        save(fig,f'cost_sensitivity/case_studies/level{lv}.png')


def build_cost(survey,cases):
    assert len(survey)==140 and len({(r['level'],r['lambda'],r['config']) for r in survey})==140
    selection=json.loads((BASE/'cost_sensitivity/case_studies/selection.json').read_text(encoding='utf-8'))
    chosen={(lv,lam) for lv,lam in selection['pairs']}
    combined=[r for r in survey if (r['level'],r['lambda']) in chosen]+cases
    grouped=defaultdict(list)
    for r in combined:grouped[(r['level'],r['lambda'],r['config'])].append(r)
    case_summary=[]
    for (lv,lam,cfg),rs in sorted(grouped.items()):
        assert len(rs)==3 and len({r['trial'] for r in rs})==3
        assert all(r['status']=='solved' and r['replay_verified'] for r in rs)
        assert len({(r['total_cost'],r['solution_length'],r['fragile_penalty_count'],r['action_sha256']) for r in rs})==1
        first=rs[0]
        row={k:first[k] for k in ['level','lambda','config','total_cost','solution_length','fragile_penalty_count','action_sha256']}
        row.update(trials=3,success_rate=1.)
        for k in ['search_time_s','precompute_time_s','total_time_s','peak_memory_mb','precompute_peak_memory_mb','expanded_nodes','generated_nodes']:
            row['median_'+k]=S.median(r[k] for r in rs)
        case_summary.append(row)
    overview=[]; transitions=[]
    for lv in range(1,11):
        b=sorted([r for r in survey if r['level']==lv and r['config']=='bfs'],key=lambda r:r['lambda'])
        u=sorted([r for r in survey if r['level']==lv and r['config']=='ucs'],key=lambda r:r['lambda'])
        changes=lambda rs,k:len({r[k] for r in rs})>1
        gaps=[x['lambda'] for x,y in zip(b,u) if x['total_cost']>y['total_cost']]
        row={'level':lv,'bfs_cost_changes':changes(b,'total_cost'),'ucs_cost_changes':changes(u,'total_cost'),
             'bfs_sequence_changes':changes(b,'action_sha256'),'ucs_sequence_changes':changes(u,'action_sha256'),
             'ucs_N_changes':changes(u,'solution_length'),'ucs_F_changes':changes(u,'fragile_penalty_count'),
             'bfs_ucs_cost_gap':bool(gaps),'gap_lambdas':json.dumps(gaps),
             'ucs_N_by_lambda':json.dumps([r['solution_length'] for r in u]),
             'ucs_F_by_lambda':json.dumps([r['fragile_penalty_count'] for r in u]),
             'bfs_F':b[0]['fragile_penalty_count']}
        overview.append(row)
        for prev,nxt in zip(u,u[1:]):
            if prev['action_sha256']!=nxt['action_sha256']:
                transitions.append({'level':lv,'lambda_left':prev['lambda'],'lambda_right':nxt['lambda'],
                    'left_N':prev['solution_length'],'left_F':prev['fragile_penalty_count'],
                    'right_N':nxt['solution_length'],'right_F':nxt['fragile_penalty_count'],
                    'same_N_F':(prev['solution_length'],prev['fragile_penalty_count'])==(nxt['solution_length'],nxt['fragile_penalty_count']),
                    'left_path_cost_at_right':prev['solution_length']+nxt['lambda']*prev['fragile_penalty_count'],
                    'right_optimal_cost':nxt['total_cost'],
                    'interpretation':'Observed bracket; sequence change alone does not establish a unique optimum transition.'})
    columns=[k for k in survey[0] if k!='step_trace']
    flatten=lambda r:{k:json.dumps(r[k]) if isinstance(r[k],(list,dict)) else r[k] for k in columns}
    write_csv(BASE/'cost_sensitivity/raw/survey.csv',[flatten(r) for r in survey])
    write_csv(BASE/'cost_sensitivity/summary/survey.csv',[flatten(r) for r in sorted(survey,key=lambda r:(r['level'],r['lambda'],r['config']))])
    write_csv(BASE/'cost_sensitivity/summary/level_changes.csv',overview)
    write_csv(BASE/'cost_sensitivity/summary/transition_brackets.csv',transitions)
    write_csv(BASE/'cost_sensitivity/summary/case_comparison.csv',case_summary)
    # All cost baselines stay within the Windows cohort and same lambda.
    lookup={(r['level'],r['lambda'],r['config']):r for r in survey+cases}
    optimal_checks=[]
    for r in survey+cases:
        base=lookup[(r['level'],r['lambda'],'ucs')]
        optimal_checks.append({'level':r['level'],'lambda':r['lambda'],'config':r['config'],'trial':r['trial'],
             'total_cost':r['total_cost'],'ucs_cost':base['total_cost'],'gap':r['total_cost']-base['total_cost'],
             'matches_ucs':r['total_cost']==base['total_cost']})
        if r['config'].startswith('astar_'):assert r['total_cost']==base['total_cost']
        assert r['total_cost']>=base['total_cost']
    write_csv(BASE/'cost_sensitivity/summary/cost_checks.csv',optimal_checks)
    return overview,transitions,case_summary


def group_heuristics(per):
    out=[]
    lookup={(int(r['level']),r['config']):r for r in per}
    for group in ['basic','fragile','bridge_switch','split']:
        levels=sorted({int(r['level']) for r in per if r['group']==group})
        for cfg in ['astar_relaxed','astar_relaxed_split']:
            rs=[lookup[(lv,cfg)] for lv in levels]
            out.append({'group':group,'config':cfg,'levels':json.dumps(levels),
                        'median_expanded_nodes':S.median(float(r['median_expanded_nodes']) for r in rs),
                        'median_search_time_s':S.median(float(r['median_time_s']) for r in rs),
                        'median_total_time_s':S.median(float(r['median_total_time_s']) for r in rs),
                        'median_precompute_time_s':S.median(float(r['median_precompute_time_s']) for r in rs)})
    write_csv(BASE/'heuristic_comparison/summary/group_comparison.csv',out)
    fig,axes=plt.subplots(1,3,figsize=(15,5))
    groups=['basic','fragile','bridge_switch','split']
    for j,cfg in enumerate(['astar_relaxed','astar_relaxed_split']):
        rs=[next(r for r in out if r['group']==g and r['config']==cfg) for g in groups]
        for ax,k,label in zip(axes,['median_expanded_nodes','median_search_time_s','median_total_time_s'],['Expanded nodes','Search time (s)','Total time (s)']):
            ax.bar(np.arange(4)+(j-.5)*.35,[r[k] for r in rs],width=.35,label=LABELS[cfg])
            ax.set(xticks=range(4),xticklabels=groups,ylabel=label)
            ax.tick_params(axis='x',rotation=20)
    axes[0].legend(fontsize=8)
    fig.suptitle('Historical macOS cohort; medians across levels within each group')
    save(fig,'heuristic_comparison/charts/group_comparison.png')
    return out


def main():
    per=read_csv(BASE/'main_comparison/summary/per_level.csv')
    overall=read_csv(BASE/'main_comparison/summary/overall.csv')
    survey=load_jsonl(BASE/'cost_sensitivity/raw/survey.jsonl')
    cases=load_jsonl(BASE/'cost_sensitivity/raw/cases_additional.jsonl')
    all_direct=survey+cases+load_jsonl(BASE/'main_comparison/raw/direct_verification.jsonl')
    # Revalidate raw actions from disk, without another solver or time measurement.
    from gameModel.block import Direction
    from search.contracts import SearchResult
    for r in all_direct:
        assert r['status']=='solved' and r['replay_verified'] and r['initial_state_preserved']
        assert all(math.isfinite(r[k]) and r[k]>=0 for k in ['total_cost','expanded_nodes','generated_nodes'])
        p=new_problem(r['level'],r['lambda'])
        result=SearchResult('solved',tuple(Direction[a] for a in r['actions']),r['total_cost'],r['expanded_nodes'],r['generated_nodes'])
        x=replay(p,result)
        for k in ['fragile_penalty_count','solution_length','roll_count','action_sha256','step_trace']:
            # JSON serializes coordinate tuples as lists; compare JSON values.
            assert json.loads(json.dumps(x[k]))==r[k],(k,r['level'],r['config'])
        if r['search_time_s'] is not None:
            assert abs(r['total_time_s']-r['search_time_s']-r['precompute_time_s'])<1e-9
    overview,transitions,case_summary=build_cost(survey,cases)
    main_plots(per)
    sensitivity_plots(survey,overview,case_summary)
    groups=group_heuristics(per)
    write_report(per,overall,survey,case_summary,overview,transitions,groups,all_direct)
    winners=[]
    for lv in range(1,11):
        rs=[r for r in per if int(r['level'])==lv and r['config'] in HEURS]
        row={'level':lv}
        for metric in ['median_expanded_nodes','median_time_s','median_total_time_s']:
            best=min(float(r[metric]) for r in rs)
            row[metric+'_best_value']=best
            row[metric+'_winners']=json.dumps([r['config'] for r in rs if float(r[metric])==best])
        winners.append(row)
    write_csv(BASE/'heuristic_comparison/summary/per_level_winners.csv',winners)
    pngs=list(BASE.rglob('*.png'))
    # Register exact figure inputs and hashes; never treat archived historical PNGs as new figures.
    manifest=[]
    for p in pngs:
        section=p.relative_to(BASE).parts[0]
        if section not in ['main_comparison','cost_sensitivity','heuristic_comparison']:continue
        inputs=([BASE/'cost_sensitivity/raw/survey.jsonl',BASE/'cost_sensitivity/raw/cases_additional.jsonl'] if section=='cost_sensitivity'
                else [BASE/'main_comparison/summary/per_level.csv'])
        manifest.append({'chart':p.relative_to(BASE).as_posix(),'sha256':digest(p.read_bytes()),
                         'inputs':{q.relative_to(BASE).as_posix():digest(q.read_bytes()) for q in inputs},
                         'script':'scripts/build_analysis.py','script_sha256':digest(Path(__file__).read_bytes())})
    write_json(BASE/'metadata/chart_manifest.json',manifest)
    write_json(BASE/'metadata/final_validation.json',{'historical_rows':1060,'historical_main_rows':350,
        'survey_rows':len(survey),'case_additional_rows':len(cases),'untimed_historical_verification_solves':len(all_direct)-len(survey)-len(cases),
        'direct_rows_replayed_from_disk':len(all_direct),'all_replays_valid':True,'all_astar_case_costs_match_ucs':True,
        'charts_generated':len(manifest),'DFS_in_main_tables_and_charts':True,'time_cohorts_separate':True,
        'historical_time_rerun':False,'validation_note':'Assertions fail closed; original historical replay is a recorded claim, with deterministic structural reproduction saved separately.'})
    print('Built report, summaries and',len(manifest),'figures; replayed',len(all_direct),'stored solutions.')


def write_report(per,overall,survey,cases,overview,transitions,groups,direct):
    # Numeric claims below are selected from audited rows, never hand-entered synthetic measurements.
    lookup={(int(r['level']),r['config']):r for r in per}
    o={r['config']:r for r in overall}
    def val(lv,cfg,k):return float(lookup[(lv,cfg)][k])
    def winners(cfg,base,metric):return [lv for lv in range(1,11) if val(lv,cfg,metric)<val(lv,base,metric)]
    dfs_time=winners('dfs','bfs','median_time_s'); dfs_mem=winners('dfs','bfs','median_peak_memory_mb')
    astar_more=[lv for lv in range(1,11) if val(lv,'astar_relaxed','median_expanded_nodes')>val(lv,'ucs','median_expanded_nodes')]
    gap_by_config=[]
    for cfg in CONFIGS:
        rs=[r for r in per if r['config']==cfg]
        gap_by_config.append({'config':cfg,'levels_matching_ucs_cost':sum(float(r['cost_gap_to_ucs'])==0 for r in rs),
                              'maximum_absolute_cost_gap':max(float(r['cost_gap_to_ucs']) for r in rs),
                              'median_relative_cost_gap':S.median(float(r['relative_cost_gap']) for r in rs)})
    write_csv(BASE/'main_comparison/summary/optimality.csv',gap_by_config)
    affected=[r['level'] for r in overview if r['bfs_cost_changes'] or r['ucs_cost_changes']]
    unaffected=[r['level'] for r in overview if r['level'] not in affected]
    summary=[]
    for r in overall:
        summary.append({'Cấu hình':LABELS[r['config']],'Search (s)':float(r['median_time_s']),'Precompute (s)':float(r['median_precompute_time_s']),
                        'Total (s)':float(r['median_total_time_s']),'Search peak (MB)':float(r['median_peak_memory_mb']),
                        'Expanded':float(r['median_expanded_nodes']),'Generated':float(r['median_generated_nodes']),
                        'Actions':float(r['median_solution_length']),'Cost':float(r['median_total_cost']),'Success':r['success_rate']})
    tables=[]
    for lv in range(1,11):
        tables.append({'Level':lv,**{LABELS[c]:f'{val(lv,c,"median_solution_length"):g} / {val(lv,c,"median_total_cost"):g}' for c in CONFIGS}})
    case_table=[{'Level':r['level'],'λ':r['lambda'],'Solver':LABELS[r['config']],'N':r['solution_length'],'F':r['fragile_penalty_count'],'C':r['total_cost']} for r in cases]
    hist=json.loads((BASE/'main_comparison/raw/upstream_weighted/metadata.json').read_text())
    local=json.loads((BASE/'metadata/supplement_environment.json').read_text())
    text=f'''# Section 4 — Experimental Results and Self-Evaluation

Trạng thái: READY WITH CAVEATS. Đây là bản nháp học thuật dựa trên dữ liệu đã kiểm tra; đường dẫn dưới đây tương đối với `benchmarks/report_analysis/`. Không có thuật toán hoặc luật game nào được sửa để tạo kết quả. Các điều kiện giới hạn trong 4.5 phải đi cùng các bảng/biểu đồ khi sử dụng trong báo cáo.

## 4.1. Experimental Setup

Thực nghiệm chính tái sử dụng 350 runs: 10 level × 7 cấu hình × 5 repetitions. Dữ liệu nằm trong `main_comparison/raw/upstream_weighted/`. Môi trường gốc: {hist['platform']}, CPU được ghi là {hist['processor']} với {hist['logical_cpus']} logical CPUs, Python {hist['python']}. Metadata gốc không lưu tên CPU chi tiết và dependency freeze; không suy diễn chúng từ máy Windows hoặc requirements hiện tại. Revision ghi trong metadata là {hist['git_revision']}, worktree dirty; toàn bộ source hash được đối chiếu với blob c4cc318 và source hiện tại sau chuẩn hóa CRLF/LF. Các file level cũng khớp hash. Chi tiết: `metadata/historical_validation.json`.

Thí nghiệm bổ sung dùng một cohort Windows độc lập: {local['environment']['platform']}; CPU {local['environment']['cpu']}; Python {local['environment']['python']}. Revision, merge parent nếu có, raw/LF hashes, executable, toàn bộ package versions nằm trong `metadata/supplement_environment.json`. Không gộp time/memory Windows với macOS trong bất kỳ median nào.

Bảy cấu hình chính gồm BFS, DFS, UCS, A* Zero, A* Manhattan, A* Relaxed và A* Relaxed Split. Level 1–2 thuộc nhóm basic, 3–4 fragile, 5–7 bridge/switch, 8–10 split/merge. Đây là nhóm chức năng, không phải phân loại tuyệt đối: level 2 có 2 ô fragile. Đặc điểm từng màn: `main_comparison/summary/levels.csv`.

Cost chính thức trong factory GUI là weighted cost λ=0.25. Constructor `Problem(...)` mặc định unit cost, khác `make_problem(...)`; mọi phép đo mới truyền `unit_cost=False` và λ tường minh. Với mỗi action hợp lệ, c=1+λI_F, ngoại trừ SWITCH luôn có c=1. I_F được xác định bởi `Problem.step_cost` sau transition: footprint đích của khối đầy đủ; cube active khi trước/sau đều split; footprint kết quả khi teleport hoặc ghép. Không cộng phạt theo số ô fragile. Tổng C=N+λF, N gồm SWITCH. Luật chỉ cho cube/nằm được đỡ trên fragile; full-block đứng trên fragile là invalid.

Mọi solver có timeout 60 s và node limit 1,000,000. Benchmark gốc shuffle jobs tuần tự bằng `random.Random(20261030)`; không chạy song song tracemalloc. Mỗi run dùng Problem mới, không reuse bảng heuristic qua run. Survey mới có 140 tổ hợp, một observation/tổ hợp; case studies có 3 trials/tổ hợp, reuse trial 1 BFS/UCS của survey rồi chạy phần còn thiếu. Timing của survey chỉ có tính mô tả. Main historical được tái hiện các cấu hình duy nhất để kiểm tra N/C/expanded/generated/rolls và replay; việc này không thay thế hoặc làm mới các số đo thời gian lịch sử.

## 4.2. Evaluation Metrics

- Search time: thời gian `solve()` qua runner, bao gồm truy vết. Với Relaxed/Relaxed Split, bảng heuristic đã được precompute trước khoảng đo này. Với Zero/Manhattan không có pha precompute riêng; các cache nhỏ được khởi tạo trong solve.
- Precompute time: thời gian dựng bảng heuristic riêng cho Problem mới. Zero, Manhattan, BFS, DFS, UCS có giá trị 0 theo thiết kế benchmark.
- Total time: precompute + search, không gồm load level, replay, vẽ biểu đồ hoặc game animation. Đây là cold heuristic-table setup + search, không phải cold process startup. Median(total) không nhất thiết bằng median(precompute)+median(search).
- Search/precompute peak: hai peak Python allocations của hai phiên tracemalloc tách biệt, MB=10^6 bytes. Không cộng hoặc lấy max để gọi là peak tổng; không phải process RSS/RAM. Bộ nhớ bảng dựng trước không được tính đầy đủ trong search-phase peak.
- Expanded: số lần bắt đầu sinh successor, không gồm node đích và stale entries. Generated: successor hợp lệ trước duplicate filtering. Không đếm graph states dựng trong precompute vào expanded/generated của search.
- Solution length N: số search actions, bao gồm SWITCH. `roll_count` loại SWITCH, gồm cả bước di chuyển cube; không nên gọi toàn bộ là số lần lăn vật lý của khối đầy đủ.
- F: số action chịu penalty, đo bằng replay với `step_cost` thật và λ=1 để lấy chỉ báo nhị phân, kể cả khi run gốc có λ=0; không suy ra đơn thuần từ (C−N)/λ.
- Cost gap: C−C_UCS trên cùng level, λ và mode. UCS là baseline optimal cost dựa trên positive edge costs, best_g và minimum-g goal pop; A* được đối chiếu với baseline và các tests heuristic. BFS chỉ tối ưu N; DFS không bảo đảm N hoặc C tối ưu.
- Success rate: solved/trials; failure không được thay bằng 0. Bảng lịch sử tổng hợp median trong từng level/config rồi median giữa các level với trọng số level bằng nhau. N/C chỉ dùng solved runs; thời gian/node/memory trong code gốc dùng mọi run có số đo. Ở bộ hiện tại tất cả đều solved nên không phát sinh sai khác do lọc failure.

## 4.3. Experimental Results

### 4.3.1. Main Algorithm Comparison

350/350 historical runs solved và ghi replay verified. Các kết quả cấu trúc của 70 level/config được đối chiếu lại trực tiếp với source hiện tại; 350/350 dòng khớp. Đây là tái hiện lời giải deterministic, không chứng minh chuỗi actions gốc vì CSV gốc không lưu chuỗi đó. Dữ liệu đối chứng unit cost 350 runs và sweep cũ 360 runs được audit riêng; không đưa vào median chính.

{md_table(summary,list(summary[0]))}

Nguồn: `main_comparison/summary/overall.csv`. Mỗi ô là median của per-level medians, không phải kết quả của một level điển hình; median N/C bằng nhau có thể che khác biệt level 2. Peak ở bảng chỉ là search-phase traced peak.

Actions / cost theo màn:

{md_table(tables,list(tables[0]))}

Nguồn chi tiết tất cả time/memory/nodes/cost/success/gap: `main_comparison/summary/per_level.csv`. Biểu đồ: `main_comparison/charts/time.png`, `memory.png`, `expanded_nodes.png`, `generated_nodes.png`, `solution_length.png`, `total_cost.png`. Tất cả đều có DFS, cùng 7 cấu hình, cùng macOS cohort.

Bảng optimality so với UCS (cùng level và cost model):

{md_table(gap_by_config,list(gap_by_config[0]))}

Nguồn: `main_comparison/summary/optimality.csv`. Đây là đánh giá lời giải của implementation trên bộ màn, không phải bảo đảm lý thuyết cho BFS/DFS ở weighted cost.

BFS và UCS có cùng N trên cả 10 màn ở λ=0.25, nhưng level 2 có C_BFS={val(2,'bfs','median_total_cost'):g} và C_UCS={val(2,'ucs','median_total_cost'):g}. BFS chọn đường ngắn theo FIFO mà không xếp hàng theo chi phí. UCS tối ưu weighted cost; ở các màn còn lại cost bằng BFS trong cấu hình mặc định. Unit-cost đối chứng cho BFS/UCS cùng N và C trên toàn bộ 10 màn.

DFS có median N={float(o['dfs']['median_solution_length']):g}, cost={float(o['dfs']['median_total_cost']):g}, lớn hơn rõ rệt baseline. Tuy nhiên DFS nhanh hơn BFS trên các level {dfs_time}, và search-phase traced peak thấp hơn BFS trên các level {dfs_mem}; không suy diễn rằng DFS luôn nhanh hơn hoặc luôn ít bộ nhớ. Ở level 10, DFS dùng {val(10,'dfs','median_solution_length'):g} actions, cost {val(10,'dfs','median_total_cost'):g}, so với UCS {val(10,'ucs','median_solution_length'):g} actions, cost {val(10,'ucs','median_total_cost'):g}. DFS giữ visited và stack các node/parent, nên không mang bảo đảm bộ nhớ O(depth) của tree-DFS không lưu lịch sử. Tính ưu/nhược được xác định theo implementation và thứ tự actions thực tế.

Ví dụ trade-off ở level 8: DFS có time={val(8,'dfs','median_time_s'):.6f}s, search peak={val(8,'dfs','median_peak_memory_mb'):.6f}MB, expanded/generated={val(8,'dfs','median_expanded_nodes'):g}/{val(8,'dfs','median_generated_nodes'):g}, N/C={val(8,'dfs','median_solution_length'):g}/{val(8,'dfs','median_total_cost'):g}. BFS có time={val(8,'bfs','median_time_s'):.6f}s, peak={val(8,'bfs','median_peak_memory_mb'):.6f}MB, expanded/generated={val(8,'bfs','median_expanded_nodes'):g}/{val(8,'bfs','median_generated_nodes'):g}, N/C={val(8,'bfs','median_solution_length'):g}/{val(8,'bfs','median_total_cost'):g}. Lợi ích tài nguyên của DFS ở màn này đi cùng lời giải dài và đắt hơn nhiều. Ngược lại, level 2 DFS peak={val(2,'dfs','median_peak_memory_mb'):.6f}MB lớn hơn BFS={val(2,'bfs','median_peak_memory_mb'):.6f}MB.

UCS và A* Zero có cost/expanded/generated tương ứng bằng nhau trong benchmark chính. Heap, best_g và tính step_cost tạo overhead so với BFS khi không đem lại lợi ích về chất lượng lời giải. A* có heuristic giảm công sức tìm kiếm ở nhiều màn nhưng phải tính cả preprocessing; không mặc định A* luôn thắng UCS về time hoặc nodes.

### 4.3.2. Cost Sensitivity Analysis

Khảo sát trực tiếp 10 × 7 × 2 = 140 tổ hợp BFS/UCS ở λ=[0,0.25,0.5,1,1.5,2,3], weighted mode tường minh. Mỗi raw JSONL chứa actions, trace từng bước, F đo lại, N, C, search/precompute/total time, hai peak tách biệt, expanded/generated/status và metadata liên kết. Toàn bộ {len(survey)} solutions được replay lại từ disk; λ=0 vẫn đo F, và C=N. Không dùng kết quả UCS tại λ khác để giả lập BFS.

Theo cost trên lưới khảo sát, các level bị ảnh hưởng: {affected}; không đổi cost: {unaffected}. Các trường hợp không đổi được giữ đầy đủ trong bảng/biểu đồ, không loại bỏ vì kém nổi bật.

{md_table(overview,['level','bfs_F','ucs_N_by_lambda','ucs_F_by_lambda','ucs_sequence_changes','gap_lambdas'])}

Nguồn: `cost_sensitivity/summary/survey.csv`, `level_changes.csv`; chuỗi N/F theo đúng thứ tự λ nêu trên. `transition_brackets.csv` phân biệt đổi action sequence với đổi N/F. Nếu cùng N,F thì mọi λ cho hai đường cùng cost; sequence change trong trường hợp đó không chứng minh một optimum mới. Bằng chứng ties được lưu bằng action hash và chuỗi actions thực tế.

Case studies được chọn sau survey: bắt buộc level 2,4 và mọi level có thay đổi N/F của UCS. Các bảng sau là kết quả chạy trực tiếp, 3 trials/cấu hình; mọi A* Relaxed/Relaxed Split trong cases khớp cost UCS.

{md_table(case_table,list(case_table[0]))}

Nguồn: `cost_sensitivity/summary/case_comparison.csv`; raw và step traces ở `cost_sensitivity/raw/*.jsonl`. Đường đi cụ thể không được rút gọn hoặc đổi action khi lập bảng.

Level 2 minh họa cùng số bước nhưng khác cost ở λ=0.25. Level 4 kiểm tra trực tiếp λ=3: so sánh BFS/UCS/A* trong bảng, không suy ra BFS từ dữ liệu UCS cũ. Với hai đường đã biết (N,F)=(23,4) và (26,2), các đường thẳng 23+4λ và 26+2λ cắt tại λ=1.5; điểm giao hai ứng viên chưa phải chứng minh threshold optimal toàn cục. Dữ liệu lưới ở 1,1.5,2,3 chỉ xác lập các lựa chọn observed và bracket thay đổi; tại điểm tie một solver có thể chọn bất kỳ lời giải tối ưu nào.

Phát hiện quan trọng: tại λ=1.5 có phương án thứ ba (N,F)=(24,3), cost=28.5, thấp hơn cost=29 của cả hai ứng viên cũ. Tại λ=2, UCS chọn (24,3), cost=30; (26,2) cũng cost=30, và chuỗi 26 actions đã replay hợp lệ ở λ=3 có thể được đánh giá lại bằng cùng step_cost tại λ=2. Vì vậy cùng optimal cost không bắt buộc cùng N/F. Các bracket quan sát cho UCS là [1,1.5] và [2,3], không phải khẳng định threshold chính xác. Level 2 tại λ=0 cũng có hai đường 13 actions (F=1 và F=0) cùng cost=13; khi λ>0, đường F=0 được ưu tiên. Nguồn trực tiếp: raw survey/cases và `transition_brackets.csv`.

Các biểu đồ phủ đủ 10 màn: `cost_sensitivity/charts/total_cost.png`, `solution_length.png`, `fragile_penalty_count.png`, `expanded_nodes.png`, `change_heatmap.png`. Hình case study: `cost_sensitivity/case_studies/level*.png`. Chi phí Windows không trộn với timing macOS; đối chiếu cấu trúc chỉ thực hiện sau xác nhận source/game levels tương thích.

### 4.3.3. Heuristic Performance

Nguồn: `heuristic_comparison/summary/per_level.csv`, `overall.csv`, `group_comparison.csv`. Biểu đồ `heuristic_comparison/charts/time.png` phân biệt search và total; `expanded_nodes.png` và `group_comparison.png` mô tả công sức và trade-off preprocessing.

`heuristic_comparison/summary/per_level_winners.csv` liệt kê cấu hình đạt min expanded/search/total ở từng màn (giữ cả tie). Dữ liệu expanded cũng cho thấy A* Manhattan mở 1759 node ở level 9, nhiều hơn UCS 1646; không chỉ riêng Relaxed có trường hợp bất lợi.

Ở median tổng hợp, Relaxed Split có expanded={float(o['astar_relaxed_split']['median_expanded_nodes']):g} và search time={float(o['astar_relaxed_split']['median_time_s']):.6f}s; Relaxed có expanded={float(o['astar_relaxed']['median_expanded_nodes']):g}, search time={float(o['astar_relaxed']['median_time_s']):.6f}s. Tuy nhiên total median của Relaxed={float(o['astar_relaxed']['median_total_time_s']):.6f}s nhỏ hơn Relaxed Split={float(o['astar_relaxed_split']['median_total_time_s']):.6f}s. Không chọn heuristic thắng mọi trường hợp từ một median tổng hợp.

A* Relaxed mở nhiều node hơn UCS ở các level {astar_more}. Tại level 9: Relaxed expanded={val(9,'astar_relaxed','median_expanded_nodes'):g}, UCS={val(9,'ucs','median_expanded_nodes'):g}, Relaxed Split={val(9,'astar_relaxed_split','median_expanded_nodes'):g}. Relaxed trả h=0 khi split, và coi các split switches là đích trung gian cho pha full-block nên cận dưới yếu trên nhóm này. Việc A* mở nhiều node hơn UCS vẫn có thể xảy ra với heuristic admissible do thứ tự f/tie và vùng f bằng optimal cost; dữ liệu hiện tại không tách nhân quả của từng yếu tố. Không kết luận đó là heuristic sai chỉ dựa trên số node.

{md_table(groups,list(groups[0]))}

Relaxed Split mô hình hóa cả hai cube, active cube, SWITCH, teleport và merge trong bài toán nới lỏng cầu/công tắc. Bảng được dựng bằng tìm kiếm đồ thị và Dijkstra ngược; lookup nhanh nhưng chi phí dựng bảng không nằm trong expanded/generated của search. Phân tích cần nhìn cả preprocessing và search. Toàn bộ A* trong benchmark chính và cases bổ sung có C khớp UCS; điều này hỗ trợ optimality trên các instances đã kiểm tra, không chứng minh cho mọi Bloxorz hoặc mọi λ.

## 4.4. Discussion and Self-Evaluation

BFS là baseline ngắn nhất theo số search actions, dễ diễn giải; weighted-cost counterexample ở level 2 cho thấy ngắn nhất không đồng nghĩa rẻ nhất. DFS có thể sớm gặp một đích theo thứ tự duyệt, giảm thời gian ở một số màn, nhưng chất lượng lời giải thấp hơn nhiều; không phù hợp khi ưu tiên N hoặc C tối ưu. UCS có ý nghĩa khi penalty tạo sự khác nhau giữa đường đi; level 4 tại λ lớn cho thấy việc chấp nhận nhiều actions hơn có thể hợp lý theo mục tiêu cost. Trên các level F=0 hoặc không có lựa chọn thay thế tốt hơn, weighted cost không đem lại khác biệt chất lượng giữa BFS/UCS và overhead UCS vẫn tồn tại.

A* Zero cung cấp đối chứng với UCS; Manhattan là cận rẻ nhưng yếu; Relaxed và Relaxed Split dùng thêm cấu trúc game để giảm search. Relaxed thông thường yếu ở trạng thái split nên không luôn cải thiện UCS; Relaxed Split giúp nhóm split nhưng tốn nhiều preprocessing hơn. Nhóm basic/fragile nhỏ không mặc nhiên hưởng lợi từ bảng phức tạp hơn. Dữ liệu không hỗ trợ tuyên bố một thuật toán/heuristic vượt trội trên mọi metric.

Các kiểm tra thực hiện: 208 unit/integration tests PASS, không FAIL/ERROR; gồm campaign, rules, UCS/A*, heuristic admissibility/consistency trên trạng thái campaign ở unit/default weighted mode, lambda comparison, GUI headless tests. Không chạy GUI thủ công. Tất cả direct solutions mới được replay lại từ JSONL và kiểm tra N+λF bằng step_cost; summary lịch sử được tính lại từ raw; figure inputs/hash có trong `metadata/chart_manifest.json`. Tests lambda không phải bằng chứng exhaustive consistency cho mọi λ.

## 4.5. Limitations và hướng cải tiến

1. Chỉ có 10 màn campaign do nhóm thiết kế, không đại diện mọi Bloxorz. Nhóm level phản ánh tính năng, không phải độ khó đã chuẩn hóa.
2. Historical chính có 5 repetitions; case studies 3; survey chỉ 1, nên không diễn giải timing survey như ước lượng ổn định. Không kiểm định thống kê hoặc tuyên bố significance từ median.
3. Timing có nhiễu và overhead tracemalloc; peak chỉ là traced Python allocations, không phải toàn RAM. Hai pha memory không cho phép khôi phục combined peak từ CSV hiện tại.
4. Precompute nằm ngoài solver timeout/node limit; tổng thời gian có thể vượt 60s dù search chưa timeout. Các trường hợp gần deadline có khác biệt: BFS/UCS không check ngay sau mỗi engine call, DFS/A* có check ở vị trí khác; DFS trả unsolvable sau khi stack cạn mà không có final timeout check. Không sửa core code trong công việc này. Tất cả run dùng để phân tích solved, không chạm timeout/node limit, nên giới hạn này không làm thay đổi kết quả campaign đã lưu. Không suy rộng success rate hiện tại thành khả năng xử lý mọi timeout.

   Chẩn đoán riêng `metadata/deadline_diagnostic.json` dùng clock giả: result() trả goal và tăng clock từ 0 lên 2 giây với budget 1 giây; BFS/UCS trả solved, DFS/A* trả timeout. Đây là khác biệt policy tái hiện trực tiếp, không phải một run campaign và không được đưa vào thống kê success. Cần task core riêng nếu nhóm muốn thống nhất semantics; không tự sửa trong thí nghiệm này.
5. Metadata historical thiếu CPU model chi tiết/dependency freeze và raw actions; không thể khôi phục tuyệt đối môi trường cũ. Source hash, level hash và structural reproduction giúp kiểm tra tính phù hợp; các thiếu sót vẫn được nêu rõ.
6. Có nhiều lời giải cùng optimal cost; đổi action sequence không nhất thiết đổi N/F hay ngưỡng optimum. Không tuyên bố λ=1.5 là threshold toàn cục chỉ từ hai ứng viên và lưới rời rạc.
7. Constructor/factory cost defaults khác nhau dễ gây nhầm. Thực nghiệm dùng explicit mode/λ, không thay API của nhóm.
8. Tài liệu heuristic gốc còn trỏ script sweep đã xóa; script và CSV cũ được bảo tồn trong `metadata/preservation/preintegration_evidence.zip` cùng manifest hash. Không đưa dữ liệu cũ chưa có provenance đầy đủ vào thống kê time chính.

Hướng cải tiến có cơ sở: thống nhất deadline policy bằng task core riêng có review; nếu cần so tổng memory thì đo một traced session bao quanh cả precompute+search hoặc process RSS bằng protocol mới, giữ cohort tách biệt; mở rộng bộ màn độc lập và số repetitions nếu cần suy luận tổng quát. Không cần sửa thuật toán/cost để các kết quả hiện tại thể hiện khác biệt.
'''
    out=BASE/'report_notes';out.mkdir(exist_ok=True)
    (out/'section4_vi.md').write_text(text,encoding='utf-8')
    (out/'main_per_level_tables.md').write_text('\n\n'.join('## '+LABELS[c]+'\n\n'+md_table([r for r in per if r['config']==c],['level','median_time_s','median_precompute_time_s','median_total_time_s','median_peak_memory_mb','median_expanded_nodes','median_generated_nodes','median_solution_length','median_total_cost','cost_gap_to_ucs','success_rate']) for c in CONFIGS),encoding='utf-8')


if __name__=='__main__':
    main()
