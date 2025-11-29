import pygame, random, math, time
from config import *

class Food:
    """Base class for food objects."""
    def __init__(self, color, size, score, boost_duration=0):
        self.size = float(size)
        self.score = score
        self.boost_duration = boost_duration
        self.position = self.spawn()
        self.color = tuple(int(c) for c in color[:3])
        self.visible = True
        self.respawn_timer = 0.0
        self.cooldown_time = 3.0
        self.pulse_phase = 0.0
        self.is_bonus = False

    def spawn(self):
        """Spawn food at random valid position."""
        x = random.randint(FOOD_SPAWN_MARGIN, GAME_WIDTH - FOOD_SPAWN_MARGIN)
        y = random.randint(FOOD_SPAWN_MARGIN, GAME_HEIGHT - FOOD_SPAWN_MARGIN)
        return (x, y)

    def respawn(self, snake_segments):
        """Respawn food at new location avoiding snake."""
        self.visible = False
        self.respawn_timer = time.time() + self.cooldown_time
        self.pulse_phase = 0.0

        attempts = 0
        while attempts < 100:
            new_pos = self.spawn()
            valid = True
            for segment in snake_segments:
                if math.hypot(new_pos[0] - segment[0], new_pos[1] - segment[1]) < (
                    SNAKE_SEGMENT_SIZE + self.size + 10
                ):
                    valid = False
                    break
            if valid:
                self.position = new_pos
                self.visible = True
                return
            attempts += 1
        self.position = self.spawn()
        self.visible = True

    def update(self):
        """Update food state with animation."""
        if not self.visible and time.time() >= self.respawn_timer:
            self.visible = True
        self.pulse_phase += 0.12

    def check_collision(self, snake_head):
        """Check if snake head collides with food."""
        if not self.visible:
            return False
        if math.hypot(snake_head[0] - self.position[0], snake_head[1] - self.position[1]) < (self.size + SNAKE_SEGMENT_SIZE // 2):
            return True
        return False

    def _safe_glow_draw(self, screen, center_pos, size, base_color, glow_intensity=50, extra=5):
        """Helper to draw outer glow safely with alpha clamping and zero-size checks."""
        int_size = int(max(0, round(size)))
        start_r = int_size + extra
        end_r = int_size
        for r in range(start_r, end_r, -1):
            if r <= 0:
                continue
            alpha = 255 - (r - int_size) * glow_intensity
            alpha = int(max(0, min(255, alpha)))
            glow_color = (int(base_color[0]), int(base_color[1]), int(base_color[2]), alpha)
            surf_dim = r * 2
            if surf_dim <= 0:
                continue
            s = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            try:
                pygame.draw.circle(s, glow_color, (r, r), r)
                screen.blit(s, (center_pos[0] - r, center_pos[1] - r))
            except Exception:
                continue

    def draw(self, screen):
        """Draw food with pulsing effect."""
        if self.visible:
            pulse_offset = math.sin(self.pulse_phase) * 2.0
            size = self.size + pulse_offset
            int_size = max(1, int(round(size)))
            if not self.is_bonus:
                self._safe_glow_draw(screen, self.position, size, self.color, glow_intensity=50, extra=5)
            core_color = (int(self.color[0]), int(self.color[1]), int(self.color[2]))
            pygame.draw.circle(screen, core_color, (int(self.position[0]), int(self.position[1])), int_size)
            pygame.draw.circle(screen, WHITE, (int(self.position[0]), int(self.position[1])), int_size, 2)


class RegularFood(Food):
    def __init__(self):
        super().__init__(RED, FOOD_SIZE, 1, 0)
        self.cooldown_time = 0.5
        self.colors = [RED, ORANGE]
        self.color = tuple(random.choice(self.colors))

    def respawn(self, snake_segments):
        """Respawn food at new location and change color."""
        super().respawn(snake_segments)
        self.color = tuple(random.choice(self.colors))


class BonusFood(Food):
    def __init__(self):
        super().__init__(GOLD, BONUS_FOOD_SIZE, 5, 5.0)
        self.cooldown_time = 10.0
        self.is_bonus = True

    def draw(self, screen):
        """Draw Bonus Food with a strong glow effect."""
        if self.visible:
            pulse_offset = math.sin(self.pulse_phase * 1.5) * 3.0
            size = self.size + pulse_offset
            int_size = max(1, int(round(size)))
            self._safe_glow_draw(screen, self.position, size, self.color, glow_intensity=20, extra=10)
            core_color = (int(self.color[0]), int(self.color[1]), int(self.color[2]))
            pygame.draw.circle(screen, core_color, (int(self.position[0]), int(self.position[1])), int_size)
            pygame.draw.circle(screen, WHITE, (int(self.position[0]), int(self.position[1])), int_size, 2)
            pygame.draw.line(screen, WHITE, (int(self.position[0] - 6), int(self.position[1])), 
                             (int(self.position[0] + 6), int(self.position[1])), 2)
            pygame.draw.line(screen, WHITE, (int(self.position[0]), int(self.position[1] - 6)), 
                             (int(self.position[0]), int(self.position[1] + 6)), 2)
