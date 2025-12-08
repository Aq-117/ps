import pygame
import random

# Initialize Pygame
pygame.init()

# Set up the game window
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Bullet Hell Game")

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Load game sounds
shoot_sound = pygame.mixer.Sound("shoot.mp3")
enemy_hit_sound = pygame.mixer.Sound("explosion.mp3")
game_over_sound = pygame.mixer.Sound("music.mp3")
pygame.mixer.music.load("music.mp3")

# Define the player class
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.center = (screen_width // 2, screen_height - 50)
        self.speed = 8
        self.shoot_delay = 250
        self.last_shot = pygame.time.get_ticks()
        self.health = 3
        self.score = 0

    def update(self):
        # Move the player based on key presses
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < screen_width:
            self.rect.x += self.speed

    def shoot(self):
        # Shoot bullets at specified interval
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot > self.shoot_delay:
            bullet = Bullet(self.rect.centerx, self.rect.top)
            all_sprites.add(bullet)
            bullets.add(bullet)
            self.last_shot = current_time
            shoot_sound.play()

# Define the enemy class
class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((30, 30))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, screen_width - self.rect.width)
        self.rect.y = random.randint(-100, -40)
        self.speed = random.randint(1, 3)
        self.bullet_delay = random.randint(1000, 3000)
        self.last_shot = pygame.time.get_ticks()

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > screen_height + 10:
            self.rect.x = random.randint(0, screen_width - self.rect.width)
            self.rect.y = random.randint(-100, -40)
            self.speed = random.randint(1, 3)
        self.shoot()

    def shoot(self):
        # Shoot bullets at specified interval
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot > self.bullet_delay:
            bullet = Bullet(self.rect.centerx, self.rect.bottom)
            all_sprites.add(bullet)
            enemy_bullets.add(bullet)
            self.last_shot = current_time

# Define the bullet class
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 10))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = -10

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0 or self.rect.top > screen_height:
            self.kill()

# Create player and groups for sprites
player = Player()
all_sprites = pygame.sprite.Group()
all_sprites.add(player)
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemy_bullets = pygame.sprite.Group()

# Generate initial enemies
for _ in range(8):
    enemy = Enemy()
    all_sprites.add(enemy)
    enemies.add(enemy)

# Set up the game clock
clock = pygame.time.Clock()

# Game over flag and score tracking
game_over = False
score = 0

# Game loop
running = True
while running:
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not game_over:
                player.shoot()
            elif event.key == pygame.K_RETURN and game_over:
                # Reset the game
                game_over = False
                player.health = 3
                score = 0
                all_sprites.empty()
                bullets.empty()
                enemies.empty()
                enemy_bullets.empty()
                for _ in range(8):
                    enemy = Enemy()
                    all_sprites.add(enemy)
                    enemies.add(enemy)
                pygame.mixer.music.play()

    # Update
    if not game_over:
        all_sprites.update()

        # Check for bullet collisions with enemies
        bullet_hits = pygame.sprite.groupcollide(bullets, enemies, True, True)
        for hit_enemies in bullet_hits.values():
            score += len(hit_enemies)
            enemy_hit_sound.play()

        # Check for enemy collisions with player
        enemy_hits = pygame.sprite.spritecollide(player, enemies, True)
        for _ in enemy_hits:
            player.health -= 1
            enemy_hit_sound.play()

        # Check for enemy bullet collisions with player
        enemy_bullet_hits = pygame.sprite.spritecollide(player, enemy_bullets, True)
        if enemy_bullet_hits:
            player.health -= 1
            enemy_hit_sound.play()

        # Check if the player runs out of health
        if player.health <= 0:
            game_over = True
            pygame.mixer.music.stop()
            game_over_sound.play()

    # Draw
    screen.fill(BLACK)
    all_sprites.draw(screen)

    # Draw player health and score
    font = pygame.font.Font(None, 36)
    health_text = font.render(f"Health: {player.health}", True, WHITE)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(health_text, (10, 10))
    screen.blit(score_text, (screen_width - score_text.get_width() - 10, 10))

    if game_over:
        # Draw game over text
        game_over_text = font.render("Game Over", True, RED)
        text_rect = game_over_text.get_rect(center=(screen_width // 2, screen_height // 2))
        screen.blit(game_over_text, text_rect)

        # Draw instructions to restart
        restart_text = font.render("Press Enter to Restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
        screen.blit(restart_text, restart_rect)

    pygame.display.flip()

    # Set the desired frame rate
    clock.tick(60)

# Quit the game
pygame.quit()