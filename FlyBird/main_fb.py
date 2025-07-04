# main_fb.py

from FlyBird.modules.game import Game

def main_fb(sensor_data_provider=None):
    game = Game(sensor_data_provider=sensor_data_provider)
    while game.running:
        game.screens.show_start_screen()
        if not game.running:
            break
        game.screens.get_player_name()
        if not game.running:
            break
        game.screens.get_finger_choice()
        if not game.running:
            break

        while game.running:
            game.new()
            game.run()
            if game.game_over:
                game.save_results()
                game.screens.show_go_screen()
                
                if not game.running:
                    break  # Sai do loop se o jogador escolher sair
    game.quit_game()

if __name__ == '__main__':
    main_fb()




