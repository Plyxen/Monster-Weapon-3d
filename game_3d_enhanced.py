import pygame
import numpy as np
import random
import math
import time
from game_functions import (
    get_random_monster, get_weapon_choice, calculate_win_chance, 
    show_battle_result, create_stats, update_stats, animated_print
)

class Vector3D:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z
    
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            return Vector3D(self.x / mag, self.y / mag, self.z / mag)
        return Vector3D(0, 0, 0)

class MazeMap:
    def __init__(self, width=81, height=81, base_level=0):  # Moderate sized maze for good performance
        self.width = width if width % 2 == 1 else width + 1  # Ensure odd dimensions
        self.height = height if height % 2 == 1 else height + 1
        self.base_level = base_level  # Floor level
        self.wall_height = 8  # More reasonable wall height
        self.ceiling_height = 8  # Lower ceiling for better scale
        
        # Maze data: 0 = wall, 1 = floor, 2 = room, 3 = corridor
        self.maze = self.generate_maze()
        self.terrain = self.convert_maze_to_terrain()
        self.rooms = []  # List of room areas
        self.monsters = self.place_monsters()
        self.treasures = self.place_treasures()
        
    def generate_terrain(self):
        """Generate terrain after maze is created"""
        terrain = np.full((self.height, self.width), self.base_level)
        
        # Create walls based on maze layout (maze must be generated first)
        for y in range(self.height):
            for x in range(self.width):
                if (x == 0 or x == self.width-1 or y == 0 or y == self.height-1 or 
                    self.maze[y][x] == 0):  # Maze walls
                    terrain[y][x] = self.wall_height  # Wall height
                else:
                    terrain[y][x] = self.base_level  # Flat floor
        
        return terrain
    
    def generate_maze(self):
        """Generate DOOM-style maze using iterative backtracking to avoid recursion limits"""
        maze = [[0 for _ in range(self.width)] for _ in range(self.height)]
        
        # Initialize all cells as walls
        for y in range(self.height):
            for x in range(self.width):
                maze[y][x] = 0  # Wall
        
        # Iterative backtracking maze generation using a stack
        stack = []
        
        # Start maze generation from center area (aligned to 12-unit grid for wider spaces)
        start_x = 12 + (self.width // 24) * 12  # Align to 12-unit grid
        start_y = 12 + (self.height // 24) * 12
        
        # Mark starting area as 7x7 open space
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if (0 <= start_y + dy < self.height and 0 <= start_x + dx < self.width):
                    maze[start_y + dy][start_x + dx] = 1
        
        stack.append((start_x, start_y))
        
        while stack:
            current_x, current_y = stack[-1]  # Peek at top of stack
            
            # Get all possible directions from current cell (much wider spacing for huge corridors)
            directions = [(0, 12), (12, 0), (0, -12), (-12, 0)]  # Right, Down, Left, Up with 12-unit spacing
            random.shuffle(directions)
            
            found_unvisited = False
            
            for dx, dy in directions:
                nx, ny = current_x + dx, current_y + dy
                
                # Check bounds and if cell is unvisited
                if (6 <= nx < self.width - 6 and 6 <= ny < self.height - 6 and 
                    maze[ny][nx] == 0):
                    
                    # Carve very wide corridor (7 units wide) between current and next cell
                    for corridor_step in range(1, abs(dx) + abs(dy)):
                        step_x = current_x + (dx // abs(dx) if dx != 0 else 0) * corridor_step
                        step_y = current_y + (dy // abs(dy) if dy != 0 else 0) * corridor_step
                        
                        # Make corridor 7 units wide
                        if dx != 0:  # Horizontal corridor
                            for offset in range(-3, 4):  # -3, -2, -1, 0, 1, 2, 3
                                if 0 <= step_y + offset < self.height:
                                    maze[step_y + offset][step_x] = 1
                        else:  # Vertical corridor
                            for offset in range(-3, 4):  # -3, -2, -1, 0, 1, 2, 3
                                if 0 <= step_x + offset < self.width:
                                    maze[step_y][step_x + offset] = 1
                    
                    # Mark destination as 7x7 open area
                    for dy_offset in range(-3, 4):
                        for dx_offset in range(-3, 4):
                            if (0 <= ny + dy_offset < self.height and 0 <= nx + dx_offset < self.width):
                                maze[ny + dy_offset][nx + dx_offset] = 1
                    
                    # Add new cell to stack
                    stack.append((nx, ny))
                    found_unvisited = True
                    break
            
            # If no unvisited neighbors, backtrack
            if not found_unvisited:
                stack.pop()
        
        # Add large rooms randomly
        self.add_rooms(maze)
        
        # Add some random connections to make it less linear
        self.add_random_connections(maze)
        
        return maze
    
    def add_rooms(self, maze):
        """Add large DOOM-style rooms to the maze"""
        num_rooms = random.randint(8, 15)
        
        for _ in range(num_rooms):
            # Random room size (odd dimensions for proper maze integration) - much larger
            room_w = random.randrange(15, 26, 2)  # 15x15 to 25x25, odd only
            room_h = random.randrange(15, 26, 2)
            
            # Random position
            room_x = random.randrange(5, self.width - room_w - 5, 2)  # Ensure odd position
            room_y = random.randrange(5, self.height - room_h - 5, 2)
            
            # Check if area is mostly walls (good for room placement)
            wall_count = 0
            total_cells = room_w * room_h
            
            for ry in range(room_y, room_y + room_h):
                for rx in range(room_x, room_x + room_w):
                    if maze[ry][rx] == 0:
                        wall_count += 1
            
            # If mostly walls, create room
            if wall_count > total_cells * 0.8:
                # Carve out the room
                for ry in range(room_y + 1, room_y + room_h - 1):
                    for rx in range(room_x + 1, room_x + room_w - 1):
                        maze[ry][rx] = 2  # Mark as room
                
                # Store room info
                self.rooms.append({
                    'x': room_x, 'y': room_y,
                    'width': room_w, 'height': room_h,
                    'center_x': room_x + room_w // 2,
                    'center_y': room_y + room_h // 2
                })
                
                # Connect room to existing passages
                self.connect_room_to_maze(maze, room_x, room_y, room_w, room_h)
    
    def connect_room_to_maze(self, maze, room_x, room_y, room_w, room_h):
        """Connect a room to the existing maze network"""
        connections = 0
        max_connections = random.randint(2, 4)
        
        # Try to connect from each side
        sides = ['top', 'bottom', 'left', 'right']
        random.shuffle(sides)
        
        for side in sides:
            if connections >= max_connections:
                break
                
            if side == 'top':
                for x in range(room_x + 2, room_x + room_w - 2, 2):
                    if (room_y > 2 and x >= 0 and x < self.width and 
                        room_y - 2 >= 0 and maze[room_y - 2][x] == 1):  # Found passage
                        maze[room_y - 1][x] = 3  # Corridor
                        connections += 1
                        break
            elif side == 'bottom':
                for x in range(room_x + 2, room_x + room_w - 2, 2):
                    if (room_y + room_h < self.height - 2 and x >= 0 and x < self.width and
                        room_y + room_h + 1 < self.height and maze[room_y + room_h + 1][x] == 1):
                        maze[room_y + room_h][x] = 3  # Corridor
                        connections += 1
                        break
            elif side == 'left':
                for y in range(room_y + 2, room_y + room_h - 2, 2):
                    if (room_x > 2 and y >= 0 and y < self.height and
                        room_x - 2 >= 0 and maze[y][room_x - 2] == 1):
                        maze[y][room_x - 1] = 3  # Corridor
                        connections += 1
                        break
            elif side == 'right':
                for y in range(room_y + 2, room_y + room_h - 2, 2):
                    if (room_x + room_w < self.width - 2 and y >= 0 and y < self.height and
                        room_x + room_w + 1 < self.width and maze[y][room_x + room_w + 1] == 1):
                        maze[y][room_x + room_w] = 3  # Corridor
                        connections += 1
                        break
    
    def add_random_connections(self, maze):
        """Add random connections to create loops and make exploration interesting"""
        connections_added = 0
        max_connections = random.randint(15, 25)
        
        for _ in range(max_connections * 3):  # Try more times than we want
            if connections_added >= max_connections:
                break
                
            x = random.randrange(2, self.width - 2)
            y = random.randrange(2, self.height - 2)
            
            # If this is a wall and has passages on opposite sides
            if maze[y][x] == 0:
                # Check horizontal connection
                if (maze[y][x-1] in [1, 2, 3] and maze[y][x+1] in [1, 2, 3] and
                    random.random() < 0.3):
                    maze[y][x] = 3  # Corridor
                    connections_added += 1
                # Check vertical connection
                elif (maze[y-1][x] in [1, 2, 3] and maze[y+1][x] in [1, 2, 3] and
                      random.random() < 0.3):
                    maze[y][x] = 3  # Corridor
                    connections_added += 1
    
    def convert_maze_to_terrain(self):
        """Convert maze data to height-based terrain for 3D rendering"""
        terrain = []
        
        for y in range(self.height):
            row = []
            for x in range(self.width):
                if self.maze[y][x] == 0:  # Wall
                    # Make walls much taller and more prominent
                    height_variation = random.uniform(2.0, 4.0)
                    row.append(self.wall_height + height_variation)
                elif self.maze[y][x] == 2:  # Room floor
                    row.append(self.base_level)  # Keep rooms at base level
                else:  # Corridor floor (1 or 3)
                    row.append(self.base_level)
            terrain.append(row)
        
        return terrain
    
    def is_wall_occluded(self, wall_x, wall_z, player_pos, render_range=30):
        """Check if a wall is occluded by other walls closer to the player using raycasting"""
        # Calculate direction from player to wall
        dx = wall_x - player_pos.x
        dz = wall_z - player_pos.z
        distance_to_wall = (dx*dx + dz*dz)**0.5
        
        # Don't cull walls that are very close
        if distance_to_wall < 3.0:
            return False
            
        # Normalize direction vector
        if distance_to_wall == 0:
            return False
        dx /= distance_to_wall
        dz /= distance_to_wall
        
        # Cast ray from player toward wall, checking for blocking walls
        step_size = 0.5  # Check every 0.5 units
        steps = int(distance_to_wall / step_size)
        
        for i in range(1, steps):  # Start from 1 to skip player position
            check_x = player_pos.x + dx * (i * step_size)
            check_z = player_pos.z + dz * (i * step_size)
            
            # Convert to maze coordinates
            maze_x = int(check_x)
            maze_z = int(check_z)
            
            # Check if we hit a wall that's closer than our target wall
            if (0 <= maze_x < self.width and 0 <= maze_z < self.height and
                self.maze[maze_z][maze_x] == 0):  # Found a blocking wall
                # Make sure this isn't the wall we're checking
                if abs(maze_x - wall_x) > 0.5 or abs(maze_z - wall_z) > 0.5:
                    return True  # This wall is occluded
                    
        return False  # Wall is not occluded
    
    def generate_wall_faces(self, maze_map, player):
        """Generate vertical wall faces for proper 3D wall rendering"""
        wall_triangles = []
        
        # Check area around player for walls
        player_x, player_z = int(player.position.x), int(player.position.z)
        render_range = 15  # Reduced range for better performance and less z-fighting
        
        for z in range(max(0, player_z - render_range), min(maze_map.height, player_z + render_range)):
            for x in range(max(0, player_x - render_range), min(maze_map.width, player_x + render_range)):
                if maze_map.maze[z][x] == 0:  # This is a wall
                    # Check adjacent cells to create wall faces
                    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # North, East, South, West
                    
                    for dx, dz in directions:
                        adj_x, adj_z = x + dx, z + dz
                        
                        # Create wall face if adjacent cell is a corridor or out of bounds
                        if (adj_x < 0 or adj_x >= maze_map.width or 
                            adj_z < 0 or adj_z >= maze_map.height or 
                            maze_map.maze[adj_z][adj_x] != 0):  # Adjacent is not a wall
                            
                            wall_height = maze_map.wall_height
                            floor_level = maze_map.base_level
                            
                            # Create wall face vertices
                            if dx == 0:  # North/South face
                                face_x = x + 0.5
                                face_z = z + 0.5 + dz * 0.5
                                
                                v1 = Vector3D(face_x - 0.5, floor_level, face_z)
                                v2 = Vector3D(face_x + 0.5, floor_level, face_z)
                                v3 = Vector3D(face_x + 0.5, floor_level + wall_height, face_z)
                                v4 = Vector3D(face_x - 0.5, floor_level + wall_height, face_z)
                            else:  # East/West face
                                face_x = x + 0.5 + dx * 0.5
                                face_z = z + 0.5
                                
                                v1 = Vector3D(face_x, floor_level, face_z - 0.5)
                                v2 = Vector3D(face_x, floor_level, face_z + 0.5)
                                v3 = Vector3D(face_x, floor_level + wall_height, face_z + 0.5)
                                v4 = Vector3D(face_x, floor_level + wall_height, face_z - 0.5)
                            
                            # Project vertices to screen
                            screen_vertices = []
                            total_distance = 0
                            
                            for vertex in [v1, v2, v3, v4]:
                                screen_pos = self.camera.project_3d_to_2d(
                                    vertex, player.position, player.rotation_x, player.rotation_y,
                                    self.width, self.height
                                )
                                if screen_pos and screen_pos[2] > 0.001 and screen_pos[2] < 100 and 0 <= screen_pos[0] < self.width and 0 <= screen_pos[1] < self.height:
                                    screen_vertices.append(screen_pos)
                                    total_distance += screen_pos[2]
                                else:
                                    break
                            
                            # Create triangles from quad (2 triangles per wall face)
                            if len(screen_vertices) == 4:
                                avg_distance = total_distance / 4
                                wall_color = (120, 100, 80)  # Brown wall color
                                
                                # Triangle 1: v1, v2, v3
                                tri1 = ([screen_vertices[0], screen_vertices[1], screen_vertices[2]], wall_height, avg_distance)
                                # Triangle 2: v1, v3, v4  
                                tri2 = ([screen_vertices[0], screen_vertices[2], screen_vertices[3]], wall_height, avg_distance)
                                
                                wall_triangles.append(tri1)
                                wall_triangles.append(tri2)
        
        return wall_triangles
    
    def place_monsters(self):
        """Place monsters in maze corridors and rooms"""
        monsters = {}
        num_monsters = random.randint(20, 35)  # More monsters for bigger maze
        
        # Collect all valid positions (corridors and rooms)
        valid_positions = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.maze[y][x] in [1, 2, 3]:  # Floor spaces
                    valid_positions.append((x, y))
        
        # Shuffle for random placement
        random.shuffle(valid_positions)
        
        placed = 0
        for x, z in valid_positions:
            if placed >= num_monsters:
                break
                
            # Skip positions too close to each other
            too_close = False
            for (mx, mz) in monsters.keys():
                if abs(x - mx) + abs(z - mz) < 3:  # Manhattan distance
                    too_close = True
                    break
            
            if not too_close:
                monster_name, monster_info = get_random_monster()
                
                # Stronger monsters in rooms, weaker in corridors
                if self.maze[z][x] == 2:  # Room
                    health_bonus = random.randint(1, 2)
                else:
                    health_bonus = 0
                
                monsters[(x, z)] = {
                    'name': monster_name,
                    'info': monster_info,
                    'defeated': False,
                    'health': random.randint(2, 4) + health_bonus
                }
                placed += 1
        
        return monsters
    
    def place_treasures(self):
        """Place treasure chests in strategic maze locations"""
        treasures = {}
        num_treasures = random.randint(15, 25)  # More treasures for exploration
        
        # Prioritize room centers and dead ends
        treasure_positions = []
        
        # Add room centers
        for room in self.rooms:
            cx, cy = room['center_x'], room['center_y']
            if (cx, cy) not in self.monsters:
                treasure_positions.append((cx, cy, 'room_center'))
        
        # Find dead ends in corridors
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.maze[y][x] in [1, 3]:  # Corridor
                    # Count adjacent floor spaces
                    adjacent_floors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dy == 0 and dx == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if (0 <= nx < self.width and 0 <= ny < self.height and 
                                self.maze[ny][nx] in [1, 2, 3]):
                                adjacent_floors += 1
                    
                    # Dead end or corner
                    if adjacent_floors <= 2:
                        treasure_positions.append((x, y, 'dead_end'))
        
        # Add some random positions
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if (self.maze[y][x] in [1, 2, 3] and 
                    (x, y) not in self.monsters and 
                    random.random() < 0.1):
                    treasure_positions.append((x, y, 'random'))
        
        # Shuffle and place treasures
        random.shuffle(treasure_positions)
        
        placed = 0
        for x, z, location_type in treasure_positions:
            if placed >= num_treasures:
                break
                
            if (x, z) not in self.monsters and (x, z) not in treasures:
                # Better treasures in rooms and dead ends
                if location_type == 'room_center':
                    treasure_type = random.choice(['mega_health', 'weapon_upgrade', 'points', 'mega_health'])
                elif location_type == 'dead_end':
                    treasure_type = random.choice(['health', 'weapon_upgrade', 'points'])
                else:
                    treasure_type = random.choice(['health', 'points', 'health'])
                
                treasures[(x, z)] = {
                    'opened': False,
                    'contents': treasure_type
                }
                placed += 1
        
        return treasures
    
    def get_floor_height(self, x, z):
        """Get floor height - returns floor 1 unit below base level"""
        # Floor is 1 unit below where walls start from
        return self.base_level - 1.0
    
    def get_height(self, x, z):
        """Get terrain height at given coordinates with bounds checking"""
        if 0 <= int(x) < self.width and 0 <= int(z) < self.height:
            maze_x, maze_z = int(x), int(z)
            # Always return base level for player position queries
            # This ensures player stays on the floor level
            return self.base_level
        return self.base_level  # Return floor level even for out of bounds



class Player:
    def __init__(self, start_x=20, start_z=20):
        self.position = Vector3D(start_x, 0.7, start_z)  # Start at eye level above floor
        self.rotation_y = 0  # Horizontal rotation
        self.rotation_x = 0  # Look straight ahead normally  
        self.speed = 0.2  # Much slower, more controllable movement
        self.max_hp = 5
        self.hp = self.max_hp
        self.velocity_y = 0  # Vertical velocity for jumping
        self.is_jumping = False
        self.jump_strength = 5.0  # Stronger jump
        self.gravity = -15.0  # Stronger gravity for better feel
        self.weapon = "kard"
        self.weapon_emoji = "⚔️"
        self.stats = create_stats()
        self.experience = 0
        self.level = 1
        self.minimum_safe_height = None  # Will be set by game initialization
        
    def jump(self):
        """Make player jump if on ground"""
        if not self.is_jumping and abs(self.velocity_y) < 0.1:  # Only jump if on ground
            self.velocity_y = self.jump_strength
            self.is_jumping = True
            print(f"🦘 Player jumped! Velocity: {self.velocity_y}")  # Debug jump
    
    def apply_physics(self, maze_map, dt=1.0/60.0):
        """Apply physics: gravity, ground collision, etc."""
        # Get floor height (floor is 1 unit below base level)
        floor_height = maze_map.base_level - 1.0
        player_eye_height = 1.7  # Player eye level above their feet
        ground_level = floor_height + player_eye_height  # Player eye level when standing on floor
        
        # Apply gravity
        self.velocity_y += self.gravity * dt
        
        # Update Y position
        self.position.y += self.velocity_y * dt
        
        # Ground collision - check if player hits the floor
        if self.position.y <= ground_level:
            self.position.y = ground_level
            self.velocity_y = 0
            self.is_jumping = False
        
        # Prevent falling through floor
        if self.position.y < ground_level:
            self.position.y = ground_level
            self.velocity_y = 0
    
    def update_position(self, maze_map):
        """Update player position with physics - deprecated, physics now in main loop"""
        # Physics are now applied continuously in the main game loop
        pass
    
    def can_move_to(self, new_x, new_z, maze_map):
        """Simplified collision detection to prevent rendering issues"""
        # Check map boundaries with small buffer
        buffer = 0.2  # Smaller buffer to prevent complex calculations
        if not (buffer <= new_x < maze_map.width - buffer and buffer <= new_z < maze_map.height - buffer):
            return False
        
        # Check if destination is walkable in maze
        maze_x = int(new_x)
        maze_z = int(new_z)
        
        # Only allow movement in walkable areas (corridors, rooms, doors)
        if maze_map.maze[maze_z][maze_x] in [1, 2, 3]:  # Walkable areas
            return True
        
        return False  # Block movement into walls (0) or other non-walkable areas
    
    def is_on_ground(self, maze_map):
        """Check if player is currently on the ground"""
        floor_height = maze_map.get_floor_height(self.position.x, self.position.z)
        player_eye_height = 1.7
        ground_level = floor_height + player_eye_height
        
        # Player is on ground if they're at or very close to ground level
        return abs(self.position.y - ground_level) < 0.1
    
    def move_forward(self, maze_map):
        """Move forward in the direction the camera is looking (W key)"""
        # Match camera projection: uses -rotation_y, so forward is in -Z direction when rotation_y=0
        # Forward vector calculation matching camera transform
        cos_y = math.cos(math.radians(-self.rotation_y))
        sin_y = math.sin(math.radians(-self.rotation_y))
        
        # Forward direction in camera space is (0, 0, 1), transform to world space
        forward_x = sin_y
        forward_z = cos_y
        
        new_x = self.position.x + forward_x * self.speed
        new_z = self.position.z + forward_z * self.speed
        
        # Try wall sliding if direct movement fails
        if not self.can_move_to(new_x, new_z, maze_map):
            # Try sliding along X axis
            if self.can_move_to(new_x, self.position.z, maze_map):
                self.position.x = new_x
                self.update_position(maze_map)
            # Try sliding along Z axis  
            elif self.can_move_to(self.position.x, new_z, maze_map):
                self.position.z = new_z
                self.update_position(maze_map)
        else:
            self.position.x = new_x
            self.position.z = new_z
            self.update_position(maze_map)
    
    def move_backward(self, maze_map):
        """Move backward opposite to camera direction (S key)"""
        # Backward is opposite to forward direction
        cos_y = math.cos(math.radians(-self.rotation_y))
        sin_y = math.sin(math.radians(-self.rotation_y))
        
        # Backward direction (opposite of forward)
        backward_x = -sin_y
        backward_z = -cos_y
        
        new_x = self.position.x + backward_x * self.speed
        new_z = self.position.z + backward_z * self.speed
        
        # Try wall sliding if direct movement fails
        if not self.can_move_to(new_x, new_z, maze_map):
            # Try sliding along X axis
            if self.can_move_to(new_x, self.position.z, maze_map):
                self.position.x = new_x
                self.update_position(maze_map)
            # Try sliding along Z axis
            elif self.can_move_to(self.position.x, new_z, maze_map):
                self.position.z = new_z
                self.update_position(maze_map)
        else:
            self.position.x = new_x
            self.position.z = new_z
            self.update_position(maze_map)
    
    def strafe_left(self, maze_map):
        """Move left perpendicular to camera direction (A key)"""
        # Left is perpendicular to forward direction (90 degrees counter-clockwise)
        cos_y = math.cos(math.radians(-self.rotation_y))
        sin_y = math.sin(math.radians(-self.rotation_y))
        
        # Left direction: rotate forward vector 90 degrees counter-clockwise
        left_x = -cos_y
        left_z = sin_y
        
        new_x = self.position.x + left_x * self.speed
        new_z = self.position.z + left_z * self.speed
        
        # Try wall sliding if direct movement fails
        if not self.can_move_to(new_x, new_z, maze_map):
            # Try sliding along X axis
            if self.can_move_to(new_x, self.position.z, maze_map):
                self.position.x = new_x
                self.update_position(maze_map)
            # Try sliding along Z axis
            elif self.can_move_to(self.position.x, new_z, maze_map):
                self.position.z = new_z
                self.update_position(maze_map)
        else:
            self.position.x = new_x
            self.position.z = new_z
            self.update_position(maze_map)
    
    def strafe_right(self, maze_map):
        """Move right perpendicular to camera direction (D key)"""
        # Right is perpendicular to forward direction (90 degrees clockwise)
        cos_y = math.cos(math.radians(-self.rotation_y))
        sin_y = math.sin(math.radians(-self.rotation_y))
        
        # Right direction: rotate forward vector 90 degrees clockwise
        right_x = cos_y
        right_z = -sin_y
        
        new_x = self.position.x + right_x * self.speed
        new_z = self.position.z + right_z * self.speed
        
        # Try wall sliding if direct movement fails
        if not self.can_move_to(new_x, new_z, maze_map):
            # Try sliding along X axis
            if self.can_move_to(new_x, self.position.z, maze_map):
                self.position.x = new_x
                self.update_position(maze_map)
            # Try sliding along Z axis
            elif self.can_move_to(self.position.x, new_z, maze_map):
                self.position.z = new_z
                self.update_position(maze_map)
        else:
            self.position.x = new_x
            self.position.z = new_z
            self.update_position(maze_map)
    
    def gain_experience(self, amount):
        """Add experience and check for level up"""
        self.experience += amount
        new_level = (self.experience // 100) + 1
        
        if new_level > self.level:
            self.level = new_level
            self.max_hp += 1
            self.hp = self.max_hp  # Full heal on level up
            return True  # Level up occurred
        return False

class Camera:
    def __init__(self, fov=70, near=0.001, far=500):  # Extremely minimal near clipping
        self.fov = fov
        self.near = near
        self.far = far
    
    def project_3d_to_2d(self, point, player_pos, player_rot_x, player_rot_y, screen_width, screen_height):
        """Enhanced 3D to 2D projection with proper camera transform"""
        # Translate relative to player (camera position)
        rel_x = point.x - player_pos.x
        rel_y = point.y - player_pos.y  
        rel_z = point.z - player_pos.z
        
        # Apply horizontal rotation (Y-axis rotation for looking left/right)
        cos_y = math.cos(math.radians(-player_rot_y))
        sin_y = math.sin(math.radians(-player_rot_y))
        
        rotated_x = rel_x * cos_y - rel_z * sin_y
        rotated_z = rel_x * sin_y + rel_z * cos_y
        
        # Apply vertical rotation (X-axis rotation for looking up/down) - FIXED INVERSION
        cos_x = math.cos(math.radians(player_rot_x))  # Removed negative sign to fix inversion
        sin_x = math.sin(math.radians(player_rot_x))  # Removed negative sign to fix inversion
        
        final_y = rel_y * cos_x - rotated_z * sin_x
        final_z = rel_y * sin_x + rotated_z * cos_x
        
        # Clip objects behind camera or too close (extremely minimal near clipping)
        if final_z <= 0.001:  # Extremely small near plane to prevent see-through
            return None
        
        # Perspective projection
        fov_factor = math.tan(math.radians(self.fov / 2))
        
        # Project to screen coordinates
        screen_x = (rotated_x / (final_z * fov_factor)) * (screen_width / 2) + (screen_width / 2)
        screen_y = (-final_y / (final_z * fov_factor)) * (screen_height / 2) + (screen_height / 2)  # Flip Y-axis
        
        return (int(screen_x), int(screen_y), final_z)

class Renderer:
    def __init__(self, screen_width=1024, screen_height=768):
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("🐲 Monster Weapons 3D Explorer 🗡️")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 20)
        self.large_font = pygame.font.Font(None, 36)
        self.width = screen_width
        self.height = screen_height
        self.camera = Camera()
        
        # Enhanced color palette with better terrain colors
        self.colors = {
            'sky_top': (135, 206, 250),
            'sky_bottom': (220, 240, 255),
            'ground_base': (34, 139, 34),
            'ground_low': (60, 150, 60),
            'ground_mid': (85, 130, 55),
            'ground_high': (100, 120, 50),
            'hill_low': (120, 100, 70),
            'hill_mid': (140, 90, 60),
            'hill_high': (160, 80, 50),
            'mountain': (139, 69, 19),
            'rock': (120, 120, 120),
            'cliff': (90, 90, 90),
            'wall': (70, 70, 70),
            'snow': (240, 240, 240),
            'water': (64, 164, 223),
            'monster': (255, 80, 80),
            'monster_glow': (255, 150, 150),
            'treasure': (255, 215, 0),
            'treasure_glow': (255, 255, 150),
            'player': (0, 255, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'purple': (128, 0, 128),
            'orange': (255, 165, 0),
            'ui_bg': (0, 0, 0, 128)  # Semi-transparent black
        }
    
    def render_sky_gradient(self):
        """Render a clean sky background"""
        # Clean sky color to prevent purple artifacts
        sky_color = (30, 50, 80)  # Deep blue sky
        pygame.draw.rect(self.screen, sky_color, (0, 0, self.width, self.height))
        
        # No ground color fill - let 3D rendering handle it
    
    def get_terrain_color(self, height, max_height):
        """Get realistic terrain color based on elevation"""
        ratio = height / max_height if max_height > 0 else 0
        
        if height > max_height * 0.9:  # Walls and cliffs
            return self.colors['wall']
        elif height > max_height * 0.8:  # Rocky cliffs
            return self.colors['cliff']
        elif height > max_height * 0.7:  # High rocks
            return self.colors['rock']
        elif height > max_height * 0.6:  # Mountain peaks
            return self.colors['mountain']
        elif height > max_height * 0.45:  # High hills
            return self.colors['hill_high']
        elif height > max_height * 0.3:  # Medium hills
            return self.colors['hill_mid']
        elif height > max_height * 0.15:  # Low hills
            return self.colors['hill_low']
        elif height > max_height * 0.05:  # Elevated ground
            return self.colors['ground_high']
        else:  # Base ground level
            return self.colors['ground_base']
    
    def get_maze_color(self, height, wall_height):
        """Get color for maze elements based on height"""
        if height >= wall_height * 0.8:  # High walls
            return self.colors['wall']
        elif height >= wall_height * 0.6:  # Medium walls
            return self.colors['cliff']
        elif height >= wall_height * 0.4:  # Low walls
            return self.colors['rock']
        elif height > 0.5:  # Elevated floor
            return self.colors['ground_mid']
        else:  # Base floor
            return self.colors['ground_base']
    
    def draw_ui_background(self, rect, color=(0, 0, 0, 200), border_color=(255, 255, 255), border_width=2):
        """Draw a semi-transparent background with border for UI elements"""
        # Create surface with per-pixel alpha
        bg_surface = pygame.Surface((rect.width, rect.height))
        bg_surface.set_alpha(color[3] if len(color) > 3 else 200)
        bg_surface.fill(color[:3])
        self.screen.blit(bg_surface, rect.topleft)
        
        # Draw border
        if border_width > 0:
            pygame.draw.rect(self.screen, border_color, rect, border_width)
    
    def render_terrain(self, maze_map, player):
        """Render 3D maze with polygon surfaces and improved graphics"""
        self.render_sky_gradient()
        
        # First, render ground plane
        self.render_ground_plane(maze_map, player)
        
        # Render maze walls as proper 3D faces  
        self.render_maze_walls(maze_map, player)
        
        # Render maze as connected triangular surfaces
        self.render_terrain_surfaces(maze_map, player)
        
        # Add maze wireframe for detail (reduced)
        # self.render_terrain_wireframe(maze_map, player)  # Disabled to see walls better
    
    def render_terrain_surfaces(self, maze_map, player):
        """Render maze as filled polygons/triangles"""
        step = 2  # Balance between quality and performance
        triangles = []
        
        # Generate triangular surfaces
        for z in range(0, maze_map.height - step, step):
            for x in range(0, maze_map.width - step, step):
                # Bounds checking to prevent crashes when far from map
                if (z + step >= maze_map.height or x + step >= maze_map.width or 
                    z < 0 or x < 0):
                    continue
                    
                # Get four corner points
                corners = [
                    (x, maze_map.terrain[z][x], z),
                    (x + step, maze_map.terrain[z][x + step], z),
                    (x, maze_map.terrain[z + step][x], z + step),
                    (x + step, maze_map.terrain[z + step][x + step], z + step)
                ]
                
                # Create two triangles from quad
                tri1 = [corners[0], corners[1], corners[2]]
                tri2 = [corners[1], corners[3], corners[2]]
                
                for triangle in [tri1, tri2]:
                    # Project triangle points to screen
                    screen_points = []
                    avg_height = 0
                    avg_distance = 0
                    
                    for px, py, pz in triangle:
                        world_pos = Vector3D(px, py, pz)
                        screen_pos = self.camera.project_3d_to_2d(
                            world_pos, player.position, player.rotation_x, player.rotation_y,
                            self.width, self.height
                        )
                        
                        if screen_pos and screen_pos[2] > 0.001 and screen_pos[2] < 100 and 0 <= screen_pos[0] < self.width and 0 <= screen_pos[1] < self.height:
                            screen_points.append((screen_pos[0], screen_pos[1]))
                            avg_height += py
                            avg_distance += screen_pos[2]
                    
                    # Only render if all points are visible
                    if len(screen_points) == 3:
                        avg_height /= 3
                        avg_distance /= 3
                        
                        # Skip triangles that are too far or behind
                        if avg_distance > 150:  # Further increased render distance
                            continue
                            
                        triangles.append((screen_points, avg_height, avg_distance))
        
        # Wall faces are now rendered separately in render_maze_walls()
        
        # Sort triangles by distance (furthest first) with better precision
        triangles.sort(key=lambda t: t[2], reverse=True)
        
        # Render triangles
        for screen_points, height, distance in triangles:
            # All points should be on screen
            if all(0 <= p[0] < self.width and 0 <= p[1] < self.height for p in screen_points):
                color = self.get_maze_color(height, maze_map.wall_height)
                
                # Add lighting effect based on height and distance
                lighting_factor = max(0.3, min(1.0, 1.0 - distance / 30))
                shaded_color = tuple(int(c * lighting_factor) for c in color)
                
                try:
                    pygame.draw.polygon(self.screen, shaded_color, screen_points)
                except:
                    pass  # Skip invalid polygons
    
    def render_terrain_wireframe(self, maze_map, player):
        """Add wireframe detail on top of surfaces"""
        step = 2  # Denser wireframe for smoother appearance
        
        # Horizontal lines
        for z in range(0, maze_map.height, step):
            line_points = []
            for x in range(0, maze_map.width, 2):
                # Bounds checking
                if z >= maze_map.height or x >= maze_map.width or z < 0 or x < 0:
                    continue
                    
                height = maze_map.terrain[z][x]
                world_pos = Vector3D(x, height, z)
                
                screen_pos = self.camera.project_3d_to_2d(
                    world_pos, player.position, player.rotation_x, player.rotation_y,
                    self.width, self.height
                )
                
                if screen_pos and screen_pos[2] > 0 and screen_pos[2] < 100:  # Further increased wireframe distance
                    line_points.append(screen_pos)
            
            # Draw connected wireframe lines
            for i in range(len(line_points) - 1):
                if (0 <= line_points[i][0] < self.width and 0 <= line_points[i][1] < self.height and
                    0 <= line_points[i+1][0] < self.width and 0 <= line_points[i+1][1] < self.height):
                    
                    wireframe_color = (60, 80, 60)  # Dark green wireframe
                    pygame.draw.line(self.screen, wireframe_color, 
                                   (line_points[i][0], line_points[i][1]),
                                   (line_points[i+1][0], line_points[i+1][1]), 1)
        
        # Vertical lines
        for x in range(0, maze_map.width, step):
            line_points = []
            for z in range(0, maze_map.height, 2):
                # Bounds checking
                if z >= maze_map.height or x >= maze_map.width or z < 0 or x < 0:
                    continue
                    
                height = maze_map.terrain[z][x]
                world_pos = Vector3D(x, height, z)
                
                screen_pos = self.camera.project_3d_to_2d(
                    world_pos, player.position, player.rotation_x, player.rotation_y,
                    self.width, self.height
                )
                
                if screen_pos and screen_pos[2] > 0 and screen_pos[2] < 100:  # Further increased wireframe distance
                    line_points.append(screen_pos)
            
            # Draw connected wireframe lines
            for i in range(len(line_points) - 1):
                if (0 <= line_points[i][0] < self.width and 0 <= line_points[i][1] < self.height and
                    0 <= line_points[i+1][0] < self.width and 0 <= line_points[i+1][1] < self.height):
                    
                    wireframe_color = (60, 80, 60)  # Dark green wireframe
                    pygame.draw.line(self.screen, wireframe_color, 
                                   (line_points[i][0], line_points[i][1]),
                                   (line_points[i+1][0], line_points[i+1][1]), 1)
    
    def render_maze_walls(self, maze_map, player):
        """Render vertical wall faces as solid surfaces with proper depth sorting"""
        wall_quads = []
        walls_considered = 0
        walls_culled = 0
        
        # Check area around player for walls
        player_x, player_z = int(player.position.x), int(player.position.z)
        render_range = 25  # Balanced range for moderate sized maze
        
        for z in range(max(0, player_z - render_range), min(maze_map.height, player_z + render_range)):
            for x in range(max(0, player_x - render_range), min(maze_map.width, player_x + render_range)):
                if maze_map.maze[z][x] == 0:  # This is a wall
                    # Distance culling for walls - don't render walls too far away
                    distance_to_wall = ((x - player.position.x)**2 + (z - player.position.z)**2)**0.5
                    if distance_to_wall > render_range + 5:  # Extended range to prevent pop-in
                        continue
                        
                    # Occlusion culling - skip walls that are behind other walls
                    if maze_map.is_wall_occluded(x, z, player.position):
                        continue
                        
                    # Check adjacent cells to create wall faces
                    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # North, East, South, West
                    
                    for dx, dz in directions:
                        adj_x, adj_z = x + dx, z + dz
                        
                        # Create wall face if adjacent cell is a corridor
                        if (0 <= adj_x < maze_map.width and 0 <= adj_z < maze_map.height and 
                            maze_map.maze[adj_z][adj_x] != 0):  # Adjacent is not a wall
                            
                            wall_height = maze_map.wall_height
                            floor_level = maze_map.base_level
                            
                            # Create wall face vertices based on direction
                            if dx == 0:  # North/South face
                                if dz == 1:  # North face
                                    v1 = Vector3D(x, floor_level, z + 1)
                                    v2 = Vector3D(x + 1, floor_level, z + 1)
                                    v3 = Vector3D(x + 1, floor_level + wall_height, z + 1)
                                    v4 = Vector3D(x, floor_level + wall_height, z + 1)
                                else:  # South face
                                    v1 = Vector3D(x + 1, floor_level, z)
                                    v2 = Vector3D(x, floor_level, z)
                                    v3 = Vector3D(x, floor_level + wall_height, z)
                                    v4 = Vector3D(x + 1, floor_level + wall_height, z)
                            else:  # East/West face
                                if dx == 1:  # East face
                                    v1 = Vector3D(x + 1, floor_level, z + 1)
                                    v2 = Vector3D(x + 1, floor_level, z)
                                    v3 = Vector3D(x + 1, floor_level + wall_height, z)
                                    v4 = Vector3D(x + 1, floor_level + wall_height, z + 1)
                                else:  # West face
                                    v1 = Vector3D(x, floor_level, z)
                                    v2 = Vector3D(x, floor_level, z + 1)
                                    v3 = Vector3D(x, floor_level + wall_height, z + 1)
                                    v4 = Vector3D(x, floor_level + wall_height, z)
                            
                            # Project vertices to screen with improved clipping
                            screen_vertices = []
                            distances = []
                            all_vertices_projected = []
                            
                            for vertex in [v1, v2, v3, v4]:
                                screen_pos = self.camera.project_3d_to_2d(
                                    vertex, player.position, player.rotation_x, player.rotation_y,
                                    self.width, self.height
                                )
                                if screen_pos and screen_pos[2] > 0.001:  # Only check near plane, not screen bounds
                                    # Clamp coordinates to extended screen bounds to prevent drawing errors
                                    clamped_x = max(-200, min(self.width + 200, screen_pos[0]))
                                    clamped_y = max(-200, min(self.height + 200, screen_pos[1]))
                                    screen_vertices.append((clamped_x, clamped_y))
                                    distances.append(screen_pos[2])
                                    all_vertices_projected.append(True)
                                else:
                                    all_vertices_projected.append(False)
                            
                            # Render wall quad if at least 2 vertices are visible (improved partial rendering)
                            if len(screen_vertices) >= 2:
                                avg_distance = sum(distances) / 4
                                
                                # Wall color with distance-based lighting
                                base_color = 140
                                lighting_factor = max(0.4, min(1.0, 1.0 - avg_distance / 25))
                                wall_color = (
                                    int(base_color * lighting_factor),
                                    int((base_color - 30) * lighting_factor),
                                    int((base_color - 60) * lighting_factor)
                                )
                                
                                wall_quads.append((screen_vertices, wall_color, avg_distance))
        
        # Sort wall quads by distance (furthest first) for proper depth rendering
        wall_quads.sort(key=lambda quad: quad[2], reverse=True)
        
        # Render sorted wall quads
        for screen_vertices, wall_color, distance in wall_quads:
            try:
                pygame.draw.polygon(self.screen, wall_color, screen_vertices)
                # Add subtle outline for definition
                outline_color = (wall_color[0]//2, wall_color[1]//2, wall_color[2]//2)
                pygame.draw.polygon(self.screen, outline_color, screen_vertices, 1)
            except:
                pass  # Skip invalid polygons
    
    def render_ground_plane(self, maze_map, player):
        """Render detailed floor plane everywhere with enhanced visibility"""
        grid_size = 2  # Larger grid for better visibility
        ground_quads = []
        
        # Calculate visible range around player - optimized for moderate maze
        render_distance = 35  # Balanced for moderate sized maze
        start_x = max(0, int(player.position.x - render_distance))
        end_x = min(maze_map.width, int(player.position.x + render_distance))
        start_z = max(0, int(player.position.z - render_distance))
        end_z = min(maze_map.height, int(player.position.z + render_distance))
        
        # Render floor ONLY in walkable areas (where player can actually stand)
        for z in range(start_z, end_z - grid_size, grid_size):
            for x in range(start_x, end_x - grid_size, grid_size):
                # Check if this area is walkable (corridors=1, rooms=2, doors=3)
                maze_x = max(0, min(maze_map.width - 1, int(x + grid_size/2)))
                maze_z = max(0, min(maze_map.height - 1, int(z + grid_size/2)))
                
                # Only render floor where player can actually walk
                if (0 <= maze_x < maze_map.width and 0 <= maze_z < maze_map.height and 
                    maze_map.maze[maze_z][maze_x] in [1, 2, 3]):  # Only walkable areas
                    
                    # Create floor quad BELOW player feet
                    floor_y = maze_map.base_level - 1.0  # Floor 1 unit below base level
                    corners = [
                        Vector3D(x, floor_y, z),
                        Vector3D(x + grid_size, floor_y, z),
                        Vector3D(x + grid_size, floor_y, z + grid_size),
                        Vector3D(x, floor_y, z + grid_size)
                    ]
                    
                    # Project to screen
                    screen_corners = []
                    total_distance = 0
                    
                    for corner in corners:
                        screen_pos = self.camera.project_3d_to_2d(
                            corner, player.position, player.rotation_x, player.rotation_y,
                            self.width, self.height
                        )
                        
                        if screen_pos and screen_pos[2] > 0.001 and screen_pos[2] < 120:
                            screen_corners.append((screen_pos[0], screen_pos[1]))
                            total_distance += screen_pos[2]
                    
                    # Only render if all corners are visible
                    if len(screen_corners) == 4:
                        avg_distance = total_distance / 4
                        if avg_distance < 80:  # Increased distance for better floor visibility
                            # Floor color for walkable areas - very bright and visible
                            if maze_map.maze[maze_z][maze_x] == 2:  # Room
                                base_color = (140, 170, 200)  # Bright blue for room floors
                            else:  # Corridor (1) or door (3)
                                base_color = (120, 160, 120)  # Bright green for corridor floors
                            
                            ground_quads.append((screen_corners, avg_distance, base_color))
        
        # Sort by distance (furthest first)
        ground_quads.sort(key=lambda q: q[1], reverse=True)
        
        # Render floor quads
        for screen_corners, distance, base_color in ground_quads:
            try:
                # Distance-based lighting with better visibility
                fade_factor = max(0.7, 1.0 - distance / 50)  # Much brighter and further visibility
                color = tuple(int(c * fade_factor) for c in base_color)
                
                pygame.draw.polygon(self.screen, color, screen_corners)
                
                # Add prominent grid lines for texture
                grid_color = tuple(min(255, int(c * 1.5)) for c in color)  # Brighter grid lines
                pygame.draw.polygon(self.screen, grid_color, screen_corners, 2)  # Thicker lines
            except:
                pass
    
    def render_objects(self, maze_map, player):
        """Render monsters, treasures with enhanced 3D graphics"""
        objects = []
        
        # Collect monsters with proper culling
        for (x, z), monster in maze_map.monsters.items():
            if not monster['defeated']:
                # Distance culling - only render monsters within reasonable range
                distance_to_monster = ((x - player.position.x)**2 + (z - player.position.z)**2)**0.5
                if distance_to_monster > 50:  # Balanced range for moderate maze
                    continue
                    
                height = maze_map.get_height(x, z) + 2
                world_pos = Vector3D(x, height, z)
                
                screen_pos = self.camera.project_3d_to_2d(
                    world_pos, player.position, player.rotation_x, player.rotation_y,
                    self.width, self.height
                )
                
                # Extended screen bounds - render slightly outside visible area to prevent pop-in
                if screen_pos and screen_pos[2] > 0.1 and screen_pos[2] < 100 and -100 <= screen_pos[0] < self.width + 100 and -100 <= screen_pos[1] < self.height + 100:
                    objects.append(('monster', screen_pos, monster, (x, z)))
        
        # Collect treasures with proper culling
        for (x, z), treasure in maze_map.treasures.items():
            if not treasure['opened']:
                # Distance culling - only render treasures within reasonable range
                distance_to_treasure = ((x - player.position.x)**2 + (z - player.position.z)**2)**0.5
                if distance_to_treasure > 40:  # Balanced range for moderate maze
                    continue
                    
                height = maze_map.get_height(x, z) + 1
                world_pos = Vector3D(x, height, z)
                
                screen_pos = self.camera.project_3d_to_2d(
                    world_pos, player.position, player.rotation_x, player.rotation_y,
                    self.width, self.height
                )
                
                # Extended screen bounds - render slightly outside visible area to prevent pop-in
                if screen_pos and screen_pos[2] > 0.1 and screen_pos[2] < 80 and -100 <= screen_pos[0] < self.width + 100 and -100 <= screen_pos[1] < self.height + 100:
                    objects.append(('treasure', screen_pos, treasure, (x, z)))
        
        # Sort objects by distance (furthest first)
        objects.sort(key=lambda obj: obj[1][2], reverse=True)
        
        # Render objects with enhanced 3D effects
        for obj_type, screen_pos, obj_data, world_pos in objects:
            distance = screen_pos[2]
            size = max(4, int(20 / distance))
            
            if obj_type == 'monster':
                # Enhanced monster rendering with glow effect
                glow_size = size + 3
                
                # Outer glow
                pygame.draw.circle(self.screen, self.colors['monster_glow'], 
                                 (screen_pos[0], screen_pos[1]), glow_size)
                
                # Main body with gradient effect
                pygame.draw.circle(self.screen, self.colors['monster'], 
                                 (screen_pos[0], screen_pos[1]), size)
                
                # Inner highlight
                highlight_size = max(2, size // 2)
                pygame.draw.circle(self.screen, (255, 120, 120), 
                                 (screen_pos[0] - size//3, screen_pos[1] - size//3), highlight_size)
                
                # Border
                pygame.draw.circle(self.screen, self.colors['black'], 
                                 (screen_pos[0], screen_pos[1]), size, 2)
                
                # Monster emoji (if close enough)
                if distance < 20:
                    emoji_size = max(16, int(32 / distance))
                    try:
                        monster_font = pygame.font.Font(None, emoji_size)
                        emoji_text = monster_font.render(obj_data['info']['emoji'], True, self.colors['white'])
                        text_rect = emoji_text.get_rect(center=(screen_pos[0], screen_pos[1] - size - 20))
                        
                        # Add text shadow
                        shadow_text = monster_font.render(obj_data['info']['emoji'], True, self.colors['black'])
                        shadow_rect = shadow_text.get_rect(center=(screen_pos[0] + 2, screen_pos[1] - size - 18))
                        self.screen.blit(shadow_text, shadow_rect)
                        self.screen.blit(emoji_text, text_rect)
                    except:
                        pass
            
            elif obj_type == 'treasure':
                # Enhanced treasure rendering with shine effect
                glow_size = size + 2
                
                # Outer golden glow
                pygame.draw.circle(self.screen, self.colors['treasure_glow'], 
                                 (screen_pos[0], screen_pos[1]), glow_size)
                
                # Main treasure body
                pygame.draw.circle(self.screen, self.colors['treasure'], 
                                 (screen_pos[0], screen_pos[1]), size)
                
                # Shine effect
                shine_size = max(2, size // 3)
                pygame.draw.circle(self.screen, (255, 255, 200), 
                                 (screen_pos[0] - size//4, screen_pos[1] - size//4), shine_size)
                
                # Border with darker gold
                pygame.draw.circle(self.screen, (200, 150, 0), 
                                 (screen_pos[0], screen_pos[1]), size, 2)
                
                # Treasure symbol with better rendering
                if distance < 15:
                    try:
                        treasure_size = max(12, int(24 / distance))
                        treasure_font = pygame.font.Font(None, treasure_size)
                        treasure_text = treasure_font.render("💰", True, self.colors['white'])
                        text_rect = treasure_text.get_rect(center=(screen_pos[0], screen_pos[1] - size - 15))
                        
                        # Add text shadow
                        shadow_text = treasure_font.render("💰", True, self.colors['black'])
                        shadow_rect = shadow_text.get_rect(center=(screen_pos[0] + 1, screen_pos[1] - size - 14))
                        self.screen.blit(shadow_text, shadow_rect)
                        self.screen.blit(treasure_text, text_rect)
                    except:
                        pass
    
    def render_minimap(self, maze_map, player):
        """Render a minimap in the corner"""
        minimap_size = 120
        minimap_x = self.width - minimap_size - 10
        minimap_y = 10
        
        # Minimap background with border
        minimap_rect = pygame.Rect(minimap_x - 2, minimap_y - 2, minimap_size + 4, minimap_size + 4)
        self.draw_ui_background(minimap_rect, (0, 0, 0, 200), (0, 255, 255), 3)
        
        # Inner minimap area
        minimap_bg = pygame.Surface((minimap_size, minimap_size))
        minimap_bg.fill((20, 20, 20))
        minimap_bg.set_alpha(220)
        self.screen.blit(minimap_bg, (minimap_x, minimap_y))
        
        # Scale factors
        scale_x = minimap_size / maze_map.width
        scale_z = minimap_size / maze_map.height
        
        # Draw terrain on minimap
        for z in range(0, maze_map.height, 2):
            for x in range(0, maze_map.width, 2):
                # Bounds checking
                if z >= maze_map.height or x >= maze_map.width or z < 0 or x < 0:
                    continue
                    
                height = maze_map.terrain[z][x]
                color = self.get_maze_color(height, maze_map.wall_height)
                
                map_x = int(x * scale_x) + minimap_x
                map_y = int(z * scale_z) + minimap_y
                
                pygame.draw.rect(self.screen, color, (map_x, map_y, 2, 2))
        
        # Draw monsters on minimap
        for (x, z), monster in maze_map.monsters.items():
            if not monster['defeated']:
                map_x = int(x * scale_x) + minimap_x
                map_y = int(z * scale_z) + minimap_y
                pygame.draw.circle(self.screen, self.colors['red'], (map_x, map_y), 2)
        
        # Draw treasures on minimap
        for (x, z), treasure in maze_map.treasures.items():
            if not treasure['opened']:
                map_x = int(x * scale_x) + minimap_x
                map_y = int(z * scale_z) + minimap_y
                pygame.draw.circle(self.screen, self.colors['yellow'], (map_x, map_y), 1)
        
        # Draw player on minimap
        player_map_x = int(player.position.x * scale_x) + minimap_x
        player_map_y = int(player.position.z * scale_z) + minimap_y
        pygame.draw.circle(self.screen, self.colors['green'], (player_map_x, player_map_y), 3)
        
        # Player direction indicator
        dir_x = player_map_x + int(8 * math.sin(math.radians(player.rotation_y)))
        dir_y = player_map_y + int(8 * math.cos(math.radians(player.rotation_y)))
        pygame.draw.line(self.screen, self.colors['green'], 
                        (player_map_x, player_map_y), (dir_x, dir_y), 2)
        
        # Minimap border
        pygame.draw.rect(self.screen, self.colors['white'], 
                        (minimap_x-1, minimap_y-1, minimap_size+2, minimap_size+2), 2)
    
    def render_ui(self, player, maze_map=None):
        """Render UI elements with better visibility"""
        # Main UI panel background (left side)
        main_ui_rect = pygame.Rect(10, 10, 280, 140)
        self.draw_ui_background(main_ui_rect, (0, 0, 0, 220), (0, 255, 255), 2)
        
        # Health bar
        health_bg = pygame.Rect(15, 15, 220, 20)
        pygame.draw.rect(self.screen, (40, 40, 40), health_bg)
        pygame.draw.rect(self.screen, (255, 255, 255), health_bg, 2)
        
        # Health fill
        health_ratio = player.hp / player.max_hp
        health_fill = pygame.Rect(17, 17, int(health_ratio * 216), 16)
        
        if health_ratio > 0.6:
            health_color = (0, 255, 0)  # Bright green
        elif health_ratio > 0.3:
            health_color = (255, 165, 0)  # Orange
        else:
            health_color = (255, 0, 0)  # Bright red
        
        pygame.draw.rect(self.screen, health_color, health_fill)
        
        # Health text with shadow for better visibility
        health_text = self.font.render(f"❤️ HP: {player.hp}/{player.max_hp}", True, (255, 255, 0))  # Yellow text
        shadow_text = self.font.render(f"❤️ HP: {player.hp}/{player.max_hp}", True, (0, 0, 0))
        self.screen.blit(shadow_text, (18, 46))  # Shadow
        self.screen.blit(health_text, (17, 45))
        
        # Experience bar
        exp_bg = pygame.Rect(15, 75, 220, 15)
        pygame.draw.rect(self.screen, (40, 40, 40), exp_bg)
        pygame.draw.rect(self.screen, (255, 255, 255), exp_bg, 2)
        
        exp_in_level = player.experience % 100
        exp_fill = pygame.Rect(17, 77, int((exp_in_level / 100) * 216), 11)
        # Gradient blue for experience
        pygame.draw.rect(self.screen, (0, 150, 255), exp_fill)
        
        # Level and experience text with shadow
        level_text = self.small_font.render(f"Level {player.level} - EXP: {exp_in_level}/100", True, (255, 255, 0))
        shadow_text = self.small_font.render(f"Level {player.level} - EXP: {exp_in_level}/100", True, (0, 0, 0))
        self.screen.blit(shadow_text, (18, 96))
        self.screen.blit(level_text, (17, 95))
        
        # Weapon info with shadow
        weapon_text = self.font.render(f"{player.weapon_emoji} {player.weapon.upper()}", True, (255, 255, 0))
        shadow_text = self.font.render(f"{player.weapon_emoji} {player.weapon.upper()}", True, (0, 0, 0))
        self.screen.blit(shadow_text, (271, 46))
        self.screen.blit(weapon_text, (270, 45))
        
        # Stats with shadow
        stats_text = self.small_font.render(f"Pontok: {player.stats['pontok']}", True, (255, 255, 0))
        shadow_text = self.small_font.render(f"Pontok: {player.stats['pontok']}", True, (0, 0, 0))
        self.screen.blit(shadow_text, (271, 76))
        self.screen.blit(stats_text, (270, 75))
        
        # Controls panel (right side) with background
        controls_rect = pygame.Rect(self.width - 185, 10, 170, 150)
        self.draw_ui_background(controls_rect, (0, 0, 0, 220), (255, 165, 0), 2)
        
        controls = [
            "Vezérlés:",
            "WASD - Mozgás",
            "SPACE - Ugrás",
            "Egér - Forgás", 
            "E - Interakció",
            "+/- Egér érzék.",
            "R - Új világ",
            "ESC - Kilépés"
        ]
        
        for i, control in enumerate(controls):
            color = (255, 255, 0) if i == 0 else (255, 255, 255)  # Yellow header, white text
            control_text = self.small_font.render(control, True, color)
            shadow_text = self.small_font.render(control, True, (0, 0, 0))
            self.screen.blit(shadow_text, (self.width - 179, 16 + i * 20))
            self.screen.blit(control_text, (self.width - 180, 15 + i * 20))
        
        # Position and physics info with shadow
        jump_status = "Jumping" if player.is_jumping else "On Ground"
        pos_text = self.small_font.render(f"Pos: ({player.position.x:.1f}, {player.position.y:.1f}, {player.position.z:.1f}) | {jump_status}", 
                                        True, (255, 255, 0))
        shadow_text = self.small_font.render(f"Pos: ({player.position.x:.1f}, {player.position.y:.1f}, {player.position.z:.1f}) | {jump_status}", 
                                        True, (0, 0, 0))
        self.screen.blit(shadow_text, (18, 116))
        self.screen.blit(pos_text, (17, 115))
        
        # Maze and camera info for debugging with shadow
        if maze_map:
            floor_height = maze_map.get_height(player.position.x, player.position.z)
            debug_text = self.small_font.render(f"Padló:{floor_height:.1f} | Kamera Y:{player.rotation_x:.0f}°", 
                                              True, (255, 255, 0))
            shadow_text = self.small_font.render(f"Padló:{floor_height:.1f} | Kamera Y:{player.rotation_x:.0f}°", 
                                              True, (0, 0, 0))
        else:
            debug_text = self.small_font.render(f"Kamera: X:{player.rotation_x:.0f}° Y:{player.rotation_y:.0f}°", 
                                              True, (255, 255, 0))
            shadow_text = self.small_font.render(f"Kamera: X:{player.rotation_x:.0f}° Y:{player.rotation_y:.0f}°", 
                                              True, (0, 0, 0))
        self.screen.blit(shadow_text, (271, 96))
        self.screen.blit(debug_text, (270, 95))
        
        # Ground plane reference (draw a grid on the ground)
        grid_color = (100, 120, 100)
        for i in range(-20, 21, 4):
            # Draw grid lines extending from player position
            start_world = Vector3D(player.position.x + i, 0, player.position.z - 20)
            end_world = Vector3D(player.position.x + i, 0, player.position.z + 20)
            
            start_screen = self.camera.project_3d_to_2d(
                start_world, player.position, player.rotation_x, player.rotation_y,
                self.width, self.height
            )
            end_screen = self.camera.project_3d_to_2d(
                end_world, player.position, player.rotation_x, player.rotation_y,
                self.width, self.height
            )
            
            if start_screen and end_screen:
                pygame.draw.line(self.screen, grid_color, 
                               (start_screen[0], start_screen[1]), 
                               (end_screen[0], end_screen[1]), 1)
        
        # Enhanced crosshair
        center_x, center_y = self.width // 2, self.height // 2
        
        # Outer crosshair
        pygame.draw.circle(self.screen, self.colors['white'], (center_x, center_y), 8, 2)
        # Inner crosshair
        pygame.draw.circle(self.screen, self.colors['white'], (center_x, center_y), 2)
        # Cross lines
        pygame.draw.line(self.screen, self.colors['white'], 
                        (center_x - 15, center_y), (center_x - 5, center_y), 2)
        pygame.draw.line(self.screen, self.colors['white'], 
                        (center_x + 5, center_y), (center_x + 15, center_y), 2)
        pygame.draw.line(self.screen, self.colors['white'], 
                        (center_x, center_y - 15), (center_x, center_y - 5), 2)
        pygame.draw.line(self.screen, self.colors['white'], 
                        (center_x, center_y + 5), (center_x, center_y + 15), 2)

class Game3D:
    def __init__(self):
        self.renderer = Renderer()
        self.maze_map = MazeMap()
        
        # Find a guaranteed spawn position inside walkable maze areas
        spawn_x = self.maze_map.width // 2
        spawn_z = self.maze_map.height // 2
        spawn_found = False
        
        # Method 1: Try to spawn in a room center (most reliable)
        if self.maze_map.rooms:
            for room in self.maze_map.rooms:
                test_x = room['center_x']
                test_z = room['center_y']
                # Check if room center is walkable
                if (0 <= test_x < self.maze_map.width and 
                    0 <= test_z < self.maze_map.height and
                    self.maze_map.maze[test_z][test_x] in [1, 2, 3]):  # Any walkable area
                    spawn_x, spawn_z = test_x, test_z
                    spawn_found = True
                    print(f"🏠 Spawned in room center at ({spawn_x}, {spawn_z})")
                    break
        
        # Method 2: Search systematically for any walkable area
        if not spawn_found:
            print("🔍 Searching for walkable spawn area...")
            for offset in range(1, 30):  # Wider search
                for dx in range(-offset, offset + 1, 2):  # Skip every other to speed up
                    for dz in range(-offset, offset + 1, 2):
                        test_x = spawn_x + dx
                        test_z = spawn_z + dz
                        if (0 <= test_x < self.maze_map.width and 
                            0 <= test_z < self.maze_map.height and
                            self.maze_map.maze[test_z][test_x] in [1, 2, 3]):  # Walkable areas
                            spawn_x, spawn_z = test_x, test_z
                            spawn_found = True
                            print(f"🎯 Found walkable area at ({spawn_x}, {spawn_z})")
                            break
                    if spawn_found:
                        break
                if spawn_found:
                    break
            
        # Method 3: Guaranteed fallback - find ANY walkable area in entire maze
        if not spawn_found:
            print("🚨 Emergency spawn search across entire maze...")
            for z in range(1, self.maze_map.height - 1, 3):  # Skip areas for speed
                for x in range(1, self.maze_map.width - 1, 3):
                    if self.maze_map.maze[z][x] in [1, 2, 3]:  # Walkable
                        spawn_x, spawn_z = x, z
                        spawn_found = True
                        print(f"🆘 Emergency spawn at ({spawn_x}, {spawn_z})")
                        break
                if spawn_found:
                    break
            
        # Method 4: Last resort - force create walkable area
        if not spawn_found:
            spawn_x = self.maze_map.width // 2
            spawn_z = self.maze_map.height // 2
            # Force create 5x5 walkable area around center
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if (0 <= spawn_x + dx < self.maze_map.width and 
                        0 <= spawn_z + dz < self.maze_map.height):
                        self.maze_map.maze[spawn_z + dz][spawn_x + dx] = 2  # Force room
            print(f"🔨 FORCED 5x5 spawn area at ({spawn_x}, {spawn_z})")
        
        self.player = Player(spawn_x, spawn_z)
        
        # Force player to spawn at proper maze height using physics
        floor_height = self.maze_map.get_floor_height(spawn_x, spawn_z)  # Floor is base_level - 1.0
        player_eye_height = floor_height + 1.7  # Eye level 1.7 units above floor
        self.player.position = Vector3D(spawn_x, player_eye_height, spawn_z)
        self.player.velocity_y = 0  # Start with no vertical velocity
        self.player.is_jumping = False  # Start on ground
        
        # Validate spawn position
        cell_type = self.maze_map.maze[int(spawn_z)][int(spawn_x)]
        cell_names = {0: "Wall", 1: "Corridor", 2: "Room", 3: "Door"}
        cell_name = cell_names.get(cell_type, "Unknown")
        
        if cell_type in [1, 2, 3]:
            print(f"✅ Player spawned successfully in {cell_name} at ({spawn_x}, {spawn_z})")
        else:
            print(f"❌ WARNING: Player spawned in {cell_name}! This shouldn't happen.")
        
        print(f"🏰 Eye level: {player_eye_height} | Floor: {floor_height}")
        print(f"👁️ Camera looking down at: {self.player.rotation_x}° to see floor better")
        
        # Set minimum safe height for maze
        self.player.minimum_safe_height = player_eye_height
        print(f"👤 Final position: ({self.player.position.x:.1f}, {self.player.position.y:.1f}, {self.player.position.z:.1f})")
        
        self.running = True
        self.mouse_sensitivity = 0.15  # Reduced for better control
        self.battle_active = False
        self.messages = []  # For displaying temporary messages
        self.message_timer = 0
        
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        print("🎮 DOOM-Style Maze Explorer betöltve!")
        print("🏰 Hatalmas véletlenszerű labirintus generálva!")
        print("🗺️ Szobák, folyosók, szörnyek és kincsek!")
        print("🐭 Egér érzékenység: Használd a +/- billentyűket az állításhoz!")
        print(f"📍 Spawn pozíció: ({spawn_x}, {spawn_z})")
        print(f"� Szobák száma: {len(self.maze_map.rooms)}")
        print(f"👤 Játékos magassága: {self.player.position.y:.1f}")
        
    def add_message(self, text, duration=3000):
        """Add a temporary message to display"""
        self.messages.append({'text': text, 'time': pygame.time.get_ticks(), 'duration': duration})
    
    def handle_input(self):
        """Handle keyboard and mouse input with improved responsiveness"""
        keys = pygame.key.get_pressed()
        
        # Movement with variable speed
        move_speed = self.player.speed
        if keys[pygame.K_LSHIFT]:  # Run faster with shift
            move_speed *= 1.8
        
        # Jump control
        if keys[pygame.K_SPACE]:
            self.player.jump()
        
        if keys[pygame.K_w]:
            old_speed = self.player.speed
            self.player.speed = move_speed
            self.player.move_forward(self.maze_map)
            self.player.speed = old_speed
        if keys[pygame.K_s]:
            old_speed = self.player.speed
            self.player.speed = move_speed
            self.player.move_backward(self.maze_map)
            self.player.speed = old_speed
        if keys[pygame.K_a]:
            old_speed = self.player.speed
            self.player.speed = move_speed
            self.player.strafe_left(self.maze_map)
            self.player.speed = old_speed
        if keys[pygame.K_d]:
            old_speed = self.player.speed
            self.player.speed = move_speed
            self.player.strafe_right(self.maze_map)
            self.player.speed = old_speed

        # Mouse look (natural FPS controls) - FIXED Y-axis inversion
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        self.player.rotation_y -= mouse_dx * self.mouse_sensitivity  # Natural: mouse right = look right
        self.player.rotation_x -= mouse_dy * self.mouse_sensitivity  # FIXED: mouse up = look up, mouse down = look down
        
        # Clamp vertical rotation
        self.player.rotation_x = max(-80, min(80, self.player.rotation_x))
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Ignore arrow keys to prevent potential crashes
                if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    continue
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_e:
                    self.interact()
                elif event.key == pygame.K_r:  # Regenerate map
                    self.regenerate_world()
                elif event.key == pygame.K_f:  # Toggle fullscreen
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:  # Increase mouse sensitivity
                    self.mouse_sensitivity = min(1.0, self.mouse_sensitivity + 0.05)
                    self.add_message(f"🐭 Egér érzékenység: {self.mouse_sensitivity:.2f}", 1500)
                elif event.key == pygame.K_MINUS:  # Decrease mouse sensitivity
                    self.mouse_sensitivity = max(0.05, self.mouse_sensitivity - 0.05)
                    self.add_message(f"🐭 Egér érzékenység: {self.mouse_sensitivity:.2f}", 1500)
                elif event.key == pygame.K_t:  # Debug info
                    floor_h = self.maze_map.get_height(self.player.position.x, self.player.position.z)
                    px, pz = int(self.player.position.x), int(self.player.position.z)
                    
                    # Bounds checking for debug
                    if 0 <= px < self.maze_map.width and 0 <= pz < self.maze_map.height:
                        maze_cell = self.maze_map.maze[pz][px]
                        cell_type = ['Wall', 'Corridor', 'Room', 'Door'][maze_cell]
                    else:
                        cell_type = 'Out of bounds'
                    
                    print(f"🔍 Debug Info:")
                    print(f"   Player pos: ({self.player.position.x:.1f}, {self.player.position.y:.1f}, {self.player.position.z:.1f})")
                    print(f"   Floor height: {floor_h:.1f}")
                    print(f"   Maze cell type: {cell_type}")
                    print(f"   Camera rotation: ({self.player.rotation_x:.1f}°, {self.player.rotation_y:.1f}°)")
                    print(f"   Rooms in maze: {len(self.maze_map.rooms)}")
                    self.add_message(f"🏰 Y:{self.player.position.y:.1f} Floor:{floor_h:.1f} {cell_type}", 3000)
    
    def regenerate_world(self):
        """Generate a new random maze with guaranteed spawn"""
        self.maze_map = MazeMap()
        
        # Use the same reliable spawn finding logic
        spawn_x = self.maze_map.width // 2
        spawn_z = self.maze_map.height // 2
        spawn_found = False
        
        # Try rooms first
        if self.maze_map.rooms:
            for room in self.maze_map.rooms:
                test_x = room['center_x']
                test_z = room['center_y']
                if (0 <= test_x < self.maze_map.width and 
                    0 <= test_z < self.maze_map.height and
                    self.maze_map.maze[test_z][test_x] in [1, 2, 3]):
                    spawn_x, spawn_z = test_x, test_z
                    spawn_found = True
                    break
        
        # Search for walkable areas if no room found
        if not spawn_found:
            for offset in range(1, 20):
                for dx in range(-offset, offset + 1, 2):
                    for dz in range(-offset, offset + 1, 2):
                        test_x = spawn_x + dx
                        test_z = spawn_z + dz
                        if (0 <= test_x < self.maze_map.width and 
                            0 <= test_z < self.maze_map.height and
                            self.maze_map.maze[test_z][test_x] in [1, 2, 3]):
                            spawn_x, spawn_z = test_x, test_z
                            spawn_found = True
                            break
                    if spawn_found:
                        break
                if spawn_found:
                    break
        
        # Emergency fallback
        if not spawn_found:
            for z in range(1, self.maze_map.height - 1, 2):
                for x in range(1, self.maze_map.width - 1, 2):
                    if self.maze_map.maze[z][x] in [1, 2, 3]:
                        spawn_x, spawn_z = x, z
                        spawn_found = True
                        break
                if spawn_found:
                    break
        
        # Set maze spawn height using physics system
        floor_height = self.maze_map.get_floor_height(spawn_x, spawn_z)
        player_eye_height = floor_height + 1.0
        self.player.position = Vector3D(spawn_x, player_eye_height, spawn_z)
        self.player.minimum_safe_height = player_eye_height
        # Reset physics state
        self.player.is_jumping = False
        self.player.velocity_y = 0
        print(f"🔄 Regenerated maze - player at eye level: {self.player.position.y}")
        print(f"🔄 Floor height: {floor_height}")
        self.add_message("� Új labirintus generálva!", 2000)
    
    def interact(self):
        """Enhanced interaction system"""
        player_x = int(round(self.player.position.x))
        player_z = int(round(self.player.position.z))
        
        # Check larger area for interactions
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                check_x, check_z = player_x + dx, player_z + dz
                distance = math.sqrt(dx*dx + dz*dz)
                
                # Only interact with close objects
                if distance > 2.5:
                    continue
                
                # Monster interaction
                if (check_x, check_z) in self.maze_map.monsters:
                    monster = self.maze_map.monsters[(check_x, check_z)]
                    if not monster['defeated']:
                        self.start_battle(monster, (check_x, check_z))
                        return
                
                # Treasure interaction
                if (check_x, check_z) in self.maze_map.treasures:
                    treasure = self.maze_map.treasures[(check_x, check_z)]
                    if not treasure['opened']:
                        self.open_treasure(treasure)
                        return
        
        self.add_message("🔍 Nincs itt semmi...", 1500)
    
    def start_battle(self, monster, position):
        """Enhanced battle system"""
        self.add_message(f"⚔️ Harc: {monster['name'].upper()}!", 3000)
        
        # Use existing battle logic
        win_chance = calculate_win_chance(monster['name'], self.player.weapon)
        won = random.randint(1, 100) <= win_chance
        
        if won:
            exp_gain = random.randint(15, 35)
            self.player.experience += exp_gain
            
            hp_gain = 1
            if win_chance == 25:  # Heroic victory
                hp_gain = 2
                exp_gain *= 2
                self.add_message(f"🌟 HEROIKUS GYŐZELEM! +{hp_gain} HP, +{exp_gain} EXP!", 4000)
            else:
                self.add_message(f"🎉 Győzelem! +{hp_gain} HP, +{exp_gain} EXP!", 3000)
                
            self.player.hp = min(self.player.max_hp, self.player.hp + hp_gain)
            monster['defeated'] = True
            
            # Check for level up
            if self.player.gain_experience(0):  # Just check, exp already added
                self.add_message(f"⭐ SZINT FEL! Level {self.player.level}!", 4000)
        else:
            damage = 2
            self.player.hp -= damage
            self.add_message(f"💀 Vereség! -{damage} HP", 3000)
            
            if self.player.hp <= 0:
                self.add_message("☠️ MEGHALTÁL! Játék vége!", 5000)
                time.sleep(2)
                self.running = False
                return
        
        # Update stats
        update_stats(self.player.stats, monster['name'], self.player.weapon, won, 
                    hp_gain if won else -damage, win_chance)
    
    def open_treasure(self, treasure):
        """Enhanced treasure system"""
        treasure['opened'] = True
        content = treasure['contents']
        
        if content == 'health':
            heal = random.randint(1, 2)
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.add_message(f"💚 Gyógyital! +{heal} HP", 2500)
            
        elif content == 'mega_health':
            heal = random.randint(2, 4)
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.add_message(f"💖 Nagy gyógyital! +{heal} HP", 3000)
            
        elif content == 'weapon_upgrade':
            self.add_message("🗡️ Fegyver fejlesztés! (WIP)", 2500)
            
        elif content == 'points':
            points = random.randint(30, 75)
            self.player.stats['pontok'] += points
            self.add_message(f"💰 +{points} pont!", 2500)
        
        # Always give some experience for finding treasures
        exp_gain = random.randint(5, 15)
        self.player.experience += exp_gain
        
        if self.player.gain_experience(0):
            self.add_message(f"⭐ SZINT FEL! Level {self.player.level}!", 4000)
    
    def render_messages(self):
        """Render temporary messages"""
        current_time = pygame.time.get_ticks()
        y_offset = 140
        
        # Remove expired messages
        self.messages = [msg for msg in self.messages 
                        if current_time - msg['time'] < msg['duration']]
        
        # Render remaining messages
        for msg in self.messages:
            age = current_time - msg['time']
            alpha = max(0, 255 - int((age / msg['duration']) * 255))
            
            if alpha > 0:
                text_surface = self.renderer.font.render(msg['text'], True, self.renderer.colors['white'])
                text_surface.set_alpha(alpha)
                
                # Center the message
                text_rect = text_surface.get_rect(center=(self.renderer.width // 2, y_offset))
                self.renderer.screen.blit(text_surface, text_rect)
                y_offset += 30
    
    def run(self):
        """Enhanced main game loop"""
        print("🎮 Monster Weapons 3D Explorer elindítva!")
        print("🗺️ Fedezd fel a világot és harcolj a szörnyekkel!")
        print("💎 Gyűjts kincseket és szerezz tapasztalatot!")
        print()
        print("📋 Vezérlés:")
        print("   WASD - Mozgás (SHIFT - gyorsabb)")
        print("   Egér - Kamera forgás")
        print("   E - Interakció")
        print("   R - Új világ generálás")
        print("   F - Teljes képernyő")
        print("   ESC - Kilépés")
        
        while self.running:
            # Calculate delta time for physics
            dt = self.renderer.clock.get_time() / 1000.0  # Convert milliseconds to seconds
            
            self.handle_input()
            
            # Apply physics EVERY frame (gravity, collision, etc.)
            self.player.apply_physics(self.maze_map, dt)
            
            # Render everything
            self.renderer.render_terrain(self.maze_map, self.player)
            self.renderer.render_objects(self.maze_map, self.player)
            self.renderer.render_minimap(self.maze_map, self.player)
            self.renderer.render_ui(self.player, self.maze_map)
            self.render_messages()
            
            pygame.display.flip()
            self.renderer.clock.tick(60)
        
        pygame.quit()
        
        # Show final stats
        print("\n" + "="*50)
        print("🏆 JÁTÉK VÉGE - VÉGSŐ STATISZTIKÁK")
        print("="*50)
        print(f"⭐ Elért szint: {self.player.level}")
        print(f"🎯 Tapasztalat: {self.player.experience}")
        print(f"💰 Pontok: {self.player.stats['pontok']}")
        print(f"⚔️ Győzelmek: {self.player.stats['gyozelmek']}")
        print(f"💀 Vereségek: {self.player.stats['veresegek']}")
        print(f"🌟 Heroikus győzelmek: {self.player.stats['heroikus_gyozelmek']}")
        print("="*50)
        print("🎮 Köszönjük a játékot! 👋")

if __name__ == "__main__":
    try:
        game = Game3D()
        game.run()
    except Exception as e:
        print(f"❌ Hiba történt: {e}")
        input("Nyomj ENTER-t a kilépéshez...")