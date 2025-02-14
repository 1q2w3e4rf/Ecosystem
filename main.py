import pygame
import random
import math

# Инициализация Pygame
pygame.init()

# Размеры окна
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Экосистема")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
LIGHT_GREEN = (144, 238, 144)
YELLOW = (255,255,0)

# Константы игры
FPS = 60
TILE_SIZE = 20

DAY_LENGTH = 150
NIGHT_LENGTH = 75
DAY_COLOR = LIGHT_GREEN
NIGHT_COLOR = (0, 0, 20)
TRANSITION_DURATION = 10

# Функции помощники
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

class Entity:
    """Базовый класс для всех сущностей в экосистеме."""
    def __init__(self, x, y, speed, size, max_health, max_hunger, max_thirst, color, lifespan=None):
        """Инициализирует сущность с заданными параметрами."""
        self.x = x
        self.y = y
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
        self.move_direction = (random.uniform(-1, 1), random.uniform(-1, 1))

        self.is_colliding_with_edge = False

    def update(self, dt, entities, resources, map_obj, water_sources, day_night_cycle):
        """Обновляет состояние сущности."""
        is_day = day_night_cycle.is_day()

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

        hunger_loss = 0  # Инициализация hunger_loss
        thirst_loss = 0  # Инициализация thirst_loss

        # ИЗМЕНЕНО: Уменьшаем потребление ресурсов ночью для травоядных
        if isinstance(self, Herbivore):
            if is_day:
                hunger_loss = self.energy_loss_rate * dt
                thirst_loss = self.thirst_loss_rate * dt
            else:
                hunger_loss = (self.energy_loss_rate / 4) * dt  # Значительно меньше ночью
                thirst_loss = (self.thirst_loss_rate / 4) * dt # Значительно меньше ночью
        elif isinstance(self, Predator):
            if not is_day:
                hunger_loss = self.energy_loss_rate * dt
                thirst_loss = self.thirst_loss_rate * dt
            else:
                hunger_loss = (self.energy_loss_rate / 4) * dt  # Значительно меньше ночью
                thirst_loss = (self.thirst_loss_rate / 4) * dt # Значительно меньше ночью

        self.hunger += hunger_loss
        self.thirst += thirst_loss

        if self.hunger >= self.max_hunger or self.thirst >= self.max_thirst:
            self.health -= 1 * dt

        if self.max_age is not None and self.age >= self.max_age:
            entities.remove(self)
            return

        if self.health <= 0:
            entities.remove(self)
            return
        if self.thirst >= self.max_thirst * 1.5:
            entities.remove(self)
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
            self.avoid_water(water_sources, dt, entities)

        if self.target:
            if isinstance(self.target, tuple):
                target_x, target_y = self.target
            else:
                target_x, target_y = self.target.x, self.target.y
            dx, dy = normalize(target_x - self.x, target_y - self.y)
            self.x += dx * self.speed * dt
            self.y += dy * self.speed * dt

            if self.target and distance(self.x, self.y, target_x, target_y) <= 10:
                self.on_target_reached(entities, resources, map_obj)

        else:
            if (isinstance(self, Herbivore) and is_day) or (isinstance(self, Predator) and not is_day):
                self.wander(dt, map_obj)

        if self.reproductive_drive >= self.time_to_reproduce:
            self.reproductive_ready = True

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= dt

        self.check_for_food_and_water(dt, entities, resources, water_sources, is_day)
        self.avoid_other_entities(dt, entities, is_day)

        # Добавлено: перенос через границы карты
        self.x = self.x % map_obj.width
        self.y = self.y % map_obj.height
    def check_for_food_and_water(self, dt, entities, resources, water_sources, is_day):
        """Проверяет наличие пищи и воды и устанавливает цели для их поиска."""
        if not self.target and ((isinstance(self, Herbivore) and is_day) or (isinstance(self, Predator) and not is_day)):
            if self.thirst > self.thirst_threshold_drink:
                self.target = self.find_water_target(water_sources)
            elif self.hunger > self.hunger_threshold_eat:
                self.target = self.find_target(entities, resources, is_day)

    def avoid_other_entities(self, dt, entities, is_day):
        """Избегает столкновений с другими сущностями."""
        pass

    def avoid_edges(self, map_obj):
        """Избегает выхода за границы карты."""
        avoidance_distance = self.size + 20
        avoid_vector = (0, 0)

        if self.x - self.size / 2 < avoidance_distance:
            avoid_vector = (avoidance_distance - (self.x - self.size / 2), 0)
        elif self.x + self.size / 2 > map_obj.width - avoidance_distance:
            avoid_vector = (map_obj.width - avoidance_distance - (self.x + self.size / 2), 0)
        elif self.y - self.size / 2 < avoidance_distance:
            avoid_vector = (0, avoidance_distance - (self.y - self.size / 2))
        elif self.y + self.size / 2 > map_obj.height - avoidance_distance:
            avoid_vector = (0, map_obj.height - avoidance_distance - (self.y + self.size / 2))

        if avoid_vector != (0, 0):
            return normalize(*avoid_vector)
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
                    self.x += dx * self.speed * dt * 3
                    self.y += dy * self.speed * dt * 3

    def wander(self, dt, map_obj):
        """Заставляет сущность беспорядочно бродить по карте."""
        self.wander_timer += dt
        if self.wander_timer >= self.wander_interval or self.wander_target is None or distance(self.x, self.y, self.wander_target[0], self.wander_target[1]) <= 10:
            self.wander_timer = 0
            self.wander_interval = random.randint(3, 8)
            self.wander_target = (random.randint(20, map_obj.width - 20), random.randint(20, map_obj.height - 20))

        dx, dy = normalize(self.wander_target[0] - self.x, self.wander_target[1] - self.y)
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt

    def on_target_reached(self, entities, resources, map_obj):
        """Выполняет действия, когда сущность достигает своей цели."""
        if isinstance(self.target, Food):
            if self.target in resources:
                self.hunger = 0
                resources.remove(self.target)
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

class Predator(Entity):
    """Класс, представляющий хищника."""
    def __init__(self, x, y):
        """Инициализирует хищника с заданными параметрами."""
        super().__init__(x, y, 15, 10, 100, 30, 60, RED, lifespan = 2000)
        self.attack_damage = 30
        self.growth_time = 0
        self.is_baby = False
        self.time_to_reproduce = 125
        self.vision_range = 200
        self.hunt_range = 100
        self.target_search_interval = 2
        self.last_target_search = 0
        self.hunger_threshold_attack = 3
        self.eating_cross = None
        self.chase_timer = 0
        self.max_chase_time = 30
        self.patrol_timer = 0
        self.patrol_interval = random.randint(2, 6)
        self.eat_timer = 0
        self.eat_interval = 20
        self.eating_crosses = []
        self.is_eating_cross = False
        self.has_eaten_cross = False

        self.avoid_predator_timer = 0
        self.avoid_predator_duration = 20
        self.hunger_desperation_threshold = self.max_hunger * 0.75


    def find_target(self, entities, resources, is_day):
        """Находит цель для охоты (травоядное)."""
        if self.is_drinking or self.reproductive_ready or is_day == True:
            return None

        if self.hunger < self.hunger_threshold_attack:
            return None

        closest_herbivore = None
        min_distance = float('inf')
        for entity in entities:
            if isinstance(entity, Herbivore):
                dist = distance(self.x, self.y, entity.x, entity.y)
                if dist < min_distance and dist <= self.hunt_range:
                    min_distance = dist
                    closest_herbivore = entity
        return closest_herbivore

    def on_target_reached(self, entities, resources, map_obj):
        """Выполняет действия, когда хищник достигает своей цели."""
        if isinstance(self.target, Herbivore) and self.hunger > self.hunger_threshold_attack:
            self.attack(entities, map_obj)
            self.target = None
        elif isinstance(self.target, Water):
            self.is_drinking = True
        elif isinstance(self.target, EatingCross) and self.is_eating_cross:
            self.try_eat(entities, map_obj)
            self.target = None
        elif self.target and self.reproductive_ready and type(self.target) == type(self):
            self.check_reproduce(entities)
        elif self.target and type(self.target) is tuple:
            self.target = None

    def update(self, dt, entities, resources, map_obj, water_sources, day_night_cycle):
        """Обновляет состояние хищника."""
        now = pygame.time.get_ticks() / 1000.0

        is_day = day_night_cycle.is_day()

        if now - self.last_target_search >= self.target_search_interval:
            self.last_target_search = now
            if not self.target or not isinstance(self.target, Herbivore) or self.target not in entities:
                self.target = self.find_target(entities, resources, is_day)
                self.chase_timer = 0

        if self.hunger >= self.hunger_desperation_threshold:
            self.target = self.find_target(entities, resources, is_day)
            if self.target:
                super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)
                return

        if self.thirst > self.thirst_threshold_drink:
            self.target = self.find_water_target(water_sources)  # Ищем воду
            if self.target:
                super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)
                return

        if self.reproductive_ready and not self.target:
            self.target = self.find_reproduction_target(entities)
            if self.target:
                super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)
                return

        if not self.target and not self.is_drinking and is_day == False:
            self.patrol(dt, map_obj)


        if self.target and isinstance(self.target, Herbivore):
            self.chase_timer += dt
            if self.chase_timer >= self.max_chase_time:
                self.target = None
                self.chase_timer = 0

        super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)

        self.reproductive_drive += dt / 2
        if self.reproductive_drive >= self.reproduction_threshold:
            self.check_reproduce(entities)

        if self.is_baby:
            self.growth_time += dt
            if self.growth_time >= 300:
                self.size = self.max_size
                self.is_baby = False

        self.avoid_water(water_sources, dt, entities)

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
                self.try_eat(entities, map_obj)

        if self.avoid_predator_timer > 0:
            self.avoid_predator_timer -= dt


    def patrol(self, dt, map_obj):
        """Патрулирует территорию в поисках добычи."""
        self.wander(dt, map_obj)

    def attack(self, entities, map_obj):
        """Атакует травоядное."""
        if self.target and self.target in entities and distance(self.x, self.y, self.target.x, self.target.y) < self.size + self.target.size + 10:
            self.create_eating_cross(self.target, map_obj)
            entities.remove(self.target)
            self.target = None
            self.hunger = 0

    def try_eat(self, entities, map_obj):
        """Пытается съесть труп или атаковать травоядное."""
        if self.is_eating_cross and self.eating_cross:
            self.eating_cross.hunger -= 10
            if self.eating_cross.hunger <= 0:
                self.hunger = 0
                self.eating_cross = None
                self.eating_crosses.clear()
                self.is_eating_cross = False
                return
            return
        else:
            closest_cross = None
            min_distance = float('inf')
            for cross in self.eating_crosses:
                dist = distance(self.x, self.y, cross.x, cross.y)
                if dist < min_distance and self.hunger > self.hunger_threshold_attack:
                    min_distance = dist
                    closest_cross = cross
            if closest_cross:
                self.target = closest_cross
                self.is_eating_cross = True
                return
            closest_herbivore = None
            min_distance = float('inf')
            for entity in entities:
                if isinstance(entity, Herbivore):
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10 and self.hunger > self.hunger_threshold_attack:
                        min_distance = dist
                        closest_herbivore = entity
            if closest_herbivore and self.hunger > self.hunger_threshold_attack:
                self.create_eating_cross(closest_herbivore, map_obj)
                entities.remove(closest_herbivore)
                self.is_eating_cross = True

    def avoid_other_entities(self, dt, entities, is_day):
        """Избегает других сущностей."""
        if self.avoid_predator_timer > 0:
            for entity in entities:
                if entity != self and isinstance(entity, Predator):
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < self.avoidance_distance:
                        dx, dy = normalize(self.x - entity.x, self.y - entity.y)
                        self.x += dx * self.speed * dt * 3
                        self.y += dy * self.speed * dt * 3

    def create_eating_cross(self, herbivore, map_obj):
        """Создает труп травоядного после атаки."""
        eating_cross = EatingCross(herbivore.x, herbivore.y)
        self.eating_cross = eating_cross
        self.eating_crosses.append(eating_cross)

    def check_reproduce(self, entities):
        """Проверяет возможность размножения."""
        if self.reproductive_ready and self.reproduction_cooldown <= 0:
            closest_predator = None
            min_distance = float('inf')
            for entity in entities:
                if isinstance(entity, Predator) and entity != self:
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10:
                        min_distance = dist
                        closest_predator = entity

            if closest_predator and closest_predator.reproduction_cooldown <= 0:
                if self.growth_time == 0 and closest_predator.growth_time == 0:
                    self.reproduce(entities, closest_predator)


    def reproduce(self, entities, other):
        """Размножается с другим хищником."""
        if self.reproductive_ready and other.reproductive_ready:
            new_predator = Predator(self.x, self.y)
            new_predator.size = (self.size + other.size) / 4
            new_predator.max_size = min(self.size, other.size)
            new_predator.is_baby = True
            new_predator.growth_time = 0
            entities.append(new_predator)

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

class EatingCross:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hunger = 100
        self.color = YELLOW
        self.timer = 0
        self.max_timer = 60

    def update(self, dt):
        self.timer += dt

    def draw(self, screen):
        size = 15
        pygame.draw.line(screen, self.color, (self.x - size, self.y), (self.x + size, self.y), 3)
        pygame.draw.line(screen, self.color, (self.x, self.y - size), (self.x, self.y + size), 3)

class Herbivore(Entity):
    """Класс, представляющий травоядное."""
    def __init__(self, x, y):
        """Инициализирует травоядное с заданными параметрами."""
        super().__init__(x, y, 7, 10, 80, 60, 60, GREEN, lifespan = 1200)
        self.fear_distance = 45
        self.time_to_reproduce = 150
        self.target_eat_distance = 25
        self.target_drink_distance = 25
        self.fleeing_speed_multiplier = 5
        self.hunt_range = 50
        self.avoid_predator_timer = 0
        self.avoid_predator_duration = 20

    def find_target(self, entities, resources, is_day):
        """Находит цель для еды (пищу)."""
        if is_day == False:
            return None
        closest_food = None
        min_distance = float('inf')
        for resource in resources:
            if isinstance(resource, Food):
                dist = distance(self.x, self.y, resource.x, resource.y)
                if dist < min_distance:
                    min_distance = dist
                    closest_food = resource

        return closest_food

    def update(self, dt, entities, resources, map_obj, water_sources, day_night_cycle):
        """Обновляет состояние травоядного."""
        edge_avoidance_vector = self.avoid_edges(map_obj)
        is_day = day_night_cycle.is_day()
        if edge_avoidance_vector:
            dx, dy = edge_avoidance_vector
            self.x += dx * self.speed * dt * 5
            self.y += dy * self.speed * dt * 5
            return

        if self.reproductive_ready and not self.target:
            self.target = self.find_reproduction_target(entities)

        if self.is_drinking:
            super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)
            return

        if not self.target or (self.target and not isinstance(self.target, Water)):
            if self.thirst > self.thirst_threshold_drink:
                self.target = self.find_water_target(water_sources)
            elif self.hunger > self.hunger_threshold_eat:
                self.target = self.find_target(entities, resources, is_day)
        elif not self.target:
            self.wander(dt, map_obj)

        super().update(dt, entities, resources, map_obj, water_sources, day_night_cycle)

        self.reproductive_drive += dt
        if self.reproductive_drive >= self.reproduction_threshold:
            self.check_reproduce(entities)

    def on_target_reached(self, entities, resources, map_obj):
        """Выполняет действия, когда травоядное достигает своей цели."""
        if isinstance(self.target, Food):
            if self.target in resources and distance(self.x, self.y, self.target.x, self.target.y) < self.target_eat_distance:
                self.hunger = 0
                resources.remove(self.target)
            self.target = None
        elif isinstance(self.target, Water):
            if distance(self.x, self.y, self.target.x, self.target.y) < self.target_drink_distance:
                self.is_drinking = True
        elif self.target and self.reproductive_ready and type(self.target) == type(self):
            self.check_reproduce(entities)
        elif self.target and type(self.target) is tuple:
            self.target = None

    def check_reproduce(self, entities):
        """Проверяет возможность размножения."""
        if self.reproductive_ready and self.reproduction_cooldown <= 0:
            closest_herbivore = None
            min_distance = float('inf')
            for entity in entities:
                if isinstance(entity, Herbivore) and entity != self:
                    dist = distance(self.x, self.y, entity.x, entity.y)
                    if dist < min_distance and dist <= self.size + entity.size + 10:
                        min_distance = dist
                        closest_herbivore = entity

            if closest_herbivore and closest_herbivore.reproduction_cooldown <= 0:
                if self.growth_time == 0 and closest_herbivore.growth_time == 0:
                    self.reproduce(entities, closest_herbivore)


    def reproduce(self, entities, other):
        """Размножается с другим травоядным."""
        if self.reproductive_ready and other.reproductive_ready:
            new_herbivore = Herbivore(self.x, self.y)
            new_herbivore.size = (self.size + other.size) / 4
            new_herbivore.max_size = min(self.size, other.size)
            new_herbivore.is_baby = True
            new_herbivore.growth_time = 0
            entities.append(new_herbivore)

            dx, dy = normalize(new_herbivore.x - self.x, new_herbivore.y - self.y)
            separation_distance = 200

            new_herbivore.target = (new_herbivore.x + dx * separation_distance, new_herbivore.y + dy * separation_distance)
            self.target = (self.x - dx * separation_distance, self.y - dy * separation_distance)
            other.target = (other.x - dx * separation_distance, other.y - dy * separation_distance)

            self.reproductive_drive = 0
            self.reproductive_ready = False
            self.reproduction_cooldown = self.reproduction_cooldown_max
            other.reproductive_drive = 0
            other.reproductive_ready = False
            other.reproduction_cooldown = other.reproduction_cooldown_max

            self.avoid_predator_timer = self.avoid_predator_duration
            other.avoid_predator_timer = self.avoid_predator_duration



class Resource:
    def __init__(self, x, y, size, color):
        self.x = x
        self.y = y
        self.size = size
        self.color = color

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (int(self.x - self.size / 2), int(self.y - self.size / 2), self.size, self.size))


class Food(Resource):
    def __init__(self, x, y):
        super().__init__(x, y, 8, GREEN)


class Water(Resource):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, BLUE)

class DayNightCycle:
    def __init__(self, day_length, night_length, transition_duration):
        self.day_length = day_length
        self.night_length = night_length
        self.transition_duration = transition_duration
        self.cycle_duration = day_length + night_length + 2 * transition_duration
        self.timer = 0

    def update(self, dt):
        self.timer = (self.timer + dt) % self.cycle_duration

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

class Game:
    def __init__(self):
        self.day_music = pygame.mixer.Sound('home2.mp3')
        self.night_music = pygame.mixer.Sound('home.mp3')
        self.current_music = None
        self.map = Map(WIDTH, HEIGHT, TILE_SIZE)
        self.entities = []
        self.resources = []
        self.water_sources = []
        self.clock = pygame.time.Clock()
        self.last_time = pygame.time.get_ticks()
        self.hovered_entity = None
        self.day_night_cycle = DayNightCycle(DAY_LENGTH, NIGHT_LENGTH, TRANSITION_DURATION)

        self.eating_crosses = []

        self.init_entities(20, 10)
        self.init_resources(20)
        self.init_water_sources()

    def init_entities(self, num_herbivores, num_predators):
        for _ in range(num_herbivores):
            x = random.randint(20, WIDTH - 20)
            y = random.randint(20, HEIGHT - 20)
            self.entities.append(Herbivore(x, y))

        for _ in range(num_predators):
            x = random.randint(20, WIDTH - 20)
            y = random.randint(20, HEIGHT - 20)
            self.entities.append(Predator(x, y))

    def init_resources(self, num_food):
        for _ in range(num_food):
            x = random.randint(20, WIDTH - 20)
            y = random.randint(20, HEIGHT - 20)
            self.resources.append(Food(x, y))

    def init_water_sources(self):
        self.water_sources.append(Water(WIDTH // 4, HEIGHT // 4, 50))
        self.water_sources.append(Water(WIDTH // 2, HEIGHT // 2, 70))
        self.water_sources.append(Water(WIDTH * 3 // 4, HEIGHT * 3 // 4, 60))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEMOTION:
                    self.check_hover(event.pos)

            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def check_hover(self, mouse_pos):
        self.hovered_entity = None
        for entity in self.entities:
            if distance(mouse_pos[0], mouse_pos[1], entity.x, entity.y) < entity.size:
                self.hovered_entity = entity
                break

    def update(self):
        now = pygame.time.get_ticks()
        dt = (now - self.last_time) / 1000.0
        self.last_time = now

        self.day_night_cycle.update(dt)

        for entity in self.entities:
            entity.update(dt, self.entities, self.resources, self.map, self.water_sources, self.day_night_cycle)

        if random.random() < 0.01 and self.day_night_cycle.is_day():
            x = random.randint(20, WIDTH - 20)
            y = random.randint(20, HEIGHT - 20)
            self.resources.append(Food(x, y))

        for entity in self.entities:
            if isinstance(entity, Predator) and entity.eating_cross:
                entity.eating_cross.update(dt)


        for entity in self.entities:
            if isinstance(entity, Predator) and entity.eating_cross:
                if entity.eating_cross.timer >= entity.eating_cross.max_timer:
                    entity.eating_crosses.remove(entity.eating_cross)
                    entity.eating_cross = None
                    break
        if self.day_night_cycle.is_day():
            if self.current_music != self.day_music:
                if self.current_music:
                    self.current_music.stop()
                self.day_music.play(-1)  # -1 означает, что музыка будет воспроизводиться в цикле
                self.current_music = self.day_music
        else:
            if self.current_music != self.night_music:
                if self.current_music:
                    self.current_music.stop()
                self.night_music.play(-1)
                self.current_music = self.night_music


    def draw(self):
        background_color = self.day_night_cycle.get_background_color()
        self.map.draw(screen, background_color)
        for resource in self.resources:
            resource.draw(screen)
        for water in self.water_sources:
            water.draw(screen)
        for entity in self.entities:
            entity.draw(screen)
            if self.hovered_entity == entity:
                entity.draw_info(screen)

        for entity in self.entities:
            if isinstance(entity, Predator) and entity.eating_cross:
                entity.eating_cross.draw(screen)


if __name__ == '__main__':
    game = Game()
    game.run()
