"""첫 습득 방의 장치, 동작하는 위험 지형과 배경 효과."""
import json
import math

from .isometric import Mesh
from .room import RESERVOIR_BED, ROOT


WINDMILL_HUB_HEIGHT = 94
WIND_ORB_FLIGHT_START = .34
WIND_ORB_FLIGHT_END = .87
COUNTERWEIGHT_SPRITES = {
    'socket': ((165, 162, 429, 298), (52, 34), 0),
    'lever': ((895, 160, 380, 369), (34, 34), 8),
    'stone': ((1592, 160, 408, 431), (49, 36), 4),
}
ROCKFALL_BED = (153, 137, 452, 443)
ROCKFALL_BOULDER = (837, 100, 500, 514)
ROCKFALL_DEBRIS = (1538, 244, 543, 183)
SHOCK_PLATE = (167, 79, 391, 357)
CAPACITOR_CRADLE = (920, 79, 336, 454)
WALL_PIER = (1623, 79, 372, 608)
LIGHTNING_ORB_HEIGHT = 64
CHARGE_GLOW = (241, 162, 79)
CHARGE_CORE = (255, 242, 175)
CLIFF_FOG_LAYERS = {
    1: (
        ('mist-low', 3.5, 15.0, .21, 430, 91, .27),
        ('mist-high', 16.5, 14.6, .24, 460, 104, .23),
        ('mist-low', 13.2, 20.7, .17, 565, 124, .21),
    ),
    4: (
        ('mist-high', 7.5, 9.2, .26, 540, 95, .32),
        ('mist-low', 22, 12.8, .32, 580, 98, .37),
        ('mist-high', 11.8, 15.2, .51, 500, 101, .45),
        ('mist-low', 22.7, 18.7, .48, 660, 106, .40),
        ('mist-high', 3.8, 22.2, .37, 420, 100, .38),
        ('mist-low', 26.8, 25.9, .41, 540, 108, .34),
    ),
    5: (
        ('mist-low', 17.5, 12.7, .31, 510, 126, .47),
        ('mist-high', 16.3, 16.7, .48, 378, 88, .50),
        ('mist-low', 19.2, 21.0, .36, 580, 105, .43),
        ('mist-high', 16.8, 25.7, .42, 420, 98, .39),
        ('mist-low', 5.5, 29.3, .26, 510, 115, .29),
    ),
}


class AcquisitionArt:
    def __init__(self, app):
        self.app = app
        self.p = app.p
        self.images = {}
        for name, path in (('water', 'water/ripples'), ('coil', 'lightning/tesla-coil')):
            folder = ROOT / 'assets/effects/temple-preview' / path
            atlas = json.loads((folder / (folder.name + '.json')).read_text(encoding='utf-8'))
            self.images[name] = self.p.load_image(str(folder / atlas['meta']['image'])), atlas
        spike_folder = ROOT / 'assets/maps/room-01'
        self.spike_props = {name: self.p.load_image(str(spike_folder / f'{name}.png'))
                            for name in ('spike-trap-base', 'spike-blade')}
        waterworks = ROOT / 'assets/maps/room-02'
        self.waterworks = {name: self.p.load_image(str(waterworks / f'{name}.png'))
                           for name in ('cistern', 'steam-grate')}
        forge_folder = ROOT / 'assets/maps/room-03'
        self.forge_props = {name: self.p.load_image(str(forge_folder / f'{name}.png'))
                            for name in ('forge-arch', 'forge-steam-grate', 'ember-dais')}
        wind_folder = ROOT / 'assets/maps/room-04'
        self.wind_props = {name: self.p.load_image(str(wind_folder / f'{name}.png'))
                           for name in ('wind-vent', 'mist-high', 'mist-low', 'counterweight-props')}
        for name in ('mist-high', 'mist-low', 'counterweight-props'):
            self.p.SDL_SetTextureScaleMode(self.wind_props[name].texture, self.p.SDL_ScaleModeLinear)
        quarry_folder = ROOT / 'assets/maps/room-05'
        self.quarry_props = self.p.load_image(str(quarry_folder / 'rockfall-props.png'))
        self.p.SDL_SetTextureScaleMode(self.quarry_props.texture, self.p.SDL_ScaleModeLinear)
        self.turret_spec = json.loads((quarry_folder / 'lightning-turret-v1.json').read_text(encoding='utf-8'))
        self.turret_image = self.p.load_image(str(quarry_folder / self.turret_spec['image']))
        self.p.SDL_SetTextureScaleMode(self.turret_image.texture, self.p.SDL_ScaleModeLinear)
        path = ROOT / 'assets/maps/room-06/powerstation-props.png'
        self.powerstation_props = self.p.load_image(str(path))
        self.p.SDL_SetTextureScaleMode(self.powerstation_props.texture, self.p.SDL_ScaleModeLinear)

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

    def power_wave(self, path, progress):
        self.cable(path, progress >= 1)
        if not 0 <= progress < 1:
            return
        points = [self.app.point(*point) for point in path]
        legs = [(start, end, math.dist(start, end)) for start, end in zip(points, points[1:])]
        reach = progress * sum(length for _, _, length in legs)
        for (x, y), (tx, ty), length in legs:
            if not length:
                continue
            fraction = min(1, reach / length)
            dx, dy = tx - x, ty - y
            head_x, head_y = x + dx * fraction, y + dy * fraction
            self.p.draw_line(x, y, head_x, head_y, *CHARGE_GLOW)
            if reach < length:
                tail = max(0, fraction - 32 / length)
                self.app.draw_electric_arc(x + dx * tail, y + dy * tail, head_x, head_y, 6,
                                           244, int(self.app.room.elapsed * 22),
                                           glow=CHARGE_GLOW, core=CHARGE_CORE)
                self.p.draw_circle(head_x, head_y, 9, *CHARGE_GLOW, 68, filled=True)
                self.p.draw_circle(head_x, head_y, 4, *CHARGE_CORE, 228, filled=True)
                break
            reach -= length

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

    def reservoir_orb_position(self, source):
        room = self.app.room
        progress = min(1, source.age / room.reservoir['releaseSeconds'])
        fall = max(0, (progress - .1) / .9) ** 1.4
        x, y = room.reservoir['origin']
        return self.app.point(x+(source.x-x)*fall, y+(source.y-y)*fall,
                              63+(self.app.unit*.55-63)*fall)

    def water(self):
        flooded = self.app.room.reservoir_flooded
        bed = RESERVOIR_BED
        self.stone_floor(bed, (65, 135, 162, 255) if flooded else (129, 120, 126, 255),
                         self.app.view.floor_uv)
        self.cable([(6.5, 17.65), (10.6, 17.65), (10.6, 12)])
        if flooded:
            for index, (x, y) in enumerate(((7.4,14.5),(8.55,15.65),(9.55,16.5))):
                self.effect('water', x, y, .96, offset=index * 7)

    def draw_cistern(self):
        room = self.app.room
        source = room.sources[-1]
        opening = room.reservoir_opening
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

    def draw_windmill(self):
        room = self.app.room
        source = room.sources[-1]
        x, y = self.app.point(*room.windmill['origin'])
        self.app.gate_image.draw(x, y+49, 103, 110)
        hub_y = y + WINDMILL_HUB_HEIGHT
        rotation = .34
        duration = room.windmill['releaseSeconds']
        if source.phase != 'sealed':
            progress = min(1, source.age/duration)
            rotation += 2.4*(source.age + .45*math.expm1(-source.age/.45))
            rotation += math.tau*progress*progress*(3-2*progress)
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

    def wind(self):
        room = self.app.room
        source = room.sources[-1]
        duration = room.windmill['releaseSeconds']
        sx, sy = self.app.point(*room.acquisition['switch'])
        self.app.connect_image.draw(sx, sy+5, 46, 46)
        light = ((155, 244, 172) if source.phase != 'sealed' else
                 (248, 213, 125) if not room.remaining_enemies else (123, 108, 112))
        self.p.draw_circle(sx, sy+10, 5, 44, 40, 57, filled=True)
        self.p.draw_circle(sx, sy+10, 3, *light, filled=True)
        landing_age = source.age-duration*WIND_ORB_FLIGHT_END
        if source.phase in ('gathering', 'orb') and 0 <= landing_age < .68:
            bx,by = self.app.point(source.x,source.y)
            self.draw_wind_landing(bx,by,landing_age/.68)
        phase = room.gate_time / room.gate_open_seconds
        bounds = room.acquisition['bridge']
        if phase:
            self.bridge(bounds, 'stone', phase)
        else:
            x, y = self.app.point((bounds[0]+bounds[2])/2, bounds[3])
            self.app.gate_image.draw(x, y+61, 187, 120)

    def draw_counterweight_prop(self, prop, point):
        frame, size, elevation = COUNTERWEIGHT_SPRITES[prop]
        x, y = self.app.point(*point, elevation)
        self.wind_props['counterweight-props'].clip_draw(*frame, x, y, *size)

    @staticmethod
    def wind_orb_point(hub, landing, flight):
        eased = flight*flight*(3-2*flight)
        angle = flight*math.tau - math.pi/4
        sweep = math.sin(math.pi*flight)
        x = hub[0]+(landing[0]-hub[0])*eased + 63*sweep*math.cos(angle)
        y = hub[1]+(landing[1]-hub[1])*eased + 25*sweep*math.sin(angle)
        return x,y

    def draw_wind_landing(self, x, y, progress):
        radius = 10+52*progress
        alpha = round(155*(1-progress)**2)
        for segment in range(18):
            a = segment*math.tau/18
            b = a+math.tau/24
            self.p.draw_line(x+radius*math.cos(a),y+radius*.31*math.sin(a),
                             x+radius*math.cos(b),y+radius*.31*math.sin(b),
                             173,238,176,alpha)

    def draw_wind_orb(self, source):
        room = self.app.room
        progress = min(1,source.age/room.windmill['releaseSeconds'])
        hub = self.app.point(*room.windmill['origin'], WINDMILL_HUB_HEIGHT)
        landing = self.app.point(source.x,source.y,self.app.unit*.55)
        flight = max(0,min(1,(progress-WIND_ORB_FLIGHT_START)/(WIND_ORB_FLIGHT_END-WIND_ORB_FLIGHT_START)))
        x,y = self.wind_orb_point(hub,landing,flight)
        self.app.ui.begin()

        if progress < WIND_ORB_FLIGHT_START:
            convergence = progress/WIND_ORB_FLIGHT_START
            for strand in range(5):
                angle = source.age*3.8+strand*math.tau/5
                radius = 27+75*(1-convergence)
                previous = None
                for segment in range(12):
                    t = segment/11
                    radius_at = radius*(1-.72*t)
                    bearing = angle+1.55*t
                    point = (hub[0]+radius_at*math.cos(bearing),
                             hub[1]+radius_at*.53*math.sin(bearing))
                    if previous:
                        alpha = round((75+116*convergence)*math.sin(t*math.pi/2))
                        self.p.draw_line(*previous,*point,163,229,169,alpha)
                    previous = point
                self.p.draw_circle(*point,2,216,251,183,round(120+115*convergence),filled=True)
        elif flight < 1:
            tail = max(0,flight-.22)
            previous = self.wind_orb_point(hub,landing,tail)
            for sample in range(1,13):
                point = self.wind_orb_point(hub,landing,tail+(flight-tail)*sample/12)
                self.p.draw_line(*previous,*point,190,243,178,round(195*sample/12))
                self.p.draw_line(previous[0],previous[1]-3,point[0],point[1]-3,
                                 132,211,164,round(105*sample/12))
                if sample % 3 == 0:
                    self.p.draw_circle(*point,2,214,252,190,round(177*sample/12),filled=True)
                previous = point

        formed = max(0,min(1,(progress-.16)/.21))
        if not formed:
            return
        light = Mesh()
        center = x,self.app.height-y
        radius = 21 + 34*formed
        for segment in range(18):
            a = segment*math.tau/18
            b = a+math.tau/18
            glow = (168,236,156,round(94*formed))
            edge = (168,236,156,0)
            light.quad((center,(x+radius*math.cos(a),center[1]+radius*math.sin(a)),
                        (x+radius*math.cos(b),center[1]+radius*math.sin(b)),center),
                       colors=(glow,edge,edge,glow))
        light.draw(self.p)
        size = self.app.unit*(.22+.78*formed)
        self.app.source_images[source.element,'orb'].draw(x,y,size,size)

    def draw_cliff_fog(self):
        room = self.app.room
        columns = room.data['columns']
        time = room.elapsed
        quarry = room.stage == 5
        for name, x0, y0, speed, width, height, opacity in CLIFF_FOG_LAYERS[room.stage]:
            # 안개의 꼬리까지 맵 바깥을 지나고 다음 주기가 시작된다.
            margin = (width/2 + 45) / self.app.view.tile_width
            span = columns + 2*margin
            distance = (x0 + margin + time*speed) % span
            visibility = min(1, distance/margin, (span-distance)/margin)
            x,y = self.app.point(distance-margin, y0+math.sin(time*.38+x0)*.23)
            image = self.wind_props[name]
            if quarry:
                self.p.SDL_SetTextureColorMod(image.texture, 238, 199, 166)
            image.opacify(opacity*visibility*(.92+.08*math.sin(time*.52+y0)))
            image.draw(x,y,width,height)
            image.opacify(1)
            if quarry:
                self.p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def earth(self):
        room = self.app.room
        sx, sy = room.turret_room['switch']
        for x in (sx - 1.05, sx + 1.02):
            self.cable([(sx, sy), (sx, sy - .72), (x, sy - .72)], room.turrets_stopped)
            px, py = self.app.point(x, sy - .72)
            self.app.conductor_images[0 if room.turrets_stopped else 1].draw(px, py+12, 38, 37)
        if room.permanent_bridge:
            self.bridge(room.permanent_bridge, 'iron')

    def draw_turret(self, index):
        app, room, p = self.app, self.app.room, self.p
        x, y = room.turret_room['emitters'][index]
        px, py = app.point(x, y, 21)
        left, bottom, width, height = self.turret_spec['clip']
        muzzle_x, muzzle_y = self.turret_spec['muzzlePixelsTopLeft']
        scale = 1.58 * app.view.tile_width / width
        image = self.turret_image
        if room.turrets_stopped:
            p.SDL_SetTextureColorMod(image.texture, 159, 153, 158)
        image.clip_draw(left, bottom, width, height,
                        px + (width/2-muzzle_x)*scale, py + (muzzle_y-height/2)*scale,
                        width*scale, height*scale)
        if room.turrets_stopped:
            p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)
            return
        if (room.player.y < room.turret_room['activateY']
                and index != room.next_turret and room.turret_timer > .69):
            flash = min(1, (room.turret_timer - .69) / .16)
            app.ui.begin()
            app.ui.diamond(px, py, 6*flash, (255, 224, 151, round(235*flash)))
            app.draw_electric_arc(px, py, px-24*flash, py, 4, round(231*flash), int(room.elapsed*45))

    def lightning(self):
        room = self.app.room
        powered = room.acquisition_power
        relay = room.acquisition['relay']
        coil = room.acquisition['coil']
        elapsed = room.acquisition_power_elapsed
        circuit = room.power_circuit
        coil_at, door_at = circuit['coilAt'], circuit['doorAt']
        self.cable([(27.35,21.55),(27.35,23.5),(25.3,23.5)], powered)
        self.cable([room.acquisition['finalSwitch'], relay], elapsed >= 0)
        self.power_wave([relay, (coil[0], relay[1]), coil], elapsed / coil_at)
        exit_x = room.data['plannedExit']['x']
        door_y = room.data['floorRegions'][0]['y']
        self.power_wave([coil, (coil[0], door_y + 2.45), (exit_x, door_y + 2.45), (exit_x, door_y + .24)],
                        (elapsed - coil_at) / (door_at - coil_at))
        self.draw_relay(relay)
        if elapsed >= coil_at:
            self.effect('coil', *coil, 1.28, z=8)
        else:
            self.draw_idle_coil(coil)

    def draw_relay(self, point):
        room = self.app.room
        x, y = self.app.point(*point)
        self.app.conductor_images[0].draw(x, y + 12, 71, 72)
        pulse = .5 + .5 * math.sin(room.elapsed * 8)
        if not room.acquisition_relay:
            self.p.draw_circle(x, y + 20, 3, 255, 182, 87, round(45 + 62 * pulse), filled=True)
            return

        transmitting = room.acquisition_power_elapsed >= 0
        glow, core = ((CHARGE_GLOW, CHARGE_CORE) if transmitting else
                      ((101, 164, 255), (221, 241, 255)))
        hit = room.acquisition_relay_flash / room.relay_flash_seconds
        tick = int(room.elapsed * 16)
        if hit:
            self.p.draw_circle(x, y + 32, round(21 + 8 * (1 - hit)), *glow, round(105 * hit), filled=True)
            self.p.draw_circle(x, y + 32, round(10 + 24 * (1 - hit)), *core, round(214 * hit))
        self.app.draw_electric_arc(x - 18, y + 34, x + 13, y + 33, 3 + 7 * pulse + 8 * hit,
                                   round(155 + 35 * pulse + 54 * hit), tick, glow=glow, core=core)
        for index, offset in enumerate((-18, 13)):
            brightness = .5 + .5 * math.sin(room.elapsed * 10 + index * math.pi)
            self.p.draw_circle(x + offset, y + 34, 5, *glow, round(92 + brightness * 92), filled=True)
            if (tick + index) % 4 < 2:
                direction = -1 if index == 0 else 1
                self.app.draw_electric_arc(x + offset, y + 34, x + offset + direction * (6 + 9 * brightness),
                                           y + 43 + 8 * brightness, 4, 183, tick + index, glow=glow, core=core)
        for index, offset in enumerate((-12, 0, 12)):
            brightness = .5 + .5 * math.sin(room.elapsed * 9 - index * 1.6)
            self.p.draw_circle(x + offset, y - 11, 3, *core, round(98 + 129 * brightness), filled=True)

    def draw_idle_coil(self, point):
        image, atlas = self.images['coil']
        frame = atlas['frames'][0]['frame']
        pivot_x, pivot_y = atlas['meta']['pixelfx']['pivot']
        left, top, width, height = 92, 51, 40, 73
        scale = 1.28
        x, y = self.app.point(*point, 8)
        self.p.SDL_SetTextureColorMod(image.texture, 151, 143, 153)
        image.clip_draw(frame['x'] + left, image.h - frame['y'] - top - height, width, height,
                        x + (left + width / 2 - pivot_x) * scale,
                        y + (pivot_y - top - height / 2) * scale, width * scale, height * scale)
        self.p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def bulkhead_sections(self):
        for left, top, right, bottom in self.app.room.acquisition['passages']:
            width, depth = right - left, bottom - top
            horizontal = width >= depth
            count = math.ceil(max(width, depth))
            for index in range(count):
                start, end = index / count, (index + 1) / count
                if horizontal:
                    bounds = (left + width * start, top, left + width * end, bottom)
                else:
                    bounds = (left, top + depth * start, right, top + depth * end)
                last = index == count - 1
                yield bounds, horizontal or last, last or index % (4 if horizontal else 3) == 0

    def draw_bulkhead(self, bounds, front, pillar):
        room = self.app.room
        level = 1
        if room.ingest_consumed:
            start, end = room.tuning.ingest_event, room.tuning.ingest_duration
            level = max(0, (end - room.ingest_elapsed) / (end - start))
        view = self.app.view
        mesh = Mesh()
        view.wall_shadow(mesh, bounds[0], bounds[2], bounds[3])
        mesh.draw(self.p, offset=view.origin)
        mesh = Mesh()
        view.masonry_block(mesh, *bounds, 5 + 18 * level, front=front)
        view.draw_wall(mesh)
        if pillar:
            left, _, right, bottom = bounds
            x, y = self.app.point((left + right) / 2, bottom)
            sx, sy, sw, sh = WALL_PIER
            exposure = .10 + .90 * level
            height = 31 * exposure
            clip_height = round(sh * exposure)
            self.powerstation_props.clip_draw(sx, sy + sh - clip_height, sw, clip_height,
                                              x, y + height / 2, min(40, (right-left)*view.tile_width), height)

    def draw_capacitor(self):
        source = self.app.room.sources[-1]
        x, y = self.app.point(source.x, source.y)
        self.powerstation_props.clip_draw(*CAPACITOR_CRADLE, x, y + 11, 51, 51)

    def draw_lightning_orb(self, source):
        room = self.app.room
        progress = min(1, source.age / room.capacitor['releaseSeconds'])
        x, ground_y = self.app.point(source.x, source.y)
        rise = max(0, min(1, (progress - .44) / .49))
        y = ground_y + 27 + (LIGHTNING_ORB_HEIGHT - 27) * rise * rise * (3 - 2 * rise)
        tick = int(source.age * 16)
        if progress < .74:
            contacts = [room.acquisition['switch']]
            contacts.extend(((left + right) / 2, (top + bottom) / 2)
                            for left, top, right, bottom in (h['bounds'] for h in room.data['movingHazards']))
            strength = min(1, progress * 12, (.74 - progress) * 8)
            for index, contact in enumerate(contacts):
                px, py = self.app.point(*contact, 10)
                advance = max(0, min(.94, (progress - index*.05) / .71))
                mx = px + (x - px) * advance + 5 * math.sin(source.age * 14 + index) * (1 - advance)
                my = py + (y - py) * advance
                self.app.draw_electric_arc(mx, my, x, y, 8, round(225 * strength), tick + index,
                                           glow=CHARGE_GLOW, core=CHARGE_CORE)
                self.p.draw_circle(mx, my, 3, *CHARGE_CORE, round(215 * strength), filled=True)

        formed = max(0, min(1, (progress - .25) / .48))
        if formed:
            pulse = (.78 + .22 * math.sin(source.age * 11) ** 2) * formed * (1 - progress)
            for radius, alpha in ((43, 28), (30, 49), (18, 62)):
                self.p.draw_circle(x, y, round(radius * (.6 + .4 * formed)),
                                   255, 195, 98, round(alpha * pulse), filled=True)
            for index in range(9):
                angle = index * math.tau / 9 + source.age * 6
                distance = 36 - 13 * formed + index % 3 * 3
                self.p.draw_circle(x + math.cos(angle) * distance, y + .56 * math.sin(angle) * distance,
                                   1 + index % 2, *CHARGE_CORE, round(200 * pulse), filled=True)
            size = self.app.unit * (.24 + .76 * formed)
            self.app.source_images['lightning', 'orb'].draw(x, y, size, size)

        if progress >= .69:
            spread = (progress - .69) / .31
            radius = 14 + 50 * spread
            alpha = round(187 * (1 - spread) ** 2)
            for index in range(16):
                a = index * math.tau / 16
                b = a + math.tau / 22
                self.p.draw_line(x + radius * math.cos(a), ground_y + radius * .35 * math.sin(a),
                                 x + radius * math.cos(b), ground_y + radius * .35 * math.sin(b),
                                 *CHARGE_GLOW, alpha)

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
        if kind == 'spikes' and room.stage == 1:
            self.draw_spike_trap(x0,y0,x1,y1,state,progress)
            return
        if kind == 'steam' and (room.reservoir or room.forge):
            self.draw_steam_grate(x0,y0,x1,y1,state,progress,forge=bool(room.forge))
            return
        if kind == 'gust' and room.stage == 4:
            self.draw_wind_vent(x0,y0,x1,y1,state,progress)
            return
        if kind == 'rock' and room.stage == 5:
            self.draw_rockfall(x0, y0, x1, y1, state, progress)
            return
        if kind == 'shock' and room.capacitor:
            self.draw_shock_plate(x0, y0, x1, y1, state, progress)
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

    def draw_shock_plate(self, x0, y0, x1, y1, state, progress):
        width, height = x1 - x0, y1 - y0
        x = (x0 + x1) / 2
        self.powerstation_props.clip_draw(*SHOCK_PLATE, x, (y0 + y1) / 2, width, height)
        if state == 'idle':
            return
        tick = int(self.app.room.elapsed * 22)
        for index, position in enumerate((.27, .53, .78)):
            y = y0 + height * position
            spread = width * .25
            if state == 'warning':
                pulse = .47 + .4 * math.sin(progress * (6 + 2 * progress) * math.pi - index) ** 2
                self.p.draw_line(x - spread, y, x + spread, y, 255, 188, 95, round(210 * pulse))
                if progress > .65 and (tick + index) % 3 == 0:
                    self.p.draw_circle(x - spread, y + 2, 2, 255, 224, 147, 179, filled=True)
            else:
                charge = (.82 + .18 * math.sin(progress * 15 + index) ** 2
                          if state == 'active' else (1 - progress)**2 * .6)
                self.p.draw_circle(x, y, round(width * .28), 132, 111, 241, round(74 * charge), filled=True)
                self.app.draw_electric_arc(x - spread, y, x + spread, y + height * .10,
                                           height * .24 * charge, round(240 * charge), tick + index,
                                           glow=(142, 116, 255), core=(236, 229, 255))

    def draw_rockfall(self, x0, y0, x1, y1, state, progress):
        width, height = x1 - x0, y1 - y0
        image = self.quarry_props
        image.clip_draw(*ROCKFALL_BED, (x0 + x1) / 2, (y0 + y1) / 2, width, height)
        if state == 'idle':
            return
        for index, (u, v, scale) in enumerate(((.27, .38, .95), (.73, .60, .76), (.58, .25, .53))):
            x, y = x0 + u * width, y0 + v * height
            size = min(33, width * .48) * scale
            direction = -1 if index % 2 else 1
            if state == 'warning':
                pulse = .77 + .23 * math.sin(progress * (12 + 6 * progress) * math.pi)
                radius = round(size * (.28 + .17 * progress))
                self.p.draw_circle(x, y, radius, 52, 32, 34, 172, filled=True)
                self.p.draw_circle(x, y, radius + 1, 255, 186, 104, round(185 * pulse))
                start = .27 + .1 * index
                fall = max(0, (progress - start) / (1 - start))
                if fall:
                    lift = (77 + index * 12) * (1 - fall * fall)
                    image.opacify(min(1, fall * 6))
                    image.clip_composite_draw(*ROCKFALL_BOULDER, direction * (1.1 - .9 * fall), '',
                                              x - direction * 11 * (1 - fall), y + size * .28 + lift, size, size)
            else:
                impact = progress if state == 'active' else 1 + progress
                spread = 1 - math.exp(-3 * impact)
                image.opacify(.87 * max(0, 1 - impact / 2) ** 2)
                image.clip_draw(*ROCKFALL_DEBRIS, x + direction * 8 * spread, y + 2 * spread,
                                size * (1.15 + spread), size * (.47 + spread * .26))
                bounce = min(1, impact / .42)
                if bounce < 1:
                    fragment = size * (1 - .52 * bounce)
                    lift = 11 * math.sin(math.pi * bounce)
                    image.opacify(1 - bounce)
                    image.clip_composite_draw(*ROCKFALL_BOULDER, direction * (1.5 * bounce + .2), '',
                                              x + direction * 9 * bounce, y + fragment * .28 + lift,
                                              fragment, fragment * (.78 + .22 * bounce))
            image.opacify(1)

    def draw_spike_trap(self, x0, y0, x1, y1, state, progress):
        width, height = x1-x0, y1-y0
        count = max(1, round(width/self.app.view.tile_width))
        step = width/count
        base = self.spike_props['spike-trap-base']
        blade = self.spike_props['spike-blade']
        center_y = (y0+y1)/2
        if state == 'active':
            exposure = min(1,.38+.62*progress*6)
        elif state == 'retract':
            exposure = (1-progress)**2
        else:
            exposure = 0
        visible = round(blade.h*exposure)
        for index in range(count):
            x = x0 + (index+.5)*step
            base.draw(x,center_y,step,height)
            if state in ('warning','active'):
                blink = (math.sin(25*progress)+1)/2
                light = round(105+140*blink) if state == 'warning' else 229
                color = (255,196,102) if state == 'warning' else (255,106,77)
                for side in (-1,1):
                    self.p.draw_circle(x+side*step*.399,center_y-height*.3,2,*color,light,filled=True)
            if visible:
                rise = 27*visible/blade.h
                for socket in (-.26,0,.26):
                    blade.clip_draw(0,blade.h-visible,blade.w,visible,
                                    x+step*socket,center_y-1+rise/2,11,rise)

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
        if room.stage != 1:
            (self.water, self.fire, self.wind, self.earth, self.lightning)[room.stage-2]()
        if room.puzzle and room.puzzle.get('centeredSlide'):
            self.draw_counterweight_prop('socket', room.puzzle['plate'])
        elif room.puzzle:
            self.cable([room.puzzle['start'], room.puzzle['plate']], room.plate_pressed)
            x,y = self.app.point(*room.puzzle['plate'])
            self.app.ui.rounded(x-20, y-10, 40, 20, 4, (110, 185, 134, 255))
        if room.acquisition:
            trial = room.acquisition
            for point in (trial.get('switch') if not (room.forge or room.windmill) else None,
                          trial.get('finalSwitch')):
                if point:
                    x,y = self.app.point(*point)
                    self.app.connect_image.draw(x, y+5, 46, 46)
        if not room.debug_cleared:
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
                if room.inventory['wind'] and not room.puzzle.get('centeredSlide'):
                    x,y = self.app.point(*room.block)
                    self.app.ui.key_label('R', '바람으로 평형추 밀기', x, y+65, 25, 13)
            if room.can_stop_turrets:
                x, y = self.app.point(*room.turret_room['switch'])
                self.app.ui.key_label('G', '포대 정지', x, y + 60, 25, 13)
            return
        if room.acquisition_power_elapsed >= 0 or math.hypot(player.x-point[0], player.y-point[1]) > 2:
            return
        x,y = self.app.point(*point)
        if first_orb.phase == 'sealed':
            guards = any(enemy.active for enemy in room.enemies[:trial['guards']])
            if guards:
                label = (f'남은 적 {room.remaining_enemies}마리' if room.windmill else
                         '수호 적을 먼저 쓰러뜨리세요')
                self.app.ui.text(label, x, y+38, 13)
                return
            if not room.extinguished.issuperset(trial.get('preFire', ())):
                self.app.ui.text('정비 통로의 불길을 먼저 꺼 주세요', x, y+38, 13)
                return
            label = {2:'수문 열기', 3:'화로 덮개 열기', 4:'풍차 가동', 6:'차단기 내리기'}[room.stage]
            if room.capacitor:
                self.app.ui.key_label('G', label, min(self.app.width - 74, x + 86), y + 14, 25, 13)
                return
        elif not room.acquisition_relay:
            self.app.ui.text('번개 기본 공격 · 전도체 충전', x, y+37, 13)
            return
        else:
            label = '승강기 전력 연결'
        self.app.ui.key_label('G', label, x, y+38, 25, 13)
