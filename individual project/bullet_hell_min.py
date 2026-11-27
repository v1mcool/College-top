import math

import random

import pygame

# ===== 1. Окно, карта и шрифты =====
WIDTH, HEIGHT = 900, 650                                         # размер окна
WORLD_WIDTH, WORLD_HEIGHT = int(WIDTH * 1.5), int(HEIGHT * 1.5)  # карта в 1.5 раза больше окна

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bullet Hell")
clock = pygame.time.Clock()
font_20, font_22, font_30, font_72 = (pygame.font.SysFont(None, size) for size in (20, 22, 30, 72))
overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
overlay.fill((8, 8, 16, 190))

# ===== 2. Бонусы и карточки =====
UPGRADES = [("Урон +1", "пули имеют на 1 урон больше"), ("Скорострел", "+20% к скорострельности"),
            ("Скорость", "+20% к скорости бега"), ("Здоровье", "+1 HP и лечит 3 HP"),
            ("Веер", "+1 пуля в залпе")]                          # название и описание бонуса
CARDS = [pygame.Rect(60 + index * 270, 220, 240, 270) for index in range(3)]  # три рамки карточек


# ===== 3. Помощники: бонус, касание, камера =====
def apply_upgrade(player, index):
    if index == 0: player.bullet_damage += 1                     # урон
    elif index == 1: player.cooldown = max(5, int(player.cooldown * 0.8))  # темп огня
    elif index == 2: player.speed *= 1.2                         # бег
    elif index == 3:                                             # здоровье
        player.max_health += 2
        player.health += 3
        if player.health > player.max_health:
            player.health = player.max_health
    else: player.shot_count += 1                                 # веер


def circles_touch(first, second):
    return first.position.distance_to(second.position) < first.radius + second.radius


def camera(player):
    return pygame.Vector2(min(max(player.position.x - WIDTH / 2, 0), WORLD_WIDTH - WIDTH), 
                          min(max(player.position.y - HEIGHT / 2, 0), WORLD_HEIGHT - HEIGHT))


# ===== 4. Пуля =====
class Bullet:
    def __init__(self, position, velocity, friendly, target=None, damage=1):
        self.position, self.velocity = pygame.Vector2(position), pygame.Vector2(velocity)
        self.speed = self.velocity.length()
        self.friendly, self.target, self.damage = friendly, target, damage
        self.radius, self.alive = (5 if friendly else 6), True

    def update(self):
        # наводимся только на живую цель, иначе летим прямо
        if self.friendly and self.target and self.target.alive:
            direction = self.target.position - self.position     # вектор к цели
            if direction.length() > 1:
                needed_velocity = direction.normalize() * self.speed   # скорость, ведущая в цель
                self.velocity += (needed_velocity - self.velocity) * 0.12  # плавный поворот
        self.position += self.velocity                           # полёт

    def draw(self, camera_position):
        color = (120, 220, 255) if self.friendly else (255, 0, 0)   # своя или вражеская
        pygame.draw.circle(screen, color, self.position - camera_position, self.radius)  # pos минус камера


# ===== 5. Игрок =====
class Player:
    def __init__(self):
        self.position = pygame.Vector2(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
        self.radius, self.speed = 14, 6.0
        self.max_health = self.health = 10
        self.cooldown, self.fire_timer, self.immunity_timer = 25, 0, 0
        self.shot_count, self.bullet_damage = 1, 1
        self.level, self.experience, self.experience_needed = 1, 0, 5

    def update(self, keys):
        move = pygame.Vector2((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                              (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))  # ввод
        if move.x or move.y: self.position += move.normalize() * self.speed  # движение
        self.position.x = max(self.radius, min(WORLD_WIDTH - self.radius, self.position.x))  # не за край
        self.position.y = max(self.radius, min(WORLD_HEIGHT - self.radius, self.position.y))
        self.fire_timer, self.immunity_timer = max(0, self.fire_timer - 1), max(0, self.immunity_timer - 1)  # таймеры

    def shoot(self, enemies, bullets, aim_point=None):
        if self.fire_timer: return                               # пауза не прошла
        else:                      # автонаведение на ближайшего
            if not enemies: return                               # некого бить
            target = min(enemies, key=lambda enemy: enemy.position.distance_to(self.position))  # ближайший
            direction = target.position - self.position
        base_angle = math.atan2(direction.y, direction.x)        # направление в угол
        for index in range(self.shot_count):
            angle = base_angle + 0.5 * (index - (self.shot_count - 1) / 2)  # веер
            bullets.append(Bullet(self.position, pygame.Vector2(math.cos(angle), math.sin(angle)) * 9, 1, target, self.bullet_damage))  # выстрел
        self.fire_timer = self.cooldown                          # снова ждать паузу

    def take_damage(self):
        if self.immunity_timer == 0: self.health, self.immunity_timer = self.health - 1, 60  # урон и неуязвимость

    def draw(self, camera_position):
        if self.immunity_timer and (self.immunity_timer // 5) % 2 == 0: return  # мигаем
        pygame.draw.circle(screen, (90, 200, 255), self.position - camera_position, self.radius)   # тело
        pygame.draw.circle(screen, (255, 255, 255), self.position - camera_position, self.radius, 2)  # обводка


# ===== 6. Враг =====
class Enemy:
    def __init__(self, is_melee, camera_position):
        if random.random() < 0.5:
            x, y = random.choice([camera_position.x - 15, camera_position.x + WIDTH + 15]), camera_position.y + random.randint(0, HEIGHT)
        else:
            x, y = camera_position.x + random.randint(0, WIDTH), random.choice([camera_position.y - 30, camera_position.y + HEIGHT + 30])
        self.position = pygame.Vector2(x, y)
        self.is_melee = is_melee
        self.radius, self.health, self.speed = (13, 2, 2.5) if is_melee else (15, 3, 1.3)
        self.color = (255, 0, 0) if is_melee else (128, 0, 128)
        self.shoot_timer, self.alive = random.randint(50, 100), True

    def update(self, player, bullets):
        direction = player.position - self.position              # куда игрок
        distance = direction.length()                            # как далеко
        direction = direction.normalize() if distance else pygame.Vector2(1, 0)  # направление длиной 1
        if self.is_melee:
            self.position += direction * self.speed
            return
        if distance > 260: self.position += direction * self.speed
        elif distance < 170: self.position -= direction * self.speed
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = random.randint(70, 110)
            for _ in range(random.randint(1, 2)):  # 1-2 пули
                angle = math.atan2(direction.y, direction.x) + random.uniform(-0.15, 0.15)
                bullets.append(Bullet(self.position, pygame.Vector2(math.cos(angle), math.sin(angle)) * 3.2, 0)) #скорость пули врагов

    def draw(self, camera_position):
        pygame.draw.circle(screen, self.color, self.position - camera_position, self.radius)  # тело
        pygame.draw.circle(screen, (25, 25, 35), self.position - camera_position, self.radius, 2)  # обводка


# ===== 7. Попадания =====
def hit(player, enemies, bullets):
    """Все попадания кадра. Возвращает число убийств."""
    kills = 0
    for bullet in bullets:
        if not bullet.alive: continue
        if bullet.friendly:
            for enemy in enemies:
                if enemy.alive and circles_touch(bullet, enemy):  # попала во врага
                    bullet.alive = False
                    enemy.health -= bullet.damage
                    if enemy.health <= 0:
                        enemy.alive = False
                        kills = kills + 1
                        break
        elif circles_touch(bullet, player):                      # вражеская пуля попала в игрока
            bullet.alive = False
            player.take_damage()
    for enemy in enemies:  # враг в упор тоже ранит
        if enemy.alive and circles_touch(enemy, player):
            enemy.alive = False
            player.take_damage()
    return kills


# ===== 8. Рисование: фон, HUD, карточки =====
def draw_world(camera_position):
    screen.fill((18, 18, 28))                                    # стираем прошлый кадр
    pygame.draw.rect(screen, (40, 40, 60), (-camera_position.x, -camera_position.y, WORLD_WIDTH, WORLD_HEIGHT), 4)  # край карты


def hud(player, score):
    text = font_30.render(f"HP {player.health}/{player.max_health}   Ур. {player.level}   Опыт {player.experience}/{player.experience_needed}   Счёт {score}", True, (230, 230, 240))
    screen.blit(text, (20, 20))


def draw_cards(cards, level):
    screen.blit(overlay, (0, 0))                                 # затемняем игру
    text = font_72.render(f"Уровень {level}", True, (250, 220, 110))  # заголовок
    screen.blit(text, text.get_rect(center=(WIDTH / 2, 120)))    # по центру
    text = font_22.render("клик по карте или клавиши 1-3", True, (200, 200, 215))  # подсказка
    screen.blit(text, text.get_rect(center=(WIDTH / 2, 175)))
    for index, box in enumerate(CARDS):
        name, description = UPGRADES[cards[index]]               # выпавший бонус
        pygame.draw.rect(screen, (40, 44, 68), box, border_radius=12)   # плашка
        pygame.draw.rect(screen, (120, 200, 255), box, 2, border_radius=12)  # рамка
        text = font_30.render(f"{index + 1}. {name}", True, (240, 240, 250))  # номер и название
        screen.blit(text, text.get_rect(center=(box.centerx, box.y + 80)))
        text = font_20.render(description, True, (170, 175, 195))  # описание
        screen.blit(text, text.get_rect(center=(box.centerx, box.y + 130)))


# ===== 9. Главный цикл =====
def main():
    player, enemies, bullets = Player(), [], []
    score, spawn_timer, spawn_delay, state, cards = 0, 0, 45, "playing", []  # счёт, спавн, состояние
    camera_position = camera(player)
    running = True
    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif state == "dead" and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                player, enemies, bullets, cards = Player(), [], [], []
                score, spawn_timer, spawn_delay, state = 0, 0, 45, "playing"
                camera_position = camera(player)
            elif state == "levelup":                             # выбор карточки
                choice = None
                if event.type == pygame.MOUSEBUTTONDOWN:         # клик мышью
                    choice = next((index for index, box in enumerate(CARDS) if box.collidepoint(event.pos)), None)
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):  # клавиши 1-3
                    choice = event.key - pygame.K_1
                if choice is not None:
                    apply_upgrade(player, cards[choice])
                    state = "playing"

        if state == "playing":
            player.update(pygame.key.get_pressed())
            camera_position = camera(player)
            aim_point = pygame.Vector2(pygame.mouse.get_pos()) + camera_position if pygame.mouse.get_pressed()[0] else None
            player.shoot([enemy for enemy in enemies if enemy.alive], bullets, aim_point)
            spawn_timer += 1
            if spawn_timer >= spawn_delay:
                spawn_timer = 0
                enemies.append(Enemy(random.random() < 0.6, camera_position))  # 60% рукопашников
                spawn_delay = max(15, spawn_delay - 0.5)         # постепенно чаще
            for enemy in enemies: enemy.update(player, bullets)  # движение врагов
            for bullet in bullets: bullet.update()               # полёт пуль
            killed = hit(player, enemies, bullets)               # попадания
            score += killed                                      # счёт
            player.experience += killed                          # опыт
            bullets = [bullet for bullet in bullets if bullet.alive and -40 < bullet.position.x < WORLD_WIDTH + 40 and -40 < bullet.position.y < WORLD_HEIGHT + 40]  # чистка
            enemies = [enemy for enemy in enemies if enemy.alive]
            if player.experience >= player.experience_needed:    # новый уровень
                player.experience -= player.experience_needed
                player.level += 1
                player.experience_needed += 3
                cards = random.sample(range(len(UPGRADES)), 3)   # три разных бонуса
                state = "levelup"
            if player.health <= 0:
                state = "dead"                                   # смерть

        draw_world(camera_position)                              # отрисовка
        for enemy in enemies: enemy.draw(camera_position)
        for bullet in bullets: bullet.draw(camera_position)
        player.draw(camera_position)
        hud(player, score)
        if state == "levelup":                                   # экран поверх игры
            draw_cards(cards, player.level)
        elif state == "dead":
            text = font_72.render("Ты погиб", True, (255, 120, 120))
            screen.blit(text, text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 40)))
            text = font_30.render(f"Счёт: {score}. R — заново", True, (230, 230, 240))
            screen.blit(text, text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30)))
        pygame.display.flip()                                    # показать кадр
    pygame.quit()


if __name__ == "__main__":
    main()
