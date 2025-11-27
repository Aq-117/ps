#added multiple enemies
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
        self.speed = 5
        self.health = 10
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        self.rect = pygame.Rect(self.x, self.y, 
                    self.img.get_width() if self.img else 40,
                    self.img.get_height() if self.img else 30)
        
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            # Fallback drawing
            pygame.draw.polygon(screen, (0, 120, 255), 
                               [(self.x+40, self.y+15), 
                                (self.x, self.y), 
                                (self.x, self.y+30)])
        
    def move(self, keys):
        if keys[pygame.K_w] and self.y > 0:
            self.y -= self.speed
        if keys[pygame.K_s] and self.y < HEIGHT - self.rect.height:
            self.y += self.speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x < WIDTH // 2:
            self.x += self.speed
        
        # Update rect position
        self.rect.x = self.x
        self.rect.y = self.y
            
    def shoot(self, keys):
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(self.x + 40,  # Using fixed width for fallback
                                     self.y + 15,   # Half of fallback height
                                     True))
            self.shoot_cooldown = self.shoot_delay
            if has_sound:
                shoot_sound.play()
        elif self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

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
        self.set_new_angle()  # Initialize first angle

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
    global score
    
    # Player bullets hit enemies
    for bullet in player.bullets[:]:
        for enemy in enemies[:]:
            if bullet.rect.colliderect(enemy.rect):
                player.bullets.remove(bullet)
                enemies.remove(enemy)
                score += 10
                if has_sound:
                    explosion_sound.play()
                break
    
    # Enemy collision with player (instant game over)
    for enemy in enemies[:]:
        if player.rect.colliderect(enemy.rect):
            player.health = 0  # Instant game over
            if has_sound:
                explosion_sound.play()
            game_over()
            return  # Exit immediately after collision

def game_over():
    text = font.render(f"GAME OVER - Score: {score}", True, WHITE)
    screen.blit(text, (WIDTH//2 - 150, HEIGHT//2))
    pygame.display.flip()
    pygame.time.wait(3000)
    pygame.quit()
    sys.exit()

# Main game loop
running = True
while running:
    # Draw background
    if bg_img:
        screen.blit(bg_img, (0, 0))
    else:
        screen.fill(BLACK)
    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Player controls
    keys = pygame.key.get_pressed()
    player.move(keys)
    player.shoot(keys)
    
    # Spawn enemies (randomly choose between all three types)
    enemy_spawn_timer += 1  # THIS WAS MISSING - CRUCIAL FOR SPAWNING
    if enemy_spawn_timer > 120:  # Spawn every ~2 seconds (60 frames = 1 second)
        enemy_type = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 20, 10, 10], k=1)[0]  # Randomly select enemy type
        if enemy_type == 3:
            enemies.append(Enemy3())
        elif enemy_type == 2:
            enemies.append(Enemy2())
        elif enemy_type == 3:
            enemies.append(Enemy3())
        elif enemy_type == 4:
            enemies.append(Enemy4())
        else:
            enemies.append(Enemy5())
        enemy_spawn_timer = 0  # Reset timer
    
    # Update player bullets
    for bullet in player.bullets[:]:
        bullet.update()
        if bullet.x > WIDTH:
            player.bullets.remove(bullet)
    
    # Update enemies
    for enemy in enemies[:]:
        enemy.update()
        
        # Remove off-screen enemies
        if enemy.x < -40:
            enemies.remove(enemy)
            continue
            
        # Enemy shooting
        if enemy.type == 4:  # Special handling for Enemy4
            if enemy.should_shoot(player):
                enemy_bullets.append(enemy.shoot(player.x, player.y))
        else:  # All other enemies
            if enemy.should_shoot():
                enemy_bullets.append(enemy.shoot())
    
    # Updating Bullets:
    i = 0
    while i < len(enemy_bullets):
        bullet = enemy_bullets[i]
        remove_bullet = False
        
        # Update bullet based on type
        if isinstance(bullet, HomingMissile):
            if not bullet.update(player.x, player.y):  # Expired
                remove_bullet = True
            elif (bullet.x < -50 or bullet.x > WIDTH + 50 or 
                bullet.y < -50 or bullet.y > HEIGHT + 50):  # Out of bounds
                remove_bullet = True
        else:
            bullet.update()
            if bullet.x < 0:  # Regular bullet out of bounds
                remove_bullet = True
        
        # Check collision with player (for all bullet types)
        if not remove_bullet and bullet.rect.colliderect(pygame.Rect(player.x, player.y, 40, 30)):
            remove_bullet = True
            player.health -= 1
            if has_sound:
                explosion_sound.play()
            if player.health <= 0:
                game_over()
        
        # Remove if flagged
        if remove_bullet:
            enemy_bullets.pop(i)  # Safer removal by index
        else:
            i += 1  # Only increment if we didn't remove
    
    check_collisions()
    
    # Draw everything
    for bullet in player.bullets:
        bullet.draw()
    
    for bullet in enemy_bullets:
        bullet.draw()
    
    for enemy in enemies:
        enemy.draw()
    
    player.draw()
    
    # Draw UI
    health_text = font.render(f"Health: {player.health}", True, WHITE)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (10, 50))
    
    pygame.display.flip()
    clock.tick(60)

# Stop music when game ends
if has_sound:
    pygame.mixer.music.stop()
pygame.quit()