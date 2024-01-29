import asyncio
import json
from random import randint
import sys
import websockets
import time
import unittest
from unittest import mock
from asyncio import wait_for, TimeoutError

async def send(websocket, action, data):
    message = json.dumps({
        'action': action,
        'data': data,
    })
    print(f"Enviar Mensaje: {message}")
    await websocket.send(message)

async def test_send(websocket, action, data):
    # Mock para el websocket
    websocket_mock = mock.AsyncMock()

    # Llamada a la función send
    await send(websocket_mock, action, data)

    # Verificar que se llamó a websocket.send con el mensaje JSON esperado
    expected_message = json.dumps({'action': action, 'data': data})
    websocket_mock.send.assert_called_once_with(expected_message)

class TestBot(unittest.TestCase):

    async def setUp(self):
        # Configurar el bucle de eventos asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    async def tearDown(self):
        # Cerrar el bucle de eventos asyncio
        self.loop.close()

    async def test_send(self):
        # Ejecutar el bucle de eventos asíncronos para completar la tarea asincrónica
        await test_send(mock.AsyncMock(), 'move', {'game_id': '123', 'turn_token': '456', 'col': 2})
    
    @mock.patch('play.send')
    async def test_handle_challenge(self, mock_send):
        # Mock para el websocket
        websocket_mock = mock.AsyncMock()

        # Datos de prueba
        challenge_event = {'event': 'challenge', 'data': {'opponent': 'Player2', 'challenge_id': '123'}}

        # Llamada a la función handle_challenge
        await handle_challenge(websocket_mock, challenge_event)

        # Verificar que se llamó a send con el mensaje JSON esperado
        mock_send.assert_called_once_with(websocket_mock, 'accept_challenge', {'challenge_id': '123'})

    @mock.patch('play.send')
    async def test_process_move(self, mock_send):
        # Configurar el comportamiento esperado para la función send simulada
        mock_send.return_value = asyncio.Future()
        mock_send.return_value.set_result(None)

        websocket_mock = mock.AsyncMock()

        # Verificar que la función send simulada se llamó con los argumentos correctos
        await process_move(websocket_mock, {'data': {'game_id': '123', 'turn_token': '456', 'board': '...', 'side': 'N'}})
        mock_send.assert_called_once_with(websocket_mock, 'kill', {'game_id': '123', 'turn_token': '456', 'row': 1})
    
    async def test_is_optimal_move(self):
        # Prueba asincrónica para is_optimal_move
        # Simula un tablero donde el movimiento en la columna 2 sería óptimo para el jugador 'N'
        board = '... | N | S | N | ...\n... | S | N | S | ...'
        columns = 5
        rows = 2
        player = 'N'
        
        result = await is_optimal_move(board, 2, rows, columns, player)
        self.assertTrue(result)


    async def test_analyze_board(self):
        # Prueba asincrónica para analyze_board  
        # Simula un tablero donde el movimiento óptimo sería en la columna 3 para el jugador 'S'
        board = '... | N | S | N | ...\n... | S | N | S | ...'
        columns = 5
        rows = 2
        player = 'S'
        
        result = await analyze_board(board, columns, rows, player)
        self.assertEqual(result, 3)

if __name__ == '__main__':
    # Ejecutar las pruebas y mostrar un mensaje en la consola si todas pasan
    result = unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestBot))
    if result.wasSuccessful():
        print("Todas las pruebas pasaron correctamente.")
    else:
        print("Algunas pruebas fallaron.")

async def start(auth_token):
    uri = "ws://codechallenge-server-f4118f8ea054.herokuapp.com/ws?token={}".format(auth_token)
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f'Conectado a {uri}')
            await play(websocket)
    except Exception as e:
        print(f'Error de Conexion: {str(e)}')

async def play(websocket):
    try:
        while True:
            request = await websocket.recv()
            print(f"Recibido: {request}")
            
            request_data = json.loads(request)
            
            if request_data['event'] == 'update_user_list':
                pass
            elif request_data['event'] == 'game_over':
                pass
            elif request_data['event'] == 'challenge':
                await handle_challenge(websocket, request_data)
            elif request_data['event'] == 'accept_challenge':
                await handle_accept_challenge(request_data)
            elif request_data['event'] == 'your_turn':
                await process_your_turn(websocket, request_data)
    except Exception as e:
        print(f'Error in play loop: {str(e)}')
    
async def handle_challenge(websocket, request_data):
    # Handle the challenge event
    opponent = request_data['data']['opponent']
    challenge_id = request_data['data']['challenge_id']
    
    print(f"Desafio recibido de: {opponent}, challenge_id: {challenge_id}")
    
    # Siempre recibe el desafio
    await send(websocket, 'accept_challenge', {'challenge_id': challenge_id})

async def handle_accept_challenge(request_data):
    challenge_id = request_data['data']['challenge_id']
    print(f"Desafio Aceptado, challenge_id: {challenge_id}")

async def process_your_turn(websocket, request_data):
    await process_move(websocket, request_data)

async def process_move_with_timeout(websocket, request_data):
    game_id = request_data['data']['game_id']
    remaining_moves = request_data['data']['remaining_moves']
    
    # Verificar si quedan movimientos
    if remaining_moves <= 0:
        print(f"No quedan movimientos. Juego {game_id} terminado.")
        return
    
    try:
        # Esperar un máximo de 3 segundos para la ejecución de process_move
        await wait_for(process_move(websocket, request_data), timeout=3.0)
    except TimeoutError:
        print(f"Tiempo de ejecución agotado para el movimiento en el juego {game_id}.")

# Reemplaza la llamada a process_move en process_your_turn con process_move_with_timeout
async def process_your_turn(websocket, request_data):
    await process_move_with_timeout(websocket, request_data)

async def process_move(websocket, request_data):
    
    game_id = request_data['data']['game_id']
    turn_token = request_data['data']['turn_token']
    board = request_data['data']['board']
    player = request_data['data']['side']

    try:
        # Revisa las dimensiones del tablero
        columns = board.find('|', 1) - 1
        rows = board.count('\n') - 1
    except ValueError as e:
        print(f'Error al obtener las dimensiones del tablero: {e}')
        await send(websocket, 'kill', {'game_id': game_id, 'turn_token': turn_token, 'row': 1})
        return

    
    # Analiza el tablero en busca de 2 o mas piezas que tengan el mismo color
    move_col = analyze_board(board, columns, rows, player)
    
    if move_col is not None:
        # Si hay un movimiento óptimo, realiza el movimiento
        await send(websocket, 'move', {'game_id': game_id, 'turn_token': turn_token, 'col': move_col})
    else:
        # Si no hay un movimiento óptimo, decide si matar una fila, columna o diagonal
        kill_action = choose_kill_action(board, columns, rows, player, 'N' if player == 'S' else 'S')
        
        # Verifica si choose_kill_action devuelve None
        if kill_action is not None:
            await send(websocket, 'kill', {'game_id': game_id, 'turn_token': turn_token, **kill_action})
        else:
            print("No hay acción de matar válida.")
            await send(websocket, 'kill', {'game_id': game_id, 'turn_token': turn_token, 'row': 1})
    
def analyze_board(board, columns, rows, player):
    # Analiza el tablero en busca del movimiento optimo
    
    for col in range(columns):
        if is_optimal_move(board, col, rows, columns,player):
            return col
    
    # Si no hay tal movimiento no regresa nada
    return None

def is_optimal_move(board, col, rows, columns, player):
    if col < 0 or col >= columns:
        return False

    # Dividir el tablero en filas
    rows_data = board.split('\n')

    # Verificar si la columna tiene espacio vacío en alguna fila
    for row in range(rows):
        if rows_data[0][col * 6 + 3] == ' ':
            return True

    return False
        

def choose_kill_action(board, columns, rows, player, enemy_player):
    for row in range(rows):
        if should_kill_row(board, columns, rows, row, 0, enemy_player, player, 2):
            return {'row': row}

    for col in range(columns):
        if should_kill_column(board, columns, rows, 0, col, enemy_player, player, 2):
            return {'col': col}

    # Si no hay necesidad de matar una fila o columna, intenta completar tus propias 4 fichas
    for col in range(columns):
        if is_optimal_move(board, col, rows, columns, player):
            return {'col': col}

    return None

def should_kill_row(board, columns, rows, row, col, enemy_player, side, consecutive_count):
    # Verifica si es necesario matar la fila
    if row + consecutive_count > rows:
        return False  # Evitar desbordamiento de filas
    
    # Verifica si es necesario matar la fila del enemigo
    count = 0
    for c in range(col, col + consecutive_count):
        if c < columns and board[row * (columns + 1) + c + 2] == enemy_player:
            count += 1

    # Mata la fila si el lado es el mismo que el del bot y el enemigo está presente
    return count == consecutive_count and side == 'N' if enemy_player == 'S' else 'S'

def should_kill_column(board, columns, rows, row, col, enemy_player, side, consecutive_count):
    if columns + consecutive_count > rows:
        return False # Evitar desbordamiento de columnas
    
    # Verifica si es necesario matar la columna del enemigo
    count = 0
    for r in range(row, row + consecutive_count):
        if r < rows and board[r * (columns + 1) + col + 2] == enemy_player:
            count += 1

    # Mata la columna si el lado es el mismo que el del bot y el enemigo está presente
    return count == consecutive_count and side == 'N' if enemy_player == 'S' else 'S'

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        auth_token = sys.argv[1]
        asyncio.get_event_loop().run_until_complete(start(auth_token))
    else:
        print('Por favor provee tu auth_token')