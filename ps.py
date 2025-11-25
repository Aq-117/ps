import pygame
import random
import sys

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plane Shooter")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)

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
    
    def draw(self):
        pygame.draw.rect(screen, BLUE, (self.x, self.y, self.width, self.height))
        # Draw health
        for i in range(self.health):
            pygame.draw.rect(screen, GREEN, (10 + i * 30, 10, 20, 20))
    
    def move(self, keys):
        if keys[pygame.K_w] and self.y > 0:
            self.y -= self.speed
        if keys[pygame.K_s] and self.y < HEIGHT - self.height:
            self.y += self.speed
        if keys[pygame.K_a] and self.x > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x < WIDTH // 2:  # Restrict to left half
            self.x += self.speed
    
    def shoot(self):
        self.bullets.append([self.x + self.width, self.y + self.height // 2])
    
    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet[0] += 10  # Move right
            if bullet[0] > WIDTH:
                self.bullets.remove(bullet)
            else:
                pygame.draw.rect(screen, GREEN, (bullet[0], bullet[1], 10, 5))

# Enemy
class Enemy:
    def __init__(self):
        self.x = WIDTH
        self.y = random.randint(50, HEIGHT - 50)
        self.width = 50
        self.height = 30
        self.speed = 3
        self.bullets = []
        self.shoot_delay = 0
    
    def draw(self):
        pygame.draw.rect(screen, RED, (self.x, self.y, self.width, self.height))
    
    def move(self):
        self.x -= self.speed
        # Stop at 70% of screen
        if self.x < WIDTH * 0.7:
            self.x = WIDTH * 0.7
            # Shoot occasionally
            self.shoot_delay += 1
            if self.shoot_delay > 60:  # Every ~1 second at 60 FPS
                self.shoot()
                self.shoot_delay = 0
    
    def shoot(self):
        self.bullets.append([self.x, self.y + self.height // 2])
    
    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet[0] -= 7  # Move left
            if bullet[0] < 0:
                self.bullets.remove(bullet)
            else:
                pygame.draw.rect(screen, RED, (bullet[0], bullet[1], 10, 5))

# Game Setup
player = Player()
enemies = []
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
    
    # Enemy bullets hit player
    for enemy in enemies:
        for bullet in enemy.bullets[:]:
            if (player.x < bullet[0] < player.x + player.width and
                player.y < bullet[1] < player.y + player.height):
                enemy.bullets.remove(bullet)
                player.health -= 1
                if player.health <= 0:
                    game_over()
                break

def game_over():
    text = font.render(f"GAME OVER - Score: {score}", True, WHITE)
    screen.blit(text, (WIDTH//2 - 150, HEIGHT//2))
    pygame.display.flip()
    pygame.time.wait(3000)
    pygame.quit()
    sys.exit()

# Main Game Loop
running = True
while running:
    screen.fill(BLACK)
    
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.shoot()
    
    # Spawn Enemies
    enemy_spawn_timer += 1
    if enemy_spawn_timer > 120:  # Every ~2 seconds at 60 FPS
        enemies.append(Enemy())
        enemy_spawn_timer = 0
    
    # Update
    player.move(pygame.key.get_pressed())
    player.update_bullets()
    for enemy in enemies[:]:
        enemy.move()
        enemy.update_bullets()
    
    check_collisions()
    
    # Draw
    player.draw()
    for enemy in enemies:
        enemy.draw()
    
    # Draw score
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (WIDTH - 150, 20))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()