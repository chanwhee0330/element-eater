"""Robust fit of the torso silhouette; moving extremities are outliers."""
import numpy as np

def fit_outline(image,expected=None,element=None):
    a=np.asarray(image.getchannel('A'))>=128
    inside=np.zeros_like(a);inside[1:-1,1:-1]=a[1:-1,:-2]&a[1:-1,2:]&a[:-2,1:-1]&a[2:,1:-1]
    y,x=np.nonzero(a&~inside)
    keep=(y>=43)&(y<=112)&(x>8)&(x<120);x=x[keep].astype(float);y=y[keep].astype(float)
    if element=='wind':
        # Curl particles have their own alpha outline. Sample toward the body
        # interior to retain the pale torso contour rather than a green curl.
        pixels=np.asarray(image);dx=64-x;dy=78-y;distance=np.maximum(1,np.hypot(dx,dy))
        sx=np.clip(np.rint(x+dx/distance*5).astype(int),0,127);sy=np.clip(np.rint(y+dy/distance*5).astype(int),0,127)
        r,g,b,alpha=pixels[sy,sx].astype(float).T
        keep=(r>145)&(g>150)&(b>65)&(r>g*.78)&(alpha>128)&(y>=50)
        x=x[keep];y=y[keep]
    xx=(x-64)/40;yy=(y-78)/40
    design=np.column_stack([yy*yy,xx,yy,np.ones(len(x))]);rhs=-xx*xx
    rng=np.random.default_rng(7211);ids=np.array([rng.choice(len(x),4,replace=False) for _ in range(1800)])
    mats=design[ids];valid=np.abs(np.linalg.det(mats))>1e-6
    coeff=np.linalg.solve(mats[valid],rhs[ids[valid]][...,None])[...,0]
    def geom(c):
        aa,b,c1,d=c.T
        with np.errstate(invalid='ignore',divide='ignore'):
            cx=-b/2;cy=-c1/(2*aa);r2=cx*cx+aa*cy*cy-d
            rx=np.sqrt(r2);ry=np.sqrt(r2/aa)
        return np.column_stack([64+cx*40,78+cy*40,rx*40,ry*40])
    geo=geom(coeff);cx,cy,rx,ry=geo.T
    valid=np.isfinite(geo).all(axis=1)&(cx>34)&(cx<94)&(cy>65)&(cy<88)&(rx>25)&(rx<43)&(ry>23)&(ry<40)
    if expected is not None:
        near=valid&(abs(cx-expected[0])<5)&(abs(cy-expected[1])<5)&(abs(rx-expected[2])<5)&(abs(ry-expected[3])<5)
        if near.any():valid=near
    geo=geo[valid];assert len(geo)
    def errors(g):
        cx,cy,rx,ry=g.T
        return abs(np.sqrt(((x[None,:]-cx[:,None])/rx[:,None])**2+((y[None,:]-cy[:,None])/ry[:,None])**2)-1)*((rx+ry)/2)[:,None]
    diff=errors(geo);score=(diff<.8).sum(axis=1)+.25*(diff<1.5).sum(axis=1)
    best=geo[int(np.argmax(score))]
    for _ in range(4):
        sel=errors(best[None,:])[0]<1.3
        candidate=geom(np.linalg.lstsq(design[sel],rhs[sel],rcond=None)[0][None,:])[0]
        if np.isfinite(candidate).all() and max(abs(candidate-best))<2:best=candidate
    return dict(zip(['cx','cy','rx','ry'],map(float,best)),support=int((errors(best[None,:])[0]<1.3).sum()),method='torso-outline-ransac')
