from collections import deque
import time, math
from config import *
import pygame

class Snake:
    """Snake game logic with smooth following behavior."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset snake to initial state."""
        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        
        # Start with segments spread out horizontally with SEGMENT_SPACING
        self.segments = deque([
            (center_x - i * SEGMENT_SPACING, center_y) for i in range(INITIAL_LENGTH)
        ])
        self.growth_pending = 0
        self.velocity = (0.0, 0.0)
        self.speed_boost_end_time = 0.0

    def get_max_speed(self):
        """Return the current max speed, including boost."""
        if time.time() < self.speed_boost_end_time:
            return MAX_SPEED * 1.5  # 50% speed boost
        return MAX_SPEED

    def activate_boost(self, duration=3.0):
        """Activate temporary speed boost."""
        self.speed_boost_end_time = time.time() + duration

    def update(self, target_pos):
        """Update snake position with smooth, natural movement maintaining spacing."""
        if target_pos:
            head = self.segments[0]

            dx = target_pos[0] - head[0]
            dy = target_pos[1] - head[1]
            distance = math.hypot(dx, dy)
            current_max_speed = self.get_max_speed()

            # Dead zone - don't move if very close
            if distance < MIN_DISTANCE_TO_MOVE:
                return

            # Smooth acceleration/deceleration
            if distance > 0:
                # Direction vector
                dir_x = dx / distance
                dir_y = dy / distance
                
                # Scale speed based on distance (ease-in/ease-out)
                speed_factor = min(distance / 100, 1.0)
                speed = current_max_speed * speed_factor
                
                # Apply inertia for smoother movement
                inertia = 0.8 # Increased inertia for smoother tracking
                target_vel_x = dir_x * speed
                target_vel_y = dir_y * speed
                
                self.velocity = (
                    self.velocity[0] * inertia + target_vel_x * (1 - inertia),
                    self.velocity[1] * inertia + target_vel_y * (1 - inertia)
                )
                
                new_head = (
                    head[0] + self.velocity[0],
                    head[1] + self.velocity[1]
                )

                # Add new head (using floating-point for better segment spacing calculation)
                self.segments.appendleft(new_head)

                # Maintain consistent spacing between segments
                segments_to_keep = []
                segments_to_keep.append(self.segments[0])
                
                for i in range(1, len(self.segments)):
                    prev_seg = segments_to_keep[-1]
                    curr_seg = self.segments[i]
                    
                    # Calculate distance between segments
                    dx_s = curr_seg[0] - prev_seg[0]
                    dy_s = curr_seg[1] - prev_seg[1]
                    dist = math.hypot(dx_s, dy_s)
                    
                    # Only keep segment if it maintains proper spacing
                    if dist >= SEGMENT_SPACING:
                        # Adjust position to maintain exact spacing
                        if dist > 0:
                            ratio = SEGMENT_SPACING / dist
                            new_x = prev_seg[0] + dx_s * ratio
                            new_y = prev_seg[1] + dy_s * ratio
                            segments_to_keep.append((new_x, new_y))
                
                # Update segments with properly spaced ones
                self.segments = deque(segments_to_keep)
                
                # Handle growth (adds a new segment only if space allows)
                target_length = INITIAL_LENGTH + self.growth_pending
                
                while len(self.segments) < target_length:
                    if len(self.segments) >= 2:
                        tail = self.segments[-1]
                        prev = self.segments[-2]
                        # Calculate segment direction
                        dx_t = tail[0] - prev[0]
                        dy_t = tail[1] - prev[1]
                        dist = math.hypot(dx_t, dy_t)
                        
                        if dist > 0:
                            # Project new segment outwards from tail
                            new_x = tail[0] + (dx_t / dist) * SEGMENT_SPACING
                            new_y = tail[1] + (dy_t / dist) * SEGMENT_SPACING
                            self.segments.append((new_x, new_y))
                        else:
                             # Failsafe for segments on the exact same spot
                             self.segments.append((tail[0], tail[1] + SEGMENT_SPACING))
                    else:
                        # For very short snake, just append one segment away
                        tail = self.segments[-1]
                        self.segments.append((tail[0], tail[1] + SEGMENT_SPACING))

                # Trim if too long
                while len(self.segments) > target_length:
                    self.segments.pop()

    def grow(self, amount=GROWTH_RATE):
        """Add growth to snake."""
        self.growth_pending += amount

    def check_self_collision(self):
        """Check if snake head collides with its body."""
        if len(self.segments) <= SELF_COLLISION_IGNORE:
            return False

        head = self.segments[0]
        # Iterate over segments from a safe distance
        for segment in list(self.segments)[SELF_COLLISION_IGNORE:]:
            if math.hypot(head[0] - segment[0], head[1] - segment[1]) < COLLISION_THRESHOLD:
                return True
        return False

    def check_wall_collision(self):
        """Check if snake head collides with the game boundary."""
        head = self.segments[0]
        x, y = head
        
        if (x < WALL_COLLISION_MARGIN or x > GAME_WIDTH - WALL_COLLISION_MARGIN or
            y < WALL_COLLISION_MARGIN or y > GAME_HEIGHT - WALL_COLLISION_MARGIN):
            return True
        return False

    def draw(self, screen):
        """Draw snake with a gradient effect."""
        segments_list = [(int(x), int(y)) for x, y in self.segments] # Convert to int for drawing
        
        if len(segments_list) < 2:
            return
        
        # Determine base color for the body
        if time.time() < self.speed_boost_end_time:
             # Pulsating gold when boosted
            pulse = (math.sin(time.time() * 20) * 0.1) + 1.0 
            base_color = (int(GOLD[0] * pulse), int(GOLD[1] * pulse), int(GOLD[2] * pulse))
            base_outline = GOLD
        else:
            base_color = DARK_GREEN
            base_outline = GREEN
            
        # Draw body as thick line segments with metallic/gradient look
        for i in range(len(segments_list) - 1):
            start_pos = segments_list[i]
            end_pos = segments_list[i + 1]
            
            # Gradient effect from head to tail
            brightness_factor = 1.0 - (i / len(segments_list)) * 0.4
            
            # Calculate a slightly brighter color for the main body
            body_color = (
                min(255, int(base_color[0] * brightness_factor + 50 * brightness_factor)),
                min(255, int(base_color[1] * brightness_factor + 100 * brightness_factor)),
                min(255, int(base_color[2] * brightness_factor + 50 * brightness_factor))
            )
            
            thickness = SNAKE_SEGMENT_SIZE - 2
            pygame.draw.line(screen, body_color, start_pos, end_pos, thickness)
            
            # Draw a darker core line for metallic sheen
            dark_color = (
                 int(body_color[0] * 0.5),
                 int(body_color[1] * 0.5),
                 int(body_color[2] * 0.5)
            )
            pygame.draw.line(screen, dark_color, start_pos, end_pos, max(1, thickness // 3))

        # Draw circles at joints for smooth connection and head
        for i, segment in enumerate(segments_list):
            brightness_factor = 1.0 - (i / len(segments_list)) * 0.4
            
            if i == 0:
                # Draw head
                head_color = (
                    min(255, int(base_outline[0] * brightness_factor)),
                    min(255, int(base_outline[1] * brightness_factor)),
                    min(255, int(base_outline[2] * brightness_factor))
                )
                
                pygame.draw.circle(screen, head_color, segment, SNAKE_SEGMENT_SIZE)
                pygame.draw.circle(screen, base_outline, segment, SNAKE_SEGMENT_SIZE, 3)
                
                # Eye dots
                eye_x, eye_y = segment
                # Calculate eye offset based on velocity for movement direction (simplified)
                if len(segments_list) > 1:
                    next_seg = segments_list[1]
                    angle = math.atan2(eye_y - next_seg[1], eye_x - next_seg[0])
                else:
                    angle = -math.pi / 2 # Default up
                
                offset = 4
                eye_dx = offset * math.cos(angle)
                eye_dy = offset * math.sin(angle)
                
                eye1_x = eye_x + eye_dy - 2
                eye1_y = eye_y - eye_dx - 2
                eye2_x = eye_x - eye_dy + 2
                eye2_y = eye_y + eye_dx + 2
                
                pygame.draw.circle(screen, WHITE, (int(eye1_x), int(eye1_y)), 3)
                pygame.draw.circle(screen, WHITE, (int(eye2_x), int(eye2_y)), 3)
                pygame.draw.circle(screen, BLACK, (int(eye1_x), int(eye1_y)), 1)
                pygame.draw.circle(screen, BLACK, (int(eye2_x), int(eye2_y)), 1)
                
            else:
                # Draw joint circles
                size = max(1, SNAKE_SEGMENT_SIZE - 4)
                joint_color = (
                    min(255, int(base_color[0] * brightness_factor)),
                    min(255, int(base_color[1] * brightness_factor)),
                    min(255, int(base_color[2] * brightness_factor))
                )
                pygame.draw.circle(screen, joint_color, segment, size)
                pygame.draw.circle(screen, base_outline, segment, size, 2)
