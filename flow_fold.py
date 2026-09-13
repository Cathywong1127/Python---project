"""
Flow & Fold — a color-path puzzle game
----------------------------------------
Connect matching colored dots with a single continuous path.
Paths cannot cross each other. A level is solved only when
every cell on the board is covered by exactly one path.

Controls:
  - Click and drag from a colored dot to draw a path toward
    its matching dot. Drag through adjacent cells only.
  - Release the mouse to stop drawing.
  - Press R to reset the current level.
  - Press N / P to go to the Next / Previous level.
  - Press ESC to quit.

Requires: pygame  (pip install pygame --break-system-packages)
"""

import sys
import pygame

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CELL_SIZE = 70
MARGIN = 40
TOP_UI_HEIGHT = 90
FPS = 60

BG_COLOR = (250, 248, 245)
GRID_LINE_COLOR = (222, 218, 210)
TEXT_COLOR = (60, 55, 50)
PANEL_COLOR = (255, 255, 255)
ACCENT_COLOR = (120, 170, 150)

DOT_RADIUS_RATIO = 0.30
PATH_WIDTH_RATIO = 0.42

COLORS = {
    "R": (231, 111, 81),   # red/terracotta
    "B": (69, 123, 157),   # blue
    "G": (106, 153, 78),   # green
    "Y": (233, 196, 106),  # yellow
    "P": (155, 113, 179),  # purple
    "O": (244, 162, 97),   # orange
}

# ---------------------------------------------------------------------------
# Level data: grid size + dict of color -> [ (r1,c1), (r2,c2) ]
# ---------------------------------------------------------------------------

LEVELS = [
    {
        "size": 5,
        "dots": {
            "R": [(0, 0), (4, 4)],
            "B": [(0, 4), (2, 2)],
            "G": [(4, 0), (2, 1)],
        },
    },
    {
        "size": 5,
        "dots": {
            "R": [(0, 0), (3, 3)],
            "B": [(0, 4), (4, 0)],
            "G": [(1, 1), (4, 4)],
            "Y": [(2, 0), (2, 4)],
        },
    },
    {
        "size": 6,
        "dots": {
            "R": [(0, 0), (5, 5)],
            "B": [(0, 5), (5, 0)],
            "G": [(0, 2), (3, 2)],
            "Y": [(1, 1), (4, 4)],
            "O": [(2, 0), (2, 5)],
        },
    },
    {
        "size": 7,
        "dots": {
            "R": [(0, 0), (6, 6)],
            "B": [(0, 6), (6, 0)],
            "G": [(0, 3), (6, 3)],
            "Y": [(3, 0), (3, 6)],
            "P": [(1, 1), (5, 5)],
            "O": [(1, 5), (5, 1)],
        },
    },
]

# ---------------------------------------------------------------------------
# Game logic
# ---------------------------------------------------------------------------


class Level:
    def __init__(self, data):
        self.size = data["size"]
        self.dots = data["dots"]
        # cell -> color, for quick dot lookup
        self.dot_at = {}
        for color, (a, b) in self.dots.items():
            self.dot_at[a] = color
            self.dot_at[b] = color
        self.reset()

    def reset(self):
        # paths[color] = list of (r,c) cells in order drawn
        self.paths = {color: [] for color in self.dots}
        self.active_color = None

    def cell_owner(self, cell):
        """Return the color that currently occupies this cell, or None."""
        for color, path in self.paths.items():
            if cell in path:
                return color
        return None

    def start_drag(self, cell):
        color = self.dot_at.get(cell)
        if color is None:
            return
        self.active_color = color
        # If clicking an endpoint that already has a path, restart from there
        self.paths[color] = [cell]

    def continue_drag(self, cell):
        if self.active_color is None:
            return
        path = self.paths[self.active_color]
        if not path:
            return
        last = path[-1]

        if cell == last:
            return

        # backtrack: allow retracing over own path
        if len(path) >= 2 and cell == path[-2]:
            path.pop()
            return

        # must be orthogonally adjacent
        if abs(cell[0] - last[0]) + abs(cell[1] - last[1]) != 1:
            return

        # cannot step outside the grid
        if not (0 <= cell[0] < self.size and 0 <= cell[1] < self.size):
            return

        # cannot cross another color's path
        owner = self.cell_owner(cell)
        if owner is not None and owner != self.active_color:
            return

        # cannot revisit own path (no loops)
        if cell in path:
            return

        # if this cell is a dot of a different color, block
        dot_color = self.dot_at.get(cell)
        if dot_color is not None and dot_color != self.active_color:
            return

        # if this cell is the *other* endpoint of the same color, allow and stop after
        path.append(cell)

        if dot_color == self.active_color and len(path) > 1:
            # reached its own matching endpoint - path complete for now
            self.active_color = None

    def end_drag(self):
        self.active_color = None

    def is_path_complete(self, color):
        path = self.paths[color]
        if len(path) < 2:
            return False
        endpoints = set(self.dots[color])
        return path[0] in endpoints and path[-1] in endpoints and path[0] != path[-1]

    def is_solved(self):
        # every path must connect its two dots
        for color in self.dots:
            if not self.is_path_complete(color):
                return False
        # every cell on the board must be covered
        covered = set()
        for path in self.paths.values():
            covered.update(path)
        total_cells = self.size * self.size
        return len(covered) == total_cells


# ---------------------------------------------------------------------------
# Rendering / main loop
# ---------------------------------------------------------------------------


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Flow & Fold")
        self.level_index = 0
        self.level = Level(LEVELS[self.level_index])
        self.font_big = pygame.font.SysFont("arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("arial", 18)
        self.clock = pygame.time.Clock()
        self.resize_window()
        self.dragging = False

    def resize_window(self):
        size = self.level.size
        board_px = size * CELL_SIZE
        width = board_px + MARGIN * 2
        height = board_px + MARGIN * 2 + TOP_UI_HEIGHT
        self.screen = pygame.display.set_mode((width, height))
        self.board_origin = (MARGIN, MARGIN + TOP_UI_HEIGHT)

    def load_level(self, index):
        self.level_index = index % len(LEVELS)
        self.level = Level(LEVELS[self.level_index])
        self.resize_window()

    def cell_from_pixel(self, pos):
        ox, oy = self.board_origin
        x, y = pos
        col = (x - ox) // CELL_SIZE
        row = (y - oy) // CELL_SIZE
        size = self.level.size
        if 0 <= row < size and 0 <= col < size:
            return (int(row), int(col))
        return None

    def cell_center(self, cell):
        ox, oy = self.board_origin
        r, c = cell
        return (ox + c * CELL_SIZE + CELL_SIZE // 2, oy + r * CELL_SIZE + CELL_SIZE // 2)

    # -- drawing --------------------------------------------------------

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_top_ui()
        self.draw_grid()
        self.draw_paths()
        self.draw_dots()
        if self.level.is_solved():
            self.draw_solved_banner()
        pygame.display.flip()

    def draw_top_ui(self):
        title = self.font_big.render("Flow & Fold", True, TEXT_COLOR)
        self.screen.blit(title, (MARGIN, 15))
        info = self.font_small.render(
            f"Level {self.level_index + 1} / {len(LEVELS)}   "
            f"(R: reset   N: next   P: previous   Esc: quit)",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(info, (MARGIN, 52))

    def draw_grid(self):
        size = self.level.size
        ox, oy = self.board_origin
        board_px = size * CELL_SIZE
        panel_rect = pygame.Rect(ox - 6, oy - 6, board_px + 12, board_px + 12)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=12)
        for i in range(size + 1):
            pygame.draw.line(
                self.screen, GRID_LINE_COLOR,
                (ox + i * CELL_SIZE, oy), (ox + i * CELL_SIZE, oy + board_px), 1,
            )
            pygame.draw.line(
                self.screen, GRID_LINE_COLOR,
                (ox, oy + i * CELL_SIZE), (ox + board_px, oy + i * CELL_SIZE), 1,
            )

    def draw_paths(self):
        width = int(CELL_SIZE * PATH_WIDTH_RATIO)
        for color, path in self.level.paths.items():
            if len(path) < 2:
                continue
            rgb = COLORS[color]
            points = [self.cell_center(cell) for cell in path]
            pygame.draw.lines(self.screen, rgb, False, points, width)
            for p in points:
                pygame.draw.circle(self.screen, rgb, p, width // 2)

    def draw_dots(self):
        radius = int(CELL_SIZE * DOT_RADIUS_RATIO)
        for color, (a, b) in self.level.dots.items():
            rgb = COLORS[color]
            for cell in (a, b):
                center = self.cell_center(cell)
                pygame.draw.circle(self.screen, rgb, center, radius)
                pygame.draw.circle(self.screen, TEXT_COLOR, center, radius, 2)

    def draw_solved_banner(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 190))
        self.screen.blit(overlay, (0, 0))
        msg = self.font_big.render("Level solved!  Press N for next level", True, ACCENT_COLOR)
        rect = msg.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
        self.screen.blit(msg, rect)

    # -- main loop --------------------------------------------------------

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.level.reset()
                    elif event.key == pygame.K_n:
                        self.load_level(self.level_index + 1)
                    elif event.key == pygame.K_p:
                        self.load_level(self.level_index - 1)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    cell = self.cell_from_pixel(event.pos)
                    if cell is not None:
                        self.dragging = True
                        self.level.start_drag(cell)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                    self.level.end_drag()
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    cell = self.cell_from_pixel(event.pos)
                    if cell is not None:
                        self.level.continue_drag(cell)

            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
