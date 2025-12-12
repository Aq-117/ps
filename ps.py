# Proper level system, but very tiny ignorable bugs.
import pygame
import random
import sys
import os
import math
import json
from enum import Enum

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 1000, 660
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plane Shooter")
global_particles = []

# Game States
class GameState(Enum):
    MAIN_MENU = 0
    PLAYING = 1
    PAUSED = 2
    SHOP = 3
    GAME_OVER = 4
    QUIT = 5
    LEVEL_SELECT = 6
    LEVEL_COMPLETE = 7

# Colors (fallback if images fail)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 120, 255)
RED = (255, 50, 50)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (150, 50, 200)
ORANGE = (255, 165, 0)

# Load images with error handling
def load_image(name, scale=1):
    try:
        img = pygame.image.load(os.path.join("assets", name)).convert_alpha()
        return pygame.transform.scale(img, 
               (int(img.get_width() * scale), 
               (int(img.get_height() * scale))))
    except:
        print(f"Failed to load {name}, using placeholder")
        # Create colored rectangles as fallback
        surf = pygame.Surface((50, 30), pygame.SRCALPHA)
        if "player" in name:
            pygame.draw.polygon(surf, BLUE, [(50,15), (0,0), (0,30)])
        elif "enemy" in name:
            pygame.draw.polygon(surf, RED, [(0,15), (50,0), (50,30)])
        elif "bullet" in name:
            surf = pygame.Surface((10, 5), pygame.SRCALPHA)
            pygame.draw.rect(surf, GREEN, (0, 0, 10, 5))
        return surf

# Load all assets
try:
    bg_img = pygame.image.load(os.path.join("assets", "bg.png")).convert()
    bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
except:
    print("Failed to load background, using black")
    bg_img = None

player_img = load_image("player.png", 0.7)
enemy_img = load_image("enemy.png", 0.7)
bullet_img = load_image("bullet-1.png", 0.5)

# After loading images, force specific sizes:
player_img = pygame.transform.scale(player_img, (50, 30))      # Width, Height
enemy_img = pygame.transform.scale(enemy_img, (50, 30))
bullet_img = pygame.transform.scale(bullet_img, (10, 5))
homing_missile_img = bullet_img  # Using same image for now

# Load sounds
try:
    pygame.mixer.music.load(os.path.join("assets", "music.mp3"))
    shoot_sound = pygame.mixer.Sound(os.path.join("assets", "shoot.mp3"))
    explosion_sound = pygame.mixer.Sound(os.path.join("assets", "explosion.mp3"))
    has_sound = True
except:
    print("Failed to load sound files")
    has_sound = False

# Play background music
if has_sound:
    pygame.mixer.music.play(-1)  # -1 means loop indefinitely

class Player:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.x = 100
        self.y = HEIGHT // 2
        self.img = player_img
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        self.max_health = 100
        self.health = self.max_health
        self.upgrade_cost_health = 100
        self.upgrade_cost_firerate = 150
        
        # Missile attributes
        self.missiles = 3
        self.max_missiles = 3
        self.missile_recharge_timer = 0
        self.missile_recharge_delay = 900  # 15 seconds at 60 FPS
        
        # Physics parameters
        self.speed = 5
        self.acceleration = 0.2
        self.deceleration = 0.1
        self.turn_speed = 0.2
        self.friction = 0.2
        self.gravity = 0.175
        self.lift = -0.7
        self.max_vertical_speed = 6
        self.max_horizontal_speed = 6
        self.gravity_cap = self.max_vertical_speed / 2
        
        # Movement vectors
        self.vel_x = 0
        self.vel_y = 0
        
        # Visual effects
        self.hit_flash = 0
        self.invulnerable = False
        self.death_animation = False
        self.death_timer = 0
        self.death_particles = []
        self.hit_particles = []
        self.dead = False
        self.death_complete = False

        self.mouse_control = False
        self.mouse_sensitivity = 0.3
        self.mouse_button_down = False

        self.rect = pygame.Rect(self.x, self.y, 
                               self.img.get_width() if self.img else 40,
                               self.img.get_height() if self.img else 30)

    def fire_missile(self, enemies):
        if self.missiles > 0 and not self.dead:
            closest_enemy = None
            min_distance = float('inf')
            
            for enemy in enemies:
                if not enemy.dead:
                    dist = math.sqrt((enemy.rect.centerx - self.rect.centerx)**2 + 
                                    (enemy.rect.centery - self.rect.centery)**2)
                    if dist < min_distance:
                        min_distance = dist
                        closest_enemy = enemy
            
            if closest_enemy:
                self.missiles -= 1
                if has_sound:
                    shoot_sound.play()
                return PlayerHomingMissile(self.x + self.rect.width, 
                                        self.y + self.rect.height//2,
                                        closest_enemy.rect.centerx,
                                        closest_enemy.rect.centery)
        return None

    def handle_input(self, keys, mouse_pos=None):
        if self.mouse_control and mouse_pos:
            target_x, target_y = mouse_pos
            dx = target_x - (self.x + self.rect.width/2)
            dy = target_y - (self.y + self.rect.height/2)
            distance = max(1, (dx**2 + dy**2)**0.5)
            target_vel_x = (dx / distance) * self.max_horizontal_speed
            target_vel_y = (dy / distance) * self.max_vertical_speed
            self.vel_x += (target_vel_x - self.vel_x) * 0.1
            self.vel_y += (target_vel_y - self.vel_y) * 0.1
            if distance < 20:
                self.vel_y += self.gravity * 0.5
        else:
            if keys[pygame.K_a]:
                if self.vel_x > 0:
                    self.vel_x = max(0, self.vel_x - self.turn_speed)
                else:
                    self.vel_x = max(-self.max_horizontal_speed, self.vel_x - self.acceleration)
            elif keys[pygame.K_d]:
                if self.vel_x < 0:
                    self.vel_x = min(0, self.vel_x + self.turn_speed)
                else:
                    self.vel_x = min(self.max_horizontal_speed, self.vel_x + self.acceleration)
            else:
                if self.vel_x > 0:
                    self.vel_x = max(0, self.vel_x - self.deceleration)
                elif self.vel_x < 0:
                    self.vel_x = min(0, self.vel_x + self.deceleration)
            
            if keys[pygame.K_w]:
                self.vel_y = max(self.vel_y + self.lift, -self.max_vertical_speed)
            elif keys[pygame.K_s]:
                self.vel_y = min(self.vel_y + self.acceleration, self.max_vertical_speed)
            else:
                gravity_effect = min(self.gravity, self.max_vertical_speed/2 - self.vel_y)
                self.vel_y += gravity_effect

        self.vel_x = max(-self.max_horizontal_speed, min(self.max_horizontal_speed, self.vel_x))

    def update_physics(self):
        self.x += self.vel_x
        self.y += self.vel_y
        
        if self.x < 0:
            self.x = 0
            self.vel_x = 0
        if self.x > WIDTH - self.rect.width:
            self.x = WIDTH - self.rect.width
            self.vel_x = 0
        if self.y < 0:
            self.y = 0
            self.vel_y = 0
        
        if self.y >= HEIGHT - self.rect.height:
            self.y = HEIGHT - self.rect.height
            if self.health > 0:
                self.health = 0
                self.init_death_effect()
                return True
        
        self.rect.x = self.x
        self.rect.y = self.y
        return False

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(self.x + self.rect.width, 
                                    self.y + self.rect.height//2, 
                                    True, damage=10))
            self.shoot_cooldown = self.shoot_delay
            if has_sound:
                shoot_sound.play()

    def flash(self):
        self.hit_flash = 10
        self.invulnerable = True
        for _ in range(8):
            color = random.choice([
                (255, 255, 100), (255, 200, 50), 
                (200, 200, 200), (120, 120, 120),
                (255, 255, 255), (100, 180, 255)
            ])
            self.hit_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'dx': random.uniform(-2, 2),
                'dy': random.uniform(-2, 2),
                'size': random.randint(2, 4),
                'life': random.randint(10, 18),
                'color': color
            })

    def init_death_effect(self):
        if self.dead:
            return
        self.death_animation = True
        self.death_timer = 60
        self.dead = True
        self.death_animation_complete = False
        self.death_complete = False

        for _ in range(20):
            self.death_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'dx': random.uniform(-3, 3),
                'dy': random.uniform(-3, 3),
                'size': random.randint(2, 5),
                'life': random.randint(20, 40)
            })

    def update_death_effect(self):
        if not self.death_animation:
            return False
            
        self.death_timer -= 1
        
        for p in self.death_particles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy'] 
            p['life'] -= 1
            if p['life'] <= 0:
                self.death_particles.remove(p)
        
        if self.death_timer <= 0:
            self.death_animation_complete = True
            self.death_complete = True
            return True
            
        return False

    def draw_death_effect(self, surface):
        if self.death_animation:
            for p in self.death_particles:
                pygame.draw.circle(surface, 
                                (255, random.randint(100, 200), 0),
                                (int(p['x']), int(p['y'])),
                                p['size'])

    def update_hit_particles(self):
        for p in self.hit_particles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)

    def draw_hit_particles(self, surface):
        for p in self.hit_particles:
            pygame.draw.circle(surface, p['color'], 
                            (int(p['x']), int(p['y'])), 
                            p['size'])

    def get_damage_state(self):
        health_pct = self.health / self.max_health  
        if health_pct > 0.75:
            return 0
        elif health_pct > 0.5:
            return 1
        elif health_pct > 0.25:
            return 2
        else:
            return 3
    
    def draw_health_bar(self, surface):
        bar_width = 50
        bar_height = 5
        health_percentage = self.health / self.max_health 
        outline_rect = pygame.Rect(self.x, self.y - 10, bar_width, bar_height)
        fill_width = max(0, bar_width * health_percentage)
        fill_rect = pygame.Rect(self.x, self.y - 10, fill_width, bar_height)
        
        if health_percentage > 0.6:
            fill_color = (0, 255, 0)
        elif health_percentage > 0.3:
            fill_color = (255, 255, 0)
        else:
            fill_color = (255, 0, 0)
        
        pygame.draw.rect(surface, (40, 40, 40), outline_rect)
        pygame.draw.rect(surface, fill_color, fill_rect)
        pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)
        
        if self.health < self.max_health:
            for i in range(1, 3):
                marker_pos = self.x + (bar_width * (i/3))
                pygame.draw.line(surface, (70, 70, 70), 
                            (marker_pos, self.y - 10), 
                            (marker_pos, self.y - 5), 1)

    def update(self, keys, mouse_pos=None):
        if self.dead:
            if not self.death_animation:
                self.init_death_effect()
                return False
            return self.update_death_effect()
            
        self.handle_input(keys, mouse_pos)
        
        death_occurred = self.update_physics()
        if death_occurred:
            return False
        
        if keys[pygame.K_SPACE] or self.mouse_button_down:
            self.shoot()
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        # Missile recharge
        if self.missiles < self.max_missiles:
            self.missile_recharge_timer += 1
            if self.missile_recharge_timer >= self.missile_recharge_delay:
                self.missiles = min(self.missiles + 1, self.max_missiles)
                self.missile_recharge_timer = 0
        
        if self.hit_flash > 0:
            self.hit_flash -= 1
            if self.hit_flash == 0:
                self.invulnerable = False
        
        self.update_hit_particles()

        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })
        
        return False

    def draw(self, surface):
        if self.img and not self.death_animation:
            damage_state = self.get_damage_state()
            plane_img = self.img.copy()
            
            if damage_state >= 1:
                for _ in range(3):
                    start_pos = (random.randint(5, 45), random.randint(5, 25))
                    end_pos = (start_pos[0] + random.randint(-10, 10), 
                            start_pos[1] + random.randint(-10, 10))
                    pygame.draw.line(plane_img, (80, 80, 80), start_pos, end_pos, 1)
            
            if damage_state >= 2:
                for _ in range(2):
                    hole_pos = (random.randint(5, 45), random.randint(5, 25))
                    pygame.draw.circle(plane_img, (0, 0, 0), hole_pos, random.randint(1, 2))
                    pygame.draw.circle(plane_img, (150, 150, 150), hole_pos, random.randint(1, 2), 1)
            
            if damage_state >= 3:
                for _ in range(2):
                    effect_pos = (random.randint(0, 10), random.randint(5, 25))
                    if random.random() > 0.5:
                        pygame.draw.circle(plane_img, (100, 100, 100, 150), effect_pos, random.randint(2, 3))
                    else:
                        pygame.draw.circle(plane_img, (255, random.randint(100, 150), 0), effect_pos, random.randint(1, 2))
            
            angle = -self.vel_y * 2
            original_rect = plane_img.get_rect(center=(self.x + plane_img.get_width()//2, 
                                                self.y + plane_img.get_height()//2))
            rotated_img = pygame.transform.rotate(plane_img, angle)
            rotated_rect = rotated_img.get_rect(center=original_rect.center)
            surface.blit(rotated_img, rotated_rect.topleft)
            
            if self.health < self.max_health:
                self.draw_health_bar(surface)
        
        elif not self.death_animation:
            pygame.draw.polygon(surface, (0, 120, 255), 
                            [(self.x+40, self.y+15), 
                            (self.x, self.y), 
                            (self.x, self.y+30)])
            
            if self.health < self.max_health:
                health_width = 40 * (self.health / self.max_health)
                pygame.draw.rect(surface, (255,0,0), (self.x, self.y-10, 40, 3))
                pygame.draw.rect(surface, (0,255,0), (self.x, self.y-10, health_width, 3))
        
        if self.mouse_control:
            mouse_pos = pygame.mouse.get_pos()
            pygame.draw.circle(surface, (255, 255, 0), mouse_pos, 5, 1)
            pygame.draw.line(surface, (255, 255, 0), 
                            (mouse_pos[0]-10, mouse_pos[1]), 
                            (mouse_pos[0]+10, mouse_pos[1]), 1)
            pygame.draw.line(surface, (255, 255, 0), 
                            (mouse_pos[0], mouse_pos[1]-10), 
                            (mouse_pos[0], mouse_pos[1]+10), 1)
    
        if self.hit_flash > 0 and self.hit_flash % 3 < 2 and not self.death_animation:
            flash_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 150))
            surface.blit(flash_surf, (self.rect.x, self.rect.y))
        
        self.draw_hit_particles(surface)
        
        if self.death_animation:
            self.draw_death_effect(surface)

class Bullet:
    def __init__(self, x, y, is_player, damage=1):
        self.x = x
        self.y = y
        self.img = bullet_img
        self.is_player = is_player
        self.damage = damage
        self.rect = pygame.Rect(x, y, 8, 4)
        self.speed_x = 10 if is_player else -7
        self.speed_y = 0

        if not is_player:
            self.img = pygame.transform.flip(self.img, True, False)
        
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.x = self.x
        self.rect.y = self.y

    def draw(self):
        if self.img:
            if self.speed_y != 0:
                angle = math.degrees(math.atan2(-self.speed_y, abs(self.speed_x)))
                rotated_img = pygame.transform.rotate(self.img, angle)
                screen.blit(rotated_img, (self.x, self.y))
            else:
                screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, 10, 5))

class PlayerHomingMissile(Bullet):
    def __init__(self, x, y, target_x, target_y):
        super().__init__(x, y, True, damage=30)
        self.img = homing_missile_img
        self.speed = 9  # Faster than regular bullets
        self.target_x = target_x
        self.target_y = target_y
        self.rect = pygame.Rect(x, y, 15, 5)
        
    def update(self, enemies):
        # Find closest enemy if we don't have a target
        closest_enemy = None
        min_distance = float('inf')
        
        for enemy in enemies:
            if not enemy.dead:
                dist = math.sqrt((enemy.rect.centerx - self.x)**2 + 
                                (enemy.rect.centery - self.y)**2)
                if dist < min_distance:
                    min_distance = dist
                    closest_enemy = enemy
        
        if closest_enemy:
            self.target_x = closest_enemy.rect.centerx
            self.target_y = closest_enemy.rect.centery
            
            # Calculate direction to target
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = max(1, math.sqrt(dx*dx + dy*dy))
            
            # Normalize and apply speed
            self.speed_x = (dx / dist) * self.speed
            self.speed_y = (dy / dist) * self.speed
        
        # Update position
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.x = self.x
        self.rect.y = self.y
        
        # Remove if off-screen
        if (self.x < -50 or self.x > WIDTH + 50 or 
            self.y < -50 or self.y > HEIGHT + 50):
            return False
            
        return True
        
    def draw(self):
        if self.img:
            angle = math.degrees(math.atan2(self.speed_y, self.speed_x))
            rotated_img = pygame.transform.rotate(self.img, -angle)
            screen.blit(rotated_img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (0, 255, 255), (self.x, self.y, 15, 5))  # Cyan for player missiles

class EnemyHomingMissile(Bullet):
    def __init__(self, x, y, target_x, target_y):
        super().__init__(x, y, False, damage=20)
        self.img = homing_missile_img
        self.base_speed = 3
        self.target_x = target_x
        self.target_y = target_y
        self.angle = 0
        self.creation_time = pygame.time.get_ticks()
        self.lifespan = 5000
        self.last_direction_change = 0
        self.direction_change_delay = 200
        self.current_dx = -1
        self.current_dy = 0
        
    def update(self, player_x, player_y):
        self.target_x = player_x
        self.target_y = player_y
        
        if pygame.time.get_ticks() - self.creation_time > self.lifespan:
            return False
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_direction_change > self.direction_change_delay:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = max(1, (dx**2 + dy**2)**0.5)
            self.current_dx = dx / distance
            self.current_dy = dy / distance
            self.last_direction_change = current_time
        
        self.x += self.current_dx * self.base_speed
        self.y += self.current_dy * self.base_speed
        self.x -= 1.5  # Always drift left slightly
        
        self.rect.x = self.x
        self.rect.y = self.y
        return True
        
    def draw(self):
        if self.img:
            angle = math.degrees(math.atan2(self.current_dy, self.current_dx))
            rotated_img = pygame.transform.rotate(self.img, -angle)
            screen.blit(rotated_img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, 10, 5))

class Bomb(Bullet):
    def __init__(self, x, y):
        super().__init__(x, y, False, damage=30)
        self.img = pygame.transform.rotate(bullet_img, -90)
        self.speed_x = -0.5
        self.speed_y = 4
        self.rect = pygame.Rect(x, y, 10, 15)
        self.rotation_angle = 0
        self.rotation_speed = 0

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rotation_angle = (self.rotation_angle + self.rotation_speed) % 360
        self.rect.x = self.x
        self.rect.y = self.y
        return self.y < HEIGHT  # Remove when below screen

    def draw(self):
        rotated_img = pygame.transform.rotate(self.img, self.rotation_angle)
        rect = rotated_img.get_rect(center=(self.x + self.img.get_width()/2, 
                                        self.y + self.img.get_height()/2))
        screen.blit(rotated_img, rect.topleft)

class Enemy:
    def __init__(self, x, y, enemy_type, max_health=10):
        self.x = x
        self.y = y
        self.img = enemy_img
        self.type = enemy_type
        self.max_health = max_health
        self.health = max_health
        self.dead = False
        self.death_particles = []
        self.hit_particles = []
        self.rect = pygame.Rect(x, y, 50, 30)
        self.shoot_cooldown = random.randint(30, 90)  # Original cooldown range
        
    def draw_health_bar(self, surface):
        if self.health < self.max_health:
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)
            elif health_pct > 0.3:
                color = (255, 255, 0)
            else:
                color = (255, 0, 0)
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)
            pygame.draw.rect(surface, color, fill_rect)
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)

    def draw(self, surface):
        if self.img:
            surface.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(surface, (255, 50, 50),
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        
        self.draw_health_bar(surface)
        
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(surface, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))
        
        for p in self.hit_particles:
            pygame.draw.circle(surface, p['color'], 
                            (int(p['x']), int(p['y'])), 
                            p['size'])

    def update(self):
        for p in self.hit_particles[:]:
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)
                
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
            
        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })

    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self, player=None):
        self.shoot_cooldown = random.randint(30, 90)  # Original cooldown
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage=10)

    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),
                (255, 200, 50),
                (200, 200, 200),
                (120, 120, 120),
                (255, 255, 255),
                (100, 180, 255)
            ])
            self.death_particles.append({
                'x': self.rect.centerx,
                'y': self.rect.centery,
                'dx': random.uniform(-2, 2),
                'dy': random.uniform(-2, 2),
                'size': random.randint(1, 4),
                'life': random.randint(15, 30),
                'color': color
            })

    def draw_particles(self, surface):
        for p in self.death_particles[:]:
            pygame.draw.circle(surface, p['color'],
                             (int(p['x']), int(p['y'])),
                             p['size'])
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['life'] -= 1
            if p['life'] <= 0:
                self.death_particles.remove(p)

class Enemy1(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(50, HEIGHT - 50), 1, 10)
        self.speed = 3  # Original speed was 3
        
    def update(self):
        super().update()
        self.x -= self.speed
        self.rect.x = self.x

class Enemy2(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(50, HEIGHT - 50), 2, 20)
        self.stop_x = WIDTH * 0.8
        self.speed = 3  # Original speed
        self.has_stopped = False
        self.shoot_cooldown = random.randint(30, 90)  # Original cooldown
        
    def update(self):
        super().update()
        if not self.has_stopped:
            self.x -= self.speed
            if self.x <= self.stop_x:
                self.has_stopped = True
            self.rect.x = self.x

    def shoot(self):
        self.shoot_cooldown = random.randint(70, 120)  # Original cooldown
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage=15)  # Original damage

class Enemy3(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(50, HEIGHT - 50), 3, 20)
        self.stop_x = WIDTH * 0.7
        self.speed = 3  # Original speed
        self.vertical_speed = 1.5  # Original speed
        self.direction = 1
        self.has_stopped = False
        self.shoot_cooldown = random.randint(60, 100)  # Original cooldown
        
    def update(self):
        super().update()
        if not self.has_stopped:
            self.x -= self.speed
            if self.x <= self.stop_x:
                self.has_stopped = True
            self.rect.x = self.x
        else:
            self.y += self.vertical_speed * self.direction
            if self.y <= 0 or self.y >= HEIGHT - 30:
                self.direction *= -1
            self.rect.y = self.y

    def shoot(self):
        self.shoot_cooldown = random.randint(50, 100)  # Original cooldown
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage=10)  # Original damage

class Enemy4(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(50, HEIGHT - 50), 4, 20)
        self.stop_x = WIDTH * 0.9
        self.speed = 3  # Original speed
        self.shoot_cooldown = 210  # Original 3.5 second delay
        
    def update(self):
        super().update()
        if self.x > self.stop_x:
            self.x -= self.speed
            self.rect.x = self.x
            
    def should_shoot(self, player):
        return (super().should_shoot() and 
                self.x <= self.stop_x and
                abs(player.y - self.y) < HEIGHT/2)
        
    def shoot(self, player_x, player_y):
        self.shoot_cooldown = 240  # Original 4 second cooldown
        if has_sound:
            shoot_sound.play()
        missile = EnemyHomingMissile(self.x, self.y + 15, player_x, player_y)
        missile.damage = 20  # Original damage
        return missile

class Enemy5(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(int(HEIGHT * 0.2), int(HEIGHT * 0.7)), 5, 10)
        self.base_speed = 4
        self.current_speed = self.base_speed
        self.speed_x = -self.base_speed
        self.speed_y = 0
        self.angle = 0
        self.target_angle = 0
        self.angle_change_timer = 0
        self.angle_change_delay = random.randint(120, 210)
        self.original_img = self.img.copy()  # Store original for rotation
        self.set_new_angle()

    def set_new_angle(self):
        min_angle = -25
        max_angle = 25
        
        if self.y < HEIGHT * 0.3:
            self.target_angle = random.randint(0, max_angle)
        elif self.y > HEIGHT * 0.7:
            self.target_angle = random.randint(min_angle, 0)
        else:
            self.target_angle = random.randint(min_angle, max_angle)
        
        self.angle_change_timer = 0

    def update(self):
        self.angle_change_timer += 1
        if self.angle_change_timer >= self.angle_change_delay:
            self.set_new_angle()
            self.angle_change_delay = random.randint(180, 240)

        angle_diff = self.target_angle - self.angle
        if abs(angle_diff) > 0.5:
            self.angle += angle_diff * 0.05
            self.current_speed = self.base_speed * 0.8
        else:
            self.current_speed = self.base_speed

        rad_angle = math.radians(self.angle)
        self.speed_x = -self.current_speed * math.cos(rad_angle)
        self.speed_y = self.current_speed * math.sin(rad_angle)

        self.x += self.speed_x
        self.y += self.speed_y

        if self.y < HEIGHT * 0.2:
            self.y = HEIGHT * 0.2
            self.set_new_angle()
        elif self.y > HEIGHT * 0.8:
            self.y = HEIGHT * 0.8
            self.set_new_angle()

        self.rect.x = self.x
        self.rect.y = self.y
        
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def draw(self, screen):
        if self.img:
            rotated_img = pygame.transform.rotate(self.img, -self.angle)
            rotated_rect = rotated_img.get_rect()
            rotated_rect.center = (self.x + self.img.get_width() // 2, 
                                self.y + self.img.get_height() // 2)
            screen.blit(rotated_img, rotated_rect)
        else:
            pygame.draw.polygon(screen, (200, 50, 200),
                            [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))

    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        if has_sound:
            shoot_sound.play()
        
        rad_angle = math.radians(self.angle)
        speed_x = -10 * math.cos(rad_angle)
        speed_y = 10 * math.sin(rad_angle)
        
        bullet = Bullet(self.x, self.y + 15, False, damage=20)
        bullet.speed_x = speed_x
        bullet.speed_y = speed_y
        return bullet

class Enemy6(Enemy):
    def __init__(self):
        super().__init__(-100, random.randint(50, HEIGHT - 50), 6, 10)
        self.speed = 3
        self.shoot_cooldown = random.randint(60, 120)
        self.img = pygame.transform.flip(self.img, True, False)
        
    def update(self):
        super().update()
        self.x += self.speed
        self.rect.x = self.x
        
        if random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.left + 5,
                'y': self.rect.centery,
                'dx': random.uniform(-1.5, -0.5),
                'dy': random.uniform(-0.3, 0.3),
                'size': random.randint(1, 3),
                'life': random.randint(15, 25),
                'color': (150, 150, 150)
            })

    def shoot(self):
        self.shoot_cooldown = random.randint(60, 120)
        if has_sound:
            shoot_sound.play()
        
        bullet = Bullet(self.x + self.rect.width, self.y + self.rect.height//2, False, damage=10)
        bullet.speed_x = 8
        bullet.speed_y = 0
        bullet.img = pygame.transform.flip(bullet_img, True, False)
        return bullet

class Enemy7(Enemy):
    def __init__(self):
        super().__init__(WIDTH, random.randint(50, int(HEIGHT * 0.35)), 7, 20)
        self.speed = 3
        self.bomb_cooldown = random.randint(30, 60)
        self.bomb_trail = []
        
    def update(self):
        super().update()
        self.x -= self.speed
        self.rect.x = self.x
        
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1
            
        for particle in self.bomb_trail[:]:
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.bomb_trail.remove(particle)

    def draw(self, surface):
        surface.blit(self.img, (self.x, self.y))
        super().draw(surface)
        
        for particle in self.bomb_trail:
            pygame.draw.circle(surface, (255, 100, 0), 
                             (int(particle['x']), int(particle['y'])), 
                             particle['size'])

    def should_drop_bomb(self):
        return (self.bomb_cooldown <= 0 and 
                self.x < WIDTH - 50 and 
                self.x > 50)

    def drop_bomb(self):
        self.bomb_cooldown = random.randint(30, 60)
        
        for _ in range(5):
            self.bomb_trail.append({
                'x': self.x + random.randint(0, self.rect.width),
                'y': self.y + self.rect.height,
                'dx': random.uniform(-0.4, 0.4),
                'dy': random.uniform(0.4, 1.0),
                'size': random.randint(1, 3),
                'life': random.randint(15, 30),
                'color': (255, random.randint(50, 150), 0)
            })
        
        if has_sound:
            shoot_sound.play()
        
        return Bomb(self.x + self.rect.width//2, self.y + self.rect.height)

class Level:
    def __init__(self, number, unlocked=False):
        self.number = number
        self.unlocked = unlocked
        self.completed = False
        self.currently_playing = False  # New state
        self.enemy_waves = []
        self.current_wave = 0
        self.wave_timer = 0
        self.level_timer = 0
        self.all_enemies_spawned = False
        self.level_complete = False
        
        # Generate enemy waves based on level number
        self.generate_waves()
        
    def generate_waves(self):
        # Basic level design - can be expanded with more complex patterns
        if self.number == 1:
            # Level 1: Simple wave of basic enemies
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy1() for _ in range(3)]},
                {"delay": 180, "enemies": [Enemy1() for _ in range(5)]}
            ]
        elif self.number == 2:
            # Level 2: Mix of enemy types
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy1(), Enemy1(), Enemy2()]},
                {"delay": 180, "enemies": [Enemy2(), Enemy2(), Enemy1()]}
            ]
        elif self.number == 3:
            # Level 3: More enemies with different patterns
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy3(), Enemy3()]},
                {"delay": 180, "enemies": [Enemy2(), Enemy2(), Enemy1(), Enemy1()]}
            ]
        elif self.number == 4:
            # Level 4: First appearance of homing missile enemy
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy4()]},
                {"delay": 180, "enemies": [Enemy1(), Enemy1(), Enemy2(), Enemy2()]},
                {"delay": 300, "enemies": [Enemy4(), Enemy1(), Enemy1()]}
            ]
        elif self.number == 5:
            # Level 5: More challenging mix
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy5()]},
                {"delay": 120, "enemies": [Enemy5()]},
                {"delay": 240, "enemies": [Enemy3(), Enemy3(), Enemy2()]}
            ]
        elif self.number == 6:
            # Level 6: Enemy from left side
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy6() for _ in range(3)]},
                {"delay": 180, "enemies": [Enemy6(), Enemy1(), Enemy1()]}
            ]
        elif self.number == 7:
            # Level 7: Bomber enemies
            self.enemy_waves = [
                {"delay": 60, "enemies": [Enemy7()]},
                {"delay": 180, "enemies": [Enemy7(), Enemy1(), Enemy1()]},
                {"delay": 300, "enemies": [Enemy7(), Enemy7()]}
            ]
        else:
            # Default pattern for higher levels
            enemy_types = [Enemy1, Enemy2, Enemy3, Enemy4, Enemy5, Enemy6, Enemy7]
            weights = [30, 25, 15, 10, 10, 5, 5]
            
            # Increase difficulty with level number
            num_waves = min(5, 2 + self.number // 5)
            enemies_per_wave = min(10, 3 + self.number // 3)
            
            for i in range(num_waves):
                wave_enemies = []
                for _ in range(enemies_per_wave):
                    enemy_class = random.choices(enemy_types, weights=weights, k=1)[0]
                    wave_enemies.append(enemy_class())
                
                self.enemy_waves.append({
                    "delay": 60 + i * 120,
                    "enemies": wave_enemies
                })
    
    def update(self, enemies):
        self.level_timer += 1
        
        # Check if all waves have been spawned
        if self.current_wave >= len(self.enemy_waves):
            self.all_enemies_spawned = True
            return
        
        # Check if it's time to spawn the next wave
        if self.level_timer >= self.enemy_waves[self.current_wave]["delay"]:
            enemies.extend(self.enemy_waves[self.current_wave]["enemies"])
            self.current_wave += 1
    
    def is_complete(self, enemies):
        # Level is complete if all enemies are dead and all waves have been spawned
        if not self.all_enemies_spawned:
            return False
            
        # Check if any enemies are still alive
        for enemy in enemies:
            if not enemy.dead:
                return False
                
        return True

class Game:
    def __init__(self):
        self.state = GameState.MAIN_MENU
        self.player = Player()
        self.enemies = []
        self.enemy_bullets = []
        self.player_bullets = []
        self.enemy_spawn_timer = 0
        self.current_score = 0
        self.planes_destroyed = 0
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.title_font = pygame.font.SysFont(None, 72)
        self.instruction_font = pygame.font.SysFont(None, 24)
        self.pakts_font = pygame.font.SysFont(None, 50)
        self.player_name = "Player1"
        self.mouse_pos = (0, 0)
        self.mouse_clicked = False
        self.active_button = None
        self.already_saved = False
        self.save_file = "savegame.json"
        self.save_data = {
            "player_name": "Player1",
            "high_score": 0,
            "total_planes_destroyed": 0,
            "upgrades": {
                "max_health": 100,
                "shoot_delay": 15,
                "health_upgrade_cost": 100,
                "firerate_upgrade_cost": 150
            },
            "unspent_score": 0,
            "levels_unlocked": 1,
            "levels_completed": []
        }
        
        # Level system
        self.levels = [Level(i+1, i==0) for i in range(25)]  # 25 levels
        self.current_level = None
        self.level_score = 0
        self.level_planes_destroyed = 0
        self.load_game()  
        
    def load_game(self, force_defaults=False):
        try:
            if not force_defaults:
                with open(self.save_file, "r") as f:
                    self.save_data = json.load(f)
            
            # Initialize all values from save data
            self.player_name = self.save_data.get("player_name", "Player1")
            self.current_score = 0  # Start fresh each game
            self.planes_destroyed = 0  # Current session only
            
            # Get upgrades (use defaults if force_defaults is True)
            upgrades = self.save_data.get("upgrades", {
                "max_health": 100,
                "shoot_delay": 15,
                "health_upgrade_cost": 100,
                "firerate_upgrade_cost": 150
            })
            
            # Apply upgrades to player
            if hasattr(self, 'player'):
                self.player.max_health = upgrades.get("max_health", 100)
                self.player.health = self.player.max_health
                self.player.shoot_delay = upgrades.get("shoot_delay", 15)
                self.player.upgrade_cost_health = upgrades.get("health_upgrade_cost", 100)
                self.player.upgrade_cost_firerate = upgrades.get("firerate_upgrade_cost", 150)
                
            # Load level progress
            levels_unlocked = self.save_data.get("levels_unlocked", 1)
            levels_completed = self.save_data.get("levels_completed", [])
            
            for i, level in enumerate(self.levels):
                if i < levels_unlocked:
                    level.unlocked = True
                if str(i+1) in levels_completed:
                    level.completed = True
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            if not force_defaults:
                print(f"Error loading save: {e}, creating new save")
            # Initialize new save data
            self.save_data = {
                "player_name": "Player1",
                "high_score": 0,
                "total_planes_destroyed": 0,
                "upgrades": {
                    "max_health": 100,
                    "shoot_delay": 15,
                    "health_upgrade_cost": 100,
                    "firerate_upgrade_cost": 150
                },
                "unspent_score": 0,
                "levels_unlocked": 1,
                "levels_completed": []
            }
            self.save_game()

    def save_game(self):
        # Update high score to be max of previous high score and current session score
        # (Don't include unspent score in high score comparison)
        self.save_data["high_score"] = max(self.current_score, self.save_data.get("high_score", 0))
        
        # Always save upgrades
        self.save_data["upgrades"] = {
            "max_health": self.player.max_health,
            "shoot_delay": self.player.shoot_delay,
            "health_upgrade_cost": self.player.upgrade_cost_health,
            "firerate_upgrade_cost": self.player.upgrade_cost_firerate
        }
        
        # Save level progress
        self.save_data["levels_unlocked"] = max(
            self.save_data.get("levels_unlocked", 1),
            sum(1 for level in self.levels if level.unlocked)
        )
        
        # Update completed levels
        completed_levels = []
        for level in self.levels:
            if level.completed:
                completed_levels.append(str(level.number))
        self.save_data["levels_completed"] = completed_levels
        
        try:
            with open(self.save_file, "w") as f:
                json.dump(self.save_data, f, indent=4)
        except Exception as e:
            print(f"Failed to save game: {e}")

    def reset_game(self):
        """Completely reset the game state for a fresh start"""
        # Create a new player instance to ensure clean state
        self.player = Player()
        
        # Apply upgrades from save data
        self.player.max_health = self.save_data["upgrades"]["max_health"]
        self.player.health = self.player.max_health
        self.player.shoot_delay = self.save_data["upgrades"]["shoot_delay"]
        self.player.upgrade_cost_health = self.save_data["upgrades"]["health_upgrade_cost"]
        self.player.upgrade_cost_firerate = self.save_data["upgrades"]["firerate_upgrade_cost"]
        
        # Clear all game objects
        self.enemies = []
        self.enemy_bullets = []
        self.player.bullets = []
        global_particles.clear()
        
        # Reset timers and counters
        self.enemy_spawn_timer = 0
        self.current_score = 0
        self.planes_destroyed = 0
        self.level_score = 0
        self.level_planes_destroyed = 0
        self.already_saved = False
        
        # Clear any failure flags
        if hasattr(self, 'level_failed'):
            del self.level_failed
        
        # Reset the current level if one exists
        if self.current_level:
            # Create a fresh level instance to ensure clean state
            level_num = self.current_level.number
            self.levels[level_num-1] = Level(level_num, True)
            self.current_level = self.levels[level_num-1]

    def draw_main_menu(self):
        if bg_img:
            screen.blit(bg_img, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Title with proper spacing
        title = self.title_font.render("PLANE SHOOTER", True, WHITE)
        title_rect = title.get_rect(center=(WIDTH//2, HEIGHT//4 - 70))
        screen.blit(title, title_rect)
        
        # Buttons with proper spacing
        buttons = [
            {"text": "Start Game", "action": GameState.PLAYING, "reset": True},
            {"text": "Levels", "action": GameState.LEVEL_SELECT},
            {"text": "Shop", "action": GameState.SHOP},
            {"text": "Quit", "action": GameState.QUIT}
        ]
        
        for i, button in enumerate(buttons):
            y_pos = HEIGHT//2 - 170 + i * 70
            if self.draw_button(button["text"], WIDTH//2 - 100, y_pos, 200, 50, GRAY, LIGHT_GRAY):
                if button.get("reset", False):
                    self.reset_game()
                self.state = button["action"]
        
        # New Player button at the bottom
        if self.draw_button("New Player", WIDTH//2 - 100, HEIGHT - 100, 200, 50, RED, (255, 150, 150)):
            self.reset_for_new_player()
        
        # Stats with proper spacing at bottom
        stats = [
            f"Player: {self.player_name}",
            f"High Score: {self.save_data['high_score']}",
            f"Total Planes Destroyed: {self.save_data['total_planes_destroyed']}",
            f"Available Score: {self.save_data['unspent_score'] + self.current_score}"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, WHITE)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 270 + i * 40))

    def draw_level_select(self):
        if bg_img:
            screen.blit(bg_img, (0, 0))
        else:
            screen.fill(BLACK)
            
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Title
        title = self.title_font.render("SELECT LEVEL", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 30))
        
        # Back button
        if self.draw_button("Back", 20, 20, 100, 40, GRAY, LIGHT_GRAY):
            self.state = GameState.MAIN_MENU
        
        # Draw level buttons (5x5 grid)
        level_buttons = []
        for i in range(5):  # Rows
            for j in range(5):  # Columns
                level_num = i * 5 + j + 1
                if level_num > 25:  # Only show 25 levels
                    continue
                    
                level = self.levels[level_num-1]
                x = WIDTH//2 - 250 + j * 110
                y = 120 + i * 100
                
                # Determine button color based on state
                if not level.unlocked:
                    color = (50, 50, 50)  # Dark gray for locked
                    hover_color = (50, 50, 50)
                elif level.currently_playing:
                    color = (100, 100, 255)  # Blue for current level
                    hover_color = (150, 150, 255)
                elif level.completed:
                    color = (0, 150, 0)  # Green for completed
                    hover_color = (0, 200, 0)
                else:
                    color = (70, 70, 70)  # Gray for unlocked but not completed
                    hover_color = (100, 100, 100)
                
                # Draw level button
                if self.draw_button(str(level_num), x, y, 80, 80, color, hover_color):
                    if level.unlocked:
                        self.start_level(level_num)
        
        pygame.display.flip()

    def start_level(self, level_num):
        # Reset all current flags first
        for level in self.levels:
            level.currently_playing = False
        
        # Set the new current level
        self.current_level = self.levels[level_num-1]
        self.current_level.currently_playing = True
        self.reset_game()  # This should handle all necessary resets
        self.current_level = self.levels[level_num-1]
        # Reset level-specific progress
        self.current_level.current_wave = 0
        self.current_level.wave_timer = 0
        self.current_level.level_timer = 0
        self.current_level.all_enemies_spawned = False
        self.current_level.level_complete = False
        self.level_score = 0
        self.level_planes_destroyed = 0
        self.state = GameState.PLAYING
        # small flag

    def draw_level_complete(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Level Complete text
        if hasattr(self, 'level_failed'):
            complete_text = self.title_font.render("LEVEL FAILED!", True, RED)
            del self.level_failed  # Clear the flag
        else:
            complete_text = self.title_font.render("LEVEL COMPLETE!", True, GREEN)
        screen.blit(complete_text, (WIDTH//2 - complete_text.get_width()//2, HEIGHT//6))
        
        # Stats
        stats = [
            f"Level: {self.current_level.number}",
            f"Score: {self.level_score}",
            f"Planes Destroyed: {self.level_planes_destroyed}",
            f"Health Remaining: {self.player.health}/{self.player.max_health}",
            f"Total Score: {self.current_score + self.save_data['unspent_score']}"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, WHITE)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//3 - 40 + i * 40))
        
        # Buttons
        button_states = {
            'next': False,
            'replay': False,
            'menu': False,
            'shop': False
        }
        
        # Next level button (only if there is a next level and it's unlocked)
        next_level_num = self.current_level.number + 1
        next_level_unlocked = next_level_num <= 25 and (next_level_num <= self.save_data["levels_unlocked"])
        
        if next_level_unlocked:
            button_states['next'] = self.draw_button(
                "Next Level", WIDTH//2 - 220, HEIGHT//2 + 150, 200, 50, LIGHT_GRAY, WHITE
            )
        else:
            # Draw disabled button
            pygame.draw.rect(screen, (100, 100, 100), (WIDTH//2 - 220, HEIGHT//2 + 150, 200, 50))
            text = self.font.render("Next Level", True, (200, 200, 200))
            screen.blit(text, (WIDTH//2 - 220 + 100 - text.get_width()//2, HEIGHT//2 + 150 + 25 - text.get_height()//2))
        
        button_states['replay'] = self.draw_button(
            "Replay", WIDTH//2 - 220 + 220, HEIGHT//2 + 150, 200, 50, LIGHT_GRAY, WHITE
        )
        button_states['menu'] = self.draw_button(
            "Main Menu", WIDTH//2 - 220, HEIGHT//2 + 220, 200, 50, LIGHT_GRAY, WHITE
        )
        button_states['shop'] = self.draw_button(
            "Shop", WIDTH//2 - 220 + 220, HEIGHT//2 + 220, 200, 50, LIGHT_GRAY, WHITE
        )
        
        # Handle button clicks
        if button_states['next'] and next_level_unlocked:
            self.start_level(next_level_num)
        elif button_states['replay']:
            self.start_level(self.current_level.number)  # This will do a full reset
            # # Reset level-specific stats but keep session progress
            # self.level_score = 0
            # self.level_planes_destroyed = 0
            # self.player.health = self.player.max_health  # Full heal
            # self.player.dead = False
            # self.player.death_complete = False
            
            # # Clear all enemies and bullets
            # self.enemies = []
            # self.enemy_bullets = []
            # self.player_bullets = []
            
            # # Restart the same level
            # self.current_level.current_wave = 0
            # self.current_level.wave_timer = 0
            # self.current_level.level_timer = 0
            # self.current_level.all_enemies_spawned = False
            
            # self.state = GameState.PLAYING
            pygame.time.delay(200)  # Small delay to prevent instant clicks

        elif button_states['menu']:
            self.state = GameState.MAIN_MENU
        elif button_states['shop']:
            self.state = GameState.SHOP
        
        pygame.display.flip()

    def draw_shop(self):
        if bg_img:
            screen.blit(bg_img, (0, 0))
        else:
            screen.fill(BLACK)
            
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        title = self.title_font.render("UPGRADE SHOP", True, YELLOW)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        # Player stats
        total_available_score = self.save_data["unspent_score"] + self.current_score
        stats = [
            f"Available Score: {total_available_score}",
            f"Health: {self.player.max_health} (+10: {self.player.upgrade_cost_health})",
            f"Fire Rate: {60/self.player.shoot_delay:.1f} shots/sec (+1: {self.player.upgrade_cost_firerate})"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, WHITE)
            screen.blit(text, (WIDTH//2 - 200, 150 + i * 40))
        
        # Upgrade buttons
        button_states = {
            'upgrade_health': False,
            'upgrade_firerate': False,
            'back': False
        }
    
        # Check each button and update states
        total_available = self.save_data["unspent_score"] + self.current_score

        button_states['upgrade_health'] = self.draw_button(
            f"Upgrade Health ({self.player.upgrade_cost_health})", 
            WIDTH//2 - 150, 300, 300, 50,
            LIGHT_GRAY if total_available >= self.player.upgrade_cost_health else GRAY,
            WHITE if total_available >= self.player.upgrade_cost_health else GRAY
        )
        
        button_states['upgrade_firerate'] = self.draw_button(
            f"Upgrade Fire Rate ({self.player.upgrade_cost_firerate})", 
            WIDTH//2 - 150, 370, 300, 50,
            LIGHT_GRAY if total_available >= self.player.upgrade_cost_firerate else GRAY,
            WHITE if total_available >= self.player.upgrade_cost_firerate else GRAY
        )
        
        button_states['back'] = self.draw_button(
            "Back to Menu", 
            WIDTH//2 - 150, 440, 300, 50,
            LIGHT_GRAY, WHITE
        )
        
        return button_states

    def draw_button(self, text, x, y, width, height, inactive_color, active_color):
        mouse_over = x < self.mouse_pos[0] < x + width and y < self.mouse_pos[1] < y + height
        
        color = active_color if mouse_over else inactive_color
        pygame.draw.rect(screen, color, (x, y, width, height))
        
        text_surf = self.font.render(text, True, BLACK)
        text_rect = text_surf.get_rect(center=(x + width/2, y + height/2))
        screen.blit(text_surf, text_rect)
        
        return mouse_over and self.mouse_clicked

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        title = self.title_font.render("PAUSED", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        
        buttons = [
            {"text": "Resume", "action": GameState.PLAYING},
            {"text": "Main Menu", "action": GameState.MAIN_MENU, "reset": True},
            {"text": "Quit", "action": GameState.QUIT}
        ]

        for i, button in enumerate(buttons):
            y_pos = HEIGHT//2 + i * 70
            if self.draw_button(button["text"], WIDTH//2 - 100, y_pos, 200, 50, GRAY, LIGHT_GRAY):
                if button.get("reset", False):
                    self.reset_game()
                self.state = button["action"]
        
        pygame.display.flip()

    def draw_game(self):
        # Draw background
        if bg_img:
            screen.blit(bg_img, (0, 0))
        else:
            screen.fill(BLACK)
        
        # Only draw game elements if not in game over state
        if self.state != GameState.GAME_OVER and self.state != GameState.LEVEL_COMPLETE:
            # Draw bullets
            for bullet in self.player.bullets:
                bullet.draw()
            for bullet in self.enemy_bullets:
                bullet.draw()

            # Draw enemies
            for enemy in self.enemies:
                enemy.draw(screen)
                enemy.draw_particles(screen)

            # Draw player (including death animation)
            self.player.draw(screen)
            self.player.draw_hit_particles(screen)

            # Draw particles
            for p in global_particles[:]:
                pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), p['size'])
                p['x'] += p['dx']
                p['y'] += p['dy']
                p['life'] -= 1
                if p['life'] <= 0:
                    global_particles.remove(p)

            # Draw UI (only if not dead)
            if not self.player.dead:
                health_text = self.font.render(f"Health: {self.player.health}/{self.player.max_health}", True, WHITE)
                score_text = self.font.render(f"Score: {self.current_score} (Best: {self.save_data['high_score']})", True, WHITE)
                planes_text = self.font.render(f"Planes: {self.planes_destroyed}", True, WHITE)
                missile_text = self.font.render(f"Missiles: {self.player.missiles}/{self.player.max_missiles}", True, (0, 255, 255))
                level_text = self.font.render(f"Level: {self.current_level.number if self.current_level else 'Endless'}", True, WHITE)
                
                screen.blit(health_text, (10, 10))
                screen.blit(score_text, (10, 50))
                screen.blit(planes_text, (10, 90))
                screen.blit(missile_text, (10, 130))
                screen.blit(level_text, (10, 170))
        elif self.state == GameState.LEVEL_COMPLETE:
            # Draw level complete screen
            self.draw_level_complete()
            return
        else:
            # Draw game over screen when appropriate
            self.draw_game_over()
            return  # Skip the rest of the drawing

        pygame.display.flip()
        
    def check_collisions(self):
        # Player bullets hit enemies
        for bullet in self.player.bullets[:]:
            for enemy in self.enemies[:]:
                if bullet.rect.colliderect(enemy.rect) and not enemy.dead:
                    enemy.health -= bullet.damage
                    
                    if enemy.health <= 0:
                        enemy.create_death_particles()
                        global_particles.extend(enemy.death_particles)
                        self.player.bullets.remove(bullet)
                        self.enemies.remove(enemy)
                        score_gain = 1 * enemy.max_health
                        self.current_score += score_gain
                        self.level_score += score_gain
                        self.planes_destroyed += 1
                        self.level_planes_destroyed += 1
                        if has_sound:
                            explosion_sound.play()
                    else:
                        self.player.bullets.remove(bullet)
                        for _ in range(3):
                            enemy.death_particles.append({
                                'x': bullet.rect.centerx,
                                'y': bullet.rect.centery,
                                'dx': random.uniform(-1, 1),
                                'dy': random.uniform(-1, 1),
                                'size': random.randint(1, 2),
                                'life': random.randint(5, 10),
                                'color': (255, random.randint(100, 200), 0)
                            })
                        if has_sound:
                            shoot_sound.play()
                    break

        # Enemy collision with player
        for enemy in self.enemies[:]:
            if not self.player.invulnerable and not enemy.dead and self.player.rect.colliderect(enemy.rect):
                if self.player.health > 0:
                    self.player.health = 0
                    self.player.init_death_effect()
                    if has_sound:
                        explosion_sound.play()
                break

    def handle_events(self):
        self.mouse_clicked = False  # Reset click state each frame
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state = GameState.QUIT
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.handle_escape_key()
                    
                if event.key == pygame.K_p and self.state == GameState.PLAYING:
                    self.state = GameState.PAUSED
                    
                if event.key == pygame.K_m:
                    self.player.mouse_control = not self.player.mouse_control
                    
                if event.key == pygame.K_e and self.state == GameState.PLAYING:
                    missile = self.player.fire_missile(self.enemies)
                    if missile:
                        self.player.bullets.append(missile)
                        
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = event.pos
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_clicked = True

    def handle_escape_key(self):
        if self.state == GameState.SHOP:
            self.state = GameState.MAIN_MENU
        elif self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING
        elif self.state == GameState.GAME_OVER:
            self.state = GameState.MAIN_MENU
        elif self.state == GameState.MAIN_MENU:
            self.state = GameState.QUIT
        elif self.state == GameState.LEVEL_SELECT:
            self.state = GameState.MAIN_MENU
        elif self.state == GameState.LEVEL_COMPLETE:
            self.state = GameState.MAIN_MENU

    def update_game(self):
        if self.state != GameState.PLAYING:
            return
            
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        # Update player
        death_complete = self.player.update(keys, mouse_pos)
        
        # Check if player died and transition to GAME_OVER state after animation
        if self.player.dead and self.player.death_complete:
            if self.current_level:
                # In level mode, don't go to game over, just show level complete with failure
                self.level_failed = True  # Add this flag to track failed levels
                self.state = GameState.LEVEL_COMPLETE
            else:
                self.state = GameState.GAME_OVER
                self.save_game()
            return
        
        # Don't update game logic if player is in death animation
        if self.player.dead:
            return
        
        # Update level if we're in level mode
        if self.current_level:
            self.current_level.update(self.enemies)
            
            # Check if level is complete
            if self.current_level.is_complete(self.enemies):
                # Mark level as completed
                self.current_level.completed = True
                self.current_level.currently_playing = False  # Clear current flag

                
                # Unlock next level if it exists
                next_level_num = self.current_level.number + 1
                if next_level_num <= 25:
                    self.levels[next_level_num-1].unlocked = True
                    self.save_data["levels_unlocked"] = max(
                        self.save_data.get("levels_unlocked", 1),
                        next_level_num
                    )
                
                self.state = GameState.LEVEL_COMPLETE
                self.save_game()
                return
            # When level is failed:
            if self.player.dead and self.player.death_complete:
                if self.current_level:
                    self.current_level.currently_playing = False  # Clear current flag
                    self.level_failed = True
                    self.state = GameState.LEVEL_COMPLETE

        else:
            # Endless mode enemy spawning
            self.enemy_spawn_timer += 1
            if self.enemy_spawn_timer > 120:
                enemy_type = random.choices([1, 2, 3, 4, 5, 6, 7], weights=[20, 30, 20, 10, 10, 7, 7], k=1)[0]
                if enemy_type == 1:
                    self.enemies.append(Enemy1())
                elif enemy_type == 2:
                    self.enemies.append(Enemy2())
                elif enemy_type == 3:
                    self.enemies.append(Enemy3())
                elif enemy_type == 4:
                    self.enemies.append(Enemy4())
                elif enemy_type == 5:
                    self.enemies.append(Enemy5())
                elif enemy_type == 6:
                    self.enemies.append(Enemy6())
                else:
                    self.enemies.append(Enemy7())
                self.enemy_spawn_timer = 0

        # Update player bullets
        for bullet in self.player.bullets[:]:
            if isinstance(bullet, PlayerHomingMissile):
                if not bullet.update(self.enemies):
                    self.player.bullets.remove(bullet)
            else:
                bullet.update()
                if bullet.x > WIDTH:
                    self.player.bullets.remove(bullet)

        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update()
            if (enemy.x < -100) or (enemy.x > WIDTH + 100):
                self.enemies.remove(enemy)
                continue
            if not enemy.dead:
                if enemy.type == 4:
                    if enemy.should_shoot(self.player):
                        self.enemy_bullets.append(enemy.shoot(self.player.x, self.player.y))
                elif enemy.type == 6:
                    if enemy.should_shoot():
                        bullet = enemy.shoot()
                        if bullet:
                            self.enemy_bullets.append(bullet)
                elif enemy.type == 7:
                    if enemy.should_drop_bomb():
                        bomb = enemy.drop_bomb()
                        self.enemy_bullets.append(bomb)
                else:
                    if enemy.should_shoot():
                        self.enemy_bullets.append(enemy.shoot())

        # Update enemy bullets
        i = 0
        while i < len(self.enemy_bullets):
            bullet = self.enemy_bullets[i]
            remove_bullet = False
            if isinstance(bullet, EnemyHomingMissile):
                if not bullet.update(self.player.x, self.player.y):
                    remove_bullet = True
                elif (bullet.x < -50 or bullet.x > WIDTH + 50 or
                        bullet.y < -50 or bullet.y > HEIGHT + 50):
                    remove_bullet = True
            elif isinstance(bullet, Bomb):
                if not bullet.update():
                    remove_bullet = True
            else:
                bullet.update()
                if bullet.x < 0:
                    remove_bullet = True
            if not remove_bullet and bullet.rect.colliderect(self.player.rect):
                remove_bullet = True
                if not self.player.invulnerable:
                    self.player.health -= bullet.damage
                    if self.player.health <= 0:
                        self.player.health = 0
                        self.player.init_death_effect()
                    else:
                        self.player.flash()
                    if has_sound:
                        explosion_sound.play()
            if remove_bullet:
                self.enemy_bullets.pop(i)
            else:
                i += 1

        self.check_collisions()

    def reset_for_new_player(self):
        """Completely reset all progress for a new player"""
        self.save_data = {
            "player_name": "Player1",
            "high_score": 0,
            "total_planes_destroyed": 0,
            "upgrades": {
                "max_health": 100,
                "shoot_delay": 15,
                "health_upgrade_cost": 100,
                "firerate_upgrade_cost": 150
            },
            "unspent_score": 0,
            "levels_unlocked": 1,
            "levels_completed": []
        }
        self.save_game()
        
        # Create a new player instance with default values
        self.player = Player()
        # Explicitly set the default values
        self.player.max_health = 100
        self.player.health = 100
        self.player.shoot_delay = 15
        self.player.upgrade_cost_health = 100
        self.player.upgrade_cost_firerate = 150
        
        # Reset levels
        for i, level in enumerate(self.levels):
            level.unlocked = (i == 0)
            level.completed = False
        
        self.reset_game()  # Reset current session
        self.state = GameState.MAIN_MENU  # Force refresh the menu display


    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Game Over text
        game_over_text = self.title_font.render("GAME OVER", True, RED)
        screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//6))
        
        # Stats
        stats = [
            f"Session Score: {self.current_score}",
            f"High Score: {self.save_data['high_score']}",
            f"Session Planes: {self.planes_destroyed}",
            f"Total Planes: {self.save_data['total_planes_destroyed']}",
            f"Health Level: {self.player.max_health}",
            f"Fire Rate: {60/self.player.shoot_delay:.1f} shots/sec"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, WHITE)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//3 - 40 + i * 40))
        
        # Buttons
        game_over_button_states = {
            'play_again': False,
            'menu': False,
            'quit': False
        }
        
        game_over_button_states['play_again'] = self.draw_button(
            "Play Again", WIDTH//2 - 100, HEIGHT//2 + 100, 200, 50, LIGHT_GRAY, WHITE
        )
        game_over_button_states['menu'] = self.draw_button(
            "Main Menu", WIDTH//2 - 100, HEIGHT//2 + 170, 200, 50, LIGHT_GRAY, WHITE
        )
        game_over_button_states['quit'] = self.draw_button(
            "Quit", WIDTH//2 - 100, HEIGHT//2 + 240, 200, 50, LIGHT_GRAY, WHITE
        )
        
        return game_over_button_states

    def run(self):
        running = True
        while running:
            self.handle_events()
            
            if self.state == GameState.QUIT:
                running = False
                continue
                
            # Clear screen
            if bg_img:
                screen.blit(bg_img, (0, 0))
            else:
                screen.fill(BLACK)
            
            # Draw the appropriate screen
            if self.state == GameState.MAIN_MENU:
                self.draw_main_menu()
            elif self.state == GameState.PLAYING:
                self.update_game()
                self.draw_game()
            elif self.state == GameState.PAUSED:
                # Only draw game once when paused (no flickering)
                if not hasattr(self, 'paused_game_surface'):
                    # Create a surface to store the paused game state
                    self.paused_game_surface = pygame.Surface((WIDTH, HEIGHT))
                    self.draw_game()  # Draw current game state
                    # Copy the current screen to our paused surface
                    self.paused_game_surface.blit(screen, (0, 0))
                
                # Draw the paused game state
                screen.blit(self.paused_game_surface, (0, 0))
                # Draw pause overlay - reduced alpha for less darkness
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((50, 50, 50, 120))  # Changed from (0,0,0,180) to lighter gray
                screen.blit(overlay, (0, 0))
                self.draw_pause_menu()
            elif self.state == GameState.SHOP:
                shop_button_states = self.draw_shop()
                total_available = self.save_data["unspent_score"] + self.current_score
                
                if shop_button_states.get('upgrade_health', False) and total_available >= self.player.upgrade_cost_health:
                    if self.current_score >= self.player.upgrade_cost_health:
                        self.current_score -= self.player.upgrade_cost_health
                    else:
                        remaining_cost = self.player.upgrade_cost_health - self.current_score
                        self.current_score = 0
                        self.save_data["unspent_score"] -= remaining_cost
                    
                    self.player.max_health += 10
                    self.player.health = self.player.max_health
                    self.player.upgrade_cost_health = int(self.player.upgrade_cost_health * 1.5)
                    self.save_game()
                    
                elif shop_button_states.get('upgrade_firerate', False) and total_available >= self.player.upgrade_cost_firerate:
                    if self.current_score >= self.player.upgrade_cost_firerate:
                        self.current_score -= self.player.upgrade_cost_firerate
                    else:
                        remaining_cost = self.player.upgrade_cost_firerate - self.current_score
                        self.current_score = 0
                        self.save_data["unspent_score"] -= remaining_cost
                    
                    self.player.shoot_delay = max(5, self.player.shoot_delay - 3)
                    self.player.upgrade_cost_firerate = int(self.player.upgrade_cost_firerate * 1.75)
                    self.save_game()
                    
                elif shop_button_states.get('back', False):
                    # When leaving shop, add current score to unspent
                    self.save_data["unspent_score"] += self.current_score
                    self.current_score = 0
                    self.state = GameState.MAIN_MENU
                    self.save_game()
                    pygame.time.delay(200)  # Prevent accidental double clicks
                    
            elif self.state == GameState.GAME_OVER:
                # Only save once when entering game over state
                if not self.already_saved:
                    self.save_data["unspent_score"] += self.current_score
                    self.save_data["total_planes_destroyed"] += self.planes_destroyed
                    self.save_game()
                    self.already_saved = True

                game_over_button_states = self.draw_game_over()
                
                if game_over_button_states.get('play_again', False):
                    self.reset_game()
                    self.already_saved = False
                    self.state = GameState.PLAYING
                elif game_over_button_states.get('menu', False):
                    self.reset_game()
                    self.already_saved = False
                    self.state = GameState.MAIN_MENU
                elif game_over_button_states.get('quit', False):
                    self.state = GameState.QUIT
            elif self.state == GameState.LEVEL_SELECT:
                self.draw_level_select()
            elif self.state == GameState.LEVEL_COMPLETE:
                self.draw_level_complete()
            
            pygame.display.flip()
            self.clock.tick(60)
            
            # Clear paused game surface when unpausing
            if hasattr(self, 'paused_game_surface'):
                del self.paused_game_surface

# Start the game
if __name__ == "__main__":
    game = Game()
    game.run()