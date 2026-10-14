"""俄罗斯方块 (Tetris) - 使用 pygame 编写

操作说明:
    ← / →   左右移动
    ↓       加速下落(软降)
    ↑ / X   顺时针旋转
    Z       逆时针旋转
    空格     直接落到底(硬降)
    C       暂存方块 (Hold)
    P       暂停 / 继续
    R       游戏结束后重新开始
    ESC     退出
"""
import random
import sys

import pygame

# ---------------- 基本配置 ----------------
COLS, ROWS = 10, 20
CELL = 30
SIDE_W = 180
WIDTH = COLS * CELL + SIDE_W
HEIGHT = ROWS * CELL
FPS = 60

BG = (18, 18, 28)
GRID = (40, 40, 58)
TEXT = (235, 235, 245)

# 每种方块在 4x4 网格中的旋转形态 (按 SRS 风格定义坐标)
SHAPES = {
    "I": [[(0, 1), (1, 1), (2, 1), (3, 1)],
          [(2, 0), (2, 1), (2, 2), (2, 3)],
          [(0, 2), (1, 2), (2, 2), (3, 2)],
          [(1, 0), (1, 1), (1, 2), (1, 3)]],
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)]] * 4,
    "T": [[(1, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (1, 2)],
          [(1, 0), (0, 1), (1, 1), (1, 2)]],
    "S": [[(1, 0), (2, 0), (0, 1), (1, 1)],
          [(1, 0), (1, 1), (2, 1), (2, 2)],
          [(1, 1), (2, 1), (0, 2), (1, 2)],
          [(0, 0), (0, 1), (1, 1), (1, 2)]],
    "Z": [[(0, 0), (1, 0), (1, 1), (2, 1)],
          [(2, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (1, 2), (2, 2)],
          [(1, 0), (0, 1), (1, 1), (0, 2)]],
    "J": [[(0, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (2, 2)],
          [(1, 0), (1, 1), (0, 2), (1, 2)]],
    "L": [[(2, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (1, 2), (2, 2)],
          [(0, 1), (1, 1), (2, 1), (0, 2)],
          [(0, 0), (1, 0), (1, 1), (1, 2)]],
}

COLORS = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (170, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 0, 240),
    "L": (240, 160, 0),
}

# 消行得分(按一次消除的行数)
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rot = 0
        self.x = COLS // 2 - 2
        self.y = 0

    def cells(self, rot=None, x=None, y=None):
        rot = self.rot if rot is None else rot
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + cx, y + cy) for cx, cy in SHAPES[self.kind][rot % 4]]


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.next_kind = self._draw()
        self.hold_kind = None
        self.can_hold = True
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.fall_timer = 0
        self.spawn()

    # 7-bag 随机器: 保证每 7 个方块里每种都出现一次
    def _draw(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self, kind=None):
        if kind is None:
            kind = self.next_kind
            self.next_kind = self._draw()
        self.piece = Piece(kind)
        self.can_hold = True
        if not self.valid(self.piece.cells()):
            self.game_over = True

    def valid(self, cells):
        for x, y in cells:
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def move(self, dx, dy):
        cells = self.piece.cells(x=self.piece.x + dx, y=self.piece.y + dy)
        if self.valid(cells):
            self.piece.x += dx
            self.piece.y += dy
            return True
        return False

    def rotate(self, direction):
        new_rot = (self.piece.rot + direction) % 4
        # 简易墙踢: 依次尝试偏移
        for dx in (0, -1, 1, -2, 2):
            cells = self.piece.cells(rot=new_rot, x=self.piece.x + dx)
            if self.valid(cells):
                self.piece.rot = new_rot
                self.piece.x += dx
                return

    def ghost_y(self):
        y = self.piece.y
        while self.valid(self.piece.cells(y=y + 1)):
            y += 1
        return y

    def hard_drop(self):
        dist = self.ghost_y() - self.piece.y
        self.piece.y += dist
        self.score += dist * 2
        self.lock()

    def soft_drop(self):
        if self.move(0, 1):
            self.score += 1
        else:
            self.lock()

    def hold(self):
        if not self.can_hold:
            return
        current = self.piece.kind
        if self.hold_kind is None:
            self.hold_kind = current
            self.spawn()
        else:
            self.hold_kind, swap = current, self.hold_kind
            self.spawn(swap)
        self.can_hold = False

    def lock(self):
        for x, y in self.piece.cells():
            if 0 <= y < ROWS:
                self.board[y][x] = self.piece.kind
        self.clear_lines()
        self.spawn()

    def clear_lines(self):
        full = [i for i, row in enumerate(self.board) if all(c is not None for c in row)]
        if not full:
            return
        for i in full:
            del self.board[i]
            self.board.insert(0, [None] * COLS)
        n = len(full)
        self.score += LINE_SCORES[n] * self.level
        self.lines += n
        self.level = self.lines // 10 + 1

    def fall_interval(self):
        # 毫秒; 等级越高下落越快
        return max(80, 800 - (self.level - 1) * 70)

    def update(self, dt):
        if self.game_over or self.paused:
            return
        self.fall_timer += dt
        if self.fall_timer >= self.fall_interval():
            self.fall_timer = 0
            if not self.move(0, 1):
                self.lock()


# ---------------- 绘制 ----------------
def draw_cell(surface, x, y, color, size=CELL, alpha=None):
    rect = pygame.Rect(x, y, size, size)
    if alpha is not None:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=4)
        surface.blit(s, rect)
        return
    pygame.draw.rect(surface, color, rect.inflate(-2, -2), border_radius=4)
    light = tuple(min(255, c + 60) for c in color)
    pygame.draw.line(surface, light, (x + 3, y + 3), (x + size - 4, y + 3), 2)


def draw_mini(surface, kind, left, top, box=100):
    """在侧边栏小窗口里画一个方块预览。"""
    if kind is None:
        return
    cells = SHAPES[kind][0]
    mini = 22
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    w = (max(xs) - min(xs) + 1) * mini
    h = (max(ys) - min(ys) + 1) * mini
    ox = left + (box - w) // 2 - min(xs) * mini
    oy = top + (box - h) // 2 - min(ys) * mini
    for cx, cy in cells:
        draw_cell(surface, ox + cx * mini, oy + cy * mini, COLORS[kind], size=mini)


def draw(screen, game, fonts):
    small, mid, big = fonts
    screen.fill(BG)

    # 棋盘网格
    for r in range(ROWS):
        for c in range(COLS):
            pygame.draw.rect(screen, GRID, (c * CELL, r * CELL, CELL, CELL), 1)

    # 已固定的方块
    for r in range(ROWS):
        for c in range(COLS):
            kind = game.board[r][c]
            if kind:
                draw_cell(screen, c * CELL, r * CELL, COLORS[kind])

    if not game.game_over:
        # 影子(落点提示)
        gy = game.ghost_y()
        for x, y in game.piece.cells(y=gy):
            if y >= 0:
                draw_cell(screen, x * CELL, y * CELL, COLORS[game.piece.kind], alpha=70)
        # 当前方块
        for x, y in game.piece.cells():
            if y >= 0:
                draw_cell(screen, x * CELL, y * CELL, COLORS[game.piece.kind])

    # 侧边栏
    sx = COLS * CELL
    pygame.draw.rect(screen, (28, 28, 42), (sx, 0, SIDE_W, HEIGHT))
    pygame.draw.line(screen, (90, 90, 120), (sx, 0), (sx, HEIGHT), 2)

    def label(txt, y):
        screen.blit(small.render(txt, True, (160, 160, 190)), (sx + 16, y))

    label("下一个", 14)
    draw_mini(screen, game.next_kind, sx + 16, 36)
    label("暂存 (C)", 150)
    draw_mini(screen, game.hold_kind, sx + 16, 172)

    label("分数", 290)
    screen.blit(mid.render(str(game.score), True, TEXT), (sx + 16, 312))
    label("行数", 360)
    screen.blit(mid.render(str(game.lines), True, TEXT), (sx + 16, 382))
    label("等级", 430)
    screen.blit(mid.render(str(game.level), True, TEXT), (sx + 16, 452))
    label("P 暂停  ESC 退出", 560)

    # 覆盖层
    if game.game_over or game.paused:
        overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        title = "游戏结束" if game.game_over else "已暂停"
        sub = "按 R 重新开始" if game.game_over else "按 P 继续"
        t = big.render(title, True, TEXT)
        s = small.render(sub, True, TEXT)
        cx = COLS * CELL // 2
        screen.blit(t, t.get_rect(center=(cx, HEIGHT // 2 - 20)))
        screen.blit(s, s.get_rect(center=(cx, HEIGHT // 2 + 25)))


def load_fonts():
    # 优先使用 macOS / Windows / Linux 上常见的中文字体,避免中文显示成方框
    candidates = "pingfangsc,pingfang,heitisc,stheitimedium,arialunicode,microsoftyahei,simhei,notosanscjksc,wenquanyimicrohei"
    path = pygame.font.match_font(candidates)
    def make(size):
        return pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
    return make(18), make(28), make(40)


def main():
    pygame.init()
    pygame.display.set_caption("俄罗斯方块")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    fonts = load_fonts()
    game = Game()

    # 仅左/右/下键支持长按连续移动: key -> 距离下次触发还剩多少毫秒
    repeat_delay, repeat_rate = 160, 45
    held = {}

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                held.pop(event.key, None)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN):
                    held[event.key] = repeat_delay
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if game.game_over:
                    if event.key == pygame.K_r:
                        game.reset()
                    continue
                if event.key == pygame.K_p:
                    game.paused = not game.paused
                    continue
                if game.paused:
                    continue
                if event.key == pygame.K_LEFT:
                    game.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.move(1, 0)
                elif event.key == pygame.K_DOWN:
                    game.soft_drop()
                    game.fall_timer = 0
                elif event.key in (pygame.K_UP, pygame.K_x):
                    game.rotate(1)
                elif event.key == pygame.K_z:
                    game.rotate(-1)
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
                elif event.key == pygame.K_c:
                    game.hold()

        # 处理长按连发
        if not (game.game_over or game.paused):
            for key in list(held):
                held[key] -= dt
                while held[key] <= 0:
                    held[key] += repeat_rate
                    if key == pygame.K_LEFT:
                        game.move(-1, 0)
                    elif key == pygame.K_RIGHT:
                        game.move(1, 0)
                    elif key == pygame.K_DOWN:
                        game.soft_drop()
                        game.fall_timer = 0

        game.update(dt)
        draw(screen, game, fonts)
        pygame.display.flip()


if __name__ == "__main__":
    main()
