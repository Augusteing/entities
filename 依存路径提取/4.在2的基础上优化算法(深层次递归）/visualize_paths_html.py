import os, json, sys

"""依存路径可视化 (干净版本)
读取预计算 JSON, 生成 HTML, 不做路径提取计算。
"""

def load_dependency_sentences(base_dir: str, title: str):
    fp = os.path.join(base_dir, 'dependency_results', f'{title}_dependency.json')
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [s.get('parsed', []) for s in data.get('analyzed_sentences', [])]

def locate_paths_json(base_dir: str, title: str):
    p = os.path.join(base_dir, '依存路径提取结果', f'{title}依存路径.json')
    if os.path.isfile(p):
        return p
    root = os.path.join(base_dir, '依存路径提取结果')
    for fn in os.listdir(root):
        if title in fn and '依存路径' in fn and fn.endswith('.json'):
            return os.path.join(root, fn)
    raise FileNotFoundError('未找到依存路径结果 JSON')

def load_pairs(base_dir: str, title: str):
    fp = locate_paths_json(base_dir, title)
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pairs = []
    if isinstance(data, dict):
        for k in ('pairs','results','data','items'):
            if k in data and isinstance(data[k], list):
                pairs = data[k]; break
    elif isinstance(data, list):
        pairs = data
    return pairs, fp

def build_highlight_js(records):
    out = []
    for r in records:
        pos_list = r.get('path_positions')
        if pos_list and isinstance(pos_list, list):
            groups = {}
            for it in pos_list:
                if not isinstance(it, dict):
                    continue
                si = it.get('sentence_index')
                tid = it.get('token_id') or it.get('id') or it.get('token')
                if si is None or tid is None:
                    continue
                groups.setdefault(si, []).append(tid)
            for si, ids in groups.items():
                ids_str = ','.join(map(str, ids))
                js = "(function(){var s=document.querySelectorAll('.sentence')["+str(si)+"];;if(!s)return;var a=s.querySelectorAll('.tok');a.forEach(x=>{var m=x.textContent.match(/\\[(\\d+)\\]/);if(!m)return;var id=parseInt(m[1]);if(["+ids_str+"] .includes(id))x.classList.add('path');});})();"
                out.append(js.replace('] .includes', '].includes'))
        elif r.get('path_token_ids') and r.get('sentence_index') is not None:
            si = r['sentence_index']
            ids_str = ','.join(map(str, r['path_token_ids']))
            js = "(function(){var s=document.querySelectorAll('.sentence')["+str(si)+"];;if(!s)return;var a=s.querySelectorAll('.tok');a.forEach(x=>{var m=x.textContent.match(/\\[(\\d+)\\]/);if(!m)return;var id=parseInt(m[1]);if(["+ids_str+"] .includes(id))x.classList.add('path');});})();"
            out.append(js.replace('] .includes', '].includes'))
    return '\n'.join(out)

def render_html(title: str, sentences, pairs, out_path: str, src_file: str):
    sent_blocks = []
    for si, sent in enumerate(sentences):
        toks = []
        for tok in sent:
            tid = tok.get('id'); form = tok.get('form'); deprel = tok.get('deprel',''); pos = tok.get('pos','')
            toks.append(f"<span class='tok' title='id={tid} deprel={deprel} pos={pos}'>[{tid}] {form}</span>")
        sent_blocks.append(f"<div class='sentence' data-sent-index='{si}'><div class='sent-title'>句 {si}<button class='toggle-tree-btn' onclick='toggleTree({si})'>依存树</button></div><div class='linear'>{' '.join(toks)}</div><div id='tree-{si}' class='dep-tree-container' style='display:none'></div></div>")

    rows = []
    highlight_records = []
    for rec in pairs:
        subj = rec.get('subject') or rec.get('subj')
        obj = rec.get('object') or rec.get('obj')
        rel = rec.get('relation') or rec.get('rel')
        note = rec.get('note') or ''
        ptype = rec.get('path_type') or ('cross_sentence' if note=='跨句' else 'intra_sentence')
        nodes = rec.get('path_nodes') or rec.get('path') or rec.get('nodes') or []
        norm_nodes = [n if isinstance(n, dict) else {'form': str(n)} for n in nodes]
        sent_idx = rec.get('sentence_index')
        path_str = ' — '.join([f"{n.get('form','')}{'('+n.get('deprel','')+')' if n.get('deprel') else ''}" for n in norm_nodes])
        rows.append(f"<tr class='{ptype}'><td>{subj}</td><td>{rel}</td><td>{obj}</td><td>{sent_idx if sent_idx is not None else ''}</td><td>{path_str}</td><td>{note or ptype}</td></tr>")
        highlight_records.append({
            'path_positions': rec.get('path_positions') or rec.get('token_positions'),
            'path_token_ids': rec.get('path_token_ids'),
            'sentence_index': sent_idx
        })

    highlight_js = build_highlight_js(highlight_records)
    sent_json = json.dumps([[{'id':t.get('id'),'form':t.get('form'),'head':t.get('head'),'deprel':t.get('deprel')} for t in s] for s in sentences], ensure_ascii=False)

    css = ("body{font-family:Arial,Helvetica,sans-serif;line-height:1.5;margin:16px;}" \
           ".sentence{margin:8px 0;padding:8px;border:1px solid #ddd;border-radius:4px;}" \
           ".sent-title{font-weight:bold;margin-bottom:4px;color:#555;}" \
           ".tok{display:inline-block;margin:2px 3px;padding:2px 4px;border-radius:3px;background:#f5f5f5;font-size:13px;}" \
           ".tok.path{background:#ffe4b5;}" \
           ".toggle-tree-btn{margin-left:12px;font-size:12px;padding:2px 6px;cursor:pointer;}" \
           ".dep-tree-container{margin-top:6px;border-top:1px dashed #ccc;padding-top:6px;}" \
           "table{border-collapse:collapse;margin-top:20px;width:100%;}" \
           "th,td{border:1px solid #ccc;padding:4px 6px;font-size:13px;}" \
           "th{background:#fafafa;}" \
           "tr:nth-child(even){background:#f9f9f9;}" \
           ".summary{margin:12px 0;padding:8px;background:#eef;border-left:4px solid #66c;}" \
           "svg.dep-tree{width:100%;height:auto;overflow:visible;}" \
           ".dep-node{fill:#fff;stroke:#555;stroke-width:1px;}" \
           ".dep-edge{stroke:#999;stroke-width:1px;}" \
           ".dep-label{font-size:12px;dominant-baseline:middle;text-anchor:middle;}" \
           ".dep-rel{font-size:10px;fill:#666;}")

    js = f"""const sentencesData={sent_json};\nfunction toggleTree(i){{const c=document.getElementById('tree-'+i);if(!c)return;if(c.style.display==='none'){{c.style.display='block';if(!c.dataset.rendered){{drawTree(i,sentencesData[i],c);c.dataset.rendered='1';}}}}else{{c.style.display='none';}}}}\nfunction drawTree(idx,tokens,container){{if(!tokens||!tokens.length){{container.innerHTML='<em>无数据</em>';return;}}const children=new Map();tokens.forEach(t=>children.set(t.id,[]));const roots=[];tokens.forEach(t=>{{if(t.head===0||t.head==='0'){{roots.push(t);}}else if(children.has(Number(t.head)))children.get(Number(t.head)).push(t);}});if(!roots.length)roots.push(tokens[0]);const depth=new Map(),order=[];roots.forEach(r=>{{depth.set(r.id,0);order.push(r);}});for(let k=0;k<order.length;k++){{const cur=order[k],d=depth.get(cur.id);(children.get(cur.id)||[]).forEach(ch=>{{depth.set(ch.id,d+1);order.push(ch);}});}}const maxD=Math.max(...depth.values());const layers=[...Array(maxD+1)].map(()=>[]);tokens.sort((a,b)=>a.id-b.id).forEach(t=>layers[depth.get(t.id)].push(t));const lvlH=70,baseW=70,hM=30,vM=20;let w=Math.max(tokens.length*baseW,400),h=(maxD+1)*lvlH+vM*2;const pos=new Map();layers.forEach((ly,d)=>{{const gap=(w-hM*2)/(ly.length+1);ly.forEach((t,i)=>pos.set(t.id,{{x:hM+gap*(i+1),y:vM+d*lvlH}}));}});const NS='http://www.w3.org/2000/svg';const svg=document.createElementNS(NS,'svg');svg.classList.add('dep-tree');svg.setAttribute('viewBox','0 0 '+w+' '+h);tokens.forEach(t=>{{if(t.head&&Number(t.head)!==0&&pos.has(Number(t.head))){{const p=pos.get(Number(t.head)),c=pos.get(t.id);const line=document.createElementNS(NS,'line');line.setAttribute('x1',p.x);line.setAttribute('y1',p.y+18);line.setAttribute('x2',c.x);line.setAttribute('y2',c.y-18);line.setAttribute('class','dep-edge');svg.appendChild(line);const midX=(p.x+c.x)/2,midY=(p.y+c.y)/2;const rel=document.createElementNS(NS,'text');rel.textContent=t.deprel||'';rel.setAttribute('x',midX);rel.setAttribute('y',midY-4);rel.setAttribute('class','dep-rel');svg.appendChild(rel);}}}});tokens.forEach(t=>{{const p=pos.get(t.id);const g=document.createElementNS(NS,'g');const cir=document.createElementNS(NS,'circle');cir.setAttribute('cx',p.x);cir.setAttribute('cy',p.y);cir.setAttribute('r',18);cir.setAttribute('class','dep-node');g.appendChild(cir);const label=document.createElementNS(NS,'text');label.setAttribute('x',p.x);label.setAttribute('y',p.y);label.setAttribute('class','dep-label');label.textContent=t.form;g.appendChild(label);const idl=document.createElementNS(NS,'text');idl.setAttribute('x',p.x);idl.setAttribute('y',p.y+28);idl.setAttribute('class','dep-rel');idl.textContent='['+t.id+']';g.appendChild(idl);svg.appendChild(g);}});container.innerHTML='';container.appendChild(svg);}}\n{highlight_js}"""

    html = f"""<!DOCTYPE html><html lang='zh'><head><meta charset='UTF-8'/><title>{title} 依存路径可视化</title><style>{css}</style></head><body><h2>{title} - 依存路径可视化</h2><div class='summary'>来源: {os.path.basename(src_file)} | 记录数: {len(pairs)} | 仅展示预计算结果</div><h3>句子分词</h3>{''.join(sent_blocks)}<h3>实体对路径结果</h3><table><tr><th>主语</th><th>关系</th><th>宾语</th><th>句序</th><th>路径节点</th><th>备注/类型</th></tr>{''.join(rows)}</table><script>{js}</script></body></html>"""

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print('[OK] 生成可视化:', out_path)

def main(title: str):
    base = os.path.abspath(os.path.dirname(__file__))
    sentences = load_dependency_sentences(base, title)
    pairs, src = load_pairs(base, title)
    out_dir = os.path.join(base, '依存路径提取结果'); os.makedirs(out_dir, exist_ok=True)
    out_html = os.path.join(out_dir, f'{title}_paths.html')
    render_html(title, sentences, pairs, out_html, src)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python visualize_paths_html.py 文章标题')
    else:
        main(sys.argv[1])