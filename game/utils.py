import pygame
import threading
import cv2
import time
from config import *
from game.snake import Snake
from game.food import RegularFood, BonusFood
from game.tracker import HandTracker
from collections import deque
import random
import os
import json
from game.audio import make_sine_sound, make_bass_loop

class FingerSnakeGame:
    """Main game controller with ultra-smooth tracking."""

    def __init__(self):
        pygame.init()
        # Window includes game board (GAME_WIDTH) plus an information panel on the right
        total_width = GAME_WIDTH + INFO_PANEL_WIDTH
        self.screen = pygame.display.set_mode((total_width, GAME_HEIGHT))
        pygame.display.set_caption("Finger-Controlled Snake")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        # Tiny font for compact labels inside camera preview
        self.tiny_font = pygame.font.Font(None, 18)
        # Slightly smaller font specifically for the INDEX label
        # (make it smaller than tiny_font so it's less obtrusive)
        self.index_font = pygame.font.Font(None, 14)
        # Monospaced tiny font for the NO HAND message. Use SysFont to pick a
        # monospace face available on the system; fall back to tiny_font if
        # SysFont is not available.
        try:
            # Request a bold monospace font so the "NO HAND DETECTED" message
            # appears emphasized in the camera preview.
            self.mono_tiny_font = pygame.font.SysFont('monospace', 14, bold=True)
        except Exception:
            self.mono_tiny_font = self.tiny_font
            try:
                # If fallback font supports bolding, enable it to match intent.
                self.mono_tiny_font.set_bold(True)
            except Exception:
                pass

        # Game objects
        self.snake = Snake()
        self.foods = [RegularFood()]
        self.score = 0
        self.game_state = "MENU"
        self.flash_timer = 0 # For collision feedback

        # Enhanced tracking
        self.hand_tracker = HandTracker()
        self.last_finger_pos = None
        self.finger_detected = False

        # Multi-level smoothing
        self.smooth_pos = None
        self.smoothing_factor = SMOOTHING_FACTOR
        self.position_history = deque(maxlen=SMOOTHING_WINDOW)

        # Camera / threading setup
        self.cap = cv2.VideoCapture(0)
        # Check if camera opened successfully
        if not self.cap.isOpened():
            print("Warning: Could not open camera. Running without camera input.")
            self.running = True
            self.cap = None
        else:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.frame_lock = threading.Lock()
        self.latest_frame_small = None
        self.latest_overlay_text = None
        self.latest_overlay_pos = None
        self.latest_overlay_detected = False
        self.shared_finger_pos = None
        self.shared_finger_detected = False

        self.running = True
        self.camera_thread = None
        if self.cap is not None:
            self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
            self.camera_thread.start()

        self.camera_surface = None

        # Transition timers
        self.menu_detect_start = None
        self.gameover_detect_start = None
        self.transition_delay = 0.5

        # Bonus Food Management
        self.bonus_food_spawn_timer = time.time() + 15.0 # First bonus food after 15s

        # UI / control flags
        self.paused = False
        self.muted = False
        # Exit confirmation flag — when True, user must confirm quit with Y
        self.exit_confirmation = False

        # High score persistence
        self.highscore_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'highscore.json'))
        self.highscore = self._load_highscore()

        # Audio: prepare simple SFX (generated) — guarded in case mixer isn't available
        self.sounds = {}
        try:
            # Ensure mixer initialized
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init()
                except Exception:
                    pass

            # Short effects: start, eat, bonus, die
            self.sounds['start'] = make_sine_sound(freq=880, duration=0.12, volume=0.25)
            self.sounds['eat'] = make_sine_sound(freq=660, duration=0.10, volume=0.22)
            self.sounds['bonus'] = make_sine_sound(freq=1100, duration=0.18, volume=0.28)
            # death is a descending chord — approximate with two quick tones
            self.sounds['die'] = make_sine_sound(freq=220, duration=0.28, volume=0.35)
        except Exception:
            # If sound creation fails, keep sounds dict empty and continue
            self.sounds = {}

    def _load_highscore(self):
        """Load highscore from disk, return 0 if not found or on error."""
        try:
            if os.path.exists(self.highscore_file):
                with open(self.highscore_file, 'r') as f:
                    data = json.load(f)
                    return int(data.get('highscore', 0))
        except Exception:
            pass
        return 0

    def _save_highscore(self):
        """Save current highscore to disk (best-effort)."""
        try:
            with open(self.highscore_file, 'w') as f:
                json.dump({'highscore': int(self.highscore)}, f)
        except Exception:
            pass

    def map_coordinates(self, camera_pos):
        """Map camera coordinates to game coordinates."""
        x, y = camera_pos
        # Mirror only if configured to do so (keeps mapping consistent with preview)
        if 'CAMERA_MIRROR' in globals() and CAMERA_MIRROR and CAMERA_WIDTH:
            x = CAMERA_WIDTH - x
        game_x = int(x * GAME_WIDTH / CAMERA_WIDTH) if CAMERA_WIDTH else int(x)
        game_y = int(y * GAME_HEIGHT / CAMERA_HEIGHT) if CAMERA_HEIGHT else int(y)
        # Clamp to game boundaries
        game_x = max(SNAKE_SEGMENT_SIZE, min(GAME_WIDTH - SNAKE_SEGMENT_SIZE, game_x))
        game_y = max(SNAKE_SEGMENT_SIZE, min(GAME_HEIGHT - SNAKE_SEGMENT_SIZE, game_y))
        return (game_x, game_y)

    def smooth_position(self, new_pos):
        """Advanced multi-stage smoothing."""
        if new_pos is None:
            return None
        self.position_history.append(new_pos)

        # Stage 1: Moving average (with weighting)
        if self.position_history:
            total_weight = 0.0
            weighted_x = 0.0
            weighted_y = 0.0
            
            for i, pos in enumerate(self.position_history):
                weight = (i + 1) / len(self.position_history)
                weighted_x += pos[0] * weight
                weighted_y += pos[1] * weight
                total_weight += weight
            
            averaged_pos = (weighted_x / total_weight, weighted_y / total_weight)
        else:
            averaged_pos = new_pos

        # Stage 2: Exponential smoothing
        if self.smooth_pos is None:
            self.smooth_pos = averaged_pos
        else:
            x = self.smooth_pos[0] * (1 - self.smoothing_factor) + averaged_pos[0] * self.smoothing_factor
            y = self.smooth_pos[1] * (1 - self.smoothing_factor) + averaged_pos[1] * self.smoothing_factor
            self.smooth_pos = (x, y) # Keep as float for precision

        return (int(self.smooth_pos[0]), int(self.smooth_pos[1]))

    def camera_loop(self):
        """Runs hand tracking in separate thread."""
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Hand tracking (do not draw labels here; we'll render labels in pygame)
            finger_pos, detected, processed_frame = self.hand_tracker.find_finger_position(frame, draw_labels=False)
            
            game_pos = None
            if detected and finger_pos:
                game_pos = self.map_coordinates(finger_pos)
                # Note: Smoothing applied here, then shared
                game_pos = self.smooth_position(game_pos) 

            # Prepare overlay text + position (in small frame coordinates)
            h, w, _ = frame.shape
            small_w, small_h = (240, 180)
            overlay_text = None
            overlay_pos_small = None
            if detected and finger_pos is not None:
                x, y = finger_pos
                overlay_text = "INDEX"
                x_small = int(x * small_w / w)
                y_small = int(y * small_h / h)
                # If the preview is being flipped for full mirroring, mirror the
                # overlay position so the label follows what the user sees on-screen.
                if 'CAMERA_MIRROR' in globals() and CAMERA_MIRROR and not ('CAMERA_MIRROR_TEXT_ONLY' in globals() and CAMERA_MIRROR_TEXT_ONLY):
                    x_small = small_w - x_small
                overlay_pos_small = (x_small, y_small)
            else:
                # Draw NO HAND DETECTED inside the camera preview at its top-left
                overlay_text = "NO HAND DETECTED"
                overlay_pos_small = (8, 8)

            with self.frame_lock:
                self.shared_finger_pos = game_pos
                self.shared_finger_detected = detected
                self.latest_overlay_text = overlay_text
                self.latest_overlay_pos = overlay_pos_small
                self.latest_overlay_detected = detected

            # Update display frame with landmarks drawn. Respect CAMERA_MIRROR.
            if 'CAMERA_MIRROR' in globals() and CAMERA_MIRROR:
                preview_frame = cv2.flip(processed_frame, 1)
            else:
                preview_frame = processed_frame
            # Scale preview to a compact size for the info panel
            frame_small = cv2.resize(preview_frame, (240, 180))
            with self.frame_lock:
                self.latest_frame_small = frame_small

            time.sleep(0.01)

    def update_from_shared_state(self):
        """Pull latest tracking data."""
        frame_small = None
        finger_pos = None
        finger_detected = False
        overlay_text = None
        overlay_pos = None
        overlay_detected = False

        with self.frame_lock:
            if self.latest_frame_small is not None:
                frame_small = self.latest_frame_small.copy()
            finger_pos = self.shared_finger_pos
            finger_detected = self.shared_finger_detected
            # Grab overlay info set by camera thread
            overlay_text = self.latest_overlay_text
            overlay_pos = self.latest_overlay_pos
            overlay_detected = self.latest_overlay_detected

        self.finger_detected = finger_detected
        if finger_pos is not None:
            self.last_finger_pos = finger_pos

        if frame_small is not None:
            frame_rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
            self.camera_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            # Draw overlay text onto the camera preview using pygame so we can
            # control mirroring of the labels independently of the image.
            try:
                if overlay_text:
                    # small preview surface coordinates
                    surf_w = self.camera_surface.get_width()
                    surf_h = self.camera_surface.get_height()

                    # Render label:
                    label_color = GREEN if overlay_detected else RED
                    if overlay_text == "INDEX":
                        # use the slightly smaller index font to be less obtrusive
                        label_surf = self.index_font.render(overlay_text, True, label_color)
                    elif overlay_text == "NO HAND DETECTED":
                        # monospaced, smaller message so it fits nicely in the
                        # camera preview top-left
                        try:
                            label_surf = self.mono_tiny_font.render(overlay_text, True, RED)
                        except Exception:
                            label_surf = self.tiny_font.render(overlay_text, True, RED)
                    else:
                        label_surf = self.small_font.render(overlay_text, True, label_color)
                    label_rect = label_surf.get_rect()

                    if overlay_pos:
                        px, py = overlay_pos
                    else:
                        px, py = (10, 24)

                    # If configured to mirror only text, flip text surface horizontally
                    if 'CAMERA_MIRROR_TEXT_ONLY' in globals() and CAMERA_MIRROR_TEXT_ONLY:
                        label_surf = pygame.transform.flip(label_surf, True, False)

                    # Blit label — keep inside preview bounds
                    blit_x = max(0, min(surf_w - label_rect.width, px))
                    blit_y = max(0, min(surf_h - label_rect.height, py))
                    self.camera_surface.blit(label_surf, (blit_x, blit_y))
            except Exception:
                pass

    def draw_text(self, text, pos, color=WHITE, font=None):
        """Draw text on screen."""
        if font is None:
            font = self.font
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=pos)
        self.screen.blit(text_surface, text_rect)

    def draw_background(self):
        """Draw a subtle running grid background instead of a flat black fill.

        Uses GRID_CELL_PX from config to determine spacing and GRID_SCROLL_SPEED to animate.
        """
        # Fill base only within game area; clear info panel separately
        # Game area background
        game_area = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
        self.screen.fill(BLACK, game_area)
        # Info panel background (use configured INFO_PANEL_COLOR)
        info_area = pygame.Rect(GAME_WIDTH, 0, INFO_PANEL_WIDTH, GAME_HEIGHT)
        try:
            self.screen.fill(INFO_PANEL_COLOR, info_area)
        except Exception:
            # Fallback if INFO_PANEL_COLOR isn't defined
            self.screen.fill((10, 10, 10), info_area)

        cell = GRID_CELL_PX
        if cell <= 0:
            return

        # Compute offset for animation (creates 'running' effect)
        t = time.time()
        offset = int((t * GRID_SCROLL_SPEED) % cell)

        # Restrict drawing to the game area so the grid doesn't bleed into
        # the info panel. Use a clip rect for safety across different
        # backends and to avoid off-by-one drawing at the game/info border.
        prev_clip = self.screen.get_clip()
        try:
            self.screen.set_clip(game_area)

            # Vertical lines (only within the game area)
            for i, x in enumerate(range(-offset, GAME_WIDTH, cell)):
                # Major every GRID_MAJOR_EVERY
                if (i % GRID_MAJOR_EVERY) == 0:
                    color = GRID_MAJOR_LINE_COLOR
                else:
                    color = GRID_LINE_COLOR
                pygame.draw.line(self.screen, color, (x, 0), (x, GAME_HEIGHT))

            # Horizontal lines (only within the game area)
            for i, y in enumerate(range(-offset, GAME_HEIGHT, cell)):
                if (i % GRID_MAJOR_EVERY) == 0:
                    color = GRID_MAJOR_LINE_COLOR
                else:
                    color = GRID_LINE_COLOR
                pygame.draw.line(self.screen, color, (0, y), (GAME_WIDTH, y))
        finally:
            # Restore previous clipping region
            self.screen.set_clip(prev_clip)

    def draw_menu(self):
        """Draw menu screen."""
        # draw animated grid background
        self.draw_background()
        self.draw_text("FINGER-CONTROLLED SNAKE", (GAME_WIDTH // 2, GAME_HEIGHT // 2 - 80))
        self.draw_text("🐍 Ultra Smooth Edition 🍎", (GAME_WIDTH // 2, GAME_HEIGHT // 2 - 40),
                      YELLOW, self.small_font)
        self.draw_text("Show your index finger to start", (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 20),
                      YELLOW, self.small_font)

        if self.finger_detected:
            progress = ""
            if self.menu_detect_start:
                elapsed = time.time() - self.menu_detect_start
                progress = f" ({elapsed:.1f}s/{self.transition_delay}s)"
            self.draw_text(f"Finger detected! Starting...{progress}",
                           (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80),
                           GREEN, self.small_font)
        else:
            self.draw_text("Waiting for hand...", (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80),
                           RED, self.small_font)
        # On-screen hint
        self.draw_text("Press Q to quit | P to pause | M to mute", (GAME_WIDTH // 2, GAME_HEIGHT - 30), YELLOW, self.small_font)
        
    def draw_game_over(self):
        """Draw game over screen."""
        self.draw_background()
        self.draw_text("GAME OVER!", (GAME_WIDTH // 2, GAME_HEIGHT // 2 - 50), RED)
        self.draw_text(f"Final Score: {self.score}", (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 20), WHITE)
        self.draw_text("Show finger to restart", (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80),
                       YELLOW, self.small_font)
        
    def draw_hud(self):
        """Draw heads-up display."""
        # Draw HUD into the info panel (right side)
        base_x = GAME_WIDTH + 10
        current_y = 10
        score_text = self.small_font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (base_x, current_y))
        current_y += score_text.get_height() + 8
        
        # Draw Speed Boost Timer
        if time.time() < self.snake.speed_boost_end_time:
            time_left = self.snake.speed_boost_end_time - time.time()
            boost_text = self.small_font.render(f"BOOST: {time_left:.1f}s", True, GOLD)
            self.screen.blit(boost_text, (base_x, 70))

        status_color = GREEN if self.finger_detected else RED
        status_text = self.small_font.render(
            "Finger: " + ("Detected" if self.finger_detected else "Not Found"),
            True, status_color
        )
        self.screen.blit(status_text, (base_x, current_y))
        current_y += status_text.get_height() + 8

        fps_text = self.small_font.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
        self.screen.blit(fps_text, (base_x, GAME_HEIGHT - 30))
        # High score display (aligned to right of info panel)
        hs_text = self.small_font.render(f"High: {self.highscore}", True, WHITE)
        self.screen.blit(hs_text, (GAME_WIDTH + INFO_PANEL_WIDTH - 110, 10))

        # Mute / Pause indicator
        if self.muted:
            mute_text = self.small_font.render("MUTED", True, RED)
            self.screen.blit(mute_text, (GAME_WIDTH + INFO_PANEL_WIDTH - 110, 40))
        if self.paused:
            pause_text = self.font.render("PAUSED", True, YELLOW)
            pause_rect = pause_text.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2))
            self.screen.blit(pause_text, pause_rect)
        
    def draw_border(self):
        """Draw the game border."""
        # Draw a thick gray border that acts as the wall
        border_rect = (0, 0, GAME_WIDTH, GAME_HEIGHT)
        pygame.draw.rect(self.screen, DARK_GREY, border_rect, WALL_COLLISION_MARGIN)

    def draw_game_fps(self):
        """Draw FPS counter in the bottom-left of the game area."""
        try:
            fps = int(self.clock.get_fps())
            fps_surf = self.small_font.render(f"FPS: {fps}", True, WHITE)
            # small padding from left and bottom edges
            x = 8
            y = GAME_HEIGHT - fps_surf.get_height() - 8
            self.screen.blit(fps_surf, (x, y))
        except Exception:
            pass

    def run(self):
        """Main game loop."""
        if not self.running:
            self.cleanup()
            return
            
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # Handle key presses on KEYDOWN to make toggle actions
                    # (pause/mute/quit confirmation) respond to a single press.

                    # If exit confirmation dialog is active, handle Y/N/Esc on keydown
                    if self.exit_confirmation:
                        if event.key == pygame.K_y:
                            print('\n\nExit confirmed by user.')
                            self.running = False
                        elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                            # Cancel exit
                            self.exit_confirmation = False
                        # ignore other keys while confirming
                        continue

                    # If not confirming, handle primary controls on KEYDOWN
                    # Allow quitting with ESC or 'q' key — ask for confirmation
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        # Activate confirmation overlay rather than quitting immediately
                        self.exit_confirmation = True
                        continue
                    # Pause / Resume (toggle on single press)
                    elif event.key == pygame.K_p or event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                        continue
                    # Mute / Unmute (toggle on single press)
                    elif event.key == pygame.K_m:
                        self.muted = not self.muted
                        continue
                # Ignore KEYUP for control toggles to prevent double-toggling
                elif event.type == pygame.KEYUP:
                    pass

            self.update_from_shared_state()

            # If exit confirmation is active we should pause game updates
            # and render a static frame with the confirmation modal on top.
            if self.exit_confirmation:
                # Draw background + HUD + camera preview but do NOT advance game logic
                self.draw_background()
                self.draw_border()
                # Draw HUD (info panel)
                self.draw_hud()
                # Draw camera preview if available
                if self.camera_surface is not None:
                    cam_width = self.camera_surface.get_width()
                    cam_height = self.camera_surface.get_height()
                    cam_x = GAME_WIDTH + 10
                    cam_y = GAME_HEIGHT - cam_height - 10
                    self.screen.blit(self.camera_surface, (cam_x, cam_y))

                    # Draw confirmation modal centered over game area
                try:
                    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 160))
                    self.screen.blit(overlay, (0, 0))
                    msg = "Quit? Press Y to confirm, N or Esc to cancel"
                    text_surf = self.small_font.render(msg, True, WHITE)
                    text_rect = text_surf.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
                    pad = 12
                    box_rect = pygame.Rect(text_rect.left - pad, text_rect.top - pad,
                                            text_rect.width + pad * 2, text_rect.height + pad * 2)
                    pygame.draw.rect(self.screen, (40, 40, 40), box_rect, border_radius=6)
                    self.screen.blit(text_surf, text_rect)
                except Exception:
                    pass

                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # Draw game border first
            self.draw_border()

            if self.game_state == "MENU":
                self.draw_menu()

                # Menu logic
                if self.finger_detected and self.shared_finger_pos is not None:
                    if self.menu_detect_start is None:
                        self.menu_detect_start = time.time()
                    elif time.time() - self.menu_detect_start >= self.transition_delay:
                        self.game_state = "PLAYING"
                        self.snake.reset()
                        self.score = 0
                        for food in self.foods: # Respawn all foods
                             food.respawn(self.snake.segments)
                        self.menu_detect_start = None
                        # play start sound
                        try:
                            if not self.muted and 'start' in self.sounds:
                                self.sounds['start'].play()
                        except Exception:
                            pass
                else:
                    self.menu_detect_start = None

            elif self.game_state == "PLAYING":
                # When paused, skip updates but still draw HUD and camera preview
                if self.paused:
                    # Draw current frame and HUD, then flip
                    self.draw_hud()
                    if self.camera_surface is not None:
                        cam_width = self.camera_surface.get_width()
                        cam_height = self.camera_surface.get_height()
                        # Place camera preview inside the info panel
                        cam_x = GAME_WIDTH + 10
                        cam_y = GAME_HEIGHT - cam_height - 10
                        self.screen.blit(self.camera_surface, (cam_x, cam_y))
                    # Draw FPS in bottom-left of game area when paused
                    self.draw_game_fps()
                    # Draw FPS in bottom-left when showing confirmation modal
                    self.draw_game_fps()
                    pygame.display.flip()
                    self.clock.tick(FPS)
                    continue
                # draw grid background and border
                self.draw_background()
                self.draw_border()

                # Bonus Food Spawn Logic
                if len(self.foods) < 2 and time.time() >= self.bonus_food_spawn_timer:
                    new_bonus_food = BonusFood()
                    new_bonus_food.respawn(self.snake.segments)
                    self.foods.append(new_bonus_food)
                    self.bonus_food_spawn_timer = time.time() + random.uniform(20.0, 30.0)

                # Update & Draw Foods
                for food in self.foods:
                    food.update()
                    food.draw(self.screen)

                # Update Snake
                if self.finger_detected and self.last_finger_pos:
                    self.snake.update(self.last_finger_pos)

                # Check Collisions
                head = self.snake.segments[0]
                
                # Food Collision
                for food in list(self.foods):
                    if food.check_collision(head):
                        self.score += food.score
                        self.snake.grow(food.score * GROWTH_RATE)
                        # play eat/bonus sound
                        try:
                            if not self.muted and ('bonus' in self.sounds or 'eat' in self.sounds):
                                if food.is_bonus and 'bonus' in self.sounds:
                                    self.sounds['bonus'].play()
                                elif not food.is_bonus and 'eat' in self.sounds:
                                    self.sounds['eat'].play()
                        except Exception:
                            pass

                        if food.is_bonus:
                            self.snake.activate_boost(food.boost_duration)
                            try:
                                self.foods.remove(food) # Remove bonus food immediately
                            except ValueError:
                                pass
                        else:
                            food.respawn(self.snake.segments)

                # Game Over Collision (Wall or Self)
                if self.snake.check_self_collision() or self.snake.check_wall_collision():
                    self.game_state = "GAME_OVER"
                    self.flash_timer = time.time() + 0.5 # Flash screen red for 0.5s
                    self.gameover_detect_start = None
                    # Update highscore if beaten
                    try:
                        if self.score > int(self.highscore):
                            self.highscore = int(self.score)
                            self._save_highscore()
                    except Exception:
                        pass
                    # play death sound
                    try:
                        if not self.muted and 'die' in self.sounds:
                            self.sounds['die'].play()
                    except Exception:
                        pass

                self.snake.draw(self.screen)
                self.draw_hud()

                # Draw smooth pointer
                if self.last_finger_pos:
                    pygame.draw.circle(self.screen, BLUE, self.last_finger_pos, 10, 3)
                    pygame.draw.circle(self.screen, WHITE, self.last_finger_pos, 3)
                    
                # Collision Flash Effect
                if time.time() < self.flash_timer:
                    flash_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                    flash_surface.fill((255, 0, 0, 100)) # Semi-transparent red
                    self.screen.blit(flash_surface, (0, 0))

            elif self.game_state == "GAME_OVER":
                self.draw_game_over()
                
                # Game Over Transition Logic
                if self.finger_detected and self.shared_finger_pos is not None:
                    if self.gameover_detect_start is None:
                        self.gameover_detect_start = time.time()
                    elif time.time() - self.gameover_detect_start >= self.transition_delay:
                        self.game_state = "PLAYING"
                        self.snake.reset()
                        self.score = 0
                        # Re-initialize all foods
                        self.foods = [RegularFood()]
                        self.foods[0].respawn(self.snake.segments)
                        self.bonus_food_spawn_timer = time.time() + 15.0 
                        self.gameover_detect_start = None
                else:
                    self.gameover_detect_start = None

            # Camera Preview Display
            if self.camera_surface is not None:
                cam_width = self.camera_surface.get_width()
                cam_height = self.camera_surface.get_height()
                # Place camera preview inside the info panel (left-aligned)
                cam_x = GAME_WIDTH + 10
                cam_y = GAME_HEIGHT - cam_height - 10
                self.screen.blit(self.camera_surface, (cam_x, cam_y))
            # If exit confirmation is active, draw a modal confirmation overlay
            if self.exit_confirmation:
                try:
                    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 160))  # semi-transparent dark overlay
                    self.screen.blit(overlay, (0, 0))

                    msg = "Quit? Press Y to confirm, N or Esc to cancel"
                    # Use small font so it fits across different resolutions
                    text_surf = self.small_font.render(msg, True, WHITE)
                    text_rect = text_surf.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
                    # Draw a slightly brighter box behind the text for clarity
                    pad = 12
                    box_rect = pygame.Rect(text_rect.left - pad, text_rect.top - pad,
                                            text_rect.width + pad * 2, text_rect.height + pad * 2)
                    pygame.draw.rect(self.screen, (40, 40, 40), box_rect, border_radius=6)
                    self.screen.blit(text_surf, text_rect)
                except Exception:
                    # If anything goes wrong drawing the overlay, still allow exit
                    pass

            # Draw FPS in bottom-left of the game area
            self.draw_game_fps()
            pygame.display.flip()
            self.clock.tick(FPS)

        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        try:
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=1.0)
        except:
            pass

        if hasattr(self, 'cap') and self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            
        try:
            self.hand_tracker.hands.close()
        except:
            pass
        pygame.quit()
        cv2.destroyAllWindows()
