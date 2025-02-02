import pygame
import random
import sys
import math
from collections import defaultdict
from pygame import Vector2
from pygame.gfxdraw import filled_polygon, filled_circle

# Инициализация Pygame
pygame.init()

# Настройки окна
WIDTH, HEIGHT = 600, 700
CELL_SIZE = 50
GRID_WIDTH = WIDTH // CELL_SIZE
GRID_HEIGHT = (HEIGHT - 150) // CELL_SIZE  # Увеличили место под интерфейс

# Функция для преобразования hex в RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Цвета
WHITE = hex_to_rgb('#4b3e88')
BLACK = hex_to_rgb('#fff3e7')
RED = hex_to_rgb('#f71a59')
GREEN = hex_to_rgb('#1f448a')
YELLOW = hex_to_rgb('#c1d82f')
BLUE = hex_to_rgb('#008a55')
ORANGE = hex_to_rgb('#a793c6')
PURPLE = hex_to_rgb('#ffc4e3')

# Инициализация экрана
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Три в ряд")
clock = pygame.time.Clock()

# Шрифты
try:
    font = pygame.font.SysFont("Arial", 24, bold=True)
    large_font = pygame.font.SysFont("Arial", 64, bold=True)
except:
    font = pygame.font.Font(None, 24)
    large_font = pygame.font.Font(None, 64)

# Игровые объекты
SHAPES = ['circle', 'square', 'triangle', 'diamond', 'star']
COLORS = {
    'circle': YELLOW,
    'square': GREEN,
    'triangle': RED,
    'diamond': BLUE,
    'star': ORANGE
}

class GameObject:
    def __init__(self, shape, pos):
        self.shape = shape
        self.color = COLORS[shape]
        self.screen_pos = Vector2(pos)
        self.target_pos = Vector2(pos)
        self.animation_progress = 0.0
        self.should_remove = False

    def update(self, dt):
        if self.screen_pos != self.target_pos:
            self.animation_progress = min(self.animation_progress + dt * 8, 1.0)
            self.screen_pos = self.target_pos.lerp(self.screen_pos, 1 - self.animation_progress)

    def draw(self):
        x, y = int(self.screen_pos.x), int(self.screen_pos.y)
        size = CELL_SIZE//2 - 5  # Увеличили размер фигур
        
        if self.shape == 'circle':
            # Круг с градиентом
            for i in range(size, 0, -1):
                alpha = int(255 * (i/size))
                color = (*self.color, alpha)
                filled_circle(screen, x, y, i, color)
                
        elif self.shape == 'square':
            # Квадрат без обводки
            rect = pygame.Rect(x-size, y-size, 2*size, 2*size)
            pygame.draw.rect(screen, self.color, rect)
            
        elif self.shape == 'triangle':
            # Треугольник без обводки
            points = [
                (x, y - size),
                (x - size*0.9, y + size*0.9),
                (x + size*0.9, y + size*0.9)
            ]
            filled_polygon(screen, points, self.color)
            
        elif self.shape == 'diamond':
            # Ромб без обводки
            points = [
                (x, y - size),
                (x + size, y),
                (x, y + size),
                (x - size, y)
            ]
            filled_polygon(screen, points, self.color)
            
        elif self.shape == 'star':
            # Звезда без обводки
            outer_radius = size
            inner_radius = outer_radius * 0.4
            points = []
            for i in range(10):
                angle = math.pi/2 + 2*math.pi*i/10
                radius = inner_radius if i%2 else outer_radius
                points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
            filled_polygon(screen, points, self.color)

class Game:
    def __init__(self, level=1):
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.selected = None
        self.moves = 10 + level * 2
        self.goals = {shape: 5 + level * 2 for shape in SHAPES}
        self.animating = False
        self.match_processor = None
        self.level = level
        self.paused = False  # Добавлен флаг паузы
        self.init_grid()

    def init_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                while True:
                    shape = random.choice(SHAPES)
                    if (x > 0 and self.grid[y][x-1] and self.grid[y][x-1].shape == shape) or \
                       (y > 0 and self.grid[y-1][x] and self.grid[y-1][x].shape == shape):
                        continue
                    break
                pos = self.grid_to_screen((x, y))
                self.grid[y][x] = GameObject(shape, pos)

    def grid_to_screen(self, pos):
        x, y = pos
        return Vector2(x * CELL_SIZE + CELL_SIZE//2, y * CELL_SIZE + CELL_SIZE//2 + 50)

    def find_matches(self):
        matches = set()
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH - 2):
                shapes = [self.grid[y][x+i].shape for i in range(3) if self.grid[y][x+i]]
                if len(set(shapes)) == 1 and len(shapes) == 3:
                    matches.update((x+i, y) for i in range(3))
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT - 2):
                shapes = [self.grid[y+i][x].shape for i in range(3) if self.grid[y+i][x]]
                if len(set(shapes)) == 1 and len(shapes) == 3:
                    matches.update((x, y+i) for i in range(3))
        return matches

    def handle_swap(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2
        self.grid[y1][x1], self.grid[y2][x2] = self.grid[y2][x2], self.grid[y1][x1]
        self.grid[y1][x1].target_pos = self.grid_to_screen((x1, y1))
        self.grid[y2][x2].target_pos = self.grid_to_screen((x2, y2))
        self.match_processor = self.process_matches()
        self.animating = True

    def process_matches(self):
        total_removed = defaultdict(int)
        while True:
            matches = self.find_matches()
            if not matches:
                break
            for x, y in matches:
                if self.grid[y][x]:
                    total_removed[self.grid[y][x].shape] += 1
                    self.grid[y][x].should_remove = True
            self.remove_marked()
            self.fill_empty_spaces()
            yield True
        for shape, count in total_removed.items():
            self.goals[shape] = max(0, self.goals[shape] - count)
        yield False

    def remove_marked(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] and self.grid[y][x].should_remove:
                    self.grid[y][x] = None

    def fill_empty_spaces(self):
        for x in range(GRID_WIDTH):
            fall_height = 0
            for y in range(GRID_HEIGHT-1, -1, -1):
                if self.grid[y][x] is None:
                    fall_height += 1
                else:
                    if fall_height > 0:
                        new_y = y + fall_height
                        self.grid[new_y][x] = self.grid[y][x]
                        self.grid[y][x] = None
                        self.grid[new_y][x].target_pos = self.grid_to_screen((x, new_y))
            for y in range(fall_height):
                while True:
                    shape = random.choice(SHAPES)
                    if (x > 0 and self.grid[y][x-1] and self.grid[y][x-1].shape == shape) or \
                       (y > 0 and self.grid[y-1][x] and self.grid[y-1][x].shape == shape):
                        continue
                    break
                new_obj = GameObject(shape, self.grid_to_screen((x, y - fall_height)))
                new_obj.target_pos = self.grid_to_screen((x, y))
                self.grid[y][x] = new_obj

    def update(self, dt):
        if self.animating:
            self.animate_falling(dt)
            if all(obj.screen_pos == obj.target_pos for row in self.grid for obj in row if obj):
                match_proc = next(self.match_processor)
                if not match_proc:
                    self.animating = False

    def animate_falling(self, dt):
        for row in self.grid:
            for obj in row:
                if obj:
                    obj.update(dt)

def draw_text(text, x, y, color, font_type=font, center=False):
    text_surface = font_type.render(text, True, color)
    if center:
        x -= text_surface.get_width() // 2
        y -= text_surface.get_height() // 2
    screen.blit(text_surface, (x, y))

def main_menu():
    while True:
        screen.fill(BLACK)
        draw_text("GEMS MATCH 3", WIDTH//2, HEIGHT//2 - 100, PURPLE, large_font, center=True)
        draw_text("Нажмите ПРОБЕЛ чтобы начать", WIDTH//2, HEIGHT//2 + 30, WHITE, center=True)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return

def win_screen(level):
    while True:
        screen.fill(BLACK)
        draw_text("Уровень пройден!", WIDTH//2, HEIGHT//2 - 50, WHITE, large_font, center=True)
        draw_text("Нажмите ПРОБЕЛ для следующего уровня", WIDTH//2, HEIGHT//2 + 50, WHITE, center=True)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return level + 1

def lose_screen():
    while True:
        screen.fill(BLACK)
        draw_text("Вы проиграли!", WIDTH//2, HEIGHT//2 - 50, WHITE, large_font, center=True)
        draw_text("Нажмите ПРОБЕЛ для возврата в меню", WIDTH//2, HEIGHT//2 + 50, WHITE, center=True)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return

def game_loop(level):
    game = Game(level)
    running = True
    dt = 0

    while running:
        screen.fill(BLACK)
        
        # Отрисовка игрового поля
        for row in game.grid:
            for obj in row:
                if obj:
                    obj.draw()

        # Отрисовка интерфейса
        pygame.draw.rect(screen, PURPLE, (0, 0, WIDTH, 50))
        draw_text(f"УРОВЕНЬ: {level}", 20, 15, WHITE)
        draw_text(f"ХОДЫ: {game.moves}", WIDTH - 150, 15, WHITE)
        
        # Панель целей
        goal_panel = pygame.Surface((WIDTH, 90))
        goal_panel.fill((PURPLE))
        screen.blit(goal_panel, (0, HEIGHT-90))
        
        x_start = 20
        for i, (shape, count) in enumerate(game.goals.items()):
            obj = GameObject(shape, (x_start + i*100, HEIGHT-70))
            obj.draw()
            draw_text(f"{count}", x_start + i*100 + 25, HEIGHT-50, WHITE, center=True)

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and not game.animating and not game.paused:
                x, y = event.pos
                grid_x = x // CELL_SIZE
                grid_y = (y - 50) // CELL_SIZE  # Учитываем сдвиг игрового поля
                
                if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                    if game.selected:
                        if (abs(grid_x - game.selected[0]) + abs(grid_y - game.selected[1])) == 1:
                            game.handle_swap(game.selected, (grid_x, grid_y))
                            game.moves -= 1
                        game.selected = None
                    else:
                        game.selected = (grid_x, grid_y)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:  # Пауза при нажатии P
                    game.paused = not game.paused

        # Обновление анимаций (если не на паузе)
        if not game.paused:
            game.update(dt)
        
        # Отображение паузы
        if game.paused:
            draw_text("ПАУЗА", WIDTH//2, HEIGHT//2, WHITE, large_font, center=True)
        
        # Проверка завершения уровня
        if all(count <= 0 for count in game.goals.values()):
            return win_screen(level)
        if game.moves <= 0:
            lose_screen()
            return 1  # Возврат к первому уровню

        pygame.display.flip()
        dt = clock.tick(60) / 1000

def main():
    main_menu()
    level = 1
    while True:
        level = game_loop(level)
        if level == 1:  # Если игрок проиграл и вернулся в меню
            main_menu()

if __name__ == "__main__":
    main()