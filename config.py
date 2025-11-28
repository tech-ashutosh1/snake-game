CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

GAME_WIDTH = 800
GAME_HEIGHT = 600
FPS = 60

SNAKE_SEGMENT_SIZE = 14
INITIAL_LENGTH = 7
GROWTH_RATE = 2
FOOD_SIZE = 15
BONUS_FOOD_SIZE = 20

MIN_DISTANCE_TO_MOVE = 2
MAX_SPEED = 4.0

SEGMENT_SPACING = 5.0

COLLISION_THRESHOLD = 10
SELF_COLLISION_IGNORE = 5
WALL_COLLISION_MARGIN = 5

SMOOTHING_WINDOW = 15
SMOOTHING_FACTOR = 0.15

WHITE = (255,255,255)
BLACK = (0,0,0)
GREEN = (0,255,0)
DARK_GREEN = (0,150,0)
RED = (255,50,50)
YELLOW = (255,255,0)
BLUE = (100,150,255)
GOLD = (255,215,0)
DARK_GREY = (50,50,50)
ORANGE = (255, 165, 0)


FOOD_SPAWN_MARGIN = 50

# Grid background settings
# Grid cell size is specified in centimeters (visual target). We convert to pixels
# using a default DPI; you can tweak GRID_DEFAULT_DPI if your display reports different scaling.
GRID_CM = 2
GRID_DEFAULT_DPI = 96
# Pixels per grid cell (approx)
GRID_CELL_PX = max(8, int((GRID_DEFAULT_DPI / 2.54) * GRID_CM))
# Grid colors and animation speed (pixels per second)
GRID_LINE_COLOR = (28, 28, 28)
GRID_MAJOR_LINE_COLOR = (44, 44, 44)
GRID_MAJOR_EVERY = 5
GRID_SCROLL_SPEED = 12  # px/sec, small scrolling motion to make grid 'running'
