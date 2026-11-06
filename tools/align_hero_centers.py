"""Register all hero frames by torso geometry, never by the currently extended foot."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import argparse,copy,hashlib,json,math,shutil
import numpy as np
from torso_registration import fit_torso

ELEMENTS={'neutral':'무속성','water':'물','fire':'불','wind':'바람','earth':'흙','lightning':'번개'}
STATES={'idle':('대기',4,True),'walk':('걷기',10,True),'attack':('기본 공격',12,False),'ingest':('구슬 먹기',12,False)}
DIRS=['down','left','right','up']
MODEL=(64.,76.,34.,32.)

def mouth_center(image,direction):
    if direction=='up':return [64,51]
    box={'down':(39,48,89,97),'left':(10,45,63,97),'right':(66,45,119,97)}[direction]
    points=set()
    for y in range(box[1],box[3]):
        for x in range(box[0],box[2]):
            r,g,b,a=image.getpixel((x,y))
            if a>128 and 45<r<205 and g<70 and b<75 and r>g*2.2:points.add((x,y))
    from collections import deque
    groups=[]
    while points:
        start=points.pop();q=deque([start]);group=[start]
        while q:
            x,y=q.popleft()
            for p in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                if p in points:points.remove(p);q.append(p);group.append(p)
        groups.append(group)
    if not groups:return {'down':[64,76],'left':[35,73],'right':[93,73]}[direction]
    group=max(groups,key=len)
    return [round((min(x for x,y in group)+max(x for x,y in group))/2),round((min(y for x,y in group)+max(y for x,y in group))/2)]

def affine(fit,target):
    cx,cy,rx,ry=target
    sx,sy=fit['rx']/rx,fit['ry']/ry
    return (sx,0,fit['cx']-sx*cx,0,sy,fit['cy']-sy*cy)

def model_y(y,fit):
    top,bottom=fit['cy']-fit['ry'],fit['cy']+fit['ry']
    if y<top:return MODEL[1]-MODEL[3]+(y-top)/fit['rx']*MODEL[2]
    if y>bottom:return MODEL[1]+MODEL[3]+(y-bottom)/fit['rx']*MODEL[2]
    return MODEL[1]+(y-fit['cy'])/fit['ry']*MODEL[3]

def render_registered(image,fit,target):
    cx,cy,rx,ry=target;sx=fit['rx']/rx
    top,bottom=cy-ry,cy+ry
    result=Image.new('RGBA',(128,128))
    regions=[(0,max(0,round(top)),(sx,0,fit['cx']-sx*cx,0,sx,fit['cy']-fit['ry']-sx*top)),
             (max(0,round(top)),min(128,round(bottom)),affine(fit,target)),
             (min(128,round(bottom)),128,(sx,0,fit['cx']-sx*cx,0,sx,fit['cy']+fit['ry']-sx*bottom))]
    for y0,y1,matrix in regions:
        if y1>y0:
            layer=image.transform((128,128),Image.Transform.AFFINE,matrix,Image.Resampling.BICUBIC)
            result.paste(layer.crop((0,y0,128,y1)),(0,y0))
    return result

def align_assets(source,destination,report=None):
    source,destination=Path(source),Path(destination)
    records={};originals={};global_fit=1.
    for element in ELEMENTS:
        if not (source/element/f'hero-{element}-idle.png').exists():continue
        records[element]={};originals[element]={}
        for state in STATES:
            path=source/element/f'hero-{element}-{state}.png'
            sheet=Image.open(path).convert('RGBA')
            meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
            rows=[];source_rows=[]
            for row,direction in enumerate(DIRS):
                poses=[];original_row=[]
                for col in range(8):
                    image=sheet.crop((col*128,row*128,(col+1)*128,(row+1)*128));fit=fit_torso(image,element)
                    bounds=image.getchannel('A').point(lambda v:255 if v>=64 else 0).getbbox()
                    # Fit all visible art inside a shared 128px cell without using
                    # changing ears/feet to choose the origin of individual frames.
                    xmin=(bounds[0]-fit['cx'])/fit['rx']*MODEL[2];xmax=(bounds[2]-fit['cx'])/fit['rx']*MODEL[2]
                    ymin=model_y(bounds[1],fit)-114
                    ymax=model_y(bounds[3],fit)-114
                    if xmin<0:global_fit=min(global_fit,62/-xmin)
                    if xmax>0:global_fit=min(global_fit,62/xmax)
                    if ymin<0:global_fit=min(global_fit,112/-ymin)
                    if ymax>0:global_fit=min(global_fit,12/ymax)
                    poses.append({'image':image,'fit':fit,'meta':meta});original_row.append(image)
                rows.append(poses);source_rows.append(original_row)
            records[element][state]=rows;originals[element][state]=source_rows
        print('Measured '+element,flush=True)
    # Keep one target geometry across all six forms/directions/states.
    global_fit=min(1.,global_fit*.99)
    assert global_fit>.65,('unexpected art extent',global_fit)
    target=(64.,114+(MODEL[1]-114)*global_fit,MODEL[2]*global_fit,MODEL[3]*global_fit)
    corrected={};audit=[];catalog={'schema':'element-eater.hero-animations.aligned.v2','frameSize':128,'pivot':[64,114],'torsoTarget':list(target),'registrationMethod':'shared-torso-ellipse','elementCount':len(records),'sheetCount':len(records)*4,'frameCount':len(records)*128,'elements':{}}
    for element,states in records.items():
        corrected[element]={};entry={'name':ELEMENTS[element],'states':{},'mouths':{},'ingestMouths':{}}
        for state,rows in states.items():
            corrected_rows=[]
            for row,poses in enumerate(rows):
                new_row=[]
                for col,pose in enumerate(poses):
                    image=pose['image'];fitted=pose['fit'].copy()
                    aligned=render_registered(image,fitted,target)
                    after=fit_torso(aligned,element,target)
                    best_error=math.hypot(after['cx']-target[0],after['cy']-target[1]);best=(aligned,after,fitted.copy())
                    for _ in range(5):
                        if best_error<.35:break
                        fitted['cx']+=fitted['rx']/target[2]*float(np.clip(after['cx']-target[0],-2,2))
                        fitted['cy']+=fitted['ry']/target[3]*float(np.clip(after['cy']-target[1],-2,2))
                        candidate=render_registered(image,fitted,target)
                        measured=fit_torso(candidate,element,target)
                        error=math.hypot(measured['cx']-target[0],measured['cy']-target[1])
                        if error<best_error:best_error=error;best=(candidate,measured,fitted.copy())
                        after=measured
                    aligned,after,fitted=best
                    if best_error>1:
                        origin=fitted.copy()
                        for dx in [-1,-.5,0,.5,1]:
                            for dy in [-2,-1,0,1,2]:
                                adjusted=origin.copy();adjusted['cx']+=dx*origin['rx']/target[2];adjusted['cy']+=dy*origin['ry']/target[3]
                                candidate=render_registered(image,adjusted,target);measured=fit_torso(candidate,element,target)
                                error=math.hypot(measured['cx']-target[0],measured['cy']-target[1])
                                if error<best_error:best_error=error;best=(candidate,measured,adjusted)
                        aligned,after,fitted=best
                    new_row.append(aligned)
                    audit.append({'element':element,'state':state,'direction':DIRS[row],'frame':col,'before':pose['fit'],'after':after,'target':list(target),'inputTorso':fitted})
                corrected_rows.append(new_row)
            corrected[element][state]=corrected_rows
        # Preserve each complete pose. A rectangular idle-foot overwrite cuts
        # through the lower torso after registration and must never be reapplied.
        for row in range(4):
            base=corrected[element]['idle'][row][0]
            for state in ['attack','ingest']:
                corrected[element][state][row][0]=base.copy();corrected[element][state][row][7]=base.copy()
        folder=destination/element;folder.mkdir(parents=True,exist_ok=True)
        for row,direction in enumerate(DIRS):
            entry['mouths'][direction]=mouth_center(corrected[element]['attack'][row][3],direction)
            entry['ingestMouths'][direction]=mouth_center(corrected[element]['ingest'][row][3],direction)
        for state,(label,fps,loop) in STATES.items():
            sheet=Image.new('RGBA',(1024,512))
            for row in range(4):
                for col,image in enumerate(corrected[element][state][row]):sheet.paste(image,(col*128,row*128))
            file=folder/f'hero-{element}-{state}.png';sheet.save(file)
            meta=copy.deepcopy(states[state][0][0]['meta'])
            meta['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
            meta['registration']={'method':'shared-torso-ellipse','target':list(target),'pivot':[64,114],'feetNeverDefinePerFrameCenter':True,'sameTargetAcrossAllForms':True,'preserveCompletePose':True,'rectangularFootOverwrite':False}
            for row,direction in enumerate(DIRS):
                for col in range(8):
                    key=f'{direction}_{col}'
                    if key in meta['frames']:
                        meta['frames'][key]['registrationTarget']=list(target[:2])
                        meta['frames'][key]['opaqueBoundsInCell']=list(corrected[element][state][row][col].getchannel('A').point(lambda v:255 if v>=128 else 0).getbbox())
            if state=='attack':meta['muzzlePixelsTopLeft']={k:dict(zip(['x','y'],v)) for k,v in entry['mouths'].items()}
            if state=='ingest':meta['mouthPixelsTopLeft']={k:dict(zip(['x','y'],v)) for k,v in entry['ingestMouths'].items()}
            file.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            entry['states'][state]={'image':f'{element}/{file.name}','fps':fps,'loop':loop,'label':label}
        catalog['elements'][element]=entry
        print('Aligned '+element,flush=True)
    if report:Path(report).write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    return catalog,corrected,originals,audit

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--report',type=Path)
    args=p.parse_args();catalog,_,_,audit=align_assets(args.source,args.destination,args.report)
    args.catalog.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Maximum center error:',max(math.hypot(a['after']['cx']-a['target'][0],a['after']['cy']-a['target'][1]) for a in audit))
if __name__=='__main__':main()

