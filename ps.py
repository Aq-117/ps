#player movement updated with acceleration, decelaration and gravity
import pygame
import random
import sys
import os
import math

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 1000, 660
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plane Shooter")
global_particles = []

# Colors (fallback if images fail)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

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
            pygame.draw.polygon(surf, (0, 120, 255), [(50,15), (0,0), (0,30)])
        elif "enemy" in name:
            pygame.draw.polygon(surf, (255, 50, 50), [(0,15), (50,0), (50,30)])
        elif "bullet" in name:
            surf = pygame.Surface((10, 5), pygame.SRCALPHA)
            pygame.draw.rect(surf, (0, 255, 0), (0, 0, 10, 5))
        return surf

# Load all assets
try:
    bg_img = pygame.image.load(os.path.join("assets", "bg.png")).convert()
    bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
except:
    print("Failed to load background, using black")
    bg_img = None

player_img = load_image("player.png", 0.7)
enemy_img = load_image("enemy.jpg", 0.7)
bullet_img = load_image("bullet.png", 0.5)

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

# Player Class
class Player:
    def __init__(self):
        self.x = 100
        self.y = HEIGHT // 2
        self.img = player_img
        self.health = 10
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        
        # Physics parameters
        self.speed = 5
        self.acceleration = 0.2
        self.deceleration = 0.1
        self.turn_speed = 0.2 #slowing down when changing direction
        self.friction = 0.2
        self.gravity = 0.175
        self.lift = -0.7  # Negative because y increases downward
        self.max_vertical_speed = 5
        self.max_horizontal_speed = 5
        self.gravity_cap = self.max_vertical_speed / 2  # Gravity can only reach half of max speed
        
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
        
        self.rect = pygame.Rect(self.x, self.y, 
                               self.img.get_width() if self.img else 40,
                               self.img.get_height() if self.img else 30)

    def handle_input(self, keys):
        # # Horizontal movement with friction
        # if keys[pygame.K_a]:
        #     self.vel_x -= self.acceleration
        # elif keys[pygame.K_d]:
        #     self.vel_x += self.acceleration
        # else:
        #     # Apply friction when no key is pressed
        #     if abs(self.vel_x) < self.friction:
        #         self.vel_x = 0
        #     elif self.vel_x > 0:
        #         self.vel_x -= self.friction
        #     elif self.vel_x < 0:
        #         self.vel_x += self.friction

        # Horizontal movement with proper acceleration/deceleration
        if keys[pygame.K_a]:
            if self.vel_x > 0:  # If moving right and pressing left
                self.vel_x = max(0, self.vel_x - self.turn_speed)  # Slow down first
            else:
                self.vel_x = max(-self.max_horizontal_speed, self.vel_x - self.acceleration)
        elif keys[pygame.K_d]:
            if self.vel_x < 0:  # If moving left and pressing right
                self.vel_x = min(0, self.vel_x + self.turn_speed)  # Slow down first
            else:
                self.vel_x = min(self.max_horizontal_speed, self.vel_x + self.acceleration)
        else:
            # Gradual deceleration when no key is pressed
            if self.vel_x > 0:
                self.vel_x = max(0, self.vel_x - self.deceleration)
            elif self.vel_x < 0:
                self.vel_x = min(0, self.vel_x + self.deceleration)
        
        # Vertical movement
        if keys[pygame.K_w]:
            self.vel_y = max(self.vel_y + self.lift, -self.max_vertical_speed)  # Upward movement with lift
        elif keys[pygame.K_s]:
            # Downward movement - can exceed natural gravity limit
            self.vel_y = min(self.vel_y + self.acceleration, self.max_vertical_speed)
        else:
            # Natural gravity - limited to half of max vertical speed
            gravity_effect = min(self.gravity, self.max_vertical_speed/2 - self.vel_y)
            self.vel_y += gravity_effect
        
        # Clamp horizontal speed
        self.vel_x = max(-self.max_horizontal_speed, min(self.max_horizontal_speed, self.vel_x))

    def update_physics(self):
        # Update position
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Boundary checks
        if self.x < 0:
            self.x = 0
            self.vel_x = 0
        if self.x > WIDTH // 2:
            self.x = WIDTH // 2
            self.vel_x = 0
        if self.y < 0:
            self.y = 0
            self.vel_y = 0
        
        # Ground collision with instant death
        if self.y >= HEIGHT - self.rect.height:
            self.y = HEIGHT - self.rect.height
            if self.health > 0:
                self.health = 0
                self.init_death_effect()
                return True  # Signal death occurred
        
        # Update collision rect
        self.rect.x = self.x
        self.rect.y = self.y
        return False  # No death occurred

    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(self.x + self.rect.width, 
                                    self.y + self.rect.height//2, 
                                    True))
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
        
        # Update particles
        for p in self.death_particles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy'] 
            p['life'] -= 1
            if p['life'] <= 0:
                self.death_particles.remove(p)
        
        # Check if animation complete
        if self.death_timer <= 0:
            self.death_animation_complete = True
            return True  # Signal that death sequence is done
            
        return False  # Still animating

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

    # def update(self, keys):
    #     if self.dead:  # Don't process input if already dead
    #         self.update_death_effect()
    #         return
            
    #     self.handle_input(keys)
    #     death_occurred = self.update_physics()
        
    #     if death_occurred:
    #         return  # Skip other updates if player just died
        
    #     # Shooting
    #     if keys[pygame.K_SPACE]:
    #         self.shoot()
    #     if self.shoot_cooldown > 0:
    #         self.shoot_cooldown -= 1
        
    #     # Update hit flash
    #     if self.hit_flash > 0:
    #         self.hit_flash -= 1
    #         if self.hit_flash == 0:
    #             self.invulnerable = False
        
    #     # Update particles
    #     self.update_hit_particles()
    #     if self.death_animation:
    #         self.update_death_effect()

    def update(self, keys):
        if self.dead:
            # Only update death animation if dead
            death_complete = self.update_death_effect()
            return death_complete
            
        # Handle normal player updates
        self.handle_input(keys)
        
        # Update physics
        death_occurred = self.update_physics()
        if death_occurred:
            return False  # Death just occurred
        
        # Handle shooting
        if keys[pygame.K_SPACE]:
            self.shoot()
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        # Update hit flash
        if self.hit_flash > 0:
            self.hit_flash -= 1
            if self.hit_flash == 0:
                self.invulnerable = False
        
        # Update particles
        self.update_hit_particles()
        
        return False  # No death occurred

    def draw(self, surface):
        # Draw the plane
        if self.img and not self.death_animation:
            # Calculate angle based on movement (more tilt when moving faster vertically)
            angle = -self.vel_y * 2  # Adjust multiplier for more/less tilt
            
            # Store original center position before rotation
            original_rect = self.img.get_rect(center=(self.x + self.img.get_width()//2, 
                                                self.y + self.img.get_height()//2))
            
            # Rotate the image
            rotated_img = pygame.transform.rotate(self.img, angle)
            
            # Get rect of rotated image and set its center to original center
            rotated_rect = rotated_img.get_rect(center=original_rect.center)
            
            # Draw the rotated image
            surface.blit(rotated_img, rotated_rect.topleft)
        
        elif not self.death_animation:
            # Fallback drawing
            pygame.draw.polygon(surface, (0, 120, 255), 
                            [(self.x+40, self.y+15), 
                                (self.x, self.y), 
                                (self.x, self.y+30)])
            
        # Draw hit flash if active
        if self.hit_flash > 0 and self.hit_flash % 3 < 2 and not self.death_animation:
            flash_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 150))
            surface.blit(flash_surf, (self.rect.x, self.rect.y))
        
        # Draw particles
        self.draw_hit_particles(surface)
        if self.death_animation:
            self.draw_death_effect(surface)

# Bullet Class
class Bullet:
    def __init__(self, x, y, is_player):
        self.x = x
        self.y = y
        self.img = bullet_img
        self.is_player = is_player
        self.rect = pygame.Rect(x, y, 8, 4)  # Fixed size for fallback
        
        # Default straight movement
        self.speed_x = 10 if is_player else -7
        self.speed_y = 0
        
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.rect.x = self.x
        self.rect.y = self.y

    def draw(self):
        if self.img:
            # Rotate bullet if moving diagonally
            if self.speed_y != 0:
                angle = math.degrees(math.atan2(-self.speed_y, abs(self.speed_x)))
                rotated_img = pygame.transform.rotate(self.img, angle)
                screen.blit(rotated_img, (self.x, self.y))
            else:
                screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, 10, 5))

# Enemy Type 1: Original behavior (moves left across screen)
class Enemy1:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 1  # Add enemy type identifier
        self.death_particles = []
        self.dead = False  # <-- Add this line
        
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 50, 50),
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        
    def update(self):
        self.x -= self.speed
        self.rect.x = self.x
        self.shoot_cooldown -= 1
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False)

    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),   # yellow spark
                (255, 200, 50),    # orange spark
                (200, 200, 200),   # light gray (smoke)
                (120, 120, 120),   # dark gray (smoke)
                (255, 255, 255),   # white flash
                (100, 180, 255),   # blue spark
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

# Enemy Type 2: Stops at 10% of screen and stays still
class Enemy2:
    def __init__(self):
        self.stop_x = WIDTH * 0.8  # 20% from right
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 2
        self.has_stopped = False
        self.death_particles = []
        self.dead = False  # <-- Add this line
        
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 100, 100),  # Different color for visibility
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        
    def update(self):
        if not self.has_stopped:
            self.x -= self.speed
            if self.x <= self.stop_x:
                self.has_stopped = True
            self.rect.x = self.x
        
        self.shoot_cooldown -= 1
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(20, 60)  # Faster shooting than type 1
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False)

    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),   # yellow spark
                (255, 200, 50),    # orange spark
                (200, 200, 200),   # light gray (smoke)
                (120, 120, 120),   # dark gray (smoke)
                (255, 255, 255),   # white flash
                (100, 180, 255),   # blue spark
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

# Enemy Type 3: Stops at 20% of screen then moves vertically
class Enemy3:
    def __init__(self):
        self.stop_x = WIDTH * 0.7  # 30% from right
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.vertical_speed = 1.5
        self.direction = 1  # 1 for down, -1 for up
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 3
        self.has_stopped = False
        self.death_particles = []
        self.dead = False  # <-- Add this line
        
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 150, 150),  # Different color for visibility
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        
    def update(self):
        if not self.has_stopped:
            self.x -= self.speed
            if self.x <= self.stop_x:
                self.has_stopped = True
            self.rect.x = self.x
        else:
            # Move vertically and change direction at screen edges
            self.y += self.vertical_speed * self.direction
            if self.y <= 0 or self.y >= HEIGHT - 30:
                self.direction *= -1
            self.rect.y = self.y
        
        self.shoot_cooldown -= 1
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(40, 80)  # Different shooting pattern
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False)
    
    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),   # yellow spark
                (255, 200, 50),    # orange spark
                (200, 200, 200),   # light gray (smoke)
                (120, 120, 120),   # dark gray (smoke)
                (255, 255, 255),   # white flash
                (100, 180, 255),   # blue spark
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

class HomingMissile:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.img = homing_missile_img
        self.base_speed = 3  # Reduced base speed
        self.rect = pygame.Rect(x, y, 10, 5)
        self.target_x = target_x
        self.target_y = target_y
        self.angle = 0
        self.creation_time = pygame.time.get_ticks()
        self.lifespan = 5000  # 5 seconds in milliseconds
        self.last_direction_change = 0
        self.direction_change_delay = 200  # 0.2 second delay between direction changes
        self.current_dx = -1  # Initial leftward direction
        self.current_dy = 0
        
    def update(self, player_x, player_y):
        # Update target position
        self.target_x = player_x
        self.target_y = player_y
        
        # Check lifespan
        if pygame.time.get_ticks() - self.creation_time > self.lifespan:
            return False  # Signal to remove this missile
        
        # Calculate direction to player (only if enough time passed since last change)
        current_time = pygame.time.get_ticks()
        if current_time - self.last_direction_change > self.direction_change_delay:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = max(1, (dx**2 + dy**2)**0.5)
            
            # Normalize direction
            self.current_dx = dx / distance
            self.current_dy = dy / distance
            self.last_direction_change = current_time
        
        # Apply movement with consistent speed
        self.x += self.current_dx * self.base_speed
        self.y += self.current_dy * self.base_speed
        
        # Maintain some leftward momentum
        self.x -= 1.5
        
        self.rect.x = self.x
        self.rect.y = self.y
        return True  # Signal to keep this missile
        
    def draw(self):
        if self.img:
            angle = math.degrees(math.atan2(self.current_dy, self.current_dx))
            rotated_img = pygame.transform.rotate(self.img, -angle)
            screen.blit(rotated_img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, 10, 5))

class Enemy4:
    def __init__(self):
        self.stop_x = WIDTH * 0.9  # 10% from right
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = 210  # 3.5 seconds at 60 FPS (60*3.5)
        self.initial_delay = True
        self.rect = pygame.Rect(self.x, self.y, 50, 30)
        self.type = 4
        self.death_particles = []
        self.dead = False  # <-- Add this line
        
        
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 200, 200),  # Different color
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        
    def update(self):
        if self.x > self.stop_x:
            self.x -= self.speed
            self.rect.x = self.x
        
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
    def should_shoot(self, player):
        # Only shoot if cooldown is 0 and we're in position
        return (self.shoot_cooldown <= 0 and 
                self.x <= self.stop_x and
                abs(player.y - self.y) < HEIGHT/2)  # Only shoot if player is roughly aligned
        
    def shoot(self, player_x, player_y):
        self.shoot_cooldown = 240  # 4 second cooldown (60*4)
        if has_sound:
            shoot_sound.play()
        return HomingMissile(self.x, self.y + 15, player_x, player_y)
    
    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),   # yellow spark
                (255, 200, 50),    # orange spark
                (200, 200, 200),   # light gray (smoke)
                (120, 120, 120),   # dark gray (smoke)
                (255, 255, 255),   # white flash
                (100, 180, 255),   # blue spark
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

class Enemy5:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(int(HEIGHT * 0.2), int(HEIGHT * 0.7))  # Starts between 20%-70% of screen
        self.img = enemy_img
        self.base_speed = 4  # Faster than Enemy1 (speed 3)
        self.current_speed = self.base_speed
        self.speed_x = -self.base_speed  # Always moving left
        self.speed_y = 0
        self.angle = 0  # Current movement angle (degrees)
        self.target_angle = 0
        self.angle_change_timer = 0
        self.angle_change_delay = random.randint(120, 210)  # 2-3.5 seconds at 60 FPS
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, 50, 30)
        self.type = 5
        self.dead = False
        self.set_new_angle()  # Initialize first angle
        self.death_particles = []

    def set_new_angle(self):
        # Calculate new angle (limited to prevent too steep angles)
        min_angle = -25  # Degrees (upward)
        max_angle = 25   # Degrees (downward)
        
        # Adjust if near boundaries
        if self.y < HEIGHT * 0.3:  # Too high
            self.target_angle = random.randint(0, max_angle)
        elif self.y > HEIGHT * 0.7:  # Too low
            self.target_angle = random.randint(min_angle, 0)
        else:
            self.target_angle = random.randint(min_angle, max_angle)
        
        self.angle_change_timer = 0

    def update(self):
        # Update angle change timer
        self.angle_change_timer += 1
        if self.angle_change_timer >= self.angle_change_delay:
            self.set_new_angle()
            self.angle_change_delay = random.randint(180, 240)  # New 3-4 second delay

        # Smoothly transition to target angle
        angle_diff = self.target_angle - self.angle
        if abs(angle_diff) > 0.5:  # If significant difference remains
            self.angle += angle_diff * 0.05  # 5% of difference each frame
            # Reduce speed while turning (for smoothness)
            self.current_speed = self.base_speed * 0.8
        else:
            self.current_speed = self.base_speed

        # Convert angle to movement
        rad_angle = math.radians(self.angle)
        self.speed_x = -self.current_speed * math.cos(rad_angle)
        self.speed_y = self.current_speed * math.sin(rad_angle)

        # Update position
        self.x += self.speed_x
        self.y += self.speed_y

        # Enforce vertical boundaries
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

    def draw(self):
        if self.img:
            # Rotate image to face movement direction
            rotated_img = pygame.transform.rotate(self.img, -self.angle)
            # Get the rect of the rotated image
            rotated_rect = rotated_img.get_rect()
            # Set the center position to match the enemy's position
            rotated_rect.center = (self.x + self.img.get_width() // 2, 
                                self.y + self.img.get_height() // 2)
            # Draw the rotated image
            screen.blit(rotated_img, rotated_rect)
        else:
            # Fallback drawing
            pygame.draw.polygon(screen, (200, 50, 200),  # Different color
                            [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])

    def should_shoot(self):
        return self.shoot_cooldown <= 0

    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        if has_sound:
            shoot_sound.play()
        
        # Shoot in direction plane is facing
        rad_angle = math.radians(self.angle)
        speed_x = -10 * math.cos(rad_angle)  # Negative for leftward
        speed_y = 10 * math.sin(rad_angle)
        
        # Create directional bullet
        bullet = Bullet(self.x, self.y + 15, False)
        bullet.speed_x = speed_x
        bullet.speed_y = speed_y
        return bullet
    
    def create_death_particles(self):
        for _ in range(15):
            color = random.choice([
                (255, 255, 100),   # yellow spark
                (255, 200, 50),    # orange spark
                (200, 200, 200),   # light gray (smoke)
                (120, 120, 120),   # dark gray (smoke)
                (255, 255, 255),   # white flash
                (100, 180, 255),   # blue spark
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

# Game setup
player = Player()
enemies = []
enemy_bullets = []
enemy_spawn_timer = 0
score = 0
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

title_font = pygame.font.SysFont(None, 72)
instruction_font = pygame.font.SysFont(None, 24)
pakts_font = pygame.font.SysFont(None, 50)
def draw_start_screen():
    if bg_img:
        screen.blit(bg_img, (0, 0))
    else:
        screen.fill(BLACK)
    
    # Game title
    title = title_font.render("PLANE SHOOTER", True, WHITE)
    title_rect = title.get_rect(center=(WIDTH//2, HEIGHT//3))
    screen.blit(title, title_rect)
    
    # Instructions
    instructions = [
        "Controls:",
        "WASD - Move your plane",
        "SPACE - Shoot bullets",
        "Avoid enemy bullets and destroy enemies!",
        "",
        f"Starting Health: {player.health}"
    ]
    
    for i, line in enumerate(instructions):
        text = instruction_font.render(line, True, WHITE)
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 + i*30))
        screen.blit(text, text_rect)
    
    # Start prompt
    prompt = pakts_font.render("Press any key to start", True, WHITE)
    prompt_rect = prompt.get_rect(center=(WIDTH//2, HEIGHT - 100))
    screen.blit(prompt, prompt_rect)
    
    pygame.display.flip()

def show_start_screen():
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                waiting = False
        draw_start_screen()
        clock.tick(60)

# Show start screen before main game
show_start_screen()

def check_collisions():
    global score, global_particles

    # Player bullets hit enemies
    for bullet in player.bullets[:]:
        for enemy in enemies[:]:
            if bullet.rect.colliderect(enemy.rect) and not enemy.dead:
                enemy.create_death_particles()
                global_particles.extend(enemy.death_particles)  # Move particles to global list
                player.bullets.remove(bullet)
                enemies.remove(enemy)  # Instantly remove enemy
                score += 10
                if has_sound:
                    explosion_sound.play()
                break

    # Enemy collision with player (INSTANT DEATH)
    for enemy in enemies[:]:
        if not player.invulnerable and not enemy.dead and player.rect.colliderect(enemy.rect):
            if player.health > 0:
                player.health = 0  # Instantly set to 0
                player.init_death_effect()  # Start death animation
                if has_sound:
                    explosion_sound.play()
            break

def game_over():
    global game_over_triggered, running
    if game_over_triggered:
        return
    game_over_triggered = True
    text = font.render(f"GAME OVER - Score: {score}", True, WHITE)
    screen.blit(text, (WIDTH//2 - 150, HEIGHT//2))
    pygame.display.flip()
    pygame.time.wait(3000)
    running = False  # Ensure main loop exits
    if has_sound:
        pygame.mixer.music.stop()
    pygame.quit()
    sys.exit()

# Main game loop
running = True
game_over = False
game_over_time = 0
clock = pygame.time.Clock()

while running:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # 2. Get Input
    keys = pygame.key.get_pressed()
    
    # 3. Update Game State
    if not player.dead and not game_over:
        # Update player with proper physics
        player.update(keys)
        
        # Spawn enemies
        enemy_spawn_timer += 1
        if enemy_spawn_timer > 120:
            enemy_type = random.choices([1, 2, 3, 4, 5], weights=[20, 30, 20, 10, 10], k=1)[0]
            if enemy_type == 1:
                enemies.append(Enemy1())
            elif enemy_type == 2:
                enemies.append(Enemy2())
            elif enemy_type == 3:
                enemies.append(Enemy3())
            elif enemy_type == 4:
                enemies.append(Enemy4())
            else:
                enemies.append(Enemy5())
            enemy_spawn_timer = 0

        # Update player bullets
        for bullet in player.bullets[:]:
            bullet.update()
            if bullet.x > WIDTH:
                player.bullets.remove(bullet)

        # Update enemies
        for enemy in enemies[:]:
            enemy.update()
            if enemy.x < -40:
                enemies.remove(enemy)
                continue
            if not enemy.dead:
                if enemy.type == 4:
                    if enemy.should_shoot(player):
                        enemy_bullets.append(enemy.shoot(player.x, player.y))
                else:
                    if enemy.should_shoot():
                        enemy_bullets.append(enemy.shoot())

        # Update enemy bullets
        i = 0
        while i < len(enemy_bullets):
            bullet = enemy_bullets[i]
            remove_bullet = False
            if isinstance(bullet, HomingMissile):
                if not bullet.update(player.x, player.y):
                    remove_bullet = True
                elif (bullet.x < -50 or bullet.x > WIDTH + 50 or
                      bullet.y < -50 or bullet.y > HEIGHT + 50):
                    remove_bullet = True
            else:
                bullet.update()
                if bullet.x < 0:
                    remove_bullet = True
            if not remove_bullet and bullet.rect.colliderect(player.rect):
                remove_bullet = True
                if not player.invulnerable:
                    player.health -= 1
                    if player.health <= 0:
                        player.health = 0
                        player.init_death_effect()
                    else:
                        player.flash()
                    if has_sound:
                        explosion_sound.play()
            if remove_bullet:
                enemy_bullets.pop(i)
            else:
                i += 1

        check_collisions()

    # 4. Drawing
    if bg_img:
        screen.blit(bg_img, (0, 0))
    else:
        screen.fill(BLACK)

    # Draw bullets
    for bullet in player.bullets:
        bullet.draw()
    for bullet in enemy_bullets:
        bullet.draw()

    # Draw enemies
    for enemy in enemies:
        enemy.draw()
        enemy.draw_particles(screen)

    # Draw player
    player.draw(screen)
    player.draw_hit_particles(screen)

    # Draw particles
    for p in global_particles[:]:
        pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), p['size'])
        p['x'] += p['dx']
        p['y'] += p['dy']
        p['life'] -= 1
        if p['life'] <= 0:
            global_particles.remove(p)

    # Draw UI
    health_text = font.render(f"Health: {player.health}", True, WHITE)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (10, 50))

    # # 5. Death and Game Over Handling
    # if player.dead and not game_over:
    #     if player.death_animation_complete:
    #         game_over = True
    #         game_over_time = pygame.time.get_ticks()
    #         # Clear all game objects
    #         enemies.clear()
    #         enemy_bullets.clear()
    #         player.bullets.clear()
    
    # if game_over:
    #     # Show game over for 2 seconds before quitting
    #     game_over_text = font.render("GAME OVER - Final Score: " + str(score), True, WHITE)
    #     screen.blit(game_over_text, (WIDTH//2 - 180, HEIGHT//2))
        
    #     if pygame.time.get_ticks() - game_over_time > 2000:
    #         running = False

    # In your main game loop (replace the current death handling section):

    # 5. Death and Game Over Handling
    if player.dead:
        # Update death animation and check if it completed
        death_complete = player.update(keys)  # This now returns True when animation finishes
        
        if death_complete and not game_over:
            game_over = True
            game_over_time = pygame.time.get_ticks()
            # Clear all game objects
            enemies.clear()
            enemy_bullets.clear()
            player.bullets.clear()
            # Play game over sound if available
            if has_sound:
                explosion_sound.play()

    if game_over:
        # Draw game over overlay (semi-transparent)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        screen.blit(overlay, (0, 0))
        
        # Show game over text
        game_over_text = font.render("GAME OVER", True, WHITE)
        score_text = font.render(f"Final Score: {score}", True, WHITE)
        restart_text = font.render("Press ESC to quit", True, WHITE)
        
        screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - 50))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2))
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 50))
        
        # Check for exit or wait for timeout
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
        
        # Auto-exit after 2 seconds if no input
        if pygame.time.get_ticks() - game_over_time > 2000:
            running = False

    # 6. Refresh Screen
    pygame.display.flip()
    clock.tick(60)

# Clean exit
if has_sound:
    pygame.mixer.music.stop()
pygame.quit()
sys.exit()