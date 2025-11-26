#added sound, effects etc
import pygame
import random
import sys
import os

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 1400, 660
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

        self.health = 50
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        
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
        if keys[pygame.K_s] and self.y < HEIGHT - 30:  # Using fixed height for fallback
            self.y += self.speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x < WIDTH // 2:
            self.x += self.speed
            
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
        self.speed = 10 if is_player else 7
        self.is_player = is_player
        self.rect = pygame.Rect(x, y, 8, 4)  # Fixed size for fallback
        
    def update(self):
        if self.is_player:
            self.x += self.speed
        else:
            self.x -= self.speed
        self.rect.x = self.x
        self.rect.y = self.y
            
    def draw(self):
        if self.img:
            screen.blit(self.img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, 8, 4))

# Enemy Class
class Enemy:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, 40, 24)  # Fixed size for fallback
        
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
        
    def should_shoot(self):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        if has_sound:
            shoot_sound.play()
        return Bullet(self.x, self.y + 15, False)  # Using fixed position for fallback

# Game setup
player = Player()
enemies = []
enemy_bullets = []
enemy_spawn_timer = 0
score = 0
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

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
    
    # Spawn enemies
    enemy_spawn_timer += 1
    if enemy_spawn_timer > 120:
        enemies.append(Enemy())
        enemy_spawn_timer = 0
    
    # Update player bullets
    for bullet in player.bullets[:]:
        bullet.update()
        if bullet.x > WIDTH:
            player.bullets.remove(bullet)
    
    # Update enemies
    for enemy in enemies[:]:
        enemy.update()
        
        # Remove enemies that go off-screen (using image width)
        if enemy.x < -40:  # Fixed width for fallback
            enemies.remove(enemy)
            continue
            
        # Enemy shooting
        if enemy.should_shoot():
            enemy_bullets.append(enemy.shoot())
    
    # Update enemy bullets
    for bullet in enemy_bullets[:]:
        bullet.update()
        if bullet.x < 0:
            enemy_bullets.remove(bullet)
            
        # Check collision with player
        if bullet.rect.colliderect(pygame.Rect(player.x, player.y, 
                                             40, 30)):  # Fixed size for fallback
            enemy_bullets.remove(bullet)
            player.health -= 1
            if has_sound:
                explosion_sound.play()
            if player.health <= 0:
                game_over()
    
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