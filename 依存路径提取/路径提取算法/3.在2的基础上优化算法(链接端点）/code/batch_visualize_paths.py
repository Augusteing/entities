import os
import json
from datetime import datetime

"""批量依存路径可视化（加入依存树 SVG）"""

def load_dependency_result_object(result_dir, title):
    path = os.path.join(result_dir, f"{title}依存路径.json")
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_raw_parsed(dep_dir, pair_dir, title):
    dep_path = os.path.join(dep_dir, f"{title}_dependency.json")
    pair_path = os.path.join(pair_dir, f"{title}实体对.json")
    if not os.path.isfile(dep_path) or not os.path.isfile(pair_path):
        return None
    with open(dep_path, 'r', encoding='utf-8') as f:
        dep_data = json.load(f)
    with open(pair_path, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    sentences = [s.get('parsed', []) for s in dep_data.get('analyzed_sentences', [])]
    return {"sentences_parsed": sentences, "entity_pairs": pairs}

def adapt_pairs_from_result_obj(result_obj):
    return result_obj.get('pairs', [])

def render_article_html(title, sentences_parsed, pair_items, output_dir):
        # 构造句子块 & token 简表
        sent_blocks = []
        sent_tokens_min = []
        for si, sent in enumerate(sentences_parsed):
                spans = []
                mini = []
                for tok in sent:
                        tid = tok.get('id')
                        form = tok.get('form')
                        deprel = tok.get('deprel', '')
                        pos = tok.get('pos', '')
                        head = tok.get('head') if tok.get('head') is not None else tok.get('parent')
                        spans.append(f"<span class='tok' data-sent='{si}' data-id='{tid}' title='id={tid} deprel={deprel} pos={pos}'>[{tid}] {form}</span>")
                        mini.append({'id': tid, 'form': form, 'deprel': deprel, 'pos': pos, 'head': head})
                sent_tokens_min.append(mini)
                sent_blocks.append(
                        f"<div class='sentence' data-sent='{si}'><div class='sent-title'>句 {si} <button class='btn-tree' onclick='toggleTree({si})'>依存树</button></div>" +
                        ' '.join(spans) +
                        f"<div class='dep-tree-wrapper' id='tree-wrapper-{si}' data-built='0' style='display:none'><div class='dep-tree-container' id='dep-tree-{si}'></div></div></div>"
                )

        pair_rows = []
        js_pairs = []
        intra_cnt = cross_cnt = path_success_total = 0
        for p in pair_items:
                subj = p.get('subject')
                obj = p.get('object')
                rel = p.get('relation')
                note = p.get('note') or ''
                ptype = p.get('path_type') or ''
                path_list = p.get('path') or []
                path_positions = p.get('path_positions')
                if ptype == 'cross_sentence' and path_positions:
                        cross_cnt += 1; path_success_total += 1
                elif ptype == 'intra_sentence' and path_positions:
                        intra_cnt += 1; path_success_total += 1
                path_str = ' — '.join([f"{w}({d or ''})" for w, d in path_list]) if path_list else ''
                if ptype == 'intra_sentence':
                        display_sent = p.get('sentence_index') if p.get('sentence_index') is not None else ''
                elif ptype == 'cross_sentence' and path_positions:
                        display_sent = ','.join(map(str, sorted({pos['sentence_index'] for pos in path_positions})))
                else:
                        display_sent = p.get('sentence_index') if p.get('sentence_index') is not None else ''
                pair_rows.append(
                        f"<tr class='row-{ptype or 'none'}'><td>{subj}</td><td>{rel}</td><td>{obj}</td><td>{display_sent}</td><td>{path_str}</td><td>{ptype}</td><td>{note}</td></tr>"
                )
                if path_positions:
                        js_pairs.append({'path_type': ptype, 'positions': path_positions, 'subject': subj, 'object': obj})

        template = """<!DOCTYPE html>
<html lang='zh'>
<head>
    <meta charset='UTF-8'/>
    <title>__TITLE__ 依存路径可视化</title>
    <style>
        body{font-family:Arial,Helvetica,sans-serif;line-height:1.5;margin:16px;}
        .sentence{margin:8px 0;padding:8px;border:1px solid #ddd;border-radius:4px;}
        .sent-title{font-weight:bold;margin-bottom:4px;color:#555;}
        .tok{display:inline-block;margin:2px 3px;padding:2px 4px;border-radius:3px;background:#f5f5f5;cursor:default;font-size:13px;transition:background .25s;}
        .tok.intra{background:#ffe4b5;}
        .tok.cross{background:#e6f7ff;}
        .tok.subj{outline:2px solid #e74c3c;}
        .tok.obj{outline:2px solid #2980b9;}
        table{border-collapse:collapse;margin-top:18px;width:100%;font-size:13px;}
        th,td{border:1px solid #ccc;padding:4px 6px;}
        th{background:#fafafa;}
        tr:nth-child(even){background:#fafafa;}
        tr.row-cross_sentence td{background:#f0fbff;}
        tr.row-intra_sentence td{background:#fffaf1;}
        .summary{margin:12px 0;padding:8px;background:#eef;border-left:4px solid #66c;}
        .legend span{display:inline-block;margin-right:12px;font-size:12px;}
        .legend .box{width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:4px;border:1px solid #aaa;}
        .btn-tree{margin-left:10px;font-size:12px;padding:2px 6px;cursor:pointer;}
        .dep-tree-wrapper{margin-top:6px;padding:6px;border:1px dashed #ccc;background:#fafafa;}
        .dep-tree-container svg{font-family:Arial,Helvetica,sans-serif;}
        .dep-edge{stroke:#888;stroke-width:1.2px;fill:none;}
        .dep-node rect{fill:#fff;stroke:#555;stroke-width:1px;rx:4px;ry:4px;}
        .dep-node.intra rect{fill:#ffe4b5;}
        .dep-node.cross rect{fill:#e6f7ff;}
        .dep-node.subj rect{stroke:#e74c3c;stroke-width:2px;}
        .dep-node.obj rect{stroke:#2980b9;stroke-width:2px;}
        .dep-node text{font-size:12px;dominant-baseline:middle;text-anchor:middle;pointer-events:none;}
        .dep-node{cursor:default;transition:filter .25s;}
        .dep-node:hover{filter:brightness(0.92);}
    </style>
</head>
<body>
<h2>__TITLE__ - 依存路径可视化</h2>
<div class='summary'>总实体对: __TOTAL__ | 句内成功: __INTRA__ | 跨句成功: __CROSS__ | 路径成功总计: __PATH_SUCC__</div>
<div class='legend'>
    <span><span class='box' style='background:#ffe4b5'></span>句内路径节点</span>
    <span><span class='box' style='background:#e6f7ff'></span>跨句路径节点</span>
    <span><span class='box' style='border:2px solid #e74c3c'></span>主语</span>
    <span><span class='box' style='border:2px solid #2980b9'></span>宾语</span>
</div>
<h3>句子分词</h3>
__SENT_BLOCKS__
<h3>实体对路径结果</h3>
<table>
<tr><th>主语</th><th>关系</th><th>宾语</th><th>句序(集合)</th><th>路径节点</th><th>类型</th><th>备注</th></tr>
__PAIR_ROWS__
</table>
<script>
const pairPaths = __PAIR_PATHS_JSON__;
const sentencesTokens = __SENT_TOKENS_JSON__;
function highlight(){
    pairPaths.forEach(p=>{
        if(!p.positions) return;
        p.positions.forEach(pos=>{
            const el=document.querySelector(`.sentence[data-sent='${pos.sentence_index}'] .tok[data-id='${pos.id}']`);
            if(el) el.classList.add(p.path_type==='cross_sentence'?'cross':'intra');
            const n=document.querySelector(`.dep-node[data-sent='${pos.sentence_index}'][data-id='${pos.id}']`);
            if(n) n.classList.add(p.path_type==='cross_sentence'?'cross':'intra');
        });
        if(p.positions && p.positions.length>0){
            const first=p.positions[0];
            const last=p.positions[p.positions.length-1];
            const fEl=document.querySelector(`.sentence[data-sent='${first.sentence_index}'] .tok[data-id='${first.id}']`);
            const lEl=document.querySelector(`.sentence[data-sent='${last.sentence_index}'] .tok[data-id='${last.id}']`);
            if(fEl) fEl.classList.add('subj');
            if(lEl) lEl.classList.add('obj');
            const fNode=document.querySelector(`.dep-node[data-sent='${first.sentence_index}'][data-id='${first.id}']`);
            const lNode=document.querySelector(`.dep-node[data-sent='${last.sentence_index}'][data-id='${last.id}']`);
            if(fNode) fNode.classList.add('subj');
            if(lNode) lNode.classList.add('obj');
        }
    });
}
function buildTree(i){
    const c=document.getElementById('dep-tree-'+i); if(!c) return;
    const toks=sentencesTokens[i]||[]; if(!toks.length){c.innerHTML='<em>无 tokens</em>';return;}
    if(toks.every(t=>t.head===undefined||t.head===null)){c.innerHTML='<em>缺少 head 字段，无法绘制依存树</em>';return;}
    const byId=new Map(toks.map(t=>[String(t.id),t]));
    const children=new Map(); toks.forEach(t=>children.set(String(t.id),[]));
    toks.forEach(t=>{const h=t.head; if(h&&byId.has(String(h))&&String(h)!==String(t.id)) children.get(String(h)).push(t);});
    const roots=toks.filter(t=>!t.head||t.head===0||String(t.head)===String(t.id));
    if(!roots.length){toks.forEach(t=>{if(!byId.has(String(t.head))) roots.push(t);});}
    const layerGap=70,nodeGap=70,nodeSize={w:66,h:26};
    let nextX=0; const coords=new Map();
    function layout(n,d){const kids=children.get(String(n.id))||[]; if(!kids.length){const x=nextX; nextX+=nodeGap; coords.set(String(n.id),{x,y:d*layerGap}); return x;} let first=null,last=null; kids.forEach(k=>{const cx=layout(k,d+1); if(first===null) first=cx; last=cx;}); const x=(first+last)/2; coords.set(String(n.id),{x,y:d*layerGap}); return x;}
    roots.forEach(r=>layout(r,0));
    const width=Math.max(200,nextX+20); const depthMax=Math.max(...Array.from(coords.values()).map(c=>c.y)); const height=depthMax+layerGap+20;
    const svgns='http://www.w3.org/2000/svg'; const svg=document.createElementNS(svgns,'svg'); svg.setAttribute('width',width); svg.setAttribute('height',height);
    toks.forEach(t=>{const h=t.head; if(!h||!byId.has(String(h))||String(h)===String(t.id)) return; const from=coords.get(String(h)); const to=coords.get(String(t.id)); if(!from||!to) return; const path=document.createElementNS(svgns,'path'); const mx=(from.x+to.x)/2; const d=`M${from.x+nodeSize.w/2},${from.y+nodeSize.h} C ${mx},${from.y+nodeSize.h+30} ${mx},${to.y-30} ${to.x+nodeSize.w/2},${to.y}`; path.setAttribute('d',d); path.setAttribute('class','dep-edge'); svg.appendChild(path); const lbl=document.createElementNS(svgns,'text'); lbl.setAttribute('x',mx); lbl.setAttribute('y',(from.y+to.y)/2); lbl.setAttribute('text-anchor','middle'); lbl.setAttribute('font-size','10'); lbl.setAttribute('fill','#555'); lbl.textContent=t.deprel||''; svg.appendChild(lbl); });
    toks.forEach(t=>{const g=document.createElementNS(svgns,'g'); g.setAttribute('class','dep-node'); g.setAttribute('data-id',t.id); g.setAttribute('data-sent',i); const c2=coords.get(String(t.id)); if(!c2) return; const rect=document.createElementNS(svgns,'rect'); rect.setAttribute('x',c2.x); rect.setAttribute('y',c2.y); rect.setAttribute('width',nodeSize.w); rect.setAttribute('height',nodeSize.h); const text=document.createElementNS(svgns,'text'); text.setAttribute('x',c2.x+nodeSize.w/2); text.setAttribute('y',c2.y+nodeSize.h/2+1); text.textContent=`[${t.id}] ${t.form}`; g.appendChild(rect); g.appendChild(text); svg.appendChild(g); });
    c.innerHTML=''; c.appendChild(svg); setTimeout(()=>highlight(),0);
}
function toggleTree(i){const w=document.getElementById('tree-wrapper-'+i); if(!w) return; const built=w.getAttribute('data-built')==='1'; if(w.style.display==='none'){w.style.display='block'; if(!built){buildTree(i); w.setAttribute('data-built','1');}} else {w.style.display='none';}}
highlight();
</script>
<p style='margin-top:30px'><a href='index.html'>&larr; 返回索引</a></p>
</body></html>"""

        html = (template
                        .replace('__TITLE__', title)
                        .replace('__TOTAL__', str(len(pair_items)))
                        .replace('__INTRA__', str(intra_cnt))
                        .replace('__CROSS__', str(cross_cnt))
                        .replace('__PATH_SUCC__', str(path_success_total))
                        .replace('__SENT_BLOCKS__', '\n'.join(sent_blocks))
                        .replace('__PAIR_ROWS__', '\n'.join(pair_rows))
                        .replace('__PAIR_PATHS_JSON__', json.dumps(js_pairs, ensure_ascii=False))
                        .replace('__SENT_TOKENS_JSON__', json.dumps(sent_tokens_min, ensure_ascii=False))
                        )

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{title}_paths.html")
        with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
        return {
                'title': title,
                'total_pairs': len(pair_items),
                'intra_success': intra_cnt,
                'cross_success': cross_cnt,
                'path_success': path_success_total,
                'html_file': os.path.basename(out_path)
        }

def build_index_html(stats_list, output_dir):
    rows = []
    for s in stats_list:
        coverage = (s['path_success'] / s['total_pairs']) if s['total_pairs'] else 0
        rows.append(f"<tr><td><a href='{s['html_file']}'>{s['title']}</a></td><td>{s['total_pairs']}</td><td>{s['intra_success']}</td><td>{s['cross_success']}</td><td>{s['path_success']}</td><td>{coverage:.2f}</td></tr>")
    html = f"""<!DOCTYPE html><html lang='zh'><head><meta charset='UTF-8'/><title>依存路径索引</title><style>body{{font-family:Arial,Helvetica,sans-serif;line-height:1.5;margin:16px;}}table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #ccc;padding:4px 6px;font-size:13px;}}th{{background:#fafafa;}}tr:nth-child(even){{background:#f9f9f9;}}h2{{margin-bottom:8px;}}.meta{{margin:10px 0;color:#555;}}a{{text-decoration:none;color:#2c60c6;}}</style></head><body><h2>依存路径批量可视化索引</h2><div class='meta'>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 文件数：{len(stats_list)}</div><table><tr><th>标题</th><th>实体对总数</th><th>句内成功</th><th>跨句成功</th><th>路径成功总计</th><th>成功覆盖率</th></tr>{''.join(rows)}</table></body></html>"""
    index_path = os.path.join(output_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[OK] 索引生成: {index_path}")

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    dep_dir = os.path.join(base_dir, 'dependency_results')
    pair_dir = os.path.join(base_dir, '实体对')
    result_dir = os.path.join(base_dir, '依存路径提取结果')
    output_dir = result_dir
    os.makedirs(output_dir, exist_ok=True)
    import sys
    filter_sub = sys.argv[1] if len(sys.argv) > 1 else None
    dep_files = [f for f in os.listdir(dep_dir) if f.endswith('_dependency.json')]
    if filter_sub:
        dep_files = [f for f in dep_files if filter_sub in f]
    if not dep_files:
        print('[WARN] 未找到匹配的依存结果文件'); return
    stats_all = []
    log_lines = []
    for f in dep_files:
        title = f[:-len('_dependency.json')]
        result_obj = load_dependency_result_object(result_dir, title)
        if result_obj is None:
            raw = load_raw_parsed(dep_dir, pair_dir, title)
            if raw is None:
                msg = f"[MISS] 缺少依存或实体对文件: {title}"; print(msg); log_lines.append(msg); continue
            sentences_parsed = raw['sentences_parsed']
            pairs_raw = raw['entity_pairs']
            pair_items = [{
                'subject': p.get('subject'),
                'object': p.get('object'),
                'relation': p.get('relation'),
                'path': None,'path_type': None,'path_positions': None,'sentence_index': None,
                'note': '未找到预计算结果(请先运行 dependency_path.py)'
            } for p in pairs_raw]
        else:
            pair_items = adapt_pairs_from_result_obj(result_obj)
            raw = load_raw_parsed(dep_dir, pair_dir, title)
            if raw is None:
                msg = f"[MISS_PARSE] 可视化缺少原始解析: {title}"; print(msg); log_lines.append(msg); continue
            sentences_parsed = raw['sentences_parsed']
        stat = render_article_html(title, sentences_parsed, pair_items, output_dir)
        stats_all.append(stat)
        print(f"[DONE] {title} | 路径成功 {stat['path_success']}/{stat['total_pairs']}")
    if stats_all:
        build_index_html(stats_all, output_dir)
    if log_lines:
        with open(os.path.join(output_dir, 'batch_visualize_log.txt'), 'a', encoding='utf-8') as lf:
            lf.write('\n'.join(log_lines) + '\n')

if __name__ == '__main__':
    main()

