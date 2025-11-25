import pygame
import random
import sys
import os

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plane Shooter")

# Colors (fallback if images fail)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Load images with error handling
def load_image(name, scale=1):
    try:
        img = pygame.image.load(f"assets/{name}").convert_alpha()
        return pygame.transform.scale(img, 
               (int(img.get_width() * scale), 
               (int(img.get_height() * scale))))
    except:
        print(f"Failed to load {name}, using placeholder")
        # Create colored rectangles as fallback
        if "player" in name:
            surf = pygame.Surface((50, 30)), pygame.SRCALPHA
            pygame.draw.polygon(surf, (0, 120, 255), [(50,15), (0,0), (0,30)])
        elif "enemy" in name:
            surf = pygame.Surface((50, 30)), pygame.SRCALPHA
            pygame.draw.polygon(surf, (255, 50, 50), [(0,15), (50,0), (50,30)])
        elif "bullet" in name:
            surf = pygame.Surface((10, 5)), pygame.SRCALPHA
            pygame.draw.rect(surf, (0, 255, 0), (0, 0, 10, 5))
        return surf

# Load all assets
player_img = load_image("player.png", 0.7)
enemy_img = load_image("enemy-1.jpg", 0.7)
bullet_img = load_image("bullet.png", 0.5)

# Player Class
class Player:
    def __init__(self):
        self.x = 100
        self.y = HEIGHT // 2
        self.img = player_img
        self.speed = 5
        self.health = 3
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        
    def draw(self):
        screen.blit(self.img, (self.x, self.y))
        
    def move(self, keys):
        if keys[pygame.K_w] and self.y > 0:
            self.y -= self.speed
        if keys[pygame.K_s] and self.y < HEIGHT - self.img.get_height():
            self.y += self.speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x < WIDTH // 2:
            self.x += self.speed
            
    def shoot(self, keys):
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            self.bullets.append(Bullet(self.x + self.img.get_width(), 
                                     self.y + self.img.get_height()//2, 
                                     True))
            self.shoot_cooldown = self.shoot_delay
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
        self.rect = pygame.Rect(x, y, bullet_img.get_width(), bullet_img.get_height())
        
    def update(self):
        if self.is_player:
            self.x += self.speed
        else:
            self.x -= self.speed
        self.rect.x = self.x
        self.rect.y = self.y
            
    def draw(self):
        screen.blit(self.img, (self.x, self.y))

# Enemy Class
class Enemy:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.img = enemy_img
        self.speed = 3
        self.shoot_cooldown = random.randint(30, 90)
        self.rect = pygame.Rect(self.x, self.y, enemy_img.get_width(), enemy_img.get_height())
        
    def draw(self):
        screen.blit(self.img, (self.x, self.y))
        
    def update(self):
        self.x -= self.speed
        self.rect.x = self.x
        self.shoot_cooldown -= 1
        
    def should_shoot(self):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        return Bullet(self.x, self.y + self.img.get_height()//2, False)

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
        if enemy.x < -enemy.img.get_width():
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
                                             player.img.get_width(), 
                                             player.img.get_height())):
            enemy_bullets.remove(bullet)
            player.health -= 1
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

pygame.quit()