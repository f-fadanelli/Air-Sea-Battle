import pygame
import socket
import threading
import pickle
import time
import struct
import sys

pygame.init()

ip = sys.argv[1]
porta = int(sys.argv[2])

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Air-Sea Battle Server")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (135, 206, 235)
DARK_GREEN = (34, 139, 34)
LIGHT_GREEN = (144, 238, 144)

clock = pygame.time.Clock()
FPS = 60

def draw_background(screen):
    screen.fill(BLUE)
    pygame.draw.ellipse(screen, WHITE, (100, 50, 200, 100))
    pygame.draw.ellipse(screen, WHITE, (300, 80, 250, 120))
    pygame.draw.ellipse(screen, WHITE, (600, 60, 180, 90))
    pygame.draw.polygon(screen, DARK_GREEN, [(0, HEIGHT - 100), (200, HEIGHT - 300), (400, HEIGHT - 100)])
    pygame.draw.polygon(screen, DARK_GREEN, [(200, HEIGHT - 100), (400, HEIGHT - 300), (600, HEIGHT - 100)])
    pygame.draw.rect(screen, LIGHT_GREEN, (0, HEIGHT - 100, WIDTH, 100))

class Cannon:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 90
        self.speed = 5
        self.projectile = None
        self.last_angle_change = pygame.time.get_ticks()
        self.angle_change_delay = 200

    def draw(self, screen):
        pygame.draw.rect(screen, RED, (self.x, self.y, 20, 40))
        pygame.draw.line(screen, RED, (self.x + 10, self.y), (self.x + 10 + 30 * self.angle_vector()[0], self.y - 30 * self.angle_vector()[1]), 5)

    def move_horizontal(self, direction):
        if direction == "left" and self.x > 0:
            self.x -= self.speed
        elif direction == "right" and self.x < WIDTH - 20:
            self.x += self.speed

    def adjust_angle(self, direction):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_angle_change > self.angle_change_delay:
            if direction == "up" and self.angle == 60:
                self.angle = 90
            elif direction == "up" and self.angle == 90:
                self.angle = 120
            elif direction == "down" and self.angle == 120:
                self.angle = 90
            elif direction == "down" and self.angle == 90:
                self.angle = 60
            self.last_angle_change = current_time

    def angle_vector(self):
        if self.angle == 90:
            return (0, 1)
        elif self.angle == 60:
            return (-1, 1)
        elif self.angle == 120:
            return (1, 1)

    def shoot(self):
        if not self.projectile:
            self.projectile = Projectile(self.x + 10, self.y, self.angle_vector())

    def update(self):
        if self.projectile:
            self.projectile.update()
            if self.projectile.y < 0 or self.projectile.x < 0 or self.projectile.x > WIDTH:
                self.projectile = None

class Projectile:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = 7
        self.radius = 6

    def update(self):
        self.x += self.direction[0] * self.speed
        self.y -= self.direction[1] * self.speed
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius)

    def check_collision(self, airplanes):
        for airplane in airplanes:
            if (airplane.x < self.x < airplane.x + airplane.width) and (airplane.y < self.y < airplane.y + airplane.height):
                airplanes.remove(airplane)
                return True, (self.x, self.y)
        return False, None

class Airplane:
    def __init__(self, x, y, speed, size):
        self.x = x
        self.y = y
        self.width, self.height = size
        self.speed = speed
        self.shape = [
            (self.x + self.width // 2, self.y),
            (self.x + self.width, self.y + self.height // 2),
            (self.x + self.width // 2, self.y + self.height),
            (self.x, self.y + self.height // 2)
        ]

    def draw(self, screen):
        pygame.draw.polygon(screen, BLACK, self.shape)

    def update(self):
        self.x -= self.speed
        self.shape = [
            (self.x + self.width // 2, self.y),
            (self.x + self.width, self.y + self.height // 2),
            (self.x + self.width // 2, self.y + self.height),
            (self.x, self.y + self.height // 2)
        ]

class AirplaneFleet:
    def __init__(self):
        self.airplanes = []
        self.num_airplanes = 3 
        self.create_fleet()

    def create_fleet(self):
        x = WIDTH
        y = 100

        size = (80, 40)  
        speed = 3 
        vertical_spacing = 70 

        for i in range(self.num_airplanes):
            airplane = Airplane(x, y + i * vertical_spacing, speed, size)
            self.airplanes.append(airplane)

        self.num_airplanes = (self.num_airplanes + 2) % 6  
        if self.num_airplanes < 3:
            self.num_airplanes = self.num_airplanes + 3  

    def update(self):
        for airplane in self.airplanes:
            airplane.update()
        if all(airplane.x + airplane.width < 0 for airplane in self.airplanes):
            self.create_fleet()

    def draw(self, screen):
        for airplane in self.airplanes:
            airplane.draw(screen)

    def is_empty(self):
        return len(self.airplanes) == 0

def draw_collision_effect(screen, position):
    pygame.draw.circle(screen, YELLOW, (int(position[0]), int(position[1])), 24)
    pygame.draw.circle(screen, RED, (int(position[0]), int(position[1])), 12)

def receive_commands(cannon2_commands, conn, stop_event):
    while not stop_event.is_set():
        try:
            data = conn.recv(1024).decode()
            if not data:
                break  
            cannon2_commands.append(data)  
        except Exception as e:
            break

    conn.close()

def main():
    running = True
    score1 = 0
    score2 = 0

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip, porta))
    server_socket.listen(1)

    draw_background(screen)
    font = pygame.font.SysFont(None, 48)
    connection_text = font.render("Aguardando conexão...", True, BLACK)
    screen.blit(connection_text, (WIDTH // 2 - connection_text.get_width() // 2, HEIGHT // 2 - connection_text.get_height() // 2))
    pygame.display.flip()
    clock.tick(FPS)  
    conn, addr = server_socket.accept()
    print(f"Conexão de {addr} estabelecida.")

    cannon2_commands = []  
    stop_event = threading.Event() 


    command_thread = threading.Thread(target=receive_commands, args=(cannon2_commands, conn, stop_event))
    command_thread.start()

    cannon1 = Cannon(WIDTH // 2 - 30, HEIGHT - 50)
    cannon2 = Cannon(WIDTH // 2 + 10, HEIGHT - 50)
    fleet = AirplaneFleet()

    start_time = time.time()
    game_duration = 120  

    while running:
        draw_background(screen)

        elapsed_time = int(time.time() - start_time)
        current_time = game_duration - elapsed_time
        time_text = f"{current_time}"
        font = pygame.font.SysFont(None, 36)
        time_rendered = font.render(time_text, True, BLACK)
        screen.blit(time_rendered, (WIDTH - 50, 10))

        score_text1 = font.render(f"Score 1: {score1}", True, BLACK)
        score_text2 = font.render(f"Score 2: {score2}", True, BLACK)
        screen.blit(score_text1, (10, 10))
        screen.blit(score_text2, (10, 40))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    cannon1.move_horizontal("left")
                elif event.key == pygame.K_RIGHT:
                    cannon1.move_horizontal("right")
                elif event.key == pygame.K_UP:
                    cannon1.adjust_angle("up")
                elif event.key == pygame.K_DOWN:
                    cannon1.adjust_angle("down")
                elif event.key == pygame.K_SPACE:
                    cannon1.shoot()

        while cannon2_commands:
            command = cannon2_commands.pop(0) 
            if command == "move_left":
                cannon2.move_horizontal("left")
            elif command == "move_right":
                cannon2.move_horizontal("right")
            elif command == "angle_up":
                cannon2.adjust_angle("up")
            elif command == "angle_down":
                cannon2.adjust_angle("down")
            elif command == "shoot":
                cannon2.shoot()

        cannon1.update()
        cannon2.update()
        fleet.update()

        if cannon1.projectile:
            hit, position = cannon1.projectile.check_collision(fleet.airplanes)
            if hit:
                draw_collision_effect(screen, position)
                score1 += 1
                cannon1.projectile = None

        if cannon2.projectile:
            hit, position = cannon2.projectile.check_collision(fleet.airplanes)
            if hit:
                draw_collision_effect(screen, position)
                score2 += 1
                cannon2.projectile = None

        cannon1.draw(screen)
        cannon2.draw(screen)
        fleet.draw(screen)

        data = {
            's1': score1,
            's2': score2,
            'c1x': cannon1.x,
            'c1a': cannon1.angle,
            'c1p': cannon1.projectile,
            'c2x': cannon2.x,
            'c2a': cannon2.angle,
            'c2p': cannon2.projectile
        }

        serialized_data = pickle.dumps(data)

        conn.send(serialized_data)

        pygame.display.flip()
        clock.tick(FPS)
        time.sleep(0.04)
        if elapsed_time >= game_duration:
            time.sleep(1)
            running = False

    winner = 1 if score1 > score2 else 2 if score2 > score1 else 0
    server_socket.close()

    quit = 0
    while quit == 0:
        draw_background(screen)
        font = pygame.font.SysFont(None, 48)

        if winner == 0:
            result_text = font.render("Empate", True, BLACK)
        else:
            result_text = font.render(f"Vencedor: Jogador {winner}", True, BLACK)
        screen.blit(result_text, (WIDTH // 2 - result_text.get_width() // 2, HEIGHT // 2 - 50))

        quit_button = font.render("Encerrar", True, BLACK)

        screen.blit(quit_button, (WIDTH // 2 - quit_button.get_width() // 2, HEIGHT // 2 + 60))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if (WIDTH // 2 - quit_button.get_width() // 2 < mouse_x < WIDTH // 2 + quit_button.get_width() // 2) and \
                   (HEIGHT // 2 + 60 < mouse_y < HEIGHT // 2 + 90):
                    quit = 1
                    break

    pygame.quit()

if __name__ == "__main__":
    main()

