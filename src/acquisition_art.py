"""첫 습득 방의 장치, 동작하는 위험 지형과 배경 효과."""
import json
import math

from .isometric import Mesh
from .room import ROOT


class AcquisitionArt:
    def __init__(self, app):
        self.app = app
        self.p = app.p
        self.images = {}
        for name, path in (('water', 'water/ripples'),
                           ('fog', 'weather/fog'), ('coil', 'lightning/tesla-coil')):
            folder = ROOT / 'assets/effects/temple-preview' / path
            atlas = json.loads((folder / (folder.name + '.json')).read_text(encoding='utf-8'))
            self.images[name] = self.p.load_image(str(folder / atlas['meta']['image'])), atlas
        waterworks = ROOT / 'assets/maps/room-02'
        self.waterworks = {name: self.p.load_image(str(waterworks / f'{name}.png'))
                           for name in ('cistern', 'steam-grate')}
        forge_folder = ROOT / 'assets/maps/room-03'
        self.forge_props = {name: self.p.load_image(str(forge_folder / f'{name}.png'))
                            for name in ('forge-arch', 'forge-steam-grate', 'ember-dais')}
        wind_folder = ROOT / 'assets/maps/room-04'
        self.wind_props = {name: self.p.load_image(str(wind_folder / f'{name}.png'))
                           for name in ('wind-vent', 'mist-high', 'mist-low')}
        for name in ('mist-high', 'mist-low'):
            self.p.SDL_SetTextureScaleMode(self.wind_props[name].texture, self.p.SDL_ScaleModeLinear)

    def effect(self, name, x, y, scale, *, z=0, offset=0):
        image, atlas = self.images[name]
        animation = atlas['meta']['pixelfx']
        index = int(self.app.room.elapsed * animation['fps']) + offset
        frame = atlas['frames'][index % len(atlas['frames'])]['frame']
        w, h = frame['w'], frame['h']
        pivot_x, pivot_y = animation['pivot']
        px, py = self.app.point(x, y, z)
        image.clip_draw(frame['x'], image.h - frame['y'] - h, w, h,
                        px + (w / 2 - pivot_x) * scale, py + (pivot_y - h / 2) * scale,
                        w * scale, h * scale)

    def stone_floor(self, bounds, color, uv=None):
        view = self.app.view
        mesh = Mesh()
        view.floor_quad(mesh, *bounds, uv, color)
        mesh.draw(self.p, view.atlas if uv else None, view.origin)

    def cable(self, path, powered=False):
        for start, end in zip(path, path[1:]):
            ax, ay = self.app.point(*start)
            bx, by = self.app.point(*end)
            for offset in range(-3, 4):
                dx, dy = (offset, 0) if ax == bx else (0, offset)
                color = (100, 68, 69) if offset else (190, 126, 82)
                if powered and not offset:
                    glow = round(24 * math.sin(self.app.room.elapsed * 9 + sum(start)))
                    color = (255, 201 + glow, 113)
                self.p.draw_line(ax + dx, ay + dy, bx + dx, by + dy, *color)

    def bridge(self, bounds, surface, extension=1):
        view = self.app.view
        left, top, right, bottom = bounds
        if surface == 'stone':
            top = bottom - (bottom - top) * extension
        mesh = Mesh()
        colors = {'stone': (181, 211, 214, 255), 'iron': (153, 169, 197, 255),
                  'earth': (243, 189, 129, 255)}
        color = colors[surface]
        if surface == 'earth' and extension < .19:
            color = (218, 155, 104, 220)
        view.face(mesh, (left, bottom), (right, bottom), 0, -13, color, (85, 62, 78, 240))
        for x in range(math.floor(left), math.ceil(right)):
            for y in range(math.floor(top), math.ceil(bottom)):
                view.floor_quad(mesh, max(left, x), max(top, y), min(right, x + 1),
                                min(bottom, y + 1), view.cap_uv, color)
        mesh.draw(self.p, view.atlas, view.origin)
        if surface == 'stone':
            self.cable([(left+.06, top), (left+.06, bottom)])
            self.cable([(right-.06, top), (right-.06, bottom)])
        else:
            self.cable([(left, top+.06), (right, top+.06)])
            self.cable([(left, bottom-.06), (right, bottom-.06)])

    def reservoir_opening(self):
        room = self.app.room
        source = room.sources[-1]
        if source.phase == 'sealed':
            return 0
        return min(1, source.age / .36) if source.phase == 'descending' else 1

    def reservoir_orb_position(self, source):
        room = self.app.room
        progress = min(1, source.age / room.reservoir['releaseSeconds'])
        fall = max(0, (progress - .1) / .9) ** 1.4
        x, y = room.reservoir['origin']
        return self.app.point(x+(source.x-x)*fall, y+(source.y-y)*fall,
                              63+(self.app.unit*.55-63)*fall)

    def water(self):
        flooded = self.reservoir_opening() > .65
        bed = (6.5, 12, 10.6, 17.65)
        self.stone_floor(bed, (65, 135, 162, 255) if flooded else (129, 120, 126, 255),
                         self.app.view.floor_uv)
        self.cable([(6.5, 17.65), (10.6, 17.65), (10.6, 12)])
        if flooded:
            for index, (x, y) in enumerate(((7.4,14.5),(8.55,15.65),(9.55,16.5))):
                self.effect('water', x, y, .96, offset=index * 7)

    def draw_cistern(self):
        room = self.app.room
        source = room.sources[-1]
        opening = self.reservoir_opening()
        origin = room.reservoir['origin']
        splash = source.x, source.y
        x,y = self.app.point(*origin)
        self.app.ui.begin()
        self.waterworks['cistern'].draw(x,y+69,154,140)
        # 상부 수면의 반사와 문 안쪽의 셔터는 같은 석재 위에서 층을 나눠 그린다.
        for index in range(7):
            shimmer = math.sin(room.elapsed * 4.2 + index*1.7)
            dx = (index-3)*12 + shimmer*5
            self.p.draw_line(x+dx,y+101+index%3*4,x+dx+8+shimmer*3,y+101+index%3*4,
                             108,184,204,round(55+28*shimmer))
        shutter_bottom = y+49+round(24*opening)
        for offset in range(-16,17,5):
            shutter_top = y+68-abs(offset)*.25
            if shutter_bottom < shutter_top:
                self.p.draw_line(x+offset,shutter_bottom,x+offset,shutter_top,148,102,82)
                self.p.draw_line(x+offset+1,shutter_bottom,x+offset+1,shutter_top,88,62,66)
        if opening < .65:
            self.p.draw_line(x-17,shutter_bottom,x+17,shutter_bottom,181,133,103,190)
        if opening <= .18:
            return
        sx,sy = self.app.point(*splash, 2)
        jet = Mesh()
        extent = min(1, (source.age - .05) / .46) if source.phase == 'descending' else 1
        for index in range(8):
            top = index / 8
            if top >= extent:
                break
            bottom = min(extent, (index+1)/8)
            def section(t):
                wave = math.sin(room.elapsed*13 - 10*t)
                center = x+(sx-x)*t + wave*(1.5 + 1.3*t)
                height = y+60+(sy-y-60)*t
                return center, self.app.height-height, (10 + t*7)*opening
            tx,ty,tw = section(top)
            bx,by,bw = section(bottom)
            color = (54,147,186,220) if index % 2 else (76,168,200,224)
            jet.quad(((tx-tw,ty),(tx+tw,ty),(bx+bw,by),(bx-bw,by)),color=color)
        jet.draw(self.p)
        for index in range(11):
            t = (room.elapsed*2.8 + index/11) % 1
            if t >= extent:
                continue
            dx = ((index*5)%21 - 10)*opening
            wave = 2*math.sin(room.elapsed*13 - t*10)
            px, py = x+dx+wave, y+60+(sy-y-60)*t
            self.p.draw_line(px, py, px+.5, py-3-index%6, 154,227,244, 100+(index%4)*32)
        if extent == 1:
            self.effect('water', *splash, .66, offset=11)
            for index in range(8):
                t = (room.elapsed*2.2 + index/8) % 1
                sign = 1 if index % 2 else -1
                px = sx + sign*(t*(12+index%4*3)+4)
                py = sy + 10*math.sin(math.pi*t)
                self.p.draw_circle(px,py,1,162,225,240,round(180*(1-t)),filled=True)

    def forge_heat(self):
        room = self.app.room
        source = room.sources[-1]
        if source.phase == 'sealed':
            return 0
        return min(1, source.age/room.forge['releaseSeconds']) if source.phase == 'igniting' else 1

    def fire(self):
        room = self.app.room
        source = room.sources[-1]
        x,y = self.app.point(source.x,source.y)
        heat = self.forge_heat()
        if heat:
            glow = Mesh()
            center = x, self.app.height-y
            strength = round(105*heat + 15*heat*math.sin(room.elapsed*7))
            for index in range(24):
                a = index*math.tau/24
                b = a + math.tau/24
                left = center[0]+145*math.cos(a),center[1]+61*math.sin(a)
                right = center[0]+145*math.cos(b),center[1]+61*math.sin(b)
                glow.quad((center,left,right,center), colors=(
                    (255,114,36,strength),(238,75,30,0),(238,75,30,0),(255,114,36,strength)))
            glow.draw(self.p)
        self.forge_props['ember-dais'].draw(x,y+3,73,39)

    def draw_forge(self):
        room = self.app.room
        heat = self.forge_heat()
        x,y = self.app.point(*room.forge['origin'])
        self.forge_props['forge-arch'].draw(x,y+53,222,108)
        flame = self.app.flame_image
        fx = self.app.flame_spec
        for index, (dx,lift,width,height,delay) in enumerate((
                (-45,16,22,12,0),(45,16,22,12,0),(0,17,50,39,.22))):
            ignition = min(1,max(0,(heat-delay)*2))
            if dx == 0 and not ignition:
                continue
            frame_index = (int(room.elapsed*fx['fps']) + index*7) % len(self.app.flame_frames)
            frame = self.app.flame_frames[frame_index]
            scale = (.31 if dx else .65) * (.7+.3*ignition)
            clip_width = min(frame['w'],round(width/scale))
            clip_height = min(fx['pivot'][1],round(height/scale))
            flame.opacify(.27 + .73*ignition)
            flame.clip_draw(frame['x']+(frame['w']-clip_width)//2,
                            flame.h-frame['y']-fx['pivot'][1],clip_width,clip_height,
                            x+dx,y+lift+clip_height*scale/2,
                            clip_width*scale,clip_height*scale)
            flame.opacify(1)
            if dx == 0:
                for bar in (-20,-13,-6,3,10,18):
                    self.p.draw_line(x+bar,y+lift,x+bar,y+lift+height,74,46,60,184)
        for index in range(8):
            t = (room.elapsed*(.39+.26*heat) + index/8) % 1
            drift = math.sin(t*6+index)*15 + (index-3.5)*8
            alpha = round((55+150*heat)*(1-t))
            self.p.draw_circle(x+drift,y+26+98*t,1 if index%2 else 2,255,141,61,alpha,filled=True)

    def wind(self):
        room = self.app.room
        x, y = self.app.point(10.8, 15.32)
        self.app.gate_image.draw(x, y+49, 103, 110)
        hub_y = y + 94
        rotation = room.elapsed * 2.4 if room.vine_open else .34 + .1*math.sin(room.elapsed*2.1)
        rotor = Mesh()
        for index in range(4):
            angle = rotation + index * math.tau / 4
            ux, uy = math.cos(angle), math.sin(angle)
            points = [(x + ux*a - uy*b, self.app.height - hub_y + uy*a + ux*b)
                      for a,b in ((10,-4), (61,-4), (55,19), (25,15))]
            rotor.quad(points, colors=((112,153,104,255), (195,213,147,255),
                                       (119,185,122,255), (82,140,106,255)))
        rotor.draw(self.p)
        self.p.draw_circle(x, hub_y, 9, 204, 172, 106, filled=True)
        phase = room.gate_time / room.gate_open_seconds
        bounds = room.acquisition['bridge']
        if phase:
            self.bridge(bounds, 'stone', phase)
        else:
            x, y = self.app.point((bounds[0]+bounds[2])/2, bounds[3])
            self.app.gate_image.draw(x, y+61, 187, 120)

    def draw_wind_fog(self):
        room = self.app.room
        columns = room.data['columns']
        time = room.elapsed
        for name, x0, y0, speed, width, height, opacity in (
                ('mist-high', 7.5, 9.2, .26, 540, 95, .32),
                ('mist-low', 22, 12.8, .32, 580, 98, .37),
                ('mist-high', 11.8, 15.2, .51, 500, 101, .45),
                ('mist-low', 22.7, 18.7, .48, 660, 106, .40),
                ('mist-high', 3.8, 22.2, .37, 420, 100, .38),
                ('mist-low', 26.8, 25.9, .41, 540, 108, .34)):
            # 안개의 꼬리까지 맵 바깥을 지나고 다음 주기가 시작된다.
            margin = (width/2 + 45) / self.app.view.tile_width
            span = columns + 2*margin
            distance = (x0 + margin + time*speed) % span
            visibility = min(1, distance/margin, (span-distance)/margin)
            x,y = self.app.point(distance-margin, y0+math.sin(time*.38+x0)*.23)
            image = self.wind_props[name]
            image.opacify(opacity*visibility*(.92+.08*math.sin(time*.52+y0)))
            image.draw(x,y,width,height)
            image.opacify(1)

    def earth(self):
        room = self.app.room
        for index, (x, y) in enumerate(room.turret_room['emitters']):
            px, py = self.app.point(x, y)
            level = 2 if not room.turrets_stopped else 0
            self.app.conductor_images[level].draw(px, py+13, 67, 63)
            if level and (room.elapsed * 3 + index*.55) % 1 < .48:
                self.app.draw_electric_arc(px, py+22, px-23, py+15, 4, 204, index)
        if room.permanent_bridge:
            self.bridge(room.permanent_bridge, 'iron')
        self.effect('fog', 17.6+1.3*math.sin(room.elapsed*.7), 22.4, .6)

    def lightning(self):
        room = self.app.room
        powered = room.acquisition_power
        for path in ([(18.5,12.15),(18.5,8.5),(18,8.5),(18,5.4)],
                     [(18.5,12.15),(18.5,13.8),(14,13.8),(14,17)],
                     [(18.5,13.8),(22.4,13.8),(22.4,17.7)],
                     [(27.35,21.55),(27.35,23.5),(25.3,23.5)]):
            self.cable(path, powered)
        px, py = self.app.point(18.5, 12.15)
        self.app.conductor_images[3 if room.acquisition_relay else 0].draw(px, py+12, 71, 72)
        if room.sources[-1].phase == 'sealed' or powered:
            self.effect('coil', 18.5, 11.3, 1.82, z=20)
        if not room.learned_room_element:
            for left, top, right, bottom in room.acquisition['passages']:
                a = self.app.point(left, (top+bottom)/2)
                b = self.app.point(right, (top+bottom)/2)
                if right-left < bottom-top:
                    a = self.app.point((left+right)/2, top)
                    b = self.app.point((left+right)/2, bottom)
                self.app.draw_electric_arc(*a, *b, 4, 190, int(room.elapsed*12))

    def draw_hazard(self, hazard):
        room = self.app.room
        state, progress = room.hazard_state(hazard)
        kind = hazard['kind']
        left, top, right, bottom = hazard['bounds']
        x0, y1 = self.app.point(left, top)
        x1, y0 = self.app.point(right, bottom)
        cx, cy = (x0+x1)/2, (y0+y1)/2
        if x1 < 0 or x0 > self.app.width or y1 < 0 or y0 > self.app.height:
            return
        if kind == 'steam' and (room.reservoir or room.forge):
            self.draw_steam_grate(x0,y0,x1,y1,state,progress,forge=bool(room.forge))
            return
        if kind == 'gust' and room.stage == 4:
            self.draw_wind_vent(x0,y0,x1,y1,state,progress)
            return
        palette = {'spikes':(189,183,206), 'steam':(168,220,225), 'gust':(153,222,185),
                   'rock':(231,166,111), 'shock':(187,159,255)}
        color = palette[kind]
        alpha = (round(80 + 120*progress) if state == 'warning' else
                 190 if state == 'active' else 64)
        self.p.draw_rectangle(x0,y0,x1,y1,*color,alpha,filled=False)
        self.p.draw_rectangle(x0+2,y0+2,x1-2,y1-2,*color,alpha//5,filled=True)
        if state == 'warning':
            self.p.draw_line(x0, y0, x0+(x1-x0)*progress, y0, 255, 198, 112, 220)
        if state not in ('active', 'retract') and not (kind == 'rock' and state == 'warning'):
            return
        extension = min(1, .3+progress*5) if state == 'active' else 1-progress
        for index in range(5):
            x = x0+(x1-x0)*(index+.5)/5
            if kind == 'spikes':
                for base in range(-6,7):
                    self.p.draw_line(x+base, cy, x+1, cy+24*extension, *color)
            elif kind == 'shock':
                side = -1 if index % 2 else 1
                self.app.draw_electric_arc(x, cy-4, x+side*11, cy + 29*extension, 9, 220, index)
            elif kind == 'rock':
                z = 59*(1-progress) if state == 'warning' else 0
                self.p.draw_circle(x, cy+z, max(1, round((6+index%3)*extension)), *color, filled=True)
            elif kind == 'gust':
                sweep = (progress + index/5) % 1
                start = x0+(x1-x0)*sweep
                height = y0 + (index+1)*(y1-y0)/6
                self.p.draw_line(start-20*extension, height-3, start, height, *color,
                                 round(200*extension))
            else:
                lift = (13+index%3*6)*extension
                shift = 8*math.sin(room.elapsed*9+index)
                self.p.draw_circle(x+shift, cy+lift, 5+index%3, *color, round(144*extension), filled=True)

    def draw_wind_vent(self, x0, y0, x1, y1, state, progress):
        width, height = x1-x0, y1-y0
        count = max(1, round(width/self.app.view.tile_width))
        step = width/count
        vent = self.wind_props['wind-vent']
        center_y = (y0+y1)/2
        for index in range(count):
            center_x = x0 + (index+.5)*step
            vent.draw(center_x,center_y,step,height)
            if state == 'warning':
                strength = round(75+120*progress+27*math.sin(progress*20))
                self.p.draw_line(center_x-step*.24,center_y-3,center_x+step*.24,center_y-3,
                                 223,190,111,strength)
            elif state == 'active':
                self.p.draw_line(center_x-step*.29,center_y-3,center_x+step*.29,center_y-3,
                                 181,231,205,191)
        if state == 'idle':
            return
        if state == 'warning':
            strength = .12 + .19*progress
        elif state == 'active':
            strength = min(1,.48+progress*6)
        else:
            strength = .60*(1-progress)

        time = self.app.room.elapsed
        for index in range(7):
            travel = (time*(1.1 if state=='warning' else 2.0)+index/7) % 1
            head = x0+4+(width-8)*travel
            tail = max(x0+3,head-(12+width*.24)*strength)
            y = y0+(index % 4+1)*height/5+strength*(7+15*travel)
            alpha = round(224*strength*math.sin(math.pi*travel))
            for part in range(4):
                start, end = part/4, (part+1)/4
                px = tail+(head-tail)*start
                tx = tail+(head-tail)*end
                py = y+strength*4*math.sin(start*math.pi+index)
                ty = y+strength*4*math.sin(end*math.pi+index)
                self.p.draw_line(px,py-1,tx,ty-1,111,182,184,alpha//2)
                self.p.draw_line(px,py,tx,ty,218,245,228,alpha)

    def draw_steam_grate(self, x0, y0, x1, y1, state, progress, *, forge=False):
        width, height = x1-x0, y1-y0
        x, y = (x0+x1)/2, (y0+y1)/2
        grate = self.forge_props['forge-steam-grate'] if forge else self.waterworks['steam-grate']
        if forge and width > 58:
            for side in (-1,1):
                grate.draw(x+side*width/4,y,width/2,height)
        else:
            grate.draw(x,y,width,height)
        time = self.app.room.elapsed
        if state == 'idle':
            return
        blink = (math.sin(progress*(12+progress*8)) + 1) * .5
        lamp_alpha = round(90+140*blink) if state == 'warning' else 234
        lamp = (255,183,94) if state == 'warning' else (255,139,92)
        for side in (-1,1):
            self.p.draw_circle(x+side*width*.34,y-side*height*.34,2,*lamp,lamp_alpha,filled=True)
        if state == 'warning':
            extension = .21 * progress
        elif state == 'active':
            extension = min(1, .45+progress*5)
        else:
            extension = (1-progress)*.58
        for index in range(10):
            life = (time*2.3 + index/10) % 1
            dx = (index%4-1.5)*width*.16 + math.sin(time*9+index)*life*6
            lift = (4+life*39)*extension
            radius = max(1, round((3+life*9)*extension))
            alpha = round((164-100*life)*extension)
            shade = (165,132,124) if forge else (127,174,194)
            light = (247,220,199) if forge else (218,238,238)
            self.p.draw_circle(x+dx,y+lift,radius,*shade,alpha,filled=True)
            self.p.draw_circle(x+dx-1,y+lift+1,max(1,radius-2),*light,alpha,filled=True)
            if forge and state == 'active' and index % 3 == 0:
                self.p.draw_circle(x+dx,y+lift+3,1,255,157,81,alpha,filled=True)

    def draw(self):
        room = self.app.room
        if 'movingHazards' not in room.data:
            return
        self.app.ui.begin()
        if room.stage == 1:
            self.effect('fog', 4.6+math.sin(room.elapsed*.7)*.7, 14.5, .62)
            self.effect('fog', 15.3+math.sin(room.elapsed*.5)*.7, 14.9, .65, offset=8)
        else:
            (self.water, self.fire, self.wind, self.earth, self.lightning)[room.stage-2]()
        if room.puzzle:
            self.cable([room.puzzle['start'], room.puzzle['plate']], room.plate_pressed)
            x,y = self.app.point(*room.puzzle['plate'])
            self.app.ui.rounded(x-20, y-10, 40, 20, 4, (110, 185, 134, 255))
        if room.acquisition:
            trial = room.acquisition
            for point in (trial.get('switch') if not room.forge else None, trial.get('finalSwitch'),
                          room.turret_room and room.turret_room['switch']):
                if point:
                    x,y = self.app.point(*point)
                    self.app.connect_image.draw(x, y+5, 46, 46)
        for hazard in room.data['movingHazards']:
            self.draw_hazard(hazard)

    def draw_prompt(self):
        room = self.app.room
        trial = room.acquisition
        if not trial or room.ingest_elapsed >= 0:
            return
        if room.forge and room.conductor_vine_time < 0:
            vine = room.conductor_vine
            gate_x, gate_y = vine['x']+vine['width']/2, vine['y']+vine['height']
            player = room.player
            if player.y > gate_y and math.hypot(player.x-gate_x, player.y-gate_y) < 3.15:
                x,y = self.app.point(gate_x,gate_y)
                self.app.ui.panel(x-90,y-58,180,32)
                self.app.ui.text('수풀이 길을 막고 있다', x, y-42, 14)
        point = trial.get('switch')
        first_orb = room.sources[-1]
        if first_orb.phase != 'sealed':
            point = trial.get('finalSwitch')
        player = room.player
        if not point:
            if room.puzzle and not room.plate_pressed and math.hypot(player.x-room.block[0],
                                                                     player.y-room.block[1]) <= 3.3:
                if room.inventory['wind']:
                    x,y = self.app.point(*room.block)
                    self.app.ui.key_label('R', '바람으로 평형추 밀기', x, y+65, 25, 13)
            if room.turret_room and not room.turrets_stopped:
                sx, sy = room.turret_room['switch']
                if math.hypot(player.x-sx, player.y-sy) <= 2.4:
                    self.app.ui.text('정지 장치로 이동', *self.app.point(sx,sy,42), 13)
            return
        if room.acquisition_power or math.hypot(player.x-point[0], player.y-point[1]) > 2:
            return
        x,y = self.app.point(*point)
        if first_orb.phase == 'sealed':
            guards = any(enemy.active for enemy in room.enemies[:trial['guards']])
            if guards:
                self.app.ui.text('수호 적을 먼저 쓰러뜨리세요', x, y+38, 13)
                return
            if not room.extinguished.issuperset(trial.get('preFire', ())):
                self.app.ui.text('정비 통로의 불길을 먼저 꺼 주세요', x, y+38, 13)
                return
            label = {2:'수문 열기', 3:'화로 덮개 열기', 6:'차단기 내리기'}[room.stage]
        elif not room.acquisition_relay:
            self.app.ui.text('번개 기본 공격 · 전도체 충전', x, y+37, 13)
            return
        else:
            label = '승강기 전력 연결'
        self.app.ui.key_label('G', label, x, y+38, 25, 13)
