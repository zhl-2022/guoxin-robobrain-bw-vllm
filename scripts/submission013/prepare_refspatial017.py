"""Prepare the original complete location100 + placement100; no model execution."""
from pathlib import Path
import concurrent.futures
import hashlib
import io
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
REV='098de7c8785277e5d3b3270d13863c8ac85a6852'
DEST=ROOT/'datasets/session017/refspatial200-002'
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7897'}))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    assert not DEST.exists()
    DEST.mkdir(parents=True);(DEST/'raw').mkdir();(DEST/'images').mkdir();(DEST/'masks').mkdir()
    with OPENER.open(f'https://huggingface.co/api/datasets/BAAI/RefSpatial-Bench/tree/{REV}/data',timeout=45) as response:
        tree=json.load(response)
    (DEST/'raw/dataset-tree.json').write_text(json.dumps(tree,indent=2)+'\n')
    wanted={'data/location-00000-of-00001.parquet','data/placement-00000-of-00001.parquet'}
    rows=[r for r in tree if r['path'] in wanted];assert len(rows)==2
    def download(row):
        url=f'https://huggingface.co/datasets/BAAI/RefSpatial-Bench/resolve/{REV}/'+row['path']
        cached=ROOT/'datasets/session017/refspatial200/raw'/Path(row['path']).name
        if cached.is_file():raw=cached.read_bytes()
        else:
            with OPENER.open(url,timeout=120) as response:raw=response.read(60*1024**2)
        assert len(raw)==row['size'] and sha(raw)==row['lfs']['oid']
        p=DEST/'raw'/Path(row['path']).name;p.write_bytes(raw);return p
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:files=list(pool.map(download,rows))
    import pyarrow.parquet as pq
    from PIL import Image
    samples=[];annotations=[]
    for path in sorted(files):
        split=path.name.split('-')[0];values=pq.ParquetFile(path).read().to_pylist();assert len(values)==100
        for row in values:
            name=f'{split}_{row["id"]}';rgb=row['image']['bytes'];mask=row['mask']['bytes']
            image=Image.open(io.BytesIO(rgb));image.load();gold=Image.open(io.BytesIO(mask));gold.load()
            assert image.size==gold.size
            formats={'PNG':'.png','JPEG':'.jpg','BMP':'.bmp','TIFF':'.tiff','WEBP':'.webp'}
            image_name='images/'+name+formats[image.format];mask_name='masks/'+name+formats[gold.format]
            (DEST/image_name).write_bytes(rgb);(DEST/mask_name).write_bytes(mask)
            question=row['prompt']+' Please provide its 2D coordinates.'
            samples.append({'id':name,'split':split,'image':image_name,'image_sha256':sha(rgb),
                            'question':question,'image_format':image.format,'width':image.width,'height':image.height,'step':row['step']})
            annotations.append({'id':name,'mask':mask_name,'mask_sha256':sha(mask),'object':row['object'],
                                'source_prompt':row['prompt'],'source_suffix':row['suffix'],'split':split,'step':row['step']})
    assert len(samples)==len({s['id'] for s in samples})==200
    (DEST/'samples.jsonl').write_text(''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in samples),encoding='utf-8',newline='\n')
    (DEST/'annotations.json').write_text(json.dumps(annotations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    ready={'dataset':'BAAI/RefSpatial-Bench','revision':REV,'revision_date':'2025-10-23 before RoboBrain2.5 paper',
           'samples':200,'complete_splits':{'location':100,'placement':100},'unseen77_excluded_by_benchmark_scope':True,
           'source_images_and_masks_hashed':True,'selection_before_any_predictions':True,
           'prompt_source':'Pinned RoboRefer Evaluation/test_benchmark.py get_prompt RoboBrain branch',
           'coordinate_domain':'RoboBrain2.5 native0..1000; declared conversion to pixels before unmodified mask grader',
           'publisher_baseline_percent':60.5,'absolute_threshold_percent':58.5,
           'publisher_paper_names_RefSpatial_but_no_dataset_revision_published':True,
           'samples_sha256':sha((DEST/'samples.jsonl').read_bytes()),
           'annotations_sha256':sha((DEST/'annotations.json').read_bytes()),'GPU_executed':False,'numeric_pass':None,'submitted':False}
    (DEST/'READY.json').write_text(json.dumps(ready,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(ready,indent=2))


if __name__=='__main__':main()
