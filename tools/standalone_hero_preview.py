"""Write one portable HTML with embedded atlases, orbs and an animated fallback."""
from pathlib import Path
import base64,io,json
from PIL import Image

def data_uri(path,mime='image/png'):
    return f'data:{mime};base64,'+base64.b64encode(Path(path).read_bytes()).decode('ascii')

def make_fallback(source,destination):
    frames=[]
    with Image.open(source) as gif:
        for frame in range(gif.n_frames):
            gif.seek(frame)
            image=gif.convert('RGB');image.thumbnail((439,604),Image.Resampling.LANCZOS);frames.append(image)
    palette=frames[13].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    frames[0].save(destination,save_all=True,append_images=frames[1:],duration=50,loop=0,disposal=2,optimize=False)

def write_standalone(template,catalog,assets,orbs,fallback,destination):
    embedded={}
    for element,entry in catalog['elements'].items():
        for info in entry['states'].values():embedded[info['image']]=data_uri(Path(assets)/info['image'])
        key=f'orbs/{element}-orb.png';embedded[key]=data_uri(Path(orbs)/f'{element}-orb.png')
    text=Path(template).read_text(encoding='utf-8')
    text=text.replace('/* CATALOG */',json.dumps(catalog,ensure_ascii=False)).replace('/* EMBEDDED_IMAGES */',json.dumps(embedded,separators=(',',':')))
    fallback_html='<div id="fallback" style="text-align:center"><img style="width:100%;max-width:650px;height:auto" alt="기본형과 5원소의 대기, 걷기, 공격, 구슬 먹기 애니메이션" src="'+data_uri(fallback,'image/gif')+'"></div>'
    assert '<div class="grid" id="grid"></div>' in text
    text=text.replace('<div class="grid" id="grid"></div>',fallback_html+'<div class="grid" id="grid"></div>')
    assert '/* EMBEDDED_IMAGES */' not in text and '/* CATALOG */' not in text
    Path(destination).write_text(text,encoding='utf-8')
    return len(embedded)
