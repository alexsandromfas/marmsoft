import pygame
import random
import os, json
try:
    from marmsoft_sensor_provider import get_angle as sensor_provider
except Exception:
    sensor_provider = None
from objects import Road, Player, Nitro, Tree, Button, \
					Obstacle, Coins, Fuel

pygame.init()
SCREEN = WIDTH, HEIGHT = 432, 768

info = pygame.display.Info()
width = info.current_w
height = info.current_h

if width >= height:
	win = pygame.display.set_mode(SCREEN, pygame.SCALED | pygame.RESIZABLE)
else:
	win = pygame.display.set_mode(SCREEN, pygame.NOFRAME | pygame.SCALED | pygame.FULLSCREEN)

clock = pygame.time.Clock()
FPS = 30

lane_pos = [50, 95, 142, 190]

# COLORS **********************************************************************

WHITE = (255, 255, 255)
BLUE = (30, 144,255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 20)

# FONTS ***********************************************************************

font = pygame.font.SysFont('cursive', 32)
font_small = pygame.font.Font(None, 28)
font_title = pygame.font.Font(None, 40)

select_car = font.render('Select Car', True, WHITE)

# IMAGES **********************************************************************

bg = pygame.image.load('Assets/bg.png')

home_img = pygame.image.load('Assets/home.png')
play_img = pygame.image.load('Assets/buttons/play.png')
end_img = pygame.image.load('Assets/end.jpg')
end_img = pygame.transform.scale(end_img, (WIDTH, HEIGHT))
game_over_img = pygame.image.load('Assets/game_over.png')
game_over_img = pygame.transform.scale(game_over_img, (220, 220))
coin_img = pygame.image.load('Assets/coins/1.png')
dodge_img = pygame.image.load('Assets/car_dodge.png')

left_arrow = pygame.image.load('Assets/buttons/arrow.png')
right_arrow = pygame.transform.flip(left_arrow, True, False)

home_btn_img = pygame.image.load('Assets/buttons/home.png')
replay_img = pygame.image.load('Assets/buttons/replay.png')
sound_off_img = pygame.image.load("Assets/buttons/soundOff.png")
sound_on_img = pygame.image.load("Assets/buttons/soundOn.png")

cars = []
car_type = 0
for i in range(1, 9):
	img = pygame.image.load(f'Assets/cars/{i}.png')
	img = pygame.transform.scale(img, (59, 101))
	cars.append(img)

nitro_frames = []
nitro_counter = 0
for i in range(6):
	img = pygame.image.load(f'Assets/nitro/{i}.gif')
	img = pygame.transform.flip(img, False, True)
	img = pygame.transform.scale(img, (18, 36))
	nitro_frames.append(img)

# FUNCTIONS *******************************************************************
def center(image):
	return (WIDTH // 2) - image.get_width() // 2

# BUTTONS *********************************************************************
play_btn = Button(play_img, (100, 34), center(play_img)+10, HEIGHT-80)
la_btn = Button(left_arrow, (32, 42), 40, 180)
ra_btn = Button(right_arrow, (32, 42), WIDTH-60, 180)

home_btn = Button(home_btn_img, (24, 24), WIDTH // 4 - 18, HEIGHT - 80)
replay_btn = Button(replay_img, (36,36), WIDTH // 2  - 18, HEIGHT - 86)
sound_btn = Button(sound_on_img, (24, 24), WIDTH - WIDTH // 4 - 18, HEIGHT - 80)

# SOUNDS **********************************************************************

click_fx = pygame.mixer.Sound('Sounds/click.mp3')
fuel_fx = pygame.mixer.Sound('Sounds/fuel.wav')
start_fx = pygame.mixer.Sound('Sounds/start.mp3')
restart_fx = pygame.mixer.Sound('Sounds/restart.mp3')
coin_fx = pygame.mixer.Sound('Sounds/coin.mp3')

pygame.mixer.music.load('Sounds/mixkit-tech-house-vibes-130.mp3')
pygame.mixer.music.play(loops=-1)
pygame.mixer.music.set_volume(0.6)

# OBJECTS *********************************************************************
road = Road()
nitro = Nitro(WIDTH-80, HEIGHT-80)
p = Player(100, HEIGHT-120, car_type)

tree_group = pygame.sprite.Group()
coin_group = pygame.sprite.Group()
fuel_group = pygame.sprite.Group()
obstacle_group = pygame.sprite.Group()

# VARIABLES *******************************************************************
# Calibration & articulation selection
calib_ext_min = None
calib_flex_max = None
selected_artic = None
home_page = True
car_page = False
game_page = False
over_page = False

move_left = False
move_right = False
nitro_on = False
sound_on = True

counter = 0
counter_inc = 1
speed = 3
dodged = 0
coins = 0
cfuel = 100

endx, enddx = 0, 0.5
gameovery = -50

# ---------- Helper screens: articulation selection & calibration ---------
def _repo_root():
	return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def get_finger_choice():
	global selected_artic
	# Load overlays from repo assets/Mao
	mao_dir = os.path.join(_repo_root(), 'assets', 'Mao')
	try:
		base = pygame.image.load(os.path.join(mao_dir, 'mao.png')).convert_alpha()
	except Exception:
		base = None
	overlays = []
	if base:
		for fname in sorted(os.listdir(mao_dir)):
			if fname.lower().endswith('.png') and fname.lower() != 'mao.png':
				try:
					overlays.append((os.path.splitext(fname)[0], pygame.image.load(os.path.join(mao_dir,fname)).convert_alpha()))
				except Exception:
					pass
	# Fallback if assets missing
	if not base or not overlays:
		return
	# Scale to 70% height
	SCALE = 0.7
	scale = (HEIGHT * SCALE) / base.get_height()
	base_s = pygame.transform.smoothscale(base, (int(base.get_width()*scale), int(base.get_height()*scale)))
	ov_entries = []
	for name, ov in overlays:
		surf = pygame.transform.smoothscale(ov, (int(ov.get_width()*scale), int(ov.get_height()*scale)))
		mask = pygame.mask.from_surface(surf, 10)
		ov_entries.append((name, surf, mask))

	def pretty(n):
		base = os.path.splitext(os.path.basename(n))[0]
		parts = [w.capitalize() for w in base.replace('-', '_').split('_') if w]
		s = ' '.join(parts)
		s = s.replace('Metacarpofalangica','Metacarpofalângica').replace('Interfalangica','Interfalângica').replace('Medio','Médio').replace('Minimo','Mínimo')
		return s

	running = True
	hovered = None
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				mx, my = event.pos
				bx = WIDTH//2 - base_s.get_width()//2
				by = HEIGHT//2 - base_s.get_height()//2
				lx, ly = int(mx - bx), int(my - by)
				if 0 <= lx < base_s.get_width() and 0 <= ly < base_s.get_height():
					for name, surf, mask in ov_entries:
						if 0 <= lx < surf.get_width() and 0 <= ly < surf.get_height():
							try:
								if mask.get_at((lx,ly)):
									selected_artic = name
									# persist selection
									try:
										cfg_path = os.path.join(_repo_root(), 'config.json')
										cfg = {}
										if os.path.isfile(cfg_path):
											with open(cfg_path,'r',encoding='utf-8') as f:
												cfg = json.load(f)
										cfg['carracing_selected_articulation'] = selected_artic
										with open(cfg_path,'w',encoding='utf-8') as f:
											json.dump(cfg,f,ensure_ascii=False,indent=2)
									except Exception:
										pass
									return
							except Exception:
								pass

		# Draw
		win.fill((0,0,0))
		bp = (WIDTH//2 - base_s.get_width()//2, HEIGHT//2 - base_s.get_height()//2)
		win.blit(base_s, bp)
		# Simple hover label
		mx,my = pygame.mouse.get_pos()
		lx,ly = int(mx - bp[0]), int(my - bp[1])
		label = None
		if 0 <= lx < base_s.get_width() and 0 <= ly < base_s.get_height():
			for name, surf, mask in ov_entries:
				try:
					if 0 <= lx < surf.get_width() and 0 <= ly < surf.get_height():
						if mask.get_at((lx,ly)):
							label = pretty(name)
							break
				except Exception:
					pass
		if label:
			t = font_small.render(label, True, (255,255,255))
			win.blit(t, (20, HEIGHT - t.get_height() - 16))
		pygame.display.flip()
		clock.tick(60)

def calibrate_range():
	global calib_ext_min, calib_flex_max
	BTN_W, BTN_H = 180, 44
	margin = 20
	ext_btn = pygame.Rect(margin, HEIGHT//2 - BTN_H - 10, BTN_W, BTN_H)
	flex_btn = pygame.Rect(margin, HEIGHT//2 + 10, BTN_W, BTN_H)
	proceed_btn = pygame.Rect(WIDTH - margin - BTN_W, HEIGHT - margin - BTN_H, BTN_W, BTN_H)

	running = True
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				mx,my = event.pos
				if ext_btn.collidepoint((mx,my)) and sensor_provider:
					v = sensor_provider()
					if isinstance(v,(int,float)):
						calib_ext_min = v
				elif flex_btn.collidepoint((mx,my)) and sensor_provider:
					v = sensor_provider()
					if isinstance(v,(int,float)):
						calib_flex_max = v
				elif proceed_btn.collidepoint((mx,my)) and (calib_ext_min is not None) and (calib_flex_max is not None):
					if calib_flex_max < calib_ext_min:
						calib_ext_min, calib_flex_max = calib_flex_max, calib_ext_min
					return
		win.fill((0,0,0))
		title = font_title.render("Calibração de Limites", True, (255,255,255))
		win.blit(title, (margin, margin))
		cur = sensor_provider() if sensor_provider else None
		tcur = font_small.render(f"Ângulo atual: {cur:.2f}°" if isinstance(cur,(int,float)) else "Ângulo atual: --", True, (255,255,255))
		win.blit(tcur, (margin, HEIGHT//2 - BTN_H - 60))
		pygame.draw.rect(win, (200,200,200), ext_btn)
		win.blit(font_small.render("Marcar Extensão", True, (0,0,0)), font_small.render("Marcar Extensão", True, (0,0,0)).get_rect(center=ext_btn.center))
		pygame.draw.rect(win, (200,200,200), flex_btn)
		win.blit(font_small.render("Marcar Flexão", True, (0,0,0)), font_small.render("Marcar Flexão", True, (0,0,0)).get_rect(center=flex_btn.center))
		# Values
		txt_ext = font_small.render(f"Extensão: {calib_ext_min:.2f}°" if isinstance(calib_ext_min,(int,float)) else "Extensão: --", True, (255,255,255))
		txt_flex = font_small.render(f"Flexão: {calib_flex_max:.2f}°" if isinstance(calib_flex_max,(int,float)) else "Flexão: --", True, (255,255,255))
		win.blit(txt_ext, (ext_btn.right + 12, ext_btn.centery - txt_ext.get_height()//2))
		win.blit(txt_flex, (flex_btn.right + 12, flex_btn.centery - txt_flex.get_height()//2))
		# Proceed
		ok = (calib_ext_min is not None) and (calib_flex_max is not None)
		col = (200,200,200) if ok else (120,120,120)
		tcol = (0,0,0) if ok else (60,60,60)
		pygame.draw.rect(win, col, proceed_btn)
		win.blit(font_small.render("Prosseguir", True, tcol), font_small.render("Prosseguir", True, tcol).get_rect(center=proceed_btn.center))
		pygame.display.flip(); clock.tick(60)

running = True
get_finger_choice()
calibrate_range()

while running:
	win.fill(BLACK)
	
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			running = False

		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
				running = False

			if event.key == pygame.K_LEFT:
				move_left = True

			if event.key == pygame.K_RIGHT:
				move_right = True

			if event.key == pygame.K_n:
				nitro_on = True

		if event.type == pygame.KEYUP:
			if event.key == pygame.K_LEFT:
				move_left = False

			if event.key == pygame.K_RIGHT:
				move_right = False

			if event.key == pygame.K_n:
				nitro_on = False
				speed = 3
				counter_inc = 1

		if event.type == pygame.MOUSEBUTTONDOWN:
			x, y = event.pos

			if nitro.rect.collidepoint((x, y)):
				nitro_on = True
			else:
				if x <= WIDTH // 2:
					move_left = True
				else:
					move_right = True

		if event.type == pygame.MOUSEBUTTONUP:
			move_left = False
			move_right = False
			nitro_on = False
			speed = 3
			counter_inc = 1

	if home_page:
		win.blit(home_img, (0,0))
		counter += 1
		if counter % 60 == 0:
			home_page = False
			car_page = True

	if car_page:
		win.blit(select_car, (center(select_car), 80))

		win.blit(cars[car_type], (WIDTH//2-30, 150))
		if la_btn.draw(win):
			car_type -= 1
			click_fx.play()
			if car_type < 0:
				car_type = len(cars) - 1

		if ra_btn.draw(win):
			car_type += 1
			click_fx.play()
			if car_type >= len(cars):
				car_type = 0

		if play_btn.draw(win):
			car_page = False
			game_page = True

			start_fx.play()

			p = Player(100, HEIGHT-120, car_type)
			counter = 0

	if over_page:
		win.blit(end_img, (endx, 0))
		endx += enddx
		if endx >= 10 or endx<=-10:
			enddx *= -1

		win.blit(game_over_img, (center(game_over_img), gameovery))
		if gameovery < 16:
			gameovery += 1

		num_coin_img = font.render(f'{coins}', True, WHITE)
		num_dodge_img = font.render(f'{dodged}', True, WHITE)
		distance_img = font.render(f'Distance : {counter/1000:.2f} km', True, WHITE)

		win.blit(coin_img, (80, 240))
		win.blit(dodge_img, (50, 280))
		win.blit(num_coin_img, (180, 250))
		win.blit(num_dodge_img, (180, 300))
		win.blit(distance_img, (center(distance_img), (350)))

		if home_btn.draw(win):
			over_page = False
			home_page = True

			coins = 0
			dodged = 0
			counter = 0
			nitro.gas = 0
			cfuel = 100

			endx, enddx = 0, 0.5
			gameovery = -50

		if replay_btn.draw(win):
			over_page = False
			game_page = True

			coins = 0
			dodged = 0
			counter = 0
			nitro.gas = 0
			cfuel = 100

			endx, enddx = 0, 0.5
			gameovery = -50

			restart_fx.play()

		if sound_btn.draw(win):
			sound_on = not sound_on

			if sound_on:
				sound_btn.update_image(sound_on_img)
				pygame.mixer.music.play(loops=-1)
			else:
				sound_btn.update_image(sound_off_img)
				pygame.mixer.music.stop()

	if game_page:
		# Sensor control overrides keyboard when available
		if sensor_provider and (calib_ext_min is not None) and (calib_flex_max is not None) and (calib_flex_max != calib_ext_min):
			ang = sensor_provider()
			if isinstance(ang,(int,float)):
				ratio = max(0.0, min(1.0, (ang - calib_ext_min) / (calib_flex_max - calib_ext_min)))
				# dead-zone center
				if ratio < 0.4:
					move_left, move_right = True, False
				elif ratio > 0.6:
					move_left, move_right = False, True
				else:
					move_left, move_right = False, False
		win.blit(bg, (0,0))
		road.update(speed)
		road.draw(win)

		counter += counter_inc
		if counter % 60 == 0:
			tree = Tree(random.choice([-5, WIDTH-35]), -20)
			tree_group.add(tree)

		if counter % 270 == 0:
			type = random.choices([1, 2], weights=[6, 4], k=1)[0]
			x = random.choice(lane_pos)+10
			if type == 1:
				count = random.randint(1, 3)
				for i in range(count):
					coin = Coins(x,-100 - (25 * i))
					coin_group.add(coin)
			elif type == 2:
				fuel = Fuel(x, -100)
				fuel_group.add(fuel)
		elif counter % 90 == 0:
			obs = random.choices([1, 2, 3], weights=[6,2,2], k=1)[0]
			obstacle = Obstacle(obs)
			obstacle_group.add(obstacle)

		if nitro_on and nitro.gas > 0:
			x, y = p.rect.centerx - 8, p.rect.bottom - 10
			win.blit(nitro_frames[nitro_counter], (x, y))
			nitro_counter = (nitro_counter + 1) % len(nitro_frames)

			speed = 10
			if counter_inc == 1:
				counter = 0
				counter_inc = 5

		if nitro.gas <= 0:
			speed = 3
			counter_inc = 1

		nitro.update(nitro_on)
		nitro.draw(win)
		obstacle_group.update(speed)
		obstacle_group.draw(win)
		tree_group.update(speed)
		tree_group.draw(win)
		coin_group.update(speed)
		coin_group.draw(win)
		fuel_group.update(speed)
		fuel_group.draw(win)

		p.update(move_left, move_right)
		p.draw(win)

		if cfuel > 0:
			pygame.draw.rect(win, GREEN, (20, 20, cfuel, 15), border_radius=5)
		pygame.draw.rect(win, WHITE, (20, 20, 100, 15), 2, border_radius=5)
		cfuel -= 0.05

		# COLLISION DETECTION & KILLS
		for obstacle in obstacle_group:
			if obstacle.rect.y >= HEIGHT:
				if obstacle.type == 1:
					dodged += 1
				obstacle.kill() 

			if pygame.sprite.collide_mask(p, obstacle):
				pygame.draw.rect(win, RED, p.rect, 1)
				speed = 0

				game_page = False
				over_page = True

				tree_group.empty()
				coin_group.empty()
				fuel_group.empty()
				obstacle_group.empty()

		if pygame.sprite.spritecollide(p, coin_group, True):
			coins += 1
			coin_fx.play()

		if pygame.sprite.spritecollide(p, fuel_group, True):
			cfuel += 25
			fuel_fx.play()
			if cfuel >= 100:
				cfuel = 100

	pygame.draw.rect(win, BLUE, (0, 0, WIDTH, HEIGHT), 3)
	clock.tick(FPS)
	pygame.display.update()

pygame.quit()