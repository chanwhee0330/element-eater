"""8번 방의 절벽 지형 및 흙벽으로 차단할 수 있는 상시 레이저."""
import math


def contains(bounds, x, y):
    left, top, right, bottom = bounds
    return left <= x < right and top <= y < bottom


class LaserField:
    """흙벽이 빔을 끊는 위치와 이동 충돌을 계산한다."""
    beam_half_height = .095

    def __init__(self, lasers):
        self.lasers = tuple(map(tuple, lasers))
        self.row_offset = 0.0
        self.laser_cache = None

    def beams(self, terrain):
        # Return (emitter x, visible end x, y, receiver x) from the walls currently standing.
        walls = tuple(t.bounds for t in terrain if t.kind == 'wall')
        key = walls, self.row_offset
        if self.laser_cache is not None and self.laser_cache[0] == key:
            return self.laser_cache[1]
        beams = []
        for start, receiver, y in self.lasers:
            y += self.row_offset
            rightward = start < receiver
            stop = receiver
            for left, top, right, bottom in walls:
                if not top <= y < bottom:
                    continue
                if rightward and right > start and left < stop:
                    stop = max(start, left)
                elif not rightward and left < start and right > stop:
                    stop = min(start, right)
            beams.append((start, stop, y, receiver))
        self.laser_cache = key, tuple(beams)
        return self.laser_cache[1]

    def touches_beam(self, x, y, radius, terrain):
        reach = radius + self.beam_half_height
        if not any(abs(y-row-self.row_offset) < reach for _, _, row in self.lasers):
            return False
        return any(abs(y-row) < reach and min(start, stop)-radius < x < max(start, stop)+radius
                   for start, stop, row, _ in self.beams(terrain))

    def obstacle_bounds(self, terrain):
        return [(min(start, stop), row-self.beam_half_height,
                 max(start, stop), row+self.beam_half_height)
                for start, stop, row, _ in self.beams(terrain)]


class Quarry(LaserField):
    exit_seconds = .4

    def __init__(self, config, reference):
        self.config = config
        self.gates = tuple(map(tuple, config['gates']))
        super().__init__(config['lasers'])
        self.cliffs = tuple(map(tuple, reference['openCliffs']))
        self.cells = {(x, y): [] for left, top, right, bottom in reference['walkable']
                      for x in range(left, right) for y in range(top, bottom)}
        for bounds in reference['cover']:
            left, top, right, bottom = bounds
            for x in range(math.floor(left), math.ceil(right)):
                for y in range(math.floor(top), math.ceil(bottom)):
                    if (x, y) in self.cells:
                        self.cells[x, y].append(bounds)
        self.exit_time = 0.0

    def ground(self, x, y, airborne):
        covers = self.cells.get((math.floor(x), math.floor(y)))
        if covers is not None:
            return 3 if covers and any(contains(bounds, x, y) for bounds in covers) else 0
        return 4 if airborne or any(contains(bounds, x, y) for bounds in self.cliffs) else 3

    def wall_slot(self, x, y):
        for slot in self.config.get('laserWallSlots', ()):
            if contains(slot['approach'], x, y):
                return slot['position']
        return None

    def obstacles(self, room):
        bounds = [t.bounds for t in room.earth_terrain]
        if not room.stone_gate_open or not room.bridge_crossed:
            bounds.extend(self.gates)
        if not room.vine_open:
            vine = room.vine_gate
            bounds.append((vine['x'], vine['y'], vine['x']+vine['width'], vine['y']+vine['height']))
        x, y = room.block
        bounds.append((x-.49, y-.49, x+.49, y+.49))
        bounds.extend(self.obstacle_bounds(room.earth_terrain))
        return frozenset(bounds)
