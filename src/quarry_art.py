"""절벽 운반로의 레이저·돌 운반 장치 애니메이션."""
import json
import math


class QuarryArt:
    def __init__(self, app, folder):
        self.app = app
        self.meta = json.loads((folder/'quarry-laser.json').read_text(encoding='utf-8'))
        self.passage_gate = app.p.load_image(str(folder/'passage-gate.png'))
        self.exit_grille = app.p.load_image(str(folder/'exit-grille.png'))
        self.reset_lever = app.p.load_image(str(folder/'reset-lever.png'))
        self.sheet = app.p.load_image(str(folder/self.meta['image']))
        path = folder.parents[1]/'effects/earth/earth-wall-v1.png'
        self.earth_wall = app.p.load_image(str(path))

    @property
    def room(self):
        return self.app.room

    def sprite(self, name, x, y, width, mirror=False):
        size = self.meta['frameSize']
        index = int(self.room.elapsed*self.meta['fps']) % self.meta['frames']
        bottom = self.sheet.h - (self.meta['rows'][name]+1)*size
        sx, sy = self.app.point(x, y)
        if -width <= sx <= self.app.width+width and -width <= sy <= self.app.height+width:
            self.sheet.clip_composite_draw(index*size, bottom, size, size, 0, 'h' if mirror else '',
                                           sx, sy, width, width)

    def draw_beam(self, start, stop, y, receiver):
        app = self.app
        x0, sy = app.point(start,y)
        x1, _ = app.point(stop,y)
        if sy < -20 or sy > app.height+20 or max(x0,x1) < -20 or min(x0,x1) > app.width+20:
            return
        app.ui.begin()
        low, high = sorted((x0,x1))
        p = app.p
        pulse = round(12*math.sin(self.room.elapsed*11))
        for width,color in ((9,(220,45,65,63)), (5,(238,55,71,131)), (2,(250,108+pulse,81,230))):
            p.draw_rectangle(low,sy-width,high,sy+width,*color,filled=True)
        p.draw_line(low,sy,high,sy,255,238,196)
        offset = int(self.room.elapsed*164) % 38
        for travel in range(offset,round(high-low),38):
            x = x0 + travel if x1>x0 else x0 - travel
            p.draw_line(max(low,x-3),sy+1,min(high,x+3),sy+1,255,249,223)
        self.sprite('emitter', start, y, 43, mirror=start>receiver)
        self.sprite('receiver' if stop==receiver else 'receiver-cut', receiver, y, 34)

    def wall(self, terrain):
        app = self.app
        left, top, right, bottom = terrain.bounds
        unit = app.view.tile_width
        time = self.room.earth_seconds - terrain.remaining
        rise = min(1, time/.16)
        lift = 18*rise
        if terrain.remaining < .65:
            lift *= min(1, terrain.remaining/.32)
        vertical = bottom-top > right-left
        length = bottom-top if vertical else right-left
        count = max(1, math.ceil(length/.55))
        for i in range(count):
            distance = (i+.5)*length/count
            x,y = (left+right)/2,top+distance if vertical else (top+bottom)/2
            if not vertical:
                x = left+distance
            sx,sy = app.point(x,y)
            width = unit*((right-left) if vertical else length/count)
            height = max(2, unit*((length/count) if vertical else bottom-top)*.72+lift)
            self.earth_wall.clip_draw(115,177,488,341,sx,sy+lift*.44,width+3,height)

    def gate(self, bounds):
        opening = self.room.gate_time/self.room.gate_open_seconds if self.room.bridge_crossed else 0
        self.app.garden_art.slide_gate(self.passage_gate, bounds, opening)

    def plate(self):
        app = self.app
        point = self.room.puzzle['plate']
        app.acquisition_art.draw_counterweight_prop('socket', point)
        x, y = app.point(*point)
        pulse = round(22*math.sin(self.room.elapsed*7))
        app.ui.begin()
        color = (195+pulse,233+pulse//2,119) if self.room.plate_pressed else (196+pulse,143+pulse,90)
        app.p.draw_circle(x,y,4,*color,filled=True)

    def lever(self):
        app = self.app
        reset = self.room.puzzle['reset']
        x, y = app.point(*reset)
        unit = app.view.tile_width
        self.reset_lever.draw(x, y, 2.0*unit, 1.55*unit)
        app.ui.begin()
        if not self.room.plate_pressed and math.hypot(self.room.player.x-reset[0], self.room.player.y-reset[1]) <= .9:
            app.ui.text('G · 돌 복귀', x, y+35, 13)

    def hints(self):
        app, room = self.app, self.room
        x,y = room.player.x,room.player.y
        left, top, right, bottom = room.earth_bridge
        bank = top-.4 < y < bottom+.4 and (left-1 < x < left or right <= x < right+1)
        if bank and not any(t.kind == 'floor' for t in room.earth_terrain):
            sx,sy = app.point((left+right)/2, (top+bottom)/2)
            app.ui.begin()
            app.ui.key_label('R', '흙으로 발판 만들기', sx, sy+6, 23, 13)
        slot = room.quarry.wall_slot(x, y)
        if room.stone_gate_open and slot is not None:
            sx,sy = app.point(x, y)
            app.ui.begin()
            app.ui.key_label('R', '흙벽 설치', sx,sy-29,23,13)

    def layers(self):
        room = self.room
        for i,(x,y) in enumerate(room.quarry.config['lamps']):
            yield y,self.app.garden_art.sprite,('lamp-active',x,y-.22,.72,.95,i*2)
        yield room.puzzle['plate'][1]-.1,self.plate,()
        yield room.puzzle['reset'][1],self.lever,()
        for bounds in room.quarry.gates:
            yield bounds[3],self.gate,(bounds,)
        for segment in room.quarry.beams(room.earth_terrain):
            yield segment[2]-.3,self.draw_beam,segment
            start,stop,y,receiver = segment
            if stop!=receiver:
                yield y+.45,self.sprite,('impact',stop,y,44,start<receiver)
