# main_fb.py

from FlyBird.modules.game import Game

def main_fb(sensor_data_provider=None, player_name=None, patient_id=None, session_id=None):
    """
    Inicia o jogo FlyBird.
    
    Parameters
    ----------
    sensor_data_provider : callable, optional
        Função que retorna o ângulo atual do sensor.
    player_name : str, optional
        Nome do paciente (pré-preenchido da sessão clínica).
    patient_id : str, optional
        ID do paciente para salvar dados.
    session_id : str, optional
        ID da sessão clínica.
    """
    game = Game(
        sensor_data_provider=sensor_data_provider,
        player_name=player_name,
        patient_id=patient_id,
        session_id=session_id
    )
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
        # Pre-game calibration of flexion/extension limits
        game.screens.calibrate_range()
        if not game.running:
            break

        while game.running:
            game.new()
            game.run()
            if game.game_over:
                # Dados são salvos SOMENTE quando usuário clica em "Salvar Dados"
                game.screens.show_go_screen()
                
                if not game.running:
                    break  # Sai do loop se o jogador escolher sair
    game.quit_game()

if __name__ == '__main__':
    main_fb()




