import pygame
import random
import sys

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plane Shooter")

# Colors
BLACK = (0, 0, 0)
BLUE = (0, 120, 255)
RED = (255, 50, 50)
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)

# Player
class Player:
    def __init__(self):
        self.x = 100
        self.y = HEIGHT // 2
        self.width = 50
        self.height = 30
        self.speed = 5
        self.health = 3
        self.bullets = []
        self.shoot_cooldown = 0
        self.shoot_delay = 30  # frames between shots (lower = faster)
        
    def draw(self):
        # Corrected to make triangle face RIGHT →
        pygame.draw.polygon(screen, BLUE, [
            (self.x + self.width, self.y + self.height//2),  # Nose point (rightmost)
            (self.x, self.y),                                # Top-left
            (self.x, self.y + self.height)                   # Bottom-left
        ])
        
    def move(self, keys):
        if keys[pygame.K_w] and self.y > 0:
            self.y -= self.speed
        if keys[pygame.K_s] and self.y < HEIGHT - self.height:
            self.y += self.speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x < WIDTH // 2:  # Restrict to left half
            self.x += self.speed
            
    def shoot(self, keys):
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            self.bullets.append([self.x + self.width, self.y + self.height//2 - 2])
            self.shoot_cooldown = self.shoot_delay
        elif self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

# Enemy
class Enemy:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.width = 50
        self.height = 30
        self.speed = 3
        self.health = 1
        self.shoot_cooldown = random.randint(30, 90)
        
    def draw(self):
        # Draw enemy (triangle facing LEFT)
        pygame.draw.polygon(screen, RED, [
            (self.x, self.y + self.height//2),  # Nose point
            (self.x + self.width, self.y),      # Top-right
            (self.x + self.width, self.y + self.height)  # Bottom-right
        ])
        
    def update(self):
        self.x -= self.speed
        self.shoot_cooldown -= 1
        
    def should_shoot(self):
        return self.shoot_cooldown <= 0
        
    def shoot(self):
        self.shoot_cooldown = random.randint(30, 90)
        return [self.x, self.y + self.height // 2]  # Returns bullet position

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
            if (enemy.x < bullet[0] < enemy.x + enemy.width and
                enemy.y < bullet[1] < enemy.y + enemy.height):
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
    player.shoot(keys)  # Automatic shooting when space is held
    
    # Spawn enemies
    enemy_spawn_timer += 1
    if enemy_spawn_timer > 120:  # Every ~2 seconds at 60 FPS
        enemies.append(Enemy())
        enemy_spawn_timer = 0
    
    # Update player bullets
    for bullet in player.bullets[:]:
        bullet[0] += 10  # Move right
        if bullet[0] > WIDTH:
            player.bullets.remove(bullet)
    
    # Update enemies
    for enemy in enemies[:]:
        enemy.update()
        
        # Remove enemies that go off-screen
        if enemy.x < -enemy.width:
            enemies.remove(enemy)
            continue
            
        # Enemy shooting
        if enemy.should_shoot():
            enemy_bullets.append(enemy.shoot())
    
    # Update enemy bullets
    for bullet in enemy_bullets[:]:
        bullet[0] -= 7  # Move left
        if bullet[0] < 0:
            enemy_bullets.remove(bullet)
            
        # Check collision with player
        if (player.x < bullet[0] < player.x + player.width and
            player.y < bullet[1] < player.y + player.height):
            enemy_bullets.remove(bullet)
            player.health -= 1
            if player.health <= 0:
                game_over()
    
    check_collisions()
    
    # Draw everything
    for bullet in player.bullets:
        pygame.draw.rect(screen, GREEN, (bullet[0], bullet[1], 10, 5))
    
    for bullet in enemy_bullets:
        pygame.draw.rect(screen, RED, (bullet[0], bullet[1], 10, 5))
    
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