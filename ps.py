#different smoke graphics for player, but not using them in future.
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
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        self.max_health = 100      # Track max health separately
        self.health = self.max_health
        self.upgrade_cost_health = 100
        self.upgrade_cost_firerate = 150
        
        # Physics parameters
        self.speed = 5
        self.acceleration = 0.2
        self.deceleration = 0.1
        self.turn_speed = 0.2 #slowing down when changing direction
        self.friction = 0.2
        self.gravity = 0.175
        self.lift = -0.7  # Negative because y increases downward
        self.max_vertical_speed = 6
        self.max_horizontal_speed = 6
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

    def get_damage_state(self):
        """Returns damage level (0-3) based on health percentage"""
        health_pct = self.health / self.max_health  
        if health_pct > 0.75:
            return 0  # No damage
        elif health_pct > 0.5:
            return 1  # Light damage
        elif health_pct > 0.25:
            return 2  # Medium damage
        else:
            return 3  # Heavy damage
    
    def draw_health_bar(self, surface):
        """Draws a health bar above the player"""
        # Dimensions and positioning
        bar_width = 50
        bar_height = 5
        health_percentage = self.health / self.max_health 
        outline_rect = pygame.Rect(self.x, self.y - 10, bar_width, bar_height)
        fill_width = max(0, bar_width * health_percentage)
        # fill_width = max(0, bar_width * (self.health / 10))
        fill_rect = pygame.Rect(self.x, self.y - 10, fill_width, bar_height)
        
        # Color based on health level
        if health_percentage > 0.6:
            fill_color = (0, 255, 0)  # Green
        elif health_percentage > 0.3:
            fill_color = (255, 255, 0)  # Yellow
        else:
            fill_color = (255, 0, 0)  # Red
        
        # Draw the bar
        pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
        pygame.draw.rect(surface, fill_color, fill_rect)  # Current health
        pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border
        
        # Draw damage indicators
        if self.health < self.max_health:
            for i in range(1, 3):
                marker_pos = self.x + (bar_width * (i/3))
                pygame.draw.line(surface, (70, 70, 70), 
                            (marker_pos, self.y - 10), 
                            (marker_pos, self.y - 5), 1)

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

        if 0.3 < self.health/self.max_health <= 0.7 and random.random() < 0.15:  # 15% chance
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-0.8, -0.3),  # Gentle left drift
                'dy': random.uniform(-0.8, -0.2),  # Gentle upward drift
                'size': random.randint(1, 3),      # Smaller particles
                'life': random.randint(15, 30),
                'color': (180, 180, 180)           # Light gray
            })
        
        # Heavy smoke (<30% health)
        elif  0< self.health/self.max_health <= 0.3 and random.random() < 0.25:  # 25% chance
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1.2, -0.5),  # Stronger left drift
                'dy': random.uniform(-1.0, -0.3),  # Stronger upward drift
                'size': random.randint(2, 4),      # Larger particles
                'life': random.randint(20, 40),
                'color': (120, 120, 120)           # Darker gray
            })
        
        return False  # No death occurred

    def draw(self, surface):
        # Draw the plane
        if self.img and not self.death_animation:
            # Get damage state (0-3)
            damage_state = self.get_damage_state()
            
            # Create a copy of the image to modify
            plane_img = self.img.copy()
            
            # Apply damage effects based on health level
            if damage_state >= 1:  # Light damage (health 5-7)
                # Add scratches/dents
                for _ in range(3):
                    start_pos = (random.randint(5, 45), random.randint(5, 25))
                    end_pos = (start_pos[0] + random.randint(-10, 10), 
                            start_pos[1] + random.randint(-10, 10))
                    pygame.draw.line(plane_img, (80, 80, 80), start_pos, end_pos, 1)
            
            if damage_state >= 2:  # Medium damage (health 3-4)
                # Add bullet holes
                for _ in range(2):
                    hole_pos = (random.randint(5, 45), random.randint(5, 25))
                    pygame.draw.circle(plane_img, (0, 0, 0), hole_pos, random.randint(1, 2))
                    # Add metallic edge around holes
                    pygame.draw.circle(plane_img, (150, 150, 150), hole_pos, random.randint(1, 2), 1)
            
            if damage_state >= 3:  # Heavy damage (health 1-2)
                # Add smoke and fire effects
                for _ in range(2):
                    effect_pos = (random.randint(0, 10), random.randint(5, 25))
                    if random.random() > 0.5:  # 50% chance for smoke or fire
                        pygame.draw.circle(plane_img, (100, 100, 100, 150), effect_pos, random.randint(2, 3))
                    else:
                        pygame.draw.circle(plane_img, (255, random.randint(100, 150), 0), effect_pos, random.randint(1, 2))
            
            # Calculate angle based on movement
            angle = -self.vel_y * 2  # More tilt when moving faster vertically
            
            # Store original center position before rotation
            original_rect = plane_img.get_rect(center=(self.x + plane_img.get_width()//2, 
                                                self.y + plane_img.get_height()//2))
            
            # Rotate the damaged image
            rotated_img = pygame.transform.rotate(plane_img, angle)
            
            # Get rect of rotated image and set its center to original center
            rotated_rect = rotated_img.get_rect(center=original_rect.center)
            
            # Draw the rotated image
            surface.blit(rotated_img, rotated_rect.topleft)
            
            # Draw health bar if damaged
            if self.health < self.max_health:
                self.draw_health_bar(surface)
        
        elif not self.death_animation:
            # Fallback drawing if no image
            pygame.draw.polygon(surface, (0, 120, 255), 
                            [(self.x+40, self.y+15), 
                            (self.x, self.y), 
                            (self.x, self.y+30)])
            
            # Simple health indicator for fallback
            if self.health < self.max_health:
                health_width = 40 * (self.health / self.max_health)
                pygame.draw.rect(surface, (255,0,0), (self.x, self.y-10, 40, 3))
                pygame.draw.rect(surface, (0,255,0), (self.x, self.y-10, health_width, 3))
        
        # Draw hit flash if active
        if self.hit_flash > 0 and self.hit_flash % 3 < 2 and not self.death_animation:
            flash_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 150))
            surface.blit(flash_surf, (self.rect.x, self.rect.y))
        
        # Draw particles
        self.draw_hit_particles(surface)
        
        # Draw death effect if active
        if self.death_animation:
            self.draw_death_effect(surface)

# Bullet Class
class Bullet:
    def __init__(self, x, y, is_player, damage=1):
        self.x = x
        self.y = y
        self.img = bullet_img
        self.is_player = is_player
        self.damage = damage
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
        self.speed = 2
        self.shoot_cooldown = random.randint(30, 90) #earlier 30, 90
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 1  # Add enemy type identifier
        self.death_particles = []
        self.max_health = 10
        self.health = self.max_health
        self.dead = False  # <-- Add this line
        self.hit_particles = []
        
    def draw_health_bar(self, surface):
        if self.health < self.max_health:  # Only show if damaged
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            # Color based on health percentage
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)  # Green
            elif health_pct > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
            pygame.draw.rect(surface, color, fill_rect)  # Health
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border

    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 50, 50),
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:  # More than 50% damaged
                # Add smoke effect
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))
                    
        for p in self.hit_particles:
            pygame.draw.circle(screen, p['color'],  # Use global 'screen'
                            (int(p['x']), int(p['y'])), 
                            p['size'])

        # Draw hit particles (using global screen)
        for p in self.hit_particles:
            pygame.draw.circle(screen, p['color'],  # Use global 'screen'
                            (int(p['x']), int(p['y'])), 
                            p['size'])

    def update(self):
        self.x -= self.speed
        self.rect.x = self.x
        self.shoot_cooldown -= 1

        # Add smoke particles when health is low (≤50% health)
        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),  # Smoke drifts left
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })
        
        # Update existing particles
        for p in self.hit_particles[:]:
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)
        
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(70, 120)
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage=15)

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

# Enemy Type 2: Stops at 20% of screen and stays still
class Enemy2:
    def __init__(self):
        self.stop_x = WIDTH * 0.8  # 20% from right
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = random.randint(30, 90) #30, 90
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 2
        self.has_stopped = False
        self.death_particles = []
        self.max_health = 30
        self.health = self.max_health
        self.dead = False  # <-- Add this line
        self.hit_particles = []
        
    def draw_health_bar(self, surface):
        if self.health < self.max_health:  # Only show if damaged
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            # Color based on health percentage
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)  # Green
            elif health_pct > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
            pygame.draw.rect(surface, color, fill_rect)  # Health
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border

    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 100, 100),  # Different color for visibility
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:  # More than 50% damaged
                # Add smoke effect
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))

        # Draw hit particles (using global screen)
        for p in self.hit_particles:
            pygame.draw.circle(screen, p['color'],  # Use global 'screen'
                            (int(p['x']), int(p['y'])), 
                            p['size'])

    def update(self):
        if not self.has_stopped:
            self.x -= self.speed
            if self.x <= self.stop_x:
                self.has_stopped = True
            self.rect.x = self.x
        
        self.shoot_cooldown -= 1

        # Add smoke particles when health is low (≤50% health)
        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),  # Smoke drifts left
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })
        
        # Update existing particles
        for p in self.hit_particles[:]:
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(50, 90)  #  20, 60 Faster shooting than type 1
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage = 10)

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
        self.shoot_cooldown = random.randint(60, 100)
        self.rect = pygame.Rect(self.x, self.y, 40, 24)
        self.type = 3
        self.has_stopped = False
        self.death_particles = []
        self.max_health = 20
        self.health = self.max_health
        self.dead = False  # <-- Add this line
        self.hit_particles = []
        
    def draw_health_bar(self, surface):
        if self.health < self.max_health:  # Only show if damaged
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            # Color based on health percentage
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)  # Green
            elif health_pct > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
            pygame.draw.rect(surface, color, fill_rect)  # Health
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border

    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 150, 150),  # Different color for visibility
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:  # More than 50% damaged
                # Add smoke effect
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))
        
        # Draw hit particles (using global screen)
        for p in self.hit_particles:
            pygame.draw.circle(screen, p['color'],  # Use global 'screen'
                            (int(p['x']), int(p['y'])), 
                            p['size'])

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

        # Add smoke particles when health is low (≤50% health)
        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),  # Smoke drifts left
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })
        
        # Update existing particles
        for p in self.hit_particles[:]:
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)
        
    def should_shoot(self, player=None):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(50, 100)  # Different shooting pattern
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False, damage=10)
    
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
        self.damage = 1
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
        self.max_health = 20
        self.health = self.max_health
        self.dead = False  # <-- Add this line
        self.hit_particles = []
        
    def draw_health_bar(self, surface):
        if self.health < self.max_health:  # Only show if damaged
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            # Color based on health percentage
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)  # Green
            elif health_pct > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
            pygame.draw.rect(surface, color, fill_rect)  # Health
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border    

    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.polygon(screen, (255, 200, 200),  # Different color
                               [(self.x, self.y+15), 
                                (self.x+40, self.y), 
                                (self.x+40, self.y+30)])
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:  # More than 50% damaged
                # Add smoke effect
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))
                    
        # Draw hit particles (using global screen)
        for p in self.hit_particles:
            pygame.draw.circle(screen, p['color'],  # Use global 'screen'
                            (int(p['x']), int(p['y'])), 
                            p['size'])
                
    def update(self):
        if self.x > self.stop_x:
            self.x -= self.speed
            self.rect.x = self.x
        
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        # Add smoke particles when health is low (≤50% health)
        if self.health <= self.max_health * 0.5 and not self.dead and random.random() < 0.2:
            self.hit_particles.append({
                'x': self.rect.centerx - 10,
                'y': self.rect.centery,
                'dx': random.uniform(-1, -0.5),  # Smoke drifts left
                'dy': random.uniform(-1, -0.3),
                'size': random.randint(2, 4),
                'life': random.randint(20, 40),
                'color': (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            })
        
        # Update existing particles
        for p in self.hit_particles[:]:
            p['life'] -= 1
            if p['life'] <= 0:
                self.hit_particles.remove(p)
        
    def should_shoot(self, player):
        # Only shoot if cooldown is 0 and we're in position
        return (self.shoot_cooldown <= 0 and 
                self.x <= self.stop_x and
                abs(player.y - self.y) < HEIGHT/2)  # Only shoot if player is roughly aligned
        
    def shoot(self, player_x, player_y):
        self.shoot_cooldown = 240  # 4 second cooldown (60*4)
        if has_sound:
            shoot_sound.play()
            missile = HomingMissile(self.x, self.y + 15, player_x, player_y)
            missile.damage = 20
        return missile
    
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
        self.max_health = 10
        self.health = self.max_health
        self.death_particles = []

    def draw_health_bar(self, surface):
        if self.health < self.max_health:  # Only show if damaged
            bar_width = 40
            bar_height = 4
            outline_rect = pygame.Rect(self.x, self.y - 8, bar_width, bar_height)
            fill_rect = pygame.Rect(self.x, self.y - 8, bar_width * (self.health/self.max_health), bar_height)
            
            # Color based on health percentage
            health_pct = self.health / self.max_health
            if health_pct > 0.6:
                color = (0, 255, 0)  # Green
            elif health_pct > 0.3:
                color = (255, 255, 0)  # Yellow
            else:
                color = (255, 0, 0)  # Red
                
            pygame.draw.rect(surface, (40, 40, 40), outline_rect)  # Background
            pygame.draw.rect(surface, color, fill_rect)  # Health
            pygame.draw.rect(surface, (100, 100, 100), outline_rect, 1)  # Border

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
        self.draw_health_bar(screen)
        if self.health < self.max_health:
            damage_pct = 1 - (self.health / self.max_health)
            if damage_pct > 0.5:  # More than 50% damaged
                # Add smoke effect
                for _ in range(int(2 * damage_pct)):
                    smoke_pos = (
                        self.x + random.randint(0, self.rect.width),
                        self.y + random.randint(0, self.rect.height)
                    )
                    pygame.draw.circle(screen, 
                                    (random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                                    smoke_pos, random.randint(1, 3))

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
        bullet = Bullet(self.x, self.y + 15, False, damage=20)
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

def restart_game():
    global player, enemies, enemy_bullets, score, enemy_spawn_timer, game_state, game_over
    player = Player()
    enemies = []
    enemy_bullets = []
    score = 0
    enemy_spawn_timer = 0
    game_state = "running"  # Reset to running state
    game_over = False

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
                enemy.health -= bullet.damage  # Reduce health by bullet's damage
                
                if enemy.health <= 0:
                    enemy.create_death_particles()
                    global_particles.extend(enemy.death_particles)
                    player.bullets.remove(bullet)
                    enemies.remove(enemy)
                    score += 1 * enemy.max_health  # More points for tougher enemies
                    if has_sound:
                        explosion_sound.play()
                else:
                    # Just damage, not destroyed
                    player.bullets.remove(bullet)
                    # Add hit effect
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
                        shoot_sound.play()  # Different sound for hit vs kill
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

# def game_over():
#     global game_over_triggered, running
#     if game_over_triggered:
#         return
#     game_over_triggered = True
#     text = font.render(f"GAME OVER - Score: {score}", True, WHITE)
#     screen.blit(text, (WIDTH//2 - 150, HEIGHT//2))
#     pygame.display.flip()
#     pygame.time.wait(3000)
#     running = False  # Ensure main loop exits
#     if has_sound:
#         pygame.mixer.music.stop()
#     pygame.quit()
#     sys.exit()

def draw_shop():
    screen.fill((0, 0, 50))  # Dark blue background
    title = font.render("UPGRADE SHOP", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Upgrade options
    options = [
        (f"1. +10 Max Health (Cost: {player.upgrade_cost_health})", 
         player.upgrade_cost_health, "health"),
        (f"2. Faster Fire Rate (Cost: {player.upgrade_cost_firerate})", 
         player.upgrade_cost_firerate, "firerate"),
        ("3. Exit Shop", 0, "exit")
    ]
    
    for i, (text, cost, _) in enumerate(options):
        y_pos = 150 + i * 60
        # Gray out if unaffordable
        color = WHITE if score >= cost or cost == 0 else (100, 100, 100)
        screen.blit(font.render(text, True, color), (WIDTH//2 - 200, y_pos))
    
    # Display current stats
    stats = [
        f"Current Max Health: {player.max_health}",
        f"Current Fire Rate: {60/(player.shoot_delay):.1f} shots/sec",  # Convert delay to shots/second
        f"Your Score: {score}"
    ]
    for i, stat in enumerate(stats):
        screen.blit(font.render(stat, True, WHITE), (WIDTH//2 - 200, 350 + i * 40))

def draw_pause_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # Semi-transparent black
    screen.blit(overlay, (0, 0))
    
    texts = [
        ("PAUSED", title_font),
        ("Press P to Resume", font),
        ("Press 5 for Shop", font),
        ("Press ESC to Quit", font)
    ]
    
    for i, (text, font_obj) in enumerate(texts):
        rendered = font_obj.render(text, True, WHITE)
        screen.blit(rendered, (WIDTH//2 - rendered.get_width()//2, 
                             HEIGHT//2 - 100 + i * 50))

# Main game loop
game_state = "running"  # Can be "running", "paused", "shop", "game_over"
running = True
game_over = False
game_over_time = 0
clock = pygame.time.Clock()

while running:
    # # 1. Event Handling
    # for event in pygame.event.get():
    #     if event.type == pygame.QUIT:
    #         running = False

    #     if event.type == pygame.KEYDOWN:
    #         if event.key == pygame.K_p and not game_over:  # Toggle pause
    #             paused = not paused
            
    #         if paused:  # Only process these when paused
    #             if event.key == pygame.K_5:  # Enter shop from pause
    #                 paused = False
    #                 shop_active = True
                
    #             if event.key == pygame.K_p:  # Resume
    #                 paused = False

    #     if game_over and event.type == pygame.KEYDOWN:
    #         if event.key == pygame.K_r:    # Press R to restart
    #             restart_game()
    #         #elif event.key == pygame.K_s:
    #         #    shop_active = True
    #         elif event.key == pygame.K_ESCAPE:  # Press ESC to quit
    #             running = False

    #     if shop_active and event.type == pygame.KEYDOWN:
    #         if event.key == pygame.K_1 and score >= player.upgrade_cost_health:
    #             player.max_health += 1
    #             player.health = player.max_health  # Refill health
    #             score -= player.upgrade_cost_health
    #             player.upgrade_cost_health += 50  # Increase cost for next purchase
            
    #         elif event.key == pygame.K_2 and score >= player.upgrade_cost_firerate:
    #             player.shoot_delay = max(5, player.shoot_delay - 3)  # Faster firing (min delay = 5)
    #             score -= player.upgrade_cost_firerate
    #             player.upgrade_cost_firerate += 75
            
    #         elif event.key == pygame.K_3:
    #             shop_active = False  # Exit shop

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            # Global controls (work in any state)
            if event.key == pygame.K_ESCAPE:
                if game_state == "shop":
                    game_state = "paused"  # Return to pause from shop
                else:
                    running = False
            
            # State-specific controls
            if game_state == "running":
                if event.key == pygame.K_p:
                    game_state = "paused"
            
            elif game_state == "paused":
                if event.key == pygame.K_p:
                    game_state = "running"
                elif event.key == pygame.K_5:
                    game_state = "shop"
            
            elif game_state == "shop":
                if event.key == pygame.K_3:
                    game_state = "paused"  # Return to pause menu
                elif event.key == pygame.K_1 and score >= player.upgrade_cost_health:
                    player.max_health += 10
                    player.health += 10
                    score -= player.upgrade_cost_health
                    player.upgrade_cost_health += 50
                elif event.key == pygame.K_2 and score >= player.upgrade_cost_firerate:
                    player.shoot_delay = max(5, player.shoot_delay - 3)
                    score -= player.upgrade_cost_firerate
                    player.upgrade_cost_firerate += 75
            
            elif game_state == "game_over":
                if event.key == pygame.K_r:
                    restart_game()
                    game_state = "running"
                elif event.key == pygame.K_ESCAPE:
                    running = False

    # 2. Get Input
    keys = pygame.key.get_pressed()

    #if not game_over and not shop_active:  # Pause gameplay when shopping
    #    player.update(keys)
    
    # 3. Update Game State
    if game_state == "running" and not player.dead:
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
                    player.health -= bullet.damage
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
    health_text = font.render(f"Health: {player.health}/{player.max_health}", True, WHITE)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (10, 50))

    # Draw state overlays
    if game_state == "paused":
        draw_pause_screen()
    elif game_state == "shop":
        draw_shop()
    elif game_state == "game_over":
        game_over = True

    # 5. Death and Game Over Handling
    if player.dead:
        # Update death animation and check if it completed
        death_complete = player.update(keys)  # This now returns True when animation finishes
        
        if death_complete and not game_over:
            game_state = "game_over"
            game_over = True
            game_over_time = pygame.time.get_ticks()
            # Clear all game objects
            enemies.clear()
            enemy_bullets.clear()
            player.bullets.clear()
            # Play game over sound if available
            if has_sound:
                explosion_sound.play()

    if game_state == "game_over":
        # Draw game over overlay (semi-transparent)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        screen.blit(overlay, (0, 0))
        
        # Show game over text
        texts = [
            font.render("GAME OVER", True, WHITE),
            font.render(f"Final Score: {score}", True, WHITE),
            font.render("Press R to restart", True, WHITE),
            font.render("Press ESC to quit", True, WHITE),
            #font.render("Press S to open shop", True, WHITE) if not shop_active else font.render("Press S to close shop", True, WHITE)
        ]
        
        for i, text in enumerate(texts):
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 50 + i*40))
        
        # Auto-exit after 2 seconds if no input
        #if pygame.time.get_ticks() - game_over_time > 2000:
        #    running = False

    # 6. Refresh Screen
    pygame.display.flip()
    clock.tick(60)

# Clean exit
if has_sound:
    pygame.mixer.music.stop()
pygame.quit()
sys.exit()