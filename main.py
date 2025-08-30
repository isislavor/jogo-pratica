from constants import *
from pygame import Rect
from pgzero.actor import Actor
import pgzrun
import os
os.environ["SDL_VIDEO_CENTERED"] = "1"


class Platform:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.rect = Rect(x, y, w, h)

    def draw(self):
        if not has_tile:
            screen.draw.filled_rect(
                Rect(self.rect.x - camera_x, self.rect.y,
                     self.rect.w, self.rect.h),
                "darkolivegreen"
            )
            return

        camera_x_int = int(camera_x)

        x = max(self.rect.x, camera_x_int - (camera_x_int % title_width))
        end_x = self.rect.right

        source_rect = None
        use_clip = self.rect.y < GROUND_Y
        if use_clip:
            destination_clip_rect = Rect(
                int(self.rect.x - camera_x), int(self.rect.y), int(self.rect.w), int(self.rect.h))
            previous_clip = screen.surface.get_clip()

            screen.surface.set_clip(destination_clip_rect)

            source_height = min(self.rect.h, title_height)
            source_rect = (0, 0, title_width, source_height)

        while x < end_x:
            screen_x = int(x - camera_x)

            if source_rect:
                screen.surface.blit(
                    tile_surf, (screen_x, self.rect.y), source_rect)
            else:
                screen.surface.blit(tile_surf, (screen_x, self.rect.y))

            x += title_width

        if use_clip:
            screen.surface.set_clip(previous_clip)


class Hero:
    WALK_PERIOD = 10
    IDLE_PERIOD = 18
    MOVE_EPS = 0.01
    INVULN_TICKS = 60
    KNOCKBACK_X = 3.5
    KNOCKBACK_Y = 8

    def __init__(self, x: int, y: int):
        self.actor = Actor("right_guy_walking_0", pos=(x, y))
        self.actor.anchor = ('center', 'bottom')
        self.velocity_x, self.velocity_y = 0.0, 0.0
        self.on_ground = False
        self.frame = 0
        self.images_idle = ["right_guy_walking_0", "right_guy_walking_1"]
        self.images_walk = ["right_guy_walking_0", "right_guy_walking_1"]
        self.facing = 1
        self.max_health = 3
        self.health = 3
        self.invulnerability = 0

    @property
    def rect(self):
        width, height = self.actor.width, self.actor.height
        return Rect(int(self.actor.x - width / 2), int(self.actor.y - height), width, height)

    def collide(self, platforms):
        rect = self.rect
        return next((platform.rect for platform in platforms if rect.colliderect(platform.rect)), None)

    def move_horizontal(self, platforms):
        if self.velocity_x == 0:
            return

        self.actor.x += self.velocity_x

        hit = self.collide(platforms)
        if hit:
            if self.velocity_x > 0:
                self.actor.x = hit.left - self.rect.w / 2
            else:
                self.actor.x = hit.right + self.rect.w / 2

            self.velocity_x = 0

    def move_vertical(self, platforms):
        self.velocity_y += GRAVITY
        self.actor.y += self.velocity_y
        self.on_ground = False

        hit = self.collide(platforms)
        if hit:
            if self.velocity_y > 0:
                self.actor.y = hit.top
                self.on_ground = True
            elif self.velocity_y < 0:
                self.actor.y = hit.bottom + self.rect.h

            self.velocity_y = 0

        if self.actor.y > GROUND_Y:
            self.actor.y = GROUND_Y
            self.velocity_y = 0
            self.on_ground = True

    def move_and_collide(self, platforms):
        self.move_horizontal(platforms)
        self.move_vertical(platforms)
        self.actor.x = max(16, min(WORLD_W - 16, self.actor.x))

    def update(self, platforms):
        direction_x = (1 if keyboard.right else 0) - \
            (1 if keyboard.left else 0)

        self.velocity_x = direction_x * SPEED_X
        if direction_x:
            self.facing = 1 if direction_x > 0 else -1

        self.move_and_collide(platforms)
        self.animate()

        if self.invulnerability > 0:
            self.invulnerability -= 1

    def animate(self):
        self.frame += 1

        moving = abs(self.velocity_x) > self.MOVE_EPS
        images = self.images_walk if moving else self.images_idle
        period = self.WALK_PERIOD if moving else self.IDLE_PERIOD
        base = images[(self.frame // period) % len(images)]

        self.actor.image = pick_prefixed(base, left=(self.facing == -1))
        self.actor.angle = 0

    def jump(self):
        if self.on_ground:
            self.velocity_y = JUMP_VELOCITY
            if sound_on and hasattr(sounds, "jump"):
                sounds.jump.play()

    def take_hit_from(self, enemy):
        if self.invulnerability > 0:
            return

        self.health = max(0, self.health - 1)
        self.invulnerability = self.INVULN_TICKS

        direction = -1 if self.actor.x < enemy.actor.x else 1

        self.velocity_x = -direction * self.KNOCKBACK_X
        self.velocity_y = -self.KNOCKBACK_Y

        if sound_on and hasattr(sounds, "hit"):
            sounds.hit.play()

    def draw(self):
        if self.invulnerability > 0 and (self.invulnerability // 3) % 2 == 0:
            return
        draw_with_camera(self.actor)


class Enemy:
    def __init__(self, x1: int, x2: int, y: int):
        self.actor = Actor("enemy_0", pos=(x1, y))
        self.actor.anchor = ('center', 'bottom')
        self.left, self.right = x1, x2
        self.speed = 1.8
        self.frame = 0
        self.images = ["enemy_0", "enemy_1", "enemy_2", "enemy_3"]

    @property
    def rect(self):
        width, height = self.actor.width, self.actor.height
        return Rect(int(self.actor.x - width / 2), int(self.actor.y - height), width, height)

    def update(self):
        self.actor.x += self.speed

        if self.actor.x < self.left:
            self.actor.x = self.left
            self.speed = abs(self.speed)
        elif self.actor.x > self.right:
            self.actor.x = self.right
            self.speed = -abs(self.speed)

        self.frame += 1

        index = (self.frame // 12) % len(self.images)
        self.actor.image = self.images[index]
        self.actor.angle = 0

    def draw(self):
        draw_with_camera(self.actor)


def draw_with_camera(actor: Actor):
    old_x = actor.x

    try:
        actor.x = actor.x - camera_x
        actor.draw()
    finally:
        actor.x = old_x


def pick_prefixed(base: str, left: bool) -> str:
    key = (base, left)

    if key in IMAGES_VARIANTS_CACHE:
        return IMAGES_VARIANTS_CACHE[key]

    base_parts = base.split('_')
    name = f"{'left' if left else 'right'}_{'_'.join(base_parts[1:])}"

    images.load(name)

    IMAGES_VARIANTS_CACHE[key] = name
    return name


def goal_hitbox():
    return Rect(int(flag.x - flag.width / 2), int(flag.y - flag.height / 2), flag.width, flag.height)


def draw_hud():
    x, y = 10, 10
    for index in range(hero.max_health):
        color = "red" if index < hero.health else "darkred"
        screen.draw.filled_rect(Rect(x, y, 24, 18), color)
        x += 30


def update_camera():
    global camera_x

    deadzone_left = camera_x + WIDTH * 0.4
    deadzone_right = camera_x + WIDTH * 0.6

    target = hero.actor.x
    if target < deadzone_left:
        camera_x -= (deadzone_left - target)
    elif target > deadzone_right:
        camera_x += (target - deadzone_right)

    camera_x = max(0, min(WORLD_W - WIDTH, camera_x))


def start_game():
    global game_state

    hero.actor.x, hero.actor.y = 100, GROUND_Y
    hero.velocity_x = hero.velocity_y = 0
    hero.health = hero.max_health
    game_state = "play"

    try:
        if sound_on:
            music.play("bgmusic")
            music.set_volume(0.5)
        else:
            music.stop()
    except Exception:
        pass


def change_to_menu():
    global game_state
    game_state = "menu"

    try:
        music.stop()
    except Exception:
        pass


def update():
    global game_state
    if game_state != "play":
        return

    hero.update(platforms)

    for enemy in enemies:
        enemy.update()

    update_camera()

    for enemy in enemies:
        if hero.rect.colliderect(enemy.rect):
            hero.take_hit_from(enemy)

    if hero.health <= 0:
        change_to_menu()
    if hero.rect.colliderect(goal_hitbox()):
        change_to_menu()


def draw():
    screen.clear()
    screen.blit("background.jpg", (0, 0))

    if game_state == "menu":
        screen.draw.text("SPACE TUTORS", center=(WIDTH/2, 160), fontsize=56)
        screen.draw.text("Click the buttons",
                         center=(WIDTH/2, 210), fontsize=28)

        screen.draw.filled_rect(BUTTON_START, "darkslateblue")
        screen.draw.text("START", center=BUTTON_START.center,
                         fontsize=28, color="white")

        screen.draw.filled_rect(BUTTON_SOUND, "dimgray")
        screen.draw.text(f"SOUND: {'ON' if sound_on else 'OFF'}",
                         center=BUTTON_SOUND.center, fontsize=24, color="white")

        screen.draw.filled_rect(BUTTON_EXIT, "maroon")
        screen.draw.text("EXIT", center=BUTTON_EXIT.center,
                         fontsize=26, color="white")
        return

    for platform in platforms:
        platform.draw()

    draw_with_camera(flag)

    for enemy in enemies:
        enemy.draw()

    hero.draw()

    draw_hud()


def on_mouse_down(pos):
    global game_state, sound_on
    if game_state != "menu":
        return

    x, y = pos

    if BUTTON_START.collidepoint(x, y):
        start_game()
    elif BUTTON_SOUND.collidepoint(x, y):
        sound_on = not sound_on
        try:
            music.set_volume(0.5 if sound_on else 0.0)
        except Exception:
            pass
    elif BUTTON_EXIT.collidepoint(x, y):
        raise SystemExit


def on_key_down(key):
    if game_state != "play":
        return
    if key == keys.SPACE:
        hero.jump()


camera_x = 0.0

tile_surf = images.load("ground")
title_width, title_height = tile_surf.get_size()
has_tile = tile_surf is not None

IMAGES_VARIANTS_CACHE: dict[tuple[str, bool], str] = {}

game_state = "menu"
sound_on = True

BUTTON_START = Rect(WIDTH//2 - 70, 280, 140, 40)
BUTTON_SOUND = Rect(WIDTH//2 - 120, 340, 240, 40)
BUTTON_EXIT = Rect(WIDTH//2 - 60, 400, 120, 40)

hero = Hero(100, GROUND_Y)

enemies = [
    Enemy(310, 470, GROUND_Y - 150),
    Enemy(1110, 1310, GROUND_Y - 150),
    Enemy(2100, 2320, GROUND_Y - 150),
]

platforms = [
    Platform(0, GROUND_Y, WORLD_W, TILE_SIZE),
    Platform(300, GROUND_Y - 120, 180, TILE_SIZE),
    Platform(700, GROUND_Y - 160, 160, TILE_SIZE),
    Platform(1100, GROUND_Y - 120, 220, TILE_SIZE),
    Platform(1600, GROUND_Y - 180, 180, TILE_SIZE),
    Platform(2100, GROUND_Y - 120, 220, TILE_SIZE),
    Platform(2600, GROUND_Y - 120, 160, TILE_SIZE),
]

flag = Actor("flag", pos=(WORLD_W - 60, GROUND_Y - 32))

pgzrun.go()
