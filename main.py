import pygame
import random
import math
import time
from collections import deque
import pygame.math

WIDTH = 800
HEIGHT = 600
FPS = 60
TILE_SIZE = 20

DAY_LENGTH = 250
NIGHT_LENGTH = 150
DAY_COLOR = (144, 238, 144)
NIGHT_COLOR = (0, 0, 20)
TRANSITION_DURATION = 10

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)

INITIAL_HERBIVORE_COUNT = 18
INITIAL_PREDATOR_COUNT = 7
INITIAL_FOOD_COUNT = 100
MAX_HERBIVORE_COUNT = 45
MAX_PREDATOR_COUNT = 20
FOOD_SPAWN_PROBABILITY = 0.005

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("EcoSim")
clock = pygame.time.Clock()

def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def normalize(x, y):
    magnitude = math.sqrt(x**2 + y**2)
    if magnitude == 0:
        return 0, 0
    return x / magnitude, y / magnitude

def lerp_color(color1, color2, t):
    r = int(max(0, min(255, color1[0] + (color2[0] - color1[0]) * t)))
    g = int(max(0, min(255, color1[1] + (color2[1] - color1[1]) * t)))
    b = int(max(0, min(255, color1[2] + (color2[2] - color1[2]) * t)))
    return (r, g, b)

class Map:
    def __init__(self, width, height, tile_size):
        self.width = width
        self.height = height
        self.tile_size = tile_size

    def draw(self, screen, background_color):
        screen.fill(background_color)

class ResourceManager:
    """Управление ресурсами (музыка, изображения)."""
    def __init__(self):
        self.sounds = {}
        self.images = {}

    def load_sound(self, name, path):
        if name not in self.sounds:
            self.sounds[name] = pygame.mixer.Sound(path)
        return self.sounds[name]

    def load_image(self, name, path):
        if name not in self.images:
            self.images[name] = pygame.image.load(path).convert_alpha()
        return self.images[name]

class EatingCross:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hunger = 100
        self.color = YELLOW
        self.timer = 0
        self.max_timer = 60
        self.position = pygame.math.Vector2(x, y)

    def update(self, dt):
        self.timer += dt

    def draw(self, screen):
        size = 15
        pygame.draw.line(screen, self.color, (self.x - size, self.y), (self.x + size, self.y), 3)
        pygame.draw.line(screen, self.color, (self.x, self.y - size), (self.x, self.y + size), 3)

class DayNightCycle:
    def __init__(self, day_length, night_length, transition_duration):
        self.day_length = day_length
        self.night_length = night_length
        self.transition_duration = transition_duration
        self.cycle_duration = day_length + night_length + 2 * transition_duration
        self.timer = 0
        self.time_scale = 1

    def update(self, dt):
        self.timer = (self.timer + dt * self.time_scale) % self.cycle_duration

    def get_time_progress(self):
        return self.timer / self.cycle_duration

    def is_day(self):
        return self.transition_duration <= self.timer <= (self.transition_duration + self.day_length)

    def get_background_color(self):
        time_progress = self.timer

        if time_progress < self.transition_duration:
            t = time_progress / self.transition_duration
            t = (math.sin(t * math.pi / 2))
            return lerp_color(NIGHT_COLOR, DAY_COLOR, t)
        elif time_progress < self.transition_duration + self.day_length:
            return DAY_COLOR
        elif time_progress < self.transition_duration + self.day_length + self.transition_duration:
            t = (time_progress - self.transition_duration - self.day_length) / self.transition_duration
            t = (math.sin(t * math.pi / 2))
            return lerp_color(DAY_COLOR, NIGHT_COLOR, t)
        else:
            return NIGHT_COLOR

class Entity(pygame.sprite.Sprite):
    """Базовый класс для всех сущностей в экосистеме."""
    def __init__(self, x, y, speed, size, max_health, max_hunger, max_thirst, color, lifespan=None):
        super().__init__()
        self.position = pygame.math.Vector2(x, y)
        self.speed = speed
        self.max_speed = speed
        self.size = size
        self.health = max_health
        self.max_health = max_health
        self.hunger = 0
        self.max_hunger = max_hunger
        self.thirst = 0
        self.max_thirst = max_thirst
        self.sleep = 0
        self.max_sleep = 100
        self.is_asleep = False
        self.color = color
        self.target = None
        self.reproductive_drive = 0
        self.reproductive_ready = False
        self.time_to_reproduce = 400
        self.energy_loss_rate = 0.08
        self.thirst_loss_rate = 0.2
        self.wander_timer = 0
        self.wander_interval = random.randint(3, 8)
        self.wander_target = None
        self.is_baby = False
        self.baby_growth_rate = 0.01
        self.max_size = size
        self.edge_avoidance_distance = 40
        self.font = pygame.font.Font(None, 20)
        self.hunger_threshold_eat = self.max_hunger / 4
        self.thirst_threshold_drink = self.max_thirst / 4
        self.reproduction_threshold = self.time_to_reproduce / 2
        self.is_drinking = False
        self.drink_timer = 0
        self.max_drink_time = 3
        self.is_escaping = False
        self.escape_timer = 0
        self.escape_duration = 2
        self.reproduction_cooldown = 0
        self.reproduction_cooldown_max = 100
        self.avoidance_distance = 100
        self.fleeing_speed_multiplier = 1.5
        self.age = 0
        self.max_age = lifespan
        self.growth_time = 0
        self.move_direction = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.rect = pygame.Rect(int(self.position.x - self.size), int(self.position.y - self.size), 2 * self.size, 2 * self.size)
        self.is_colliding_with_edge = False

    @property
    def x(self):
        return self.position.x

    @x.setter
    def x(self, value):
        self.position.x = value
        self.rect.center = (int(self.position.x), int(self.position.y))  

    @property
    def y(self):
        return self.position.y

    @y.setter
    def y(self, value):
        self.position.y = value
        self.rect.center = (int(self.position.x), int(self.position.y))


    def update(self, dt, ecosystem):
        """Обновляет состояние сущности."""
        is_day = ecosystem.day_night_cycle.is_day()

        if isinstance(self, Herbivore):
            if is_day:
                pass
            else:
                self.is_asleep = True
                self.sleep = 0

            if self.max_age is None:
                self.max_age = 700

        elif isinstance(self, Predator):
            if is_day:
                self.is_asleep = True
                self.sleep = 0
            else:
                pass

            if self.max_age is None:
                self.max_age = 500

        self.age += dt

        if self.is_asleep:
            self.sleep += dt * 2
            if self.sleep >= self.max_sleep:
                self.is_asleep = False
            return

        hunger_loss = 0
        thirst_loss = 0

        if isinstance(self, Herbivore):
            if is_day:
                hunger_loss = self.energy_loss_rate * dt
                thirst_loss = self.thirst_loss_rate * dt
            else:
                hunger_loss = (self.energy_loss_rate / 4) * dt
                thirst_loss = (self.thirst_loss_rate / 4) * dt
        elif isinstance(self, Predator):
            if not is_day:
                hunger_loss = self.energy_loss_rate * dt
                thirst_loss = self.thirst_loss_rate * dt
            else:
                hunger_loss = (self.energy_loss_rate / 4) * dt
                thirst_loss = (self.thirst_loss_rate / 4) * dt

        self.hunger += hunger_loss
        self.thirst += thirst_loss

        if self.hunger >= self.max_hunger or self.thirst >= self.max_thirst:
            self.health -= 1 * dt

        if self.max_age is not None and self.age >= self.max_age:
            ecosystem.remove_entity(self)
            return

        if self.health <= 0:
            ecosystem.remove_entity(self)
            return

        if self.thirst >= self.max_thirst * 1.5:
            ecosystem.remove_entity(self)
            return

        hunger_factor = min(1, self.hunger / self.max_hunger / 2)
        speed_reduction = hunger_factor
        current_speed = self.max_speed * (1 - speed_reduction)

        if self.is_escaping:
            current_speed = self.max_speed * self.fleeing_speed_multiplier

        self.speed = current_speed

        if self.is_escaping:
            self.escape_timer += dt
            if self.escape_timer >= self.escape_duration:
                self.is_escaping = False
                self.escape_timer = 0
                return

        if self.is_baby:
            if self.size < self.max_size:
                self.size += self.baby_growth_rate * dt * 30
            else:
                self.is_baby = False

        if self.is_drinking:
            self.drink_timer += dt
            if self.drink_timer >= self.max_drink_time:
                self.is_drinking = False
                self.drink_timer = 0
                self.thirst = 0
                self.target = None
                return
        else:
            self.avoid_water(ecosystem.water_sources, dt, ecosystem.entities)

        # Движение к цели
        if self.target:
            if isinstance(self.target, tuple):
                target_x, target_y = self.target
            else:
                target_x, target_y = self.target.x, self.target.y

            dx, dy = normalize(target_x - self.x, target_y - self.y)
            self.move_direction = pygame.math.Vector2(dx, dy)

            self.position += self.move_direction * self.speed * dt

            if self.target and distance(self.x, self.y, target_x, target_y) <= 10:
                self.on_target_reached(ecosystem)

        else:
            if (isinstance(self, Herbivore) and is_day) or (isinstance(self, Predator) and not is_day):
                self.wander(dt, ecosystem.map)

            self.position += self.move_direction * self.speed * dt

        if self.reproductive_drive >= self.time_to_reproduce:
            self.reproductive_ready = True

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= dt

        self.check_for_food_and_water(dt, ecosystem)
        self.avoid_other_entities(dt, ecosystem.entities, is_day)

        # Добавлено: перенос через границы карты
        self.position.x = self.position.x % ecosystem.map.width
        self.position.y = self.position.y % ecosystem.map.height
        self.rect.center = (int(self.position.x), int(self.position.y))

    def avoid_other_entities(self, dt, entities, is_day):
        """Избегает столкновений с другими сущностями."""
        pass


    def avoid_edges(self, map_obj):
        """Избегает выхода за границы карты."""
        avoidance_distance = self.size + 20
        avoid_vector = pygame.math.Vector2(0, 0)

        if self.x - self.size / 2 < avoidance_distance:
            avoid_vector.x = (avoidance_distance - (self.x - self.size / 2))
        elif self.x + self.size / 2 > map_obj.width - avoidance_distance:
            avoid_vector.x = (map_obj.width - avoidance_distance - (self.x + self.size / 2))
        elif self.y - self.size / 2 < avoidance_distance:
            avoid_vector.y = (avoidance_distance - (self.y - self.size / 2))
        elif self.y + self.size / 2 > map_obj.height - avoidance_distance:
            avoid_vector.y = (map_obj.height - avoidance_distance - (self.y + self.size / 2))

        if avoid_vector != (0, 0):
            return avoid_vector.normalize()
        else:
            return None

    def avoid_water(self, water_sources, dt, entities):
        """Избегает приближения к воде, если поблизости есть хищники (для травоядных)."""
        if not self.target or not isinstance(self.target, Water):
            for water in water_sources:
                dist_to_water = distance(self.x, self.y, water.x, water.y)

                is_blocked = False
                for entity in entities:
                    if isinstance(entity, Predator) and isinstance(self, Herbivore):
                        dist_to_predator = distance(self.x, self.y, entity.x, entity.y)
                        if  dist_to_predator < self.fear_distance:
                            is_blocked = True
                            break

                if not is_blocked and dist_to_water < water.size + self.size + 10:
                    dx, dy = normalize(self.x - water.x, self.y - water.y)
                    self.position += pygame.math.Vector2(dx, dy) * self.speed * dt * 3
                    self.rect.center = (int(self.position.x), int(self.position.y)) 

    def wander(self, dt, map_obj):
        """Заставляет сущность беспорядочно бродить по карте."""
        self.wander_timer += dt
        if self.wander_timer >= self.wander_interval or self.wander_target is None or distance(self.x, self.y, self.wander_target[0], self.wander_target[1]) <= 10:
            self.wander_timer = 0
            self.wander_interval = random.randint(3, 8)
            self.wander_target = (random.randint(20, map_obj.width - 20), random.randint(20, map_obj.height - 20))

        dx, dy = normalize(self.wander_target[0] - self.x, self.wander_target[1] - self.y)
        self.move_direction = pygame.math.Vector2(dx, dy) 

        self.position += self.move_direction * self.speed * dt
        self.rect.center = (int(self.position.x), int(self.position.y))

    def on_target_reached(self, ecosystem):
        """Выполняет действия, когда сущность достигает своей цели."""
        if isinstance(self.target, Food):
            if self.target in ecosystem.resources:
                self.hunger = 0
                ecosystem.remove_resource(self.target)
            self.target = None
        elif isinstance(self.target, Water):
            self.is_drinking = True
        elif self.target and type(self.target) is tuple:
            self.target = None

    def draw(self, screen):
        """Отрисовывает сущность на экране."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

    def draw_info(self, screen):
        """Отрисовывает информацию о сущности на экране."""
        text_surface = self.font.render(
            f"Здоровье: {int(self.health)}/{self.max_health}, Голод: {int(self.hunger)}/{self.max_hunger}, Жажда: {int(self.thirst)}/{self.max_thirst}, Возраст: {int(self.age)}/{self.max_age}, Готов к размножению: {'Да' if self.reproductive_ready else 'Нет'}",
            True, WHITE
        )
        text_rect = text_surface.get_rect(center=(int(self.x), int(self.y) - 20))
        screen.blit(text_surface, text_rect)

    def find_reproduction_target(self, entities):
        """Находит подходящего партнера для размножения."""
        closest_mate = None
        min_distance = float('inf')
        for entity in entities:
            if type(entity) == type(self) and entity != self and entity.reproductive_ready and entity.reproduction_cooldown <= 0:
                dist = distance(self.x, self.y, entity.x, entity.y)
                if dist < min_distance:
                    min_distance = dist
                    closest_mate = entity
        return closest_mate

    def find_water_target(self, water_sources):
        """Находит ближайший источник воды."""
        closest_water = None
        min_distance = float('inf')
        for water in water_sources:
            dist = distance(self.x, self.y, water.x, water.y)
            if dist < min_distance:
                min_distance = dist
                closest_water = water
        return closest_water

    def find_nearest(self, items):
        """Находит ближайший объект из списка."""
        nearest = None
        min_distance = float('inf')
        for item in items:
            dist = distance(self.x, self.y, item.x, item.y)
            if dist < min_distance:
                min_distance = dist
                nearest = item
        return nearest

class Predator(Entity):
    """Класс, представляющий хищника."""
    MAX_PREDATORS = 20

    def __init__(self, x, y):
        """Инициализирует хищника с заданными параметрами."""
        super().__init__(x, y, 10, 10, 100, 40, 60, RED, lifespan=1200)
        self.attack_damage = 30
        self.growth_time = 0
        self.is_baby = False
        self.time_to_reproduce = 50
        self.vision_range = 200
        self.hunt_range = 120
        self.target_search_interval = 2
        self.last_target_search = 0
        self.hunger_threshold_attack = 6
        self.eating_cross = None
        self.chase_timer = 0
        self.max_chase_time = 30
        self.patrol_timer = 0
        self.patrol_interval = random.randint(2, 6)
        self.eat_timer = 0
        self.eat_interval = 20
        self.eating_crosses = deque(maxlen=5)
        self.is_eating_cross = False
        self.has_eaten_cross = True
        self.eat_efficiency = 0.75
        self.wake_up_delay = random.uniform(0, 50)
        self.avoid_predator_timer = 0
        self.avoid_predator_duration = 20
        self.hunger_desperation_threshold = self.max_hunger * 0.75

    def find_target(self, ecosystem, is_day):
        """Находит цель для охоты (травоядное)."""
        if self.is_drinking or self.reproductive_ready or is_day == True:
            return None

        if self.hunger < self.hunger_threshold_attack:
            return None

        closest_herbivore = None
        min_distance = float('inf')
        for entity in ecosystem.entities:
            if isinstance(entity, Herbivore):
                dist = distance(self.x, self.y, entity.x, entity.y)
                if dist < min_distance and dist <= self.hunt_range:
                    min_distance = dist
                    closest_herbivore = entity
        return closest_herbivore

    def on_target_reached(self, ecosystem):
        """Выполняет действия, когда хищник достигает своей цели."""
        if isinstance(self.target, Herbivore) and self.hunger > self.hunger_threshold_attack:
            self.attack(ecosystem)
            self.target = None
        elif isinstance(self.target, Water):
            self.is_drinking = True
        elif isinstance(self.target, EatingCross) and self.is_eating_cross:
            self.try_eat(ecosystem)
            self.target = None
        elif self.target and self.reproductive_ready and type(self.target) == type(self):
            self.check_reproduce(ecosystem)
        elif self.target and type(self.target) is tuple:
            self.target = None

    def update(self, dt, ecosystem):
        """Обновляет состояние хищника."""
        now = pygame.time.get_ticks() / 1000.0

        is_day = ecosystem.day_night_cycle.is_day()

        if not is_day and self.is_asleep:
            if self.wake_up_delay <= 0:
                self.is_asleep = False
                self.sleep = 0
            else:
                self.wake_up_delay -= dt
                return

        if now - self.last_target_search >= self.target_search_interval:
            self.last_target_search = now
            if not self.target or not isinstance(self.target, Herbivore) or self.target not in ecosystem.entities:
                self.target = self.find_target(ecosystem, is_day)
                self.chase_timer = 0

        if self.hunger >= self.hunger_desperation_threshold:
            self.target = self.find_target(ecosystem, is_day)
            if self.target:
                super().update(dt, ecosystem)
                return

        if self.reproductive_ready and not self.target:
            self.target = self.find_reproduction_target(ecosystem.entities)
            if self.target:
                super().update(dt, ecosystem)
                return

        if not self.target and not self.is_drinking and is_day == False:
            self.patrol(dt, ecosystem.map)

        if self.target and isinstance(self.target, Herbivore):
            self.chase_timer += dt
            if self.chase_timer >= self.max_chase_time:
                self.target = None
                self.chase_timer = 0

        super().update(dt, ecosystem)

        self.reproductive_drive += dt / 2
        if self.reproductive_drive >= self.reproduction_threshold:
            self.check_reproduce(ecosystem)

        if self.is_baby:
            self.growth_time += dt
            if self.growth_time >= 300:
                self.size = self.max_size
                self.is_baby = False

        self.avoid_water(ecosystem.water_sources, dt, ecosystem.entities)

        if self.hunger > self.max_hunger / 2 and is_day == False:
            self.is_asleep = False

        if self.eating_cross and self.eating_cross.hunger <= 0:
            self.eating_cross = None
            self.is_eating_cross = False
            self.has_eaten_cross = True

        if self.hunger <= self.hunger_threshold_attack:
            self.is_eating_cross = False
        elif not self.is_eating_cross:
            self.eat_timer += dt
            if self.eat_timer >= self.eat_interval:
                self.eat_timer = 0
                self.try_eat(ecosystem)

        if self.avoid_predator_timer > 0:
            self.avoid_predator_timer -= dt

    def patrol(self, dt, map_obj):
        """Патрулирует территорию в поисках добычи."""
        self.wander(dt, map_obj)

    def attack(self, ecosystem):
        """Атакует травоядное."""
        if self.target and self.target in ecosystem.entities and distance(self.x, self.y, self.target.x, self.target.y) < self.size + self.target.size + 10:
            self.create_eating_cross(self.target, ecosystem.map)
            self.target.die(ecosystem)
            self.target = None
            self.hunger = max(0, self.hunger - self.max_hunger * self.eat_efficiency)

    def try_eat(self, ecosystem):
        """Пытается съесть труп или атаковать травоядное."""
        if self.is_eating_cross and self.eating_cross:
            eat_amount = min(10, self.eating_cross.hunger)
            self.eating_cross.hunger -= eat_amount
            self.hunger = max(0, self.hunger - eat_amount)

            if self.eating_cross.hunger <= 0:
                self.hunger = max(0, self.hunger - self.max_hunger * self.eat_efficiency)
                self.eating_cross = None
                self.eating_crosses.clear()
                self.is_eating_cross = False
                return
            return
        else:
            closest_cross = self.find_nearest(self.eating_crosses)
            if closest_cross:
                self.target = closest_cross
                self.is_eating_cross = True
                return
            closest_herbivore = None
            min_distance = float('inf')
            for entity in ecosystem.entities:
                if isinstance(entity, Herbivore):
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10 and self.hunger > self.hunger_threshold_attack:
                        min_distance = dist
                        closest_herbivore = entity
            if closest_herbivore and self.hunger > self.hunger_threshold_attack:
                self.create_eating_cross(closest_herbivore, ecosystem.map)
                closest_herbivore.die(ecosystem)
                self.is_eating_cross = True

    def avoid_other_entities(self, dt, entities, is_day):
        """Избегает других сущностей."""
        if self.avoid_predator_timer > 0:
            for entity in entities:
                if entity != self and isinstance(entity, Predator):
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < self.avoidance_distance:
                        dx, dy = normalize(self.x - entity.x, self.y - entity.y)
                        self.position += pygame.math.Vector2(dx, dy) * self.speed * dt * 3
                        self.rect.center = (int(self.position.x), int(self.position.y))  

    def create_eating_cross(self, herbivore, map_obj):
        """Создает труп травоядного после атаки."""
        eating_cross = EatingCross(herbivore.x, herbivore.y)
        self.eating_cross = eating_cross
        self.eating_crosses.append(eating_cross)

    def check_reproduce(self, ecosystem):
        """Проверяет возможность размножения."""
        predator_count = sum(1 for entity in ecosystem.entities if isinstance(entity, Predator))
        if predator_count >= Predator.MAX_PREDATORS:
            return
        if self.reproductive_ready and self.reproduction_cooldown <= 0:
            closest_predator = None
            min_distance = float('inf')
            for entity in ecosystem.entities:
                if isinstance(entity, Predator) and entity != self:
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10:
                        min_distance = dist
                        closest_predator = entity

            if closest_predator and closest_predator.reproduction_cooldown <= 0:
                if self.growth_time == 0 and closest_predator.growth_time == 0:
                    self.reproduce(ecosystem, closest_predator)

    def reproduce(self, ecosystem, other):
        """Размножается с другим хищником."""
        predator_count = sum(1 for entity in ecosystem.entities if isinstance(entity, Predator))
        if predator_count >= Predator.MAX_PREDATORS:
            return

        if self.reproductive_ready and other.reproductive_ready:
            new_predator = Predator(self.x, self.y)
            new_predator.size = (self.size + other.size) / 4
            new_predator.max_size = min(self.size, other.size)
            new_predator.is_baby = True
            new_predator.growth_time = 0
            ecosystem.add_entity(new_predator)

            dx, dy = normalize(new_predator.x - self.x, new_predator.y - self.y)
            separation_distance = 200

            new_predator.target = (new_predator.x + dx * separation_distance, new_predator.y + dy * separation_distance)
            self.target = (self.x - dx * separation_distance, self.y - dy * separation_distance)
            other.target = (other.x - dx * separation_distance, other.y - dy * separation_distance)

            self.reproductive_drive = 0
            self.reproductive_ready = False
            self.reproduction_cooldown = self.reproduction_cooldown_max
            other.reproductive_drive = 0
            other.reproductive_ready = False
            other.reproduction_cooldown = other.reproduction_cooldown_max

            self.avoid_predator_timer = self.avoid_predator_duration
            other.avoid_predator_timer = other.avoid_predator_duration

    def check_for_food_and_water(self, dt, ecosystem):
        """Проверяет наличие пищи и воды и устанавливает цели для их поиска."""
        is_day = ecosystem.day_night_cycle.is_day()
        if not self.target:
            if isinstance(self, Predator):
                if self.hunger > self.hunger_threshold_eat:
                    self.target = self.find_target(ecosystem, is_day)
                elif self.thirst > self.thirst_threshold_drink:
                    self.target = self.find_water_target(ecosystem.water_sources)
                elif self.reproductive_ready:
                    self.target = self.find_reproduction_target(ecosystem.entities)
            else:
                if self.thirst > self.thirst_threshold_drink:
                    self.target = self.find_water_target(ecosystem.water_sources)
                elif self.hunger > self.hunger_threshold_eat:
                    self.target = self.find_target(ecosystem, is_day)

class Herbivore(Entity):
    """Класс, представляющий травоядное."""

    def __init__(self, x, y):
        """Инициализирует травоядное с заданными параметрами."""
        super().__init__(x, y, 7, 10, 70, 70, 60, GREEN, lifespan=2000)
        self.fear_distance = 45
        self.time_to_reproduce = 120
        self.target_eat_distance = 25
        self.target_drink_distance = 25
        self.fleeing_speed_multiplier = 5
        self.hunt_range = 50
        self.avoid_predator_timer = 0
        self.avoid_predator_duration = 20
        self.wake_up_delay = random.uniform(0, 50)

    def find_target(self, ecosystem):
        """Находит цель для еды (пищу)."""
        is_day = ecosystem.day_night_cycle.is_day()
        if not is_day:
            return None
        closest_food = None
        min_distance = float('inf')
        for resource in ecosystem.resources:
            if isinstance(resource, Food):
                dist = distance(self.x, self.y, resource.x, resource.y)
                if dist < min_distance:
                    min_distance = dist
                    closest_food = resource

        return closest_food

    def update(self, dt, ecosystem):
        """Обновляет состояние травоядного."""
        edge_avoidance_vector = self.avoid_edges(ecosystem.map)
        is_day = ecosystem.day_night_cycle.is_day()

        if is_day and self.is_asleep:
            if self.wake_up_delay <= 0:
                self.is_asleep = False
                self.sleep = 0
            else:
                self.wake_up_delay -= dt
                return

        if edge_avoidance_vector:
            self.position += edge_avoidance_vector * self.speed * dt * 5
            self.rect.center = (int(self.position.x), int(self.position.y))
            return

        if self.reproductive_ready and not self.target:
            self.target = self.find_reproduction_target(ecosystem.entities)

        if self.is_drinking:
            super().update(dt, ecosystem)
            return

        if not self.target or (self.target and not isinstance(self.target, Water)):
            if self.thirst > self.thirst_threshold_drink:
                self.target = self.find_water_target(ecosystem.water_sources)
            elif self.hunger > self.hunger_threshold_eat:
                self.target = self.find_target(ecosystem)
        elif not self.target:
            self.wander(dt, ecosystem.map)

        super().update(dt, ecosystem)

        self.reproductive_drive += dt
        if self.reproductive_drive >= self.reproduction_threshold:
            self.check_reproduce(ecosystem)

    def on_target_reached(self, ecosystem):
        """Выполняет действия, когда травоядное достигает своей цели."""
        if isinstance(self.target, Food):
            if self.target in ecosystem.resources and distance(self.x, self.y, self.target.x,
                                                               self.target.y) < self.target_eat_distance:
                self.hunger = 0
                ecosystem.remove_resource(self.target)
            self.target = None
        elif isinstance(self.target, Water):
            if distance(self.x, self.y, self.target.x, self.target.y) < self.target_drink_distance:
                self.is_drinking = True
        elif self.target and self.reproductive_ready and type(self.target) == type(self):
            self.check_reproduce(ecosystem)
        elif self.target and type(self.target) is tuple:
            self.target = None

    def check_reproduce(self, ecosystem):
        """Проверяет возможность размножения."""
        if self.reproductive_ready and self.reproduction_cooldown <= 0:
            closest_herbivore = None
            min_distance = float('inf')
            for entity in ecosystem.entities:
                if isinstance(entity, Herbivore) and entity != self:
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10:
                        min_distance = dist
                        closest_herbivore = entity

            if closest_herbivore and closest_herbivore.reproduction_cooldown <= 0:
                if self.growth_time == 0 and closest_herbivore.growth_time == 0:
                    self.reproduce(ecosystem, closest_herbivore)

    def reproduce(self, ecosystem, other):
        """Размножается с другим травоядным."""
        herbivore_count = sum(1 for entity in ecosystem.entities if isinstance(entity, Herbivore))
        if herbivore_count >= MAX_HERBIVORE_COUNT:
            return

        if self.reproductive_ready and other.reproductive_ready:
            new_herbivore = Herbivore(self.x, self.y)
            new_herbivore.size = (self.size + other.size) / 4
            new_herbivore.max_size = min(self.size, other.size)
            new_herbivore.is_baby = True
            new_herbivore.growth_time = 0
            ecosystem.add_entity(new_herbivore)

            dx, dy = normalize(new_herbivore.x - self.x, new_herbivore.y - self.y)
            separation_distance = 200

            new_herbivore.target = (new_herbivore.x + dx * separation_distance,
                                    new_herbivore.y + dy * separation_distance)
            self.target = (self.x - dx * separation_distance, self.y - dy * separation_distance)
            other.target = (other.x - dx * separation_distance, other.y - dy * separation_distance)

            self.reproductive_drive = 0
            self.reproductive_ready = False
            self.reproduction_cooldown = self.reproduction_cooldown_max
            other.reproductive_drive = 0
            other.reproductive_ready = False
            other.reproduction_cooldown = other.reproduction_cooldown_max

            self.avoid_predator_timer = self.avoid_predator_duration

    def check_for_food_and_water(self, dt, ecosystem):
        """Проверяет наличие пищи и воды и устанавливает цели для их поиска."""
        is_day = ecosystem.day_night_cycle.is_day()

        if not self.target:
            if isinstance(self, Herbivore):
                if self.thirst > self.thirst_threshold_drink:
                    self.target = self.find_water_target(ecosystem.water_sources)
                elif self.hunger > self.hunger_threshold_eat and is_day:
                    self.target = self.find_target(ecosystem)
            else:
                if self.thirst > self.thirst_threshold_drink:
                    self.target = self.find_water_target(ecosystem.water_sources)
                elif self.hunger > self.hunger_threshold_eat:
                    self.target = self.find_target(ecosystem)

    def die(self, ecosystem):
        """Удаляет травоядное из экосистемы."""
        ecosystem.remove_entity(self)

class Ecosystem:
    """Контейнер для всех сущностей и ресурсов."""
    def __init__(self, map_width, map_height):
        self.entities = []
        self.resources = []
        self.water_sources = []
        self.map = Map(map_width, map_height, 20)
        self.day_night_cycle = DayNightCycle(DAY_LENGTH, NIGHT_LENGTH, TRANSITION_DURATION)

    def add_entity(self, entity):
        self.entities.append(entity)

    def remove_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def add_resource(self, resource):
        self.resources.append(resource)

    def remove_resource(self, resource):
        if resource in self.resources:
            self.resources.remove(resource)

    def add_water_source(self, water):
        self.water_sources.append(water)

    def remove_water_source(self, water):
        if water in self.water_sources:
            self.water_sources.remove(water)

class Food:
    """Класс, представляющий еду."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 5
        self.color = BROWN

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)

class Water:
    """Класс, представляющий источник воды."""
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.color = BLUE

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)

class Game:
    """Основной класс игры."""
    def __init__(self, width, height):
        """Инициализирует игру."""
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("EcoSim")
        self.clock = pygame.time.Clock()
        self.is_running = True
        self.ecosystem = Ecosystem(width, height)
        self.resource_manager = ResourceManager()
        self.debug_font = pygame.font.Font(None, 20)
        self.last_fps_update = time.time()
        self.fps = 0
        self.frame_count = 0
        self.show_entity_info = False
        self.is_paused = False
        self.entity_count_pos = (10, 40)
        self.create_initial_entities()
        self.create_initial_resources()
        self.create_initial_water_sources()

    def create_initial_entities(self):
        """Создает начальные сущности (травоядные, хищники)."""
        for _ in range(INITIAL_HERBIVORE_COUNT):
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height - 50)
            self.ecosystem.add_entity(Herbivore(x, y))

        for _ in range(INITIAL_PREDATOR_COUNT):
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height - 50)
            self.ecosystem.add_entity(Predator(x, y))

    def create_initial_resources(self):
        """Создает начальные ресурсы (еду)."""
        for _ in range(INITIAL_FOOD_COUNT):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            self.ecosystem.add_resource(Food(x, y))

    def create_initial_water_sources(self):
        """Создает начальные источники воды."""
        self.ecosystem.add_water_source(Water(self.width // 4, self.height // 4, 30))
        self.ecosystem.add_water_source(Water(3 * self.width // 4, 3 * self.height // 4, 40))

    def handle_input(self):
        """Обрабатывает ввод пользователя."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.show_entity_info = not self.show_entity_info
                elif event.key == pygame.K_p:
                    self.is_paused = not self.is_paused  
                elif event.key == pygame.K_f: 
                    x = random.randint(0, self.width)
                    y = random.randint(0, self.height)
                    self.ecosystem.add_resource(Food(x, y))
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.ecosystem.day_night_cycle.time_scale *= 1.1
                elif event.key == pygame.K_MINUS: 
                    self.ecosystem.day_night_cycle.time_scale /= 1.1
                elif event.key == pygame.K_1:
                    self.ecosystem.day_night_cycle.time_scale = 1

    def update(self, dt):
        """Обновляет состояние игры."""
        if self.is_paused:  
            return

        self.ecosystem.day_night_cycle.update(dt)

        for entity in self.ecosystem.entities:
            entity.update(dt, self.ecosystem)

        if random.random() < FOOD_SPAWN_PROBABILITY:
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            self.ecosystem.add_resource(Food(x, y))

        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_update >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_update = current_time

    def draw(self):
        """Отрисовывает игру на экране."""
        background_color = self.ecosystem.day_night_cycle.get_background_color()
        self.ecosystem.map.draw(self.screen, background_color)

        for food in self.ecosystem.resources:
            food.draw(self.screen)

        for water in self.ecosystem.water_sources:
            water.draw(self.screen)

        for entity in self.ecosystem.entities:
            entity.draw(self.screen)
            if self.show_entity_info:
                entity.draw_info(self.screen)

        fps_text = self.debug_font.render(f"FPS: {self.fps}", True, WHITE)
        self.screen.blit(fps_text, (10, 10))

        herbivore_count = sum(1 for entity in self.ecosystem.entities if isinstance(entity, Herbivore))
        predator_count = sum(1 for entity in self.ecosystem.entities if isinstance(entity, Predator))
        entity_count_text = self.debug_font.render(
            f"Травоядные: {herbivore_count}, Хищники: {predator_count}", True, WHITE
        )
        self.screen.blit(entity_count_text, self.entity_count_pos)

        if self.is_paused:
            pause_text = self.debug_font.render("PAUSED", True, WHITE)
            text_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(pause_text, text_rect)

        pygame.display.flip()

    def run(self):
        """Запускает основной цикл игры."""
        while self.is_running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    game = Game(WIDTH, HEIGHT)
    game.run()
