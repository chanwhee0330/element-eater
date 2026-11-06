"""Rebuild all 24 final atlases from immutable, unregistered raster exports.

Pillow and NumPy are authoring dependencies. Gameplay has no NumPy dependency.
Original ImageGen art is preserved; this stage only registers raster frames.
"""
from pathlib import Path
import argparse,json,os
from align_hero_centers import align_assets
from render_aligned import render
from standalone_hero_preview import make_fallback,write_standalone

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source',type=Path)
    parser.add_argument('--assets-dir',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args();root=args.project_root.resolve()
    source=args.source or root/'assets/sprites/hero/registration-source-v1'
    assets=args.assets_dir or root/'assets/sprites/hero'
    out=args.output_dir or root/'outputs/previews/hero-elements'
    out.mkdir(parents=True,exist_ok=True)
    catalog,_,_,_=align_assets(source,assets)
    (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    render(root,out,assets)
    make_fallback(out/'all-elements-front.gif',out/'preview-fallback.gif')
    write_standalone(root/'tools/hero_elements_preview.html',catalog,assets,out/'orbs',out/'preview-fallback.gif',out/'preview.html')
    print('Rebuilt 24 registered sheets / 768 frames.')

if __name__=='__main__':main()
