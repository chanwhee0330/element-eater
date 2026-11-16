"""타일 좌표를 공유하는 입체 지도 렌더러."""
import ctypes
import json
import math
import random

from .room import ROOT, TILE_WIDTH, TILE_HEIGHT, RIM_HALF_X, RIM_HALF_Y


WALL_RIM = (110, 126, 178, 255)
WALL_TOP = (151, 176, 238, 255)
WALL_LIP = (205, 221, 255, 255)
WALL_FACE = (144, 157, 198, 255)
WALL_BASE = (87, 100, 148, 255)


class Mesh:
    """SDL이 한 번에 그릴 사각형과 색상 정점."""
    def __init__(self):
        self.vertices = []
        self.indices = []

    def quad(self, points, uv=None, color=(255, 255, 255, 255), colors=None):
        index = len(self.vertices)
        uv = uv or ((0, 0),) * 4
        self.vertices.extend(zip(points, colors or (color,) * 4, uv))
        self.indices.extend(index + i for i in (0, 1, 2, 0, 2, 3))

    def draw(self, p, image=None, offset=(0, 0)):
        if not self.vertices:
            return
        dx, dy = offset
        vertices = (p.SDL_Vertex * len(self.vertices))(*(
            p.SDL_Vertex(p.SDL_FPoint(x + dx, y + dy), p.SDL_Color(*rgba), p.SDL_FPoint(u, v))
            for (x, y), rgba, (u, v) in self.vertices
        ))
        indices = (ctypes.c_int * len(self.indices))(*self.indices)
        if p.SDL_RenderGeometry(p.pico2d.renderer, image.texture if image else None,
                                vertices, len(vertices), indices, len(indices)) < 0:
            raise RuntimeError(p.SDL_GetError().decode('utf-8', errors='replace'))


def atlas_uv(image, col, row, columns, rows):
    # 선형 필터가 이웃 아틀라스 칸을 섞지 않도록 픽셀 중심에서 샘플링한다.
    u0, u1 = col / columns + .5 / image.w, (col + 1) / columns - .5 / image.w
    v0, v1 = row / rows + .5 / image.h, (row + 1) / rows - .5 / image.h
    return ((u0, v0), (u1, v0), (u1, v1), (u0, v1))


class IsometricRoom:
    tile_width, tile_height = TILE_WIDTH, TILE_HEIGHT
    sprite_height = 54
    rear_wall_height = 104

    def __init__(self, p, width, height):
        self.p, self.width, self.height = p, width, height
        self.atlas = p.load_image(str(ROOT / 'assets/maps/isometric/masonry-atlas.png'))
        p.SDL_SetTextureScaleMode(self.atlas.texture, p.SDL_ScaleModeLinear)
        p.SDL_SetTextureBlendMode(self.atlas.texture, p.SDL_BLENDMODE_BLEND)
        self.floor_uv, self.brick_uv, self.cap_uv, self.runner_uv = (
            atlas_uv(self.atlas, i % 2, i // 2, 2, 2) for i in range(4)
        )
        self.cache = {}
        self.reference_images = {}
        self.reference_image = None
        self.reference_scale = 1
        self.shadow = Mesh()
        points = [(math.cos(i * math.tau / 16), math.sin(i * math.tau / 16)) for i in range(16)]
        for i, (x, y) in enumerate(points):
            nx, ny = points[(i + 1) % len(points)]
            self.shadow.quad(
                ((0, 0), (x * 23, y * 8), (nx * 23, ny * 8), (0, 0)),
                colors=((17, 11, 23, 165), (17, 11, 23, 0), (17, 11, 23, 0), (17, 11, 23, 165))
            )

    def project(self, x, y, z=0):
        # SDL 화면은 왼쪽 위 원점이다. 높이는 월드 y와 별도로 올린다.
        return x * self.tile_width, y * self.tile_height - z

    def floor_quad(self, mesh, x0, y0, x1, y1, uv, color, z=0):
        mesh.quad((self.project(x0, y0, z), self.project(x1, y0, z),
                   self.project(x1, y1, z), self.project(x0, y1, z)), uv, color)

    def face(self, mesh, start, end, top, bottom, light, dark=None, uv=None):
        colors = (light, light, dark or light, dark or light)
        mesh.quad((self.project(*start, top), self.project(*end, top),
                   self.project(*end, bottom), self.project(*start, bottom)),
                  self.brick_uv if uv is None else uv, colors=colors)

    def load(self, room):
        self.room = room
        self.reference_image = None
        self.reference_scale = 1
        self.tile_width, self.tile_height = type(self).tile_width, type(self).tile_height
        if room.reference_art:
            path = room.map_path.parent / room.reference_art['image']
            if path not in self.reference_images:
                self.reference_images[path] = self.p.load_image(str(path))
            self.reference_image = self.reference_images[path]
            self.reference_scale = max(room.reference_art.get('minimumScale', 1), self.width / self.reference_image.w,
                                       self.height / self.reference_image.h)
            self.tile_width = self.tile_height = room.reference_art['pixelsPerTile'] * self.reference_scale
            self.walls = []
            self.follow(room.player.x, room.player.y)
            return
        if room.map_path not in self.cache:
            self.cache[room.map_path] = self.build(room)
        self.backdrop, self.terrain, self.terrain_size, self.terrain_origin, self.walls = self.cache[room.map_path]
        self.follow(room.player.x, room.player.y)

    def follow(self, x, y):
        if self.reference_image:
            image = self.reference_image
            scale = self.reference_scale
            origin_x, origin_y = self.room.reference_art['originPixels']
            px, py = self.project(x, y)
            left = self.width / 2 - px - origin_x * scale
            top = self.height * .6 - py - origin_y * scale
            self.origin = (round(max(self.width - image.w * scale, min(0, left)) + origin_x * scale),
                           round(max(self.height - image.h * scale, min(0, top)) + origin_y * scale))
            return
        px, py = self.project(x, y)
        if self.room.acquisition:
            columns, rows = self.room.data['columns'], self.room.data['rows']
            rear_y = self.room.data['floorRegions'][0]['y']
            top_limit = 115 - rear_y * self.tile_height + self.rear_wall_height
            left = min(0, max(self.width - columns * self.tile_width, self.width / 2 - px))
            top = min(top_limit, max(self.height - rows * self.tile_height - 60, self.height * .58 - py))
            self.origin = round(left), round(top)
            return
        center_x = self.room.data['columns'] * self.tile_width / 2
        rear_y = self.room.data['floorRegions'][0]['y']
        _, wall_top = self.project(0, rear_y, self.rear_wall_height)
        # 벽 윗부분이 상단 HUD 아래에 닿으면 위쪽 추적을 멈춘다.
        vertical_offset = min(self.height * .75 - py, 100 - wall_top)
        self.origin = (round(self.width / 2 - center_x - (px - center_x) * .35),
                       round(vertical_offset))

    def point(self, x, y, z=0):
        px, py = self.project(x, y, z)
        return self.origin[0] + px, self.height - self.origin[1] - py

    def draw_shadow(self, x, y):
        px, py = self.point(x, y)
        self.p.SDL_SetRenderDrawBlendMode(self.p.pico2d.renderer, self.p.SDL_BLENDMODE_BLEND)
        self.shadow.draw(self.p, offset=(px, self.height - py + 1))

    def draw_exit_marker(self, x, y, opened):
        marker = Mesh()
        color = (155, 210, 161, 185) if opened else (178, 141, 100, 135)
        self.floor_quad(marker, x - .28, y - .28, x + .28, y + .28, None, color, .6)
        self.p.SDL_SetRenderDrawBlendMode(self.p.pico2d.renderer, self.p.SDL_BLENDMODE_BLEND)
        marker.draw(self.p, offset=self.origin)

    def draw_ground(self, draw_under_terrain=None):
        if self.reference_image:
            image = self.reference_image
            self.draw_reference_cover((0, 0, image.w, image.h))
            return
        self.backdrop.draw(self.width / 2, self.height / 2, self.width, self.height)
        if draw_under_terrain:
            draw_under_terrain()
        width, height = self.terrain_size
        ox, oy = self.terrain_origin
        dx, dy = self.origin
        dest = self.p.SDL_Rect(dx - ox, dy - oy, width, height)
        self.p.SDL_RenderCopy(self.p.pico2d.renderer, self.terrain, None, ctypes.byref(dest))

    def reference_point(self, x, y):
        origin_x, origin_y = self.room.reference_art['originPixels']
        unit = self.room.reference_art['pixelsPerTile']
        return self.point((x - origin_x) / unit, (y - origin_y) / unit)

    def draw_reference_cover(self, rect):
        x0, y0, x1, y1 = rect
        x, y = self.reference_point((x0 + x1) / 2, (y0 + y1) / 2)
        image = self.reference_image
        scale = self.reference_scale
        image.clip_draw(x0, image.h - y1, x1 - x0, y1 - y0, x, y,
                        (x1 - x0) * scale, (y1 - y0) * scale)

    def draw_wall(self, mesh):
        mesh.draw(self.p, self.atlas, self.origin)

    def wall_cap(self, mesh, x0, y0, x1, y1, height):
        self.floor_quad(mesh, x0, y0, x1, y1, self.cap_uv, WALL_RIM, height)
        inset_x, inset_y = 1.2 / self.tile_width, 1.1 / self.tile_height
        self.floor_quad(mesh, x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y,
                        self.cap_uv, WALL_TOP, height)
        self.floor_quad(mesh, x0 + inset_x, y1 - 2 * inset_y, x1 - inset_x, y1 - inset_y,
                        self.cap_uv, WALL_LIP, height)

    def wall_shadow(self, mesh, left, right, y):
        near, far = (23, 24, 44, 116), (23, 24, 44, 0)
        mesh.quad((self.project(left, y), self.project(right, y),
                   self.project(right, y + .26), self.project(left, y + .26)),
                  colors=(near, near, far, far))

    def wall_cell(self, x, y, height):
        mesh = Mesh()
        tile = self.room.data['tileIds']['wall']
        self.masonry_block(mesh, x, y, x + 1, y + 1, height,
                           front=self.room.tile(x + .5, y + 1.5) != tile)
        return mesh

    def masonry_block(self, mesh, left, top, right, bottom, height, *, front=True):
        u0, v0 = self.brick_uv[0]
        u1, v1 = self.brick_uv[2]
        # 낮은 엄폐물에는 벽돌 두 단만 보여 높이 차이를 읽기 쉽게 한다.
        v0 += (v1 - v0) * .6
        uv = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        if front:
            self.face(mesh, (left, bottom), (right, bottom), height, 0, WALL_FACE, WALL_BASE, uv=uv)
        self.wall_cap(mesh, left, top, right, bottom, height)

    def build(self, room):
        p = self.p
        data, folder = room.data, room.map_path.parent
        tiles, ids = data['tiles'], data['tileIds']
        cols, rows = data['columns'], data['rows']
        backdrop = p.load_image(str(folder / data['backdropImage']))
        p.SDL_SetTextureColorMod(backdrop.texture, 103, 92, 136)
        decor = json.loads((folder / data.get('decorations', 'source/decorations.json')).read_text(encoding='utf-8'))
        decor_path = data.get('decorationsImage', 'source/' + decor['atlas'])
        decor_atlas = p.load_image(str(folder / decor_path))
        p.SDL_SetTextureScaleMode(decor_atlas.texture, p.SDL_ScaleModeLinear)

        cliff, floor, floor_light, shadows, spikes, rugs, decals, rear, banners = (Mesh() for _ in range(9))
        walls = []
        randomizer = random.Random(data['seed'])
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile == ids['pit']:
                    continue
                if y + 1 == rows or tiles[y + 1][x] == ids['pit']:
                    self.face(cliff, (x, y + 1), (x + 1, y + 1), 0, -100,
                              (145, 122, 149, 255), (32, 25, 43, 10))
                if tile == ids['spikes']:
                    self.spike_tile(spikes, x, y)
                    continue
                brightness = randomizer.randint(218, 255)
                color = (min(255, brightness + 11), min(255, brightness + 8), brightness - 11, 255)
                uv = self.cap_uv if tile == ids['crackedFloor'] else self.floor_uv
                rotation = randomizer.randrange(4)
                self.floor_quad(floor, x, y, x + 1, y + 1, uv[rotation:] + uv[:rotation], color)
                self.floor_quad(floor_light, x, y, x + 1, y + 1, None, (197, 157, 127, 41))
                if tile == ids['wall']:
                    height = 42 if room.stage == 1 else 38
                    walls.append((y + 1, self.wall_cell(x, y, height)))
                    if y + 1 < rows and tiles[y + 1][x] in (ids['floor'], ids['mossFloor'], ids['crackedFloor']):
                        self.wall_shadow(shadows, x, x + 1, y + 1)

        for entry in decor['placements']:
            slot = decor['slots'][entry['kind']]
            uv = atlas_uv(decor_atlas, slot % 2, slot // 2, 2, 2)
            if entry.get('flip'):
                uv = (uv[1], uv[0], uv[3], uv[2])
            x, y, radius = entry['x'], entry['y'], entry['width'] / 2
            angle = math.radians(entry.get('rotation', 0))
            c, s = math.cos(angle), math.sin(angle)
            points = [self.project(x + u*c - v*s, y + u*s + v*c, .5)
                      for u, v in ((-radius, -radius), (radius, -radius), (radius, radius), (-radius, radius))]
            decals.quad(points, uv, (216, 194, 221, round(entry.get('opacity', 1) * 255)))

        bridge = data['floorRegions'][1]
        x = bridge['x'] + bridge['width'] / 2
        for y in range(bridge['y'], bridge['y'] + bridge['height']):
            self.floor_quad(rugs, x - .65, y, x + .65, y + 1, self.runner_uv, (213, 203, 228, 255), .6)

        arena = data['floorRegions'][0]
        left, top = arena['x'], arena['y']
        right = left + arena['width']
        exit_x = data['plannedExit']['x']
        self.face(rear, (exit_x - .6, top), (exit_x + .6, top),
                  self.rear_wall_height, 81, WALL_FACE, WALL_BASE)
        self.wall_cap(rear, exit_x - .6, top - .24, exit_x + .6, top, self.rear_wall_height)
        self.wall_shadow(shadows, left, exit_x - .6, top)
        self.wall_shadow(shadows, exit_x + .6, right, top)
        fixtures = []
        for x in range(left, right):
            if x == exit_x - 1:
                self.rear_wall(rear, x, top, length=.4)
                continue
            if x == exit_x:
                self.rear_wall(rear, x + .6, top, length=.4)
                continue
            self.rear_wall(rear, x, top)
            if (x - left) % 4 == 2:
                fixtures.append(self.project(x + .48, top + .03, 67))
            elif (x - left) % 5 == 3:
                self.face(banners, (x + .14, top + .02), (x + .85, top + .02),
                          86, 32, (212, 188, 214, 255), uv=self.runner_uv)
        # 뒷벽 끝에 석재 기둥을 세워 낮은 옆벽의 윗돌까지 연결한다.
        rear_ends = [(left, right, top, self.rear_wall_height)]
        ivy = Mesh()
        moss_slot = decor['slots']['moss']
        moss_uv = atlas_uv(decor_atlas, moss_slot % 2, moss_slot // 2, 2, 2)
        for run in decor.get('wallRuns', []):
            x, y, height = run['x'], run['y'], run['height']
            rear_ends.append((x, x + run['width'], y, height))
            for column in range(x, x + run['width']):
                self.rear_wall(rear, column, y, height=height)
            self.wall_shadow(shadows, x, x + run['width'], y)
            for offset in run.get('sconces', []):
                fixtures.append(self.project(x + offset, y + .03, height * .56))
            for offset in run.get('banners', []):
                center = x + offset
                self.face(banners, (center - .42, y + .02), (center + .42, y + .02),
                          height - 8, height * .26, (212, 188, 214, 255), uv=self.runner_uv)
            for offset in run.get('ivy', []):
                center = x + offset
                for shift, vine_top, drop in ((-.33, height + 3, 26), (0, height + 2, 43), (.32, height + 1, 30)):
                    self.face(ivy, (center + shift - .35, y + .04), (center + shift + .35, y + .04),
                              vine_top, vine_top - drop, (167, 190, 123, 240), uv=moss_uv)

        walls.extend(self.perimeter_walls(self.room.rim_edges))
        for x, y in decor.get('cliffSconces', []):
            fixtures.append(self.project(x, y, -28))

        for left_x, right_x, edge_y, height in rear_ends:
            for corner_x, outside_x in ((left_x, left_x - 1), (right_x, right_x)):
                if 0 <= outside_x < cols and tiles[edge_y][outside_x] != ids['pit']:
                    continue
                half = 10 / self.tile_width
                for base in range(22, height, 17):
                    self.face(rear, (corner_x - half, edge_y), (corner_x + half, edge_y),
                              min(base + 17, height), base, WALL_TOP, WALL_FACE, uv=self.cap_uv)

        ox, oy = 12, 120
        width, height = cols * self.tile_width + 24, rows * self.tile_height + oy + 112
        renderer = p.pico2d.renderer
        terrain = p.SDL_CreateTexture(renderer, p.SDL_PIXELFORMAT_RGBA8888, p.SDL_TEXTUREACCESS_TARGET, width, height)
        if not terrain:
            raise RuntimeError('입체 지도를 그릴 텍스처를 만들지 못했습니다.')
        previous = p.SDL_GetRenderTarget(renderer)
        try:
            if p.SDL_SetRenderTarget(renderer, terrain) < 0:
                raise RuntimeError('입체 지도 렌더링 대상으로 전환하지 못했습니다.')
            p.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0)
            p.SDL_RenderClear(renderer)
            p.SDL_SetRenderDrawBlendMode(renderer, p.SDL_BLENDMODE_BLEND)
            for mesh, image in ((cliff, self.atlas), (floor, self.atlas), (spikes, None),
                                (floor_light, None), (rugs, self.atlas), (decals, decor_atlas),
                                (shadows, None), (rear, self.atlas), (banners, self.atlas), (ivy, decor_atlas)):
                mesh.draw(p, image, (ox, oy))
            for x, y in fixtures:
                self.sconce(round(x + ox), self.height - round(y + oy))
        except Exception:
            p.SDL_SetRenderTarget(renderer, previous)
            p.SDL_DestroyTexture(terrain)
            raise
        finally:
            p.SDL_SetRenderTarget(renderer, previous)
        p.SDL_SetTextureBlendMode(terrain, p.SDL_BLENDMODE_BLEND)
        return backdrop, terrain, (width, height), (ox, oy), walls

    def perimeter_walls(self, edges):
        corners = self.room.rim_corners
        # 꼭짓점에는 모서리 돌을 한 번만 놓고, 양쪽 윗돌을 그 돌에 맞춘다.
        half_x, half_y = RIM_HALF_X, RIM_HALF_Y
        vertical = {start for start, _, axis in edges if axis == 'vertical'}
        for start, end, axis in edges:
            if axis != 'horizontal':
                continue
            x, y = start
            left = x + (half_x if start in corners else 0)
            right = end[0] - (half_x if end in corners else 0)
            yield y + half_y, self.rim_segment(left, y - half_y, right, y + half_y)

        # 이어진 옆벽은 끝점의 깊이로 한 번만 그려 중간 타일에서 가림이 갈리지 않게 한다.
        for x, y in sorted(vertical):
            if (x, y - 1) in vertical and (x, y) not in corners:
                continue
            end_y = y + 1
            while (x, end_y) in vertical and (x, end_y) not in corners:
                end_y += 1
            top = y + (half_y if (x, y) in corners else 0)
            bottom = end_y - (half_y if (x, end_y) in corners else 0)
            yield bottom, self.rim_segment(x - half_x, top, x + half_x, bottom, front=False)
        for x, y in sorted(corners):
            yield y + half_y, self.rim_segment(x - half_x, y - half_y, x + half_x, y + half_y)

    def rim_segment(self, x0, y0, x1, y1, *, front=True):
        mesh = Mesh()
        height = 22
        u0, v0 = self.brick_uv[0]
        u1, v1 = self.brick_uv[2]
        v0 += (v1 - v0) * .6
        u1 = u0 + (u1 - u0) * (x1 - x0)
        uv = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        if front:
            self.face(mesh, (x0, y1), (x1, y1), height, 0, WALL_FACE, WALL_BASE, uv=uv)
        self.wall_cap(mesh, x0, y0, x1, y1, height)
        self.face(mesh, (x0, y1), (x1, y1), height, height - 3, WALL_TOP, WALL_FACE, uv=uv)
        return mesh

    def spike_tile(self, mesh, x, y):
        self.floor_quad(mesh, x, y, x + 1, y + 1, None, (131, 103, 85, 255))
        self.floor_quad(mesh, x + .045, y + .055, x + .955, y + .945,
                        None, (49, 43, 54, 255))
        for row in (.32, .73):
            for col in (.22, .50, .78):
                sx, sy = x + col, y + row
                self.floor_quad(mesh, sx - .10, sy - .06, sx + .14, sy + .11,
                                None, (29, 25, 34, 255))
                tip = self.project(sx, sy, 13)
                left = self.project(sx - .085, sy)
                right = self.project(sx + .085, sy)
                front = self.project(sx, sy + .105)
                mesh.quad((tip, left, front, tip), color=(186, 181, 198, 255))
                mesh.quad((tip, front, right, tip), color=(91, 85, 108, 255))

    def rear_wall(self, mesh, x, y, length=1, *, height=None):
        height = self.rear_wall_height if height is None else height
        start, end = (x, y), (x + length, y)
        bounds = (x, y - .24, x + length, y)
        # 한 칸 폭의 입면은 아틀라스 반쪽을 사용해 벽돌 비율을 유지한다.
        u0, v0 = self.brick_uv[0]
        u1, v1 = self.brick_uv[2]
        mid = (u0 + u1) / 2
        uv = ((u0, v0), (mid, v0), (mid, v1), (u0, v1))
        self.face(mesh, start, end, height, 0, WALL_FACE, WALL_BASE, uv=uv)
        self.wall_cap(mesh, *bounds, height)

    def sconce(self, x, y):
        p = self.p
        for radius in (25, 20, 15, 11):
            p.draw_circle(x, y + 9, radius, 239, 148, 64, 13, filled=True)
        p.draw_line(x - 9, y - 8, x + 7, y - 8, 42, 29, 35)
        p.draw_line(x - 7, y - 7, x - 7, y + 3, 151, 104, 69)
        p.draw_line(x + 6, y - 7, x + 6, y + 2, 151, 104, 69)
        for dx, rise in ((-7, 0), (0, 5), (6, 0)):
            p.draw_line(x + dx, y - 4, x + dx, y + 6 + rise, 218, 170, 105)
            p.draw_circle(x + dx, y + 8 + rise, 3, 246, 169, 70, filled=True)
            p.draw_circle(x + dx, y + 9 + rise, 2, 255, 222, 148, filled=True)

    def release(self):
        for _, terrain, _, _, _ in self.cache.values():
            self.p.SDL_DestroyTexture(terrain)
        self.cache.clear()
        self.reference_images.clear()
        self.reference_image = None
        self.backdrop = self.atlas = None
