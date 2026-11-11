"""두 방의 타일 좌표를 공유하는 입체 지도 렌더러."""
from collections import defaultdict
import ctypes
import json
import math
import random

from .room import ROOT


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

    def draw(self, p, image=None, offset=(0, 0), opacity=1):
        if not self.vertices:
            return
        dx, dy = offset
        vertices = (p.SDL_Vertex * len(self.vertices))(*(
            p.SDL_Vertex(p.SDL_FPoint(x + dx, y + dy), p.SDL_Color(*rgba[:3], round(rgba[3] * opacity)), p.SDL_FPoint(u, v))
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
    tile_width, tile_height = 48, 30
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
            self.reference_scale = min(self.width / self.reference_image.w, self.height / self.reference_image.h)
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
            self.origin = ((self.width - image.w * scale) / 2 + origin_x * scale,
                           (self.height - image.h * scale) / 2 + origin_y * scale)
            return
        px, py = self.project(x, y)
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

    def draw_ground(self):
        if self.reference_image:
            self.p.draw_rectangle(0, 0, self.width, self.height, 26, 21, 32, filled=True)
            self.reference_image.draw(self.width / 2, self.height / 2,
                                      self.reference_image.w * self.reference_scale,
                                      self.reference_image.h * self.reference_scale)
            return
        self.backdrop.draw(self.width / 2, self.height / 2, self.width, self.height)
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

    def draw_wall(self, wall):
        mesh, x, y, height, is_perimeter = wall
        if is_perimeter:
            mesh.draw(self.p, self.atlas, self.origin)
            return
        player = self.room.player
        # Keep the wall geometry and fade its surfaces when it obscures the player.
        px, py = self.project(player.x, player.y)
        wx, wy = self.project(x + .5, y + .5)
        obscures_player = abs(px - wx) < self.tile_width * .95 and 0 < wy - py < height + 12
        mesh.draw(self.p, self.atlas, self.origin, opacity=.42 if obscures_player else 1)

    def wall_cell(self, x, y, height):
        mesh = Mesh()
        tile = self.room.data['tileIds']['wall']
        u0, v0 = self.brick_uv[0]
        u1, v1 = self.brick_uv[2]
        # 낮은 엄폐물에는 벽돌 두 단만 보여 높이 차이를 읽기 쉽게 한다.
        v0 += (v1 - v0) * .6
        uv = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        if self.room.tile(x + .5, y + 1.5) != tile:
            self.face(mesh, (x, y + 1), (x + 1, y + 1), height, 0, (216, 198, 213, 255), uv=uv)
        self.floor_quad(mesh, x, y, x + 1, y + 1, self.cap_uv, (210, 204, 217, 255), height)
        return mesh

    def build(self, room):
        p = self.p
        data, folder = room.data, room.map_path.parent
        tiles, ids = data['tiles'], data['tileIds']
        cols, rows = data['columns'], data['rows']
        backdrop = p.load_image(str(folder / data['backdropImage']))
        p.SDL_SetTextureColorMod(backdrop.texture, 103, 92, 136)
        decor = json.loads((folder / 'source/decorations.json').read_text(encoding='utf-8'))
        decor_atlas = p.load_image(str(folder / 'source' / decor['atlas']))
        p.SDL_SetTextureScaleMode(decor_atlas.texture, p.SDL_ScaleModeLinear)

        cliff, floor, spikes, rugs, decals, rear, banners = (Mesh() for _ in range(7))
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
                color = (brightness, brightness - 5, min(255, brightness + 3), 255)
                uv = self.cap_uv if tile == ids['crackedFloor'] else self.floor_uv
                rotation = randomizer.randrange(4)
                self.floor_quad(floor, x, y, x + 1, y + 1, uv[rotation:] + uv[:rotation], color)
                if tile == ids['wall']:
                    height = 42 if room.stage == 1 else 38
                    walls.append((y + 1, (self.wall_cell(x, y, height), x, y, height, False)))

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
                  self.rear_wall_height, 81, (224, 208, 226, 255))
        self.floor_quad(rear, exit_x - .6, top - .24, exit_x + .6, top,
                        self.cap_uv, (223, 207, 215, 255), self.rear_wall_height)
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

        # 높은 뒤쪽 벽이 이미 있는 경계는 낮은 외곽벽으로 덮지 않는다.
        decorated_edges = {(column, top) for column in range(left, right)}
        for run in decor.get('wallRuns', []):
            decorated_edges.update((column, run['y'])
                                   for column in range(run['x'], run['x'] + run['width']))
        walls.extend(self.perimeter_walls(tiles, ids['pit'], decorated_edges))
        for x, y in decor.get('cliffSconces', []):
            fixtures.append(self.project(x, y, -28))

        for left_x, right_x, edge_y, height in rear_ends:
            for corner_x, outside_x in ((left_x, left_x - 1), (right_x, right_x)):
                if 0 <= outside_x < cols and tiles[edge_y][outside_x] != ids['pit']:
                    continue
                half = 10 / self.tile_width
                for base in range(22, height, 17):
                    self.face(rear, (corner_x - half, edge_y), (corner_x + half, edge_y),
                              min(base + 17, height), base, (240, 211, 230, 255),
                              (176, 151, 180, 255), uv=self.cap_uv)

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
                                (rugs, self.atlas), (decals, decor_atlas), (rear, self.atlas), (banners, self.atlas), (ivy, decor_atlas)):
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

    def perimeter_walls(self, tiles, pit, decorated_edges):
        rows, columns = len(tiles), len(tiles[0])
        edges = []
        axes_at = defaultdict(set)
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile == pit:
                    continue
                # 한 칸 너머의 앞쪽 절벽이 이미 이 경계를 구분한다.
                cliff_behind = y >= 2 and tiles[y - 2][x] != pit
                if (y == 0 or tiles[y - 1][x] == pit) and not cliff_behind and (x, y) not in decorated_edges:
                    edges.append(((x, y), (x + 1, y), 'horizontal'))
                if y + 1 == rows or tiles[y + 1][x] == pit:
                    edges.append(((x, y + 1), (x + 1, y + 1), 'horizontal'))
                if x == 0 or row[x - 1] == pit:
                    edges.append(((x, y), (x, y + 1), 'vertical'))
                if x + 1 == columns or row[x + 1] == pit:
                    edges.append(((x + 1, y), (x + 1, y + 1), 'vertical'))

        for start, end, axis in edges:
            axes_at[start].add(axis)
            axes_at[end].add(axis)
        corners = {point for point, axes in axes_at.items() if len(axes) == 2}
        # 꼭짓점에는 모서리 돌을 한 번만 놓고, 양쪽 윗돌을 그 돌에 맞춘다.
        half_x = 10 / self.tile_width
        half_y = 10 / self.tile_height
        for start, end, axis in edges:
            x, y = start
            end_x, end_y = end
            if axis == 'horizontal':
                left = x + (half_x if start in corners else 0)
                right = end_x - (half_x if end in corners else 0)
                yield y + half_y, self.rim_segment(left, y - half_y, right, y + half_y)
            else:
                top = y + (half_y if start in corners else 0)
                bottom = end_y - (half_y if end in corners else 0)
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
            self.face(mesh, (x0, y1), (x1, y1), height, 0,
                      (201, 177, 200, 255), (126, 106, 137, 255), uv=uv)
            self.face(mesh, (x0, y1), (x1, y1), height, height - 4,
                      (229, 201, 219, 255), (164, 137, 165, 255), uv=uv)
        # 윗돌의 어두운 바깥선과 밝은 윗면으로 경계의 폭을 읽기 쉽게 한다.
        self.floor_quad(mesh, x0, y0, x1, y1, self.cap_uv, (155, 130, 156, 255), height)
        inset_x, inset_y = 1 / self.tile_width, 1 / self.tile_height
        self.floor_quad(mesh, x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y,
                        self.cap_uv, (250, 225, 242, 255), height)
        if not front:
            self.face(mesh, (x0, y1), (x1, y1), height, height - 5,
                      (186, 151, 178, 255), (137, 111, 149, 255), uv=uv)
        return mesh, (x0 + x1) / 2 - .5, y1 - .5, height, True

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
        shade = (224, 208, 226, 255)
        # 한 칸 폭의 입면은 아틀라스 반쪽을 사용해 벽돌 비율을 유지한다.
        u0, v0 = self.brick_uv[0]
        u1, v1 = self.brick_uv[2]
        mid = (u0 + u1) / 2
        uv = ((u0, v0), (mid, v0), (mid, v1), (u0, v1))
        self.face(mesh, start, end, height, 0, shade, (136, 120, 148, 255), uv=uv)
        self.floor_quad(mesh, *bounds, self.cap_uv, (223, 207, 215, 255), height)

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
