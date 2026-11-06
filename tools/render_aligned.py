from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import argparse,json,math,shutil

def render(project,out,assets=None):
    out,project=Path(out),Path(project)
    catalog=json.loads((out/'catalog.json').read_text(encoding='utf-8'))
    assets=Path(assets) if assets else out/'sprites'
    elements=catalog['elements'];states=['idle','walk','attack','ingest'];dirs=['down','left','right','up']
    names=['정면','왼쪽','오른쪽','뒷면'];sheets={};orbs={}
    (out/'previews').mkdir(exist_ok=True);(out/'orbs').mkdir(exist_ok=True)
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',size)
    for element,entry in elements.items():
        sheets[element]={state:Image.open(assets/data['image']).convert('RGBA') for state,data in entry['states'].items()}
        key='water' if element=='neutral' else element
        orb=Image.open(project/f'assets/items/elements/break-release-v3/sprites/{key}-orb.png').convert('RGBA')
        orb.save(out/f'orbs/{element}-orb.png');orbs[element]=orb
    def pose(element,state,direction,t):
        row=dirs.index(direction);info=elements[element]['states'][state];phase=t%2;elapsed=None
        if info['loop']:frame=int(t*info['fps']+1e-6)%8
        elif phase<.4 or phase>=.4+8/12:state='idle';frame=0
        else:elapsed=phase-.4;frame=min(7,int(elapsed*12+1e-6))
        return sheets[element][state].crop((frame*128,row*128,(frame+1)*128,(row+1)*128)),elapsed
    def scene(element,state,direction,t):
        image=Image.new('RGBA',(180,183));sprite,elapsed=pose(element,state,direction,t);origin=(10,7);scale=1.25
        def item():
            if state=='attack' and elapsed is not None and elapsed>=.25:
                m=elements[element]['mouths'][direction];v={'down':(0,1),'left':(-1,0),'right':(1,0),'up':(0,-1)}[direction];distance=(elapsed-.25)*160;x,y=m[0]+v[0]*distance,m[1]+v[1]*distance;size=10
            elif state=='ingest' and t%2<.4+4/12:
                start={'down':(64,125),'left':(12,74),'right':(116,74),'up':(64,6)}[direction];m=elements[element]['ingestMouths'][direction];p=max(0,min(1,(max(0,t%2-.4)-1/12)/(2/12)));ease=p*p*(3-2*p);x,y=start[0]+(m[0]-start[0])*ease,start[1]+(m[1]-start[1])*ease;size=21*(1-p*.9)
            else:return
            n=max(1,round(size*scale));art=orbs[element].resize((n,n),Image.Resampling.LANCZOS);image.alpha_composite(art,(round(origin[0]+x*scale-n/2),round(origin[1]+y*scale-n/2)))
        if direction=='up':item()
        image.alpha_composite(sprite.resize((160,160),Image.Resampling.LANCZOS),origin)
        if direction!='up':item()
        return image
    def board(t,element=None):
        rows=list(elements) if element is None else dirs
        image=Image.new('RGB',(878,86+len(rows)*187),'#14261e');d=ImageDraw.Draw(image)
        title='캐릭터 전체 · 몸통 중심 고정' if element is None else elements[element]['name']+' · 중심 정렬 수정'
        d.text((18,12),title,font=font(22),fill='#f5edd4')
        for col,state in enumerate(states):d.text((100+col*193,54),elements['water']['states'][state]['label'],font=font(18),fill='#c6d7ab')
        for row,key in enumerate(rows):
            el=key if element is None else element;direction='down' if element is None else key;y=83+row*187
            d.text((8,y+70),elements[el]['name'] if element is None else names[row],font=font(17),fill='#e7dfbd')
            for col,state in enumerate(states):
                x=83+col*193;d.rounded_rectangle((x,y,x+180,y+178),radius=12,fill='#233e30',outline='#4d6547');art=scene(el,state,direction,t);image.paste(art,(x,y),art)
        return image
    for element in [None,*elements]:
        pictures=[board(i/20,element) for i in range(80)]
        filename='all-elements-front.gif' if element is None else f'previews/{element}-four-states.gif'
        palette=pictures[13].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
        pictures=[p.quantize(palette=palette,dither=Image.Dither.NONE) for p in pictures]
        pictures[0].save(out/filename,save_all=True,append_images=pictures[1:],duration=50,loop=0,disposal=2,optimize=False)
        if element is None:board(.65).save(out/'preview-still.png')
        print('Rendered '+filename,flush=True)
    return catalog

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();render(a.project_root,a.output_dir)
