"""오원 제단, 의식과 수호자 전투의 Pico2D 표현."""

import json
import math

from .acquisition_art import ROCKFALL_BOULDER, ROCKFALL_DEBRIS
from .boss import (COLORS, EARTH_INTERVAL, FALL_SECONDS, FIRE_FAN, GATE_SECONDS, GATE_WATCH,
                   GUARDIAN_DRAW_UNIT, GUARDIAN_SHOT_LIFT, RITUAL, SHATTER_AT, SUMMON_SECONDS,
                   SUMMON_SHOCK_AT, SUMMON_SHOCK_SECONDS, WATER_GAPS, WATER_RING_DELAY)
from .elements import NAMES, WEAKNESS
from .element_master_aura import draw_master_aura


PROLOGUE_SECONDS = 7.2
ENDING_RETURN_DELAY = .8
MIXER_REVEAL_AT = .53


def ease(value):
    t = max(0,min(1,value))
    return t*t*(3-2*t)


class GuardianArt:
    def __init__(self, app):
        self.app = app
        self.p = app.p
        folder = app.room.map_path.parent
        self.props = self.p.load_image(str(folder/'guardian-objects.png'))
        self.props_frames = json.loads((folder/'guardian-objects.json').read_text(encoding='utf-8'))
        self.assembly = self.p.load_image(str(folder/'guardian-assembly.png'))
        wheel_folder = folder.parent/'room-09'
        self.gate_meta = json.loads((wheel_folder/'trial-waterwheel.json').read_text(encoding='utf-8'))
        self.gate_image = self.p.load_image(str(wheel_folder/self.gate_meta['image']))
        self.images = {element:self.p.load_image(str(path))
                       for element,(path,_) in self.room.guardian.clips.items()}

    @property
    def room(self):
        return self.app.room

    @property
    def guardian(self):
        return self.room.guardian

    @property
    def unit(self):
        return self.app.view.tile_width

    def line(self, a, b, color, alpha=255):
        self.p.draw_line(*self.app.point(*a),*self.app.point(*b),*color,round(alpha))

    def arc(self, origin, radius, start, stop, color, alpha):
        cx,cy=origin
        cursor = cx+radius*math.cos(start),cy+radius*math.sin(start)
        steps = max(6,math.ceil(abs(stop-start)*radius*3))
        for i in range(1,steps+1):
            angle = start+(stop-start)*i/steps
            end = cx+radius*math.cos(angle),cy+radius*math.sin(angle)
            self.line(cursor,end,color,alpha)
            cursor=end

    def altar_arc(self, origin, radius, start, stop, color, alpha):
        spacing = 1 / self.unit
        for offset in (-5, -4, -3, 3, 4, 5):
            glow_alpha = alpha * (6 - abs(offset)) * .11
            self.arc(origin, radius + offset * spacing, start, stop, color, glow_alpha)
        for offset in range(-2, 3):
            self.arc(origin, radius + offset * spacing, start, stop, color, alpha)

    def altar_light_tip(self, point, color):
        x, y = self.app.point(*point)
        self.app.ui.orb_socket_glow(x, y, 3, color)
        self.p.draw_circle(x, y, 4, *color, filled=True)
        self.p.draw_circle(x, y, 2, 255, 244, 219, filled=True)

    def floor(self):
        g = self.guardian
        t = self.room.elapsed
        self.app.ui.begin()
        self.app.acquisition_art.bridge(g.bridge, 'stone')
        center = g.spec['center']
        angles = [math.atan2(y-center[1], x-center[0]) for x, y in g.spec['devices']]
        for i,(point,feed) in enumerate(zip(g.spec['devices'],g.spec['feeds'])):
            color = COLORS[RITUAL[i]]
            if g.ritual < len(RITUAL) or g.summoning:
                on = RITUAL[i] in g.placed
                current = g.can_place_orb(self.room, RITUAL[i])
            else:
                on, current = RITUAL[i] == g.element and g.fall < 0, False
            if not (on or current):
                continue
            alpha = 221 if on else 100+77*math.sin(t*5)**2
            x,y = point
            diamond = [(x,y-.61),(x+.74,y),(x,y+.61),(x-.74,y)]
            for start,end in zip(diamond,diamond[1:]+diamond[:1]):
                self.line(start,end,color,alpha)
            if on:
                if RITUAL[i] in g.placed and g.summon < SUMMON_SHOCK_AT:
                    px, py = self.app.point(x, y)
                    radius = max(10, round(self.unit * .58))
                    self.app.ui.orb_socket_glow(px, py, radius, color)
                    self.p.draw_circle(px, py, radius-5, *color, 100, filled=True)
                    for edge in range(radius-5, radius+1):
                        self.p.draw_circle(px, py, edge, *color, 235)
                age = t - g.placed_at.get(RITUAL[i], t - 1)
                if not (g.ritual < len(RITUAL) or g.summoning):
                    age = 1
                a = angles[i]
                feed_progress = min(1, max(0, age / .18))
                tip = tuple(start + (end-start)*feed_progress for start, end in zip(point, feed))
                self.line(point, tip, color, alpha)
                if feed_progress < 1:
                    self.altar_light_tip(tip, color)
                    continue
                spread = ease((age - .18) / .58)
                if not spread:
                    self.altar_light_tip(feed, color)
                    continue
                left_span = ((a - angles[i-1]) % math.tau) / 2
                right_span = ((angles[(i+1) % len(angles)] - a) % math.tau) / 2
                start, stop = a-left_span*spread, a+right_span*spread
                self.altar_arc(center, 4.25, start, stop, color, alpha)
                self.altar_arc(center, 3.23, start, stop, color, alpha*.72)
                if spread < 1:
                    for tip_angle in (start, stop):
                        self.altar_light_tip((center[0]+4.25*math.cos(tip_angle),
                                              center[1]+4.25*math.sin(tip_angle)), color)
                    continue
                phase = start + (stop-start) * ((t*1.65+i*.11) % 1)
                px,py = center[0]+4.25*math.cos(phase),center[1]+4.25*math.sin(phase)
                self.p.draw_circle(*self.app.point(px,py),2,*color,filled=True)
        if g.ritual < len(RITUAL) or g.summoning and g.summon < .73:
            for i in range(5):
                a=i*math.tau/5+.23
                points = [(center[0]+r*math.cos(a+o),center[1]+r*math.sin(a+o))
                          for r,o in ((0,0),(.43,.12),(.73,-.12),(1.16,.17))]
                for start,end in zip(points,points[1:]):
                    self.line(start,end,(68,48,61))
        if g.summoning:
            self.summon_light()
        self.warnings()

    def summon_light(self):
        g = self.guardian
        t = g.summon
        cx,cy = center = g.spec['center']
        if t < 1.1:
            reach=ease(t/.84)
            for i,(x,y) in enumerate(g.spec['feeds']):
                dx,dy = x-cx,y-cy
                end = cx+dx*(1-reach),cy+dy*(1-reach)
                color=COLORS[RITUAL[i]]
                self.line((x,y),end,color,215)
                self.line((x+.025,y+.025),end,(255,229,170),184)
                self.p.draw_circle(*self.app.point(*end),3,*color,filled=True)
        for start in (.24,.7,1.18):
            phase=(t-start)/.74
            if 0 < phase < 1:
                radius=.27+5.25*phase
                self.arc(center,radius,0,math.tau,(255,211,130),223*(1-phase))
                self.arc(center,radius-.18,0,math.tau,(207,148,100),142*(1-phase))
        if .31 < t < 1.77:
            intensity=math.sin(math.pi*(t-.31)/1.46)
            x,y=self.app.point(*center)
            for r,k in ((33,.14),(22,.27),(13,.55),(7,.80)):
                self.p.draw_circle(x,y,round(r*self.unit/37),255,192,113,round(intensity*k*255),filled=True)
        impact = (t - SUMMON_SHOCK_AT) / SUMMON_SHOCK_SECONDS
        if 0 <= impact < 1:
            force = 1 - (1-impact)**2
            radius = .4 + 7.2 * force
            self.arc(center, radius, 0, math.tau, (253,239,218), 240*(1-impact))
            self.arc(center, radius + .19, 0, math.tau, (209,177,249), 170*(1-impact))
            for i in range(17):
                angle = i * 2.399
                reach = radius * (.59 + .045 * (i%7))
                px, py = self.app.point(cx+math.cos(angle)*reach, cy+math.sin(angle)*reach, 14*(1-impact))
                self.app.ui.diamond(px, py, 2 + i%3, (246,208,170,round(212*(1-impact))))

    def warnings(self):
        g=self.guardian
        if g.attack_age < 0:
            return
        element=g.element
        color=COLORS[element]
        age=g.attack_age
        release=g.clip('attack').events['release']
        origin=self.room.enemies[0].x,self.room.enemies[0].y
        if element == 'earth':
            for i,point in enumerate(g.earth_points()):
                left=release+i*EARTH_INTERVAL-age
                if left >= 0:
                    self.arc(point,1.02,0,math.tau,color,220)
                    self.arc(point,.76,age*3,math.pi+age*3,color,175)
                    x,y = self.app.point(*point)
                    self.p.draw_line(x-6,y-6,x+6,y+6,*color)
                    self.p.draw_line(x+6,y-6,x-6,y+6,*color)
        elif element == 'water':
            for i,gap in enumerate(WATER_GAPS):
                if age < release+i*WATER_RING_DELAY:
                    gap += g.heading
                    self.arc(origin,1.7+i*.79,gap+.57,gap+math.tau-.57,color,195)
        elif age < release:
            length = 6 if element == 'wind' else 12
            offsets = FIRE_FAN if element == 'fire' else (0,)
            for offset in offsets:
                a=g.heading+offset
                dx,dy=math.cos(a),math.sin(a)
                end=origin[0]+length*dx,origin[1]+length*dy
                self.line(origin,end,color,218 if element!='fire' else 152)
                if element in ('wind','lightning'):
                    span=.70 if element=='wind' else .13
                    for sign in (-1,1):
                        self.line((origin[0]+dy*span*sign,origin[1]-dx*span*sign),
                                  (end[0]+dy*span*sign,end[1]-dx*span*sign),color,164)

    def prop(self, kind, frame, point, width):
        left,bottom,w,h=self.props_frames[kind][frame]
        x,y=self.app.point(*point)
        scale=width*self.unit/w
        self.props.clip_draw(left,bottom,w,h,x,y+h*scale/2-6,w*scale,h*scale)

    def device(self, index):
        g=self.guardian
        t=self.room.elapsed
        x,y=point=g.spec['devices'][index]
        element = RITUAL[index]
        active = element in g.placed
        if index == 0:
            self.prop('basin',1+int(t*10)%12 if active else 0,point,2.12)
        elif index == 1:
            self.prop('fire',1+int(t*19)%11 if active else 0,point,1.80)
        elif index == 2:
            self.app.acquisition_art.draw_counterweight_prop('socket',point)
        elif index == 3:
            self.app.acquisition_art.draw_counterweight_prop('socket',point)
        elif index == 4:
            self.prop('coil',2+int(t*13)%3 if active else 0,point,1.62)
        if self.room.stage == 10 and not active and g.ritual < len(RITUAL):
            px, py = self.app.point(x, y, self.unit * .96)
            orb = self.app.source_images[element, 'orb']
            orb.opacify(.28)
            orb.draw(px, py, self.unit * .75, self.unit * .75)
            orb.opacify(1)

    def loose_orb(self, element):
        x, y, phase = self.guardian.orb_flight(element)
        lift = (.97 - .55*phase + .93*math.sin(math.pi*phase)
                + .07*math.sin(self.room.elapsed*5 + RITUAL.index(element)))
        px, py = self.app.point(x, y, self.unit * lift)
        if phase > 0:
            self.app.view.draw_shadow(x, y)
        self.app.source_images[element, 'orb'].draw(px, py, self.unit * .75, self.unit * .75)

    def layers(self):
        g=self.guardian
        layers=[]
        for i, (_, y) in enumerate(g.spec['devices']):
            layers.append((y, self.device, (i,)))
        if self.room.stage == 0:
            layers.append((g.spec['center'][1], self.tablet, ()))
        for element in RITUAL:
            if element in g.placed:
                layers.append((g.orb_flight(element)[1], self.loose_orb, (element,)))
        if g.summoning or g.battle or g.collapsing:
            if g.collapsing:
                layers.append((self.room.enemies[0].y-.01, self.defeat_wave, ()))
            layers.append((self.room.enemies[0].y,self.actor,()))
        point = self.room.final_reward
        if point is None and MIXER_REVEAL_AT <= g.fall < FALL_SECONDS:
            actor = self.room.enemies[0]
            point = actor.x, actor.y
        if point is not None:
            layers.append((point[1], self.reward, point))
        if g.attack_age >= 0 and g.element == 'earth':
            release=g.clip('attack').events['release']
            for i,point in enumerate(g.earth_points()):
                age=g.attack_age-release-i*EARTH_INTERVAL
                if -.29 < age < .30:
                    layers.append((point[1]+.08,self.rock,(point,age,i)))
        return layers

    def rock(self, point, age, index):
        x,y=self.app.point(*point)
        image=self.app.acquisition_art.quarry_props
        size=self.unit*(.82-.085*index)
        side=-1 if index%2 else 1
        if age < 0:
            fall=(age+.29)/.29
            image.opacify(min(1,fall*4))
            image.clip_composite_draw(*ROCKFALL_BOULDER,side*(.68-.9*fall),'',
                                      x+side*size*(1-fall)*.65,
                                      y+size*.42+self.unit*2.8*(1-fall*fall),size,size)
        else:
            spread=age/.30
            image.opacify(1-spread)
            image.clip_draw(*ROCKFALL_DEBRIS,x,y+size*.16,size*(1.25+spread),size*.63)
        image.opacify(1)

    def actor(self):
        g=self.guardian
        actor=self.room.enemies[0]
        if g.summoning and g.summon < 1.57:
            self.assemble()
            return
        point = self.app.point(actor.x,actor.y)
        self.app.view.draw_shadow(actor.x,actor.y)
        if g.fall >= 0:
            self.shatter(point, g.fall)
            return
        if g.swap >= 0:
            self.transform(point)
            return
        state,age = g.pose(actor)
        if g.summoning:
            age = 0
        self.draw_pose(g.form,g.clip(state).frame(age),point,1,hit=actor.hit_flash>0)

    def shatter(self, point, time):
        g, ui = self.guardian, self.app.ui
        frame = g.clip('idle').frame(0)
        x, y = point
        scale = self.unit / GUARDIAN_DRAW_UNIT
        if time < SHATTER_AT:
            advance = time / SHATTER_AT
            x += math.sin(time*148)*4*advance
            self.draw_pose(g.form, frame, (x, y), 1, 1-.12*advance, hit=advance > .84)
            ui.begin()
            core_y = y+self.unit*(2.33-.27*advance)
            for index, crack in enumerate((
                    ((0, 0), (-.32, .22), (-.62, .17), (-.92, .68), (-1.45, .83)),
                    ((0, 0), (.31, .18), (.50, .12), (.88, .60), (1.32, .72)),
                    ((0, 0), (-.22, -.33), (-.52, -.43), (-.63, -.84), (-1.25, -1.00)),
                    ((0, 0), (.27, -.22), (.54, -.47), (.47, -.81), (1.18, -1.02)),
                    ((0, 0), (.04, .31), (-.18, .68), (.11, .9), (-.19, 1.25)))):
                growth = 4*ease((advance-.12-index*.068)/.55)
                for piece, (a, b) in enumerate(zip(crack, crack[1:])):
                    end = max(0, min(1, growth-piece))
                    if not end:
                        continue
                    px, py = x+a[0]*self.unit, core_y+a[1]*self.unit
                    tx, ty = px+(b[0]-a[0])*self.unit*end, py+(b[1]-a[1])*self.unit*end
                    for shift in (-1, 1):
                        self.p.draw_line(px+shift, py, tx+shift, ty, *COLORS[g.form], 160)
                    self.p.draw_line(px, py, tx, ty, 255, 239, 189, 244)
            ui.diamond(x, core_y, 5+(13+3*math.sin(time*99))*advance,
                       (255, 225, 158, round(220*advance)))
            return
        age = (time-SHATTER_AT)/(FALL_SECONDS-SHATTER_AT)
        clip, pivot = frame['pico2dClip'], frame['pivotPixelsTopLeft']
        image = self.images[g.form]
        image.opacify(1-ease((age-.35)/.65))
        for row in range(5):
            top, bottom = clip['height']*row//5, clip['height']*(row+1)//5
            for col in range(5):
                left, right = clip['width']*col//5, clip['width']*(col+1)//5
                dx = ((left+right)/2-pivot['x'])*scale
                dy = (pivot['y']-(top+bottom)/2)*scale*.87
                direction = (col-2) or (1 if row%2 else -1)
                px = x+dx+direction*self.unit*1.68*ease(age)
                py = y+dy+(1+((row+col)%3)*.54)*self.unit*math.sin(math.pi*age)-age*age*self.unit*1.62
                image.clip_composite_draw(clip['left']+left, clip['bottom']+clip['height']-bottom,
                                          right-left, bottom-top, direction*.71*age, '', px, py,
                                          (right-left)*scale, (bottom-top)*scale*.87)
        image.opacify(1)

    def defeat_wave(self):
        app = self.app
        g, boss = self.guardian, self.room.enemies[0]
        progress = (g.fall-SHATTER_AT)/(FALL_SECONDS-SHATTER_AT)
        if progress < 0:
            return
        app.ui.begin()
        color = COLORS[g.form]
        x, y = app.point(boss.x, boss.y)
        for offset, tint in ((0, (255, 226, 171)), (.12, color)):
            age = min(1, max(0, (progress-offset)/.74))
            self.arc((boss.x, boss.y), .72 + 6.2*ease(age), 0, math.tau, tint,
                     250*(1-age) if progress >= offset else 0)
        for i in range(28):
            angle = i*2.399
            radius = self.unit*(.38+(2.4+(i%8)*.44)*ease(progress))
            px = x+radius*math.cos(angle)
            py = y+radius*.51*math.sin(angle)+self.unit*(i%5)*.40*math.sin(progress*math.pi)
            app.ui.diamond(px, py, (2+i%4)*(1-progress), (*color, round(223*(1-progress))))
        flash = 1-ease(progress/.22)
        if flash:
            app.ui.diamond(x, y+self.unit*2, 9+37*flash, (255, 238, 187, round(215*flash)))

    def defeat_camera(self):
        app, g = self.app, self.guardian
        boss = self.room.enemies[0]
        player = self.room.player
        look = ease(g.fall/.17)*(1-ease((g.fall-.69)/.25))
        impact = 1-ease((g.fall-SHATTER_AT)/.17) if g.fall >= SHATTER_AT else 0
        focus = (player.x+(boss.x-player.x)*look + math.sin(g.fall*207)*.17*impact,
                 player.y+(boss.y-1.1-player.y)*look + math.cos(g.fall*174)*.12*impact)
        app.draw_world_from(focus, 1+.25*look)
        app.ui.begin()
        bars = round(46*look)
        if bars:
            self.p.draw_rectangle(0, 0, app.width-1, bars, 10, 8, 16, filled=True)
            self.p.draw_rectangle(0, app.height-bars, app.width-1, app.height-1, 10, 8, 16, filled=True)

    def draw_pose(self, form, frame, point, opacity, vertical_scale=1, hit=False):
        if opacity <= 0:
            return
        image=self.images[form]
        clip,pivot=frame['pico2dClip'],frame['pivotPixelsTopLeft']
        w,h=clip['width'],clip['height']
        scale=self.unit/GUARDIAN_DRAW_UNIT
        height=scale*vertical_scale
        x,y=point
        image.opacify(opacity)
        if hit:
            self.p.SDL_SetTextureColorMod(image.texture,255,175,175)
        image.clip_draw(clip['left'],clip['bottom'],w,h,
                        x+(w/2-pivot['x'])*scale,y+(pivot['y']-h/2)*height,w*scale,h*height)
        image.opacify(1)
        self.p.SDL_SetTextureColorMod(image.texture,255,255,255)

    def transform(self, point):
        g=self.guardian
        clip=g.clip('transform')
        switch=clip.events['elementChange']
        fade=ease((g.swap-switch+.20)/.46)
        # 공용 준비 동작 뒤에는 이번에 뽑힌 형태의 실제 시트를 드러낸다.
        charge=clip.frame(min(g.swap,clip.ends[5]-1e-6))
        self.draw_pose(g.form,charge,point,1-fade)
        arriving=g.clips[g.next_form][1]['idle'].frame(max(0,g.swap-switch))
        self.draw_pose(g.next_form,arriving,point,fade)
        burst=1-abs(g.swap-switch)/.28
        if burst > 0:
            self.app.ui.begin()
            x,y=point
            y+=self.unit*2.45
            shade=COLORS[g.next_form]
            for factor,alpha in ((.92,50),(.61,107),(.32,201)):
                radius=round(self.unit*burst*factor)
                if radius:
                    self.p.draw_circle(x,y,radius,*shade,round(burst*alpha),filled=True)

    def assemble(self):
        g=self.guardian
        if g.summon < .36:
            return
        settle=ease((g.summon-.36)/1.02)
        x,y=self.app.point(*g.spec['center'])
        scale=self.unit/GUARDIAN_DRAW_UNIT
        self.assembly.opacify(min(1,.16+1.26*settle))
        displaced=((-53,4),(50,9),(0,43),(0,-8),(4,-23))
        for i,(dx,dy) in enumerate(displaced):
            self.assembly.clip_draw(i*256,0,256,256,x+dx*(1-settle)*scale,
                                    y+(113+dy*(1-settle))*scale,256*scale,256*scale)
        self.assembly.opacify(1)
        self.app.ui.begin()
        for i in range(19):
            angle=2.399*i
            age=(g.summon*1.32+i*.071)%1
            r=(32+(i%5)*9)*age
            px=x+math.cos(angle)*r*scale
            py=y+(39+math.sin(angle)*r*.61-35*age)*scale
            self.p.draw_line(px,py,px+2,py+5,242,171,95,round(190*(1-age)))

    def exit(self):
        g=self.guardian
        x,y=self.app.point(15,g.spec['exitGate'][3])
        width,height=self.gate_meta['frameSize']
        positions=self.gate_meta['openingFrames']
        frame=0 if g.gate_progress <= 0 else 1+min(positions, int(g.gate_progress*positions))
        row,col=divmod(frame,self.gate_meta['columns'])
        scale=self.unit/30*.92
        self.gate_image.clip_draw(col*width,self.gate_image.h-(row+1)*height,width,height,
                                  x,y+(110-height/2)*scale,width*scale,height*scale)
    def core(self, x, y, size, elapsed):
        ui = self.app.ui
        ui.begin()
        orbit = size * 1.55
        for index, element in enumerate(RITUAL):
            angle = elapsed * 1.8 + index * math.tau / len(RITUAL)
            px = x + math.cos(angle) * orbit
            py = y + math.sin(angle) * orbit * .65
            self.p.draw_line(x, y, px, py, *COLORS[element], 95)
            orb = self.app.source_images[element, 'orb']
            orb.draw(px, py, size * .79, size * .79)
        ui.diamond(x, y, size, (70, 49, 77))
        ui.diamond(x, y, size * .84, (221, 187, 113))
        ui.diamond(x, y, size * .68, (69, 54, 98))
        ui.diamond(x, y + size * .09, size * .48, (152, 129, 207))
        ui.diamond(x - size * .12, y + size * .23, size * .21, (255, 240, 200))

    def reward(self, x, y):
        app = self.app
        reveal = ease((self.guardian.fall-MIXER_REVEAL_AT)/(FALL_SECONDS-MIXER_REVEAL_AT))
        if reveal == 1:
            app.view.draw_shadow(x, y)
            app.acquisition_art.draw_counterweight_prop('socket', (x, y))
        elapsed = self.room.elapsed
        burst_lift = (1-reveal)*1.15 + 1.5*math.sin(math.pi*reveal)
        px, py = app.point(x, y, app.unit * (.96 + .07 * math.sin(elapsed * 3) + burst_lift))
        if self.guardian.reward_loaded:
            self.core(px, py, app.unit * .28, elapsed)
        else:
            app.ui.begin()
            app.ui.diamond(px, py, 17+12*math.sin(math.pi*reveal), (143, 117, 181))
            app.ui.diamond(px, py, 12+8*math.sin(math.pi*reveal), (30, 22, 44))
            for i, element in enumerate(RITUAL):
                angle = math.tau * i / len(RITUAL) + math.pi / 2
                color = COLORS[element] if element in self.guardian.reward_orbs else (87, 67, 104)
                app.ui.diamond(px + 18 * math.cos(angle), py + 15 * math.sin(angle), 3, color)

    def reward_prompt(self):
        app = self.app
        g = self.guardian
        disabled = False
        if self.room.can_claim_final_reward:
            if g.reward_loaded:
                key, label = 'F', '혼합 구슬 먹기'
            else:
                key, label = 'G', f'혼합기 열기 ({len(g.reward_orbs)}/5)'
            point = self.room.final_reward
        else:
            retrieve = g.ritual == len(RITUAL)
            element = g.nearby_pedestal(self.room.player, retrieve=retrieve)
            if not element:
                return
            if g.can_place_orb(self.room, element):
                key, label = 'G', f'{NAMES[element]} 구슬 올리기'
            elif not retrieve and element not in g.placed:
                required = '원소 선택 필요' if self.room.inventory[element] else '구슬 필요'
                key, label = 'G', f'{NAMES[element]} {required}'
                disabled = True
            elif g.ritual == len(RITUAL) and not g.summoning and element in g.placed:
                key, label = 'F', f'{NAMES[element]} 구슬 먹기'
            else:
                return
            point = g.orb_flight(element)[:2] if retrieve else g.spec['devices'][RITUAL.index(element)]
        self.draw_interaction_prompt(point, key, label, disabled=disabled)

    def draw_interaction_prompt(self, point, key, label, *, disabled=False):
        app = self.app
        x, y = app.point(*point, app.unit * 1.96)
        app.ui.begin()
        app.ui.panel(x - 104, y - 18, 208, 36, accent=True)
        app.ui.key_label(key, label, x, y, 23, disabled=disabled)

    def tablet(self):
        app, ui = self.app, self.app.ui
        x, y = app.point(*self.guardian.spec['center'])
        scale = self.unit / 37
        ui.begin()
        ui.rounded(x-40*scale, y-9*scale, 80*scale, 21*scale, 6*scale, (40, 31, 50, 255))
        ui.rounded(x-36*scale, y, 72*scale, 54*scale, 8*scale, (62, 46, 68, 255))
        ui.rounded(x-32*scale, y+7*scale, 64*scale, 44*scale, 6*scale, (135, 110, 126, 255))
        ui.rounded(x-27*scale, y+11*scale, 54*scale, 35*scale, 4*scale, (92, 73, 91, 255))
        for row, widths in enumerate(((8, 13, 10), (12, 8, 12), (7, 12, 8))):
            left = x - 21*scale
            for width in widths:
                ui.rounded(left, y+(34-row*8)*scale, width*scale, 2*scale, 0, (216, 181, 133, 255))
                left += (width+4)*scale

    def prologue(self):
        app, ui = self.app, self.app.ui
        t = app.prologue_read_elapsed
        x, y = app.width / 2, app.height * .22
        ui.begin()
        if t is None:
            ui.panel(x-122, app.height-76, 244, 56, accent=True)
            ui.text('0 · 오원 제단', x, app.height-49, 20)
            if app.near_prologue_tablet:
                px, py = app.point(*self.guardian.spec['center'], self.unit * 2.28)
                ui.panel(px-74, py-18, 148, 36, accent=True)
                ui.key_label('F', '석판 읽기', px, py, 23)
            elif element := self.guardian.nearby_pedestal(self.room.player):
                point = self.guardian.spec['devices'][RITUAL.index(element)]
                self.draw_interaction_prompt(point, 'G', f'{NAMES[element]} 구슬을 놓으세요', disabled=True)
            return
        if t < 4.75:
            ui.panel(x - 264, y - 58, 528, 116, accent=True, radius=12)
            ui.text('제단의 석판', x, y + 32, 16, ui.gold)
            ui.text('다섯 자리에 원소 구슬을 올려라.', x, y, 20)
            ui.text('모든 구슬을 올린 자에게 거대한 보물을 내리리라.', x, y - 29, 15)
        smoke = ease((t - 4.25) / 1.65)
        if smoke:
            layers = (('mist-low', -.32, .25, .29, .88, .34),
                      ('mist-high', .39, .27, -.29, .93, .37),
                      ('mist-low', .16, .40, -.11, 1.06, .44),
                      ('mist-high', -.20, .52, .15, 1.12, .48),
                      ('mist-low', -.05, .31, .08, 1.18, .56))
            for index, (name, offset, base, drift, width, height) in enumerate(layers):
                amount = ease((t-4.25-index*.095)/1.55)
                image = app.acquisition_art.wind_props[name]
                image.opacify(amount * (.67 if index < 2 else .83))
                image.draw(x + app.width*(offset + drift*amount),
                           app.height*(base + .18*amount),
                           app.width*width*(.69+.31*amount),
                           app.height*height*(.55+.45*amount))
                image.opacify(1)
            darkness = round(255 * ease((t - 5.45) / 1.3))
            self.p.draw_rectangle(0, 0, app.width-1, app.height-1, 0, 0, 0, darkness, filled=True)
            if t >= 5.65:
                visibility = 1 - ease((t-6.7)/.42)
                ui.text('주인공은 연기 속에서 정신을 잃었다.', x, y, 16,
                        tuple(round(channel*visibility) for channel in ui.cream))

    def mixed_projectile(self, shot):
        app = self.app
        x, y = app.point(shot.x, shot.y, app.view.tile_height * GUARDIAN_SHOT_LIFT)
        dx, dy = app.view.project(shot.dx, shot.dy)
        app.ui.begin()
        stretch = min(.26, shot.age * shot.speed / 8)
        for i, element in enumerate(RITUAL):
            phase = shot.age * 16 + i * math.tau / len(RITUAL)
            color = COLORS[element]
            side = 12 * math.cos(phase)
            lift = 9 * math.sin(phase)
            previous = (x + side, y + lift)
            app.p.draw_circle(*previous, 4, *color, 235, filled=True)
            for trail in range(8, 0, -1):
                angle = phase - trail * .61
                px = x - dx * trail * stretch + 17 * math.cos(angle)
                py = y + dy * trail * stretch + 17 * math.sin(angle)
                app.p.draw_line(*previous, px, py, *color, 225 - trail * 20)
                app.ui.diamond(px, py, 7 - trail * .66, (*color, 240 - trail * 22))
                previous = (px, py)
        app.p.draw_circle(x, y, 4, 255, 240, 217, 225, filled=True)

    def ending(self, elapsed):
        app = self.app
        ui = app.ui
        ui.begin()
        self.p.draw_rectangle(0, 0, app.width - 1, app.height - 1,
                              13, 11, 24, round(218 * ease(elapsed / .32)), filled=True)
        if elapsed < .32:
            player = self.room.player
            rise = ease(elapsed / .32)
            x, y = app.point(player.x, player.y, app.unit * (.96 + .54 * rise))
            self.core(x, y, app.unit * (.28 + .12 * rise), elapsed)
            return
        x, y = app.width / 2, app.height / 2
        ui.panel(x - 226, y - 196, 452, 392, accent=True, radius=15)
        ui.text('엘리먼트 마스터', x, y + 152, 26)
        ui.text('엘리먼트 이터 · 게임 클리어', x, y + 115, 14, ui.gold)
        form = self.room.selected
        key = ('hero', 'idle') if form == 'neutral' else ('hero', 'idle', form)
        draw_master_aura(app, x, y-116, 91, elapsed, front=False)
        app.draw_actor_frame(key, 'down', int(elapsed * 4) % 8, x, y - 116, 1.05)
        draw_master_aura(app, x, y-116, 91, elapsed, front=True)
        rise = ease((elapsed - .32) / .65)
        self.core(x, y + 14 + 52 * rise + 3 * math.sin(elapsed * 4), 28, elapsed)
        if elapsed >= ENDING_RETURN_DELAY:
            ui.key_label('Enter', '타이틀로 돌아가기', x, y - 153, 54)

    def status(self):
        g=self.guardian
        if g.fall >= 0:
            if g.gate_progress >= 1:
                ui = self.app.ui
                x, y = self.app.width / 2, self.app.height - 111
                ui.begin()
                ui.panel(x - 215, y - 18, 430, 36, accent=True)
                label = ('Space 혼합 공격 · 북쪽 성문으로 나가기' if g.reward_tasted else
                         '떨어진 구슬을 회수하세요' if g.placed else '쓰러진 수호자 자리 · 오원 혼합기')
                ui.text(label, x, y, 15)
            return
        self.app.ui.begin()
        y=self.app.height-129
        width=430
        x=(self.app.width-width)/2
        self.app.ui.panel(x,y,width,46,accent=True)
        if g.battle:
            actor=self.room.enemies[0]
            form=g.element
            text=(f'오원 수호자 · {NAMES[g.next_form]} 변신'
                  if g.swap>=0 else
                  f'오원 수호자   {NAMES[form]} · 약점 {NAMES[WEAKNESS[form]]} · {math.ceil(g.form_left)}초')
            self.app.ui.text(text,x+14,y+28,14,align='left')
            self.app.ui.text(f'{actor.hp} / {actor.max_hp}',x+width-14,y+28,14,align='right')
            self.app.ui.rounded(x+14,y+7,width-28,6,2,(73,59,72,255))
            self.app.ui.rounded(x+14,y+7,(width-28)*actor.hp/actor.max_hp,6,2,(*COLORS[form],255))
            if g.placed:
                self.app.ui.text(f'F · 떨어진 구슬 다시 먹기 ({len(g.placed)}개 남음)',
                                 self.app.width/2, y-16, 13)
            return
        if g.ritual < len(RITUAL):
            text=f'G · 원소 구슬 올리기   ·   {g.ritual}/{len(RITUAL)}'
            colors=RITUAL
            ratios=[float(element in g.placed) for element in colors]
        else:
            text='제단 각성'
            colors=RITUAL
            ratios=[1]*len(colors)
        self.app.ui.text(text,self.app.width/2,y+28,15)
        segment=(width-28)/len(colors)
        for i,(color,fill) in enumerate(zip(colors,ratios)):
            left=x+14+i*segment
            self.app.ui.rounded(left,y+7,segment-4,6,2,(73,59,72,255))
            if fill:
                self.app.ui.rounded(left,y+7,(segment-4)*fill,6,2,(*COLORS[color],255))

    def show_exit_inset(self):
        g=self.guardian
        if not FALL_SECONDS <= g.fall < FALL_SECONDS+GATE_SECONDS+GATE_WATCH:
            return False
        x,y=self.app.point(15,g.spec['exitGate'][3])
        return not (140<=x<=self.app.width-140 and 74<=y<=self.app.height-146)

    def camera(self):
        g=self.guardian
        t=g.summon
        amount=ease(min(t/.34,(SUMMON_SECONDS-t)/.34))
        player=self.room.player
        cx,cy=g.spec['center']
        focus=(player.x+(cx-player.x)*amount,player.y+(cy-player.y)*amount)
        impulse = max(0, 1 - (t-SUMMON_SHOCK_AT)/.3) if t >= SUMMON_SHOCK_AT else 0
        focus = (focus[0]+math.sin(t*99)*.105*impulse, focus[1]+math.cos(t*87)*.085*impulse)
        self.app.draw_world_from(focus,1+.18*amount)
