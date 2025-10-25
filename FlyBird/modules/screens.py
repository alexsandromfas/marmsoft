"""Helper screens for menu prompts and game over display."""

import pygame
from FlyBird.modules.settings import *
from FlyBird.modules.utils import *

class Screens:
    """Collection of simple UI screens used by :class:`Game`."""

    def __init__(self, game):
        """Store references to the main :class:`Game` object."""
        self.game = game
        self.screen = game.screen
        self.clock = game.clock
        self.font = game.font

    def show_start_screen(self):
        """Display the initial title and wait for ENTER."""
        self.screen.fill(BLACK)
        font_large = pygame.font.Font(None, 72)
        title_text = font_large.render("FlyBird", True, WHITE)
        self.screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3))

        font_small = pygame.font.Font(None, 36)
        instruction_text = font_small.render("Pressione ENTER para iniciar", True, WHITE)
        self.screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()

        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    self.game.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        waiting = False



    def show_go_screen(self):
        """Display score information and allow the player to choose an action."""
        # Calculate score and amplitudes
        obstacles_passed = self.game.bird.obstacles_passed
        if self.game.bird.amplitudes:
            total_phalange1 = max(a[0] for a in self.game.bird.amplitudes) - min(a[0] for a in self.game.bird.amplitudes)
            total_phalange2 = max(a[1] for a in self.game.bird.amplitudes) - min(a[1] for a in self.game.bird.amplitudes)
        else:
            total_phalange1 = total_phalange2 = 0

        # Game Over screen
        self.screen.fill(BLACK)
        self.game.save_results
        font_large = pygame.font.Font(None, 72)
        game_over_text = font_large.render("GAME OVER", True, WHITE)
        self.screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 6))

        font_small = pygame.font.Font(None, 36)
        # Display score
        score_text = font_small.render(f"Obstáculos ultrapassados: {obstacles_passed}", True, WHITE)
        amplitude_text = font_small.render(
            f"Amplitude Falange 1: {total_phalange1:.2f}°   Amplitude Falange 2: {total_phalange2:.2f}°", True, WHITE)
        self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 6 + 80))
        self.screen.blit(amplitude_text, (WIDTH // 2 - amplitude_text.get_width() // 2, HEIGHT // 6 + 120))

        # Buttons
        buttons = []
        button_texts = ["Jogar Novamente", "Trocar Paciente", "Sair"]
        button_actions = [self.game.play_again, self.game.change_patient, self.game.quit_game]
        button_width = 200
        button_height = 50
        button_margin = 20
        total_height = len(button_texts) * (button_height + button_margin) - button_margin
        start_y = HEIGHT // 2

        for i, text in enumerate(button_texts):
            rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * (button_height + button_margin), button_width, button_height)
            buttons.append((rect, text, button_actions[i]))

        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    self.game.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    for rect, text, action in buttons:
                        if rect.collidepoint(mouse_pos):
                            action()
                            waiting = False
                            break

            # Redraw the screen elements
            self.screen.fill(BLACK)
            self.screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 6))
            self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 6 + 80))
            self.screen.blit(amplitude_text, (WIDTH // 2 - amplitude_text.get_width() // 2, HEIGHT // 6 + 120))

            for rect, text, _ in buttons:
                pygame.draw.rect(self.screen, WHITE, rect)
                button_text = font_small.render(text, True, BLACK)
                text_rect = button_text.get_rect(center=rect.center)
                self.screen.blit(button_text, text_rect)

            pygame.display.flip()

    
    def get_player_name(self):
        """Prompt the player to enter their name."""
        font_small = pygame.font.Font(None, 36)
        name_prompt = font_small.render("Digite seu nome:", True, WHITE)
        input_box = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 20, 300, 40)
        name_text = ''
        active = True
        cursor_visible = True
        cursor_timer = 0
        cursor_interval = 500  # milliseconds

        # Next button
        next_button = pygame.Rect(WIDTH // 2 - 50, input_box.bottom + 20, 100, 40)
        next_button_text = font_small.render("Próximo", True, BLACK)

        while active:
            current_time = pygame.time.get_ticks()
            if current_time - cursor_timer > cursor_interval:
                cursor_visible = not cursor_visible
                cursor_timer = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    active = False
                    self.game.running = False
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if name_text.strip() != '':
                            active = False
                            self.game.player_name = name_text
                            return
                    elif event.key == pygame.K_BACKSPACE:
                        name_text = name_text[:-1]
                    else:
                        name_text += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    if next_button.collidepoint(mouse_pos):
                        if name_text.strip() != '':
                            active = False
                            self.game.player_name = name_text
                            return

            self.screen.fill(BLACK)
            self.screen.blit(name_prompt, (WIDTH // 2 - name_prompt.get_width() // 2, HEIGHT // 2 - 80))
            pygame.draw.rect(self.screen, WHITE, input_box, 2)
            name_surface = font_small.render(name_text, True, WHITE)
            self.screen.blit(name_surface, (input_box.x + 5, input_box.y + 5))

            # Blinking cursor
            if cursor_visible:
                cursor_rect = pygame.Rect(input_box.x + 5 + name_surface.get_width(), input_box.y + 5, 2, name_surface.get_height())
                pygame.draw.rect(self.screen, WHITE, cursor_rect)

            # Draw Next button
            pygame.draw.rect(self.screen, WHITE, next_button)
            text_rect = next_button_text.get_rect(center=next_button.center)
            self.screen.blit(next_button_text, text_rect)

            pygame.display.flip()
            self.clock.tick(30)


    def get_finger_choice(self):
        """Selection screen using hand overlays; writes chosen articulation to config.json."""
        # Helpers
        import os, json
        def repo_root():
            return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        def mao_dir():
            # Prefer assets/Mao
            p = os.path.join(repo_root(), 'assets', 'Mao')
            return p if os.path.isdir(p) else None
        def pretty(name: str) -> str:
            base = os.path.splitext(os.path.basename(name))[0]
            parts = [w.capitalize() for w in base.replace('-', '_').split('_') if w]
            s = ' '.join(parts)
            s = s.replace('Metacarpofalangica','Metacarpofalângica').replace('Interfalangica','Interfalângica').replace('Medio','Médio').replace('Minimo','Mínimo')
            return s
        def load_overlays():
            d = mao_dir()
            if not d:
                return None, []
            base_path = os.path.join(d, 'mao.png')
            try:
                base_surf = pygame.image.load(base_path).convert_alpha()
            except Exception:
                base_surf = None
            overlays = []
            for fname in sorted(os.listdir(d)):
                if not fname.lower().endswith('.png'):
                    continue
                if fname.lower() == 'mao.png':
                    continue
                fp = os.path.join(d, fname)
                try:
                    ov = pygame.image.load(fp).convert_alpha()
                    overlays.append((os.path.splitext(fname)[0], ov))
                except Exception:
                    pass
            return base_surf, overlays
        def tint_surface(surf, color=(0,255,0), alpha=120):
            tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            tint.fill((*color, alpha))
            out = surf.copy()
            out.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            return out

        base_surf, overlays = load_overlays()
        if not base_surf or not overlays:
            # Fallback: if assets missing, keep old buttons
            font_small = pygame.font.Font(None, 36)
            msg = font_small.render("Assets de mão não encontrados.", True, WHITE)
            self.screen.fill(BLACK)
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
            pygame.display.flip()
            pygame.time.delay(1200)
            # fallback to previous simple list
            fingers = ['Polegar', 'Indicador', 'Médio', 'Anelar', 'Mínimo']
            active = True
            while active:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        active=False; self.game.running=False; return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        active=False; return
                self.screen.fill(BLACK)
                self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
                pygame.display.flip(); self.clock.tick(30)
            return

        # Scale to 85% of screen height to avoid UI overlapping markers
        MARGIN = 24
        SCALE = 0.85
        scale = (HEIGHT * SCALE) / base_surf.get_height()
        base_scaled = pygame.transform.smoothscale(base_surf, (int(base_surf.get_width()*scale), int(base_surf.get_height()*scale)))
        overlay_entries = []  # (name, surf_scaled, mask, tinted_selected, tinted_hover)
        for name, ov in overlays:
            surf_s = pygame.transform.smoothscale(ov, (int(ov.get_width()*scale), int(ov.get_height()*scale)))
            mask = pygame.mask.from_surface(surf_s, 10)
            tinted_sel = tint_surface(surf_s, color=(0,255,0), alpha=140)
            tinted_hover = tint_surface(surf_s, color=(128,200,255), alpha=120)
            overlay_entries.append([name, surf_s, mask, tinted_sel, tinted_hover])

        selected = None
        font_small = pygame.font.Font(None, 32)
        font_title = pygame.font.Font(None, 40)
        title_surf = font_title.render("Escolha a articulação (clique na imagem)", True, WHITE)
        # Confirm button bottom-right
        BTN_W, BTN_H = 240, 44
        confirm_rect = pygame.Rect(WIDTH - MARGIN - BTN_W, HEIGHT - MARGIN - BTN_H, BTN_W, BTN_H)

        # Load current mapping for display
        cfg_path = os.path.join(repo_root(), 'config.json')
        def read_mapping():
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    c = json.load(f)
                return c.get('sensorMapping', {})
            except Exception:
                return {}

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game.running = False
                    return
                if event.type == pygame.MOUSEMOTION:
                    pass
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx,my = event.pos
                    # detect top-left area of image (we draw at left centered horizontally?)
                    # We'll draw base at center horizontally
                    bx = WIDTH//2 - base_scaled.get_width()//2
                    by = HEIGHT//2 - base_scaled.get_height()//2
                    local = (mx - bx, my - by)
                    if 0 <= local[0] < base_scaled.get_width() and 0 <= local[1] < base_scaled.get_height():
                        # within image; overlays are same size and aligned
                        lx, ly = int(local[0]), int(local[1])
                        for name, surf_s, mask, _tinted_sel, _tinted_hover in overlay_entries:
                            try:
                                if 0 <= lx < surf_s.get_width() and 0 <= ly < surf_s.get_height():
                                    if mask.get_at((lx,ly)):
                                        selected = name
                                        break
                            except Exception:
                                pass
                    # Confirm click
                    if confirm_rect.collidepoint((mx,my)) and selected:
                        # Persist selection
                        try:
                            cfg = {}
                            if os.path.isfile(cfg_path):
                                with open(cfg_path, 'r', encoding='utf-8') as f:
                                    cfg = json.load(f)
                            cfg['flybird_selected_articulation'] = selected
                            with open(cfg_path, 'w', encoding='utf-8') as f:
                                json.dump(cfg, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        # Also store pretty label on game for CSV
                        self.game.selected_finger = pretty(selected)
                        return

            # Draw
            self.screen.fill(BLACK)
            # Center image (with reduced height)
            base_pos = (WIDTH//2 - base_scaled.get_width()//2, HEIGHT//2 - base_scaled.get_height()//2)
            self.screen.blit(base_scaled, base_pos)
            # Draw all overlays normally, then apply tint for hovered/selected so others don't disappear
            mx,my = pygame.mouse.get_pos()
            local = (mx - base_pos[0], my - base_pos[1])
            mapping = read_mapping()
            hovered = None
            # First draw all markers
            for name, surf_s, _mask, _tinted_sel, _tinted_hover in overlay_entries:
                self.screen.blit(surf_s, base_pos)
            # Determine hovered by per-pixel alpha
            lx, ly = int(local[0]), int(local[1])
            if 0 <= lx < base_scaled.get_width() and 0 <= ly < base_scaled.get_height():
                for name, surf_s, mask, _ts, _th in overlay_entries:
                    try:
                        if 0 <= lx < surf_s.get_width() and 0 <= ly < surf_s.get_height():
                            if mask.get_at((lx,ly)):
                                hovered = name
                                break
                    except Exception:
                        pass
            # Then draw highlight for selected and hovered
            for name, surf_s, _mask, tinted_sel, tinted_hover in overlay_entries:
                if selected == name:
                    self.screen.blit(tinted_sel, base_pos)
                elif hovered == name:
                    self.screen.blit(tinted_hover, base_pos)
            # Title (top-left)
            self.screen.blit(title_surf, (MARGIN, MARGIN))
            # Selected / hovered label and mapped sensor (bottom-left)
            info_name = selected or hovered
            if info_name:
                info = f"{pretty(info_name)}"
                sensor = mapping.get(info_name)
                if sensor:
                    info += f" — Sensor: {sensor}"
                text = font_small.render(info, True, WHITE)
                self.screen.blit(text, (MARGIN, HEIGHT - MARGIN - text.get_height()))
            # Confirm button (bottom-right)
            col = (200,200,200) if selected else (120,120,120)
            pygame.draw.rect(self.screen, col, confirm_rect)
            btn_text = font_small.render("Confirmar", True, BLACK if selected else (60,60,60))
            self.screen.blit(btn_text, btn_text.get_rect(center=confirm_rect.center))

            pygame.display.flip()
            self.clock.tick(60)


    def calibrate_range(self):
        """Pre-game calibration screen to capture flexion/extension angle limits.

        - Limite Extensão (menor ângulo) mapeia para o topo da tela.
        - Limite Flexão (maior ângulo) mapeia para a base da tela.
        """
        font_title = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 32)
        title = font_title.render("Calibração de Limites", True, WHITE)
        info1 = font_small.render("Defina os limites com o sensor em tempo real:", True, WHITE)
        info2 = font_small.render("- Extensão: menor ângulo (Topo)", True, WHITE)
        info3 = font_small.render("- Flexão: maior ângulo (Base)", True, WHITE)

        # Buttons
        BTN_W, BTN_H = 240, 50
        margin = 24
        ext_btn = pygame.Rect(margin, HEIGHT//2 - BTN_H - 10, BTN_W, BTN_H)
        flex_btn = pygame.Rect(margin, HEIGHT//2 + 10, BTN_W, BTN_H)
        proceed_btn = pygame.Rect(WIDTH - margin - BTN_W, HEIGHT - margin - BTN_H, BTN_W, BTN_H)

        ext_value = None
        flex_value = None

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game.running = False
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if ext_btn.collidepoint((mx, my)):
                        val = self.game.sensor_data_provider() if self.game.sensor_data_provider else None
                        if val is not None:
                            ext_value = val
                    elif flex_btn.collidepoint((mx, my)):
                        val = self.game.sensor_data_provider() if self.game.sensor_data_provider else None
                        if val is not None:
                            flex_value = val
                    elif proceed_btn.collidepoint((mx, my)) and (ext_value is not None) and (flex_value is not None):
                        # Normalize order: ensure ext <= flex
                        if flex_value < ext_value:
                            ext_value, flex_value = flex_value, ext_value
                        # Persist to game and bird
                        self.game.calib_ext_min = ext_value
                        self.game.calib_flex_max = flex_value
                        if hasattr(self.game, 'bird') and self.game.bird is not None:
                            self.game.bird.calib_ext_min = ext_value
                            self.game.bird.calib_flex_max = flex_value
                        return

            # Draw screen
            self.screen.fill(BLACK)
            # Title
            self.screen.blit(title, (margin, margin))
            self.screen.blit(info1, (margin, margin + title.get_height() + 8))
            self.screen.blit(info2, (margin, margin + title.get_height() + 8 + info1.get_height() + 4))
            self.screen.blit(info3, (margin, margin + title.get_height() + 8 + info1.get_height() + 4 + info2.get_height() + 2))

            # Live angle reading
            current_val = self.game.sensor_data_provider() if self.game.sensor_data_provider else None
            angle_text = font_small.render(f"Ângulo atual: {current_val:.2f}°" if isinstance(current_val, (int,float)) else "Ângulo atual: --", True, WHITE)
            self.screen.blit(angle_text, (margin, HEIGHT//2 - BTN_H - 60))

            # Buttons
            pygame.draw.rect(self.screen, (200,200,200), ext_btn)
            self.screen.blit(font_small.render("Marcar Limite Extensão", True, BLACK), font_small.render("Marcar Limite Extensão", True, BLACK).get_rect(center=ext_btn.center))

            pygame.draw.rect(self.screen, (200,200,200), flex_btn)
            self.screen.blit(font_small.render("Marcar Limite Flexão", True, BLACK), font_small.render("Marcar Limite Flexão", True, BLACK).get_rect(center=flex_btn.center))

            # Show captured values
            ext_val_text = font_small.render(f"Extensão: {ext_value:.2f}°" if isinstance(ext_value, (int,float)) else "Extensão: --", True, WHITE)
            flex_val_text = font_small.render(f"Flexão: {flex_value:.2f}°" if isinstance(flex_value, (int,float)) else "Flexão: --", True, WHITE)
            self.screen.blit(ext_val_text, (ext_btn.right + 20, ext_btn.centery - ext_val_text.get_height()//2))
            self.screen.blit(flex_val_text, (flex_btn.right + 20, flex_btn.centery - flex_val_text.get_height()//2))

            # Proceed button (enabled only after both captured)
            enabled = (ext_value is not None) and (flex_value is not None)
            btn_col = (200,200,200) if enabled else (120,120,120)
            txt_col = BLACK if enabled else (60,60,60)
            pygame.draw.rect(self.screen, btn_col, proceed_btn)
            self.screen.blit(font_small.render("Prosseguir", True, txt_col), font_small.render("Prosseguir", True, txt_col).get_rect(center=proceed_btn.center))

            pygame.display.flip()
            self.clock.tick(60)

