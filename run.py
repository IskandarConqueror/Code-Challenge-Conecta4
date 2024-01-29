import asyncio
import json
from random import randint
import sys
import websockets
import time
import unittest
from asyncio import test_utils
from unittest import mock

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

    async def asyncSetUp(self):
        # Configurar el bucle de eventos asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    async def asyncTearDown(self):
        # Cerrar el bucle de eventos asyncio
        self.loop.close()

    @test_utils.run_until_complete
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

async def process_move(websocket, request_data):
    
    game_id = request_data['data']['game_id']
    turn_token = request_data['data']['turn_token']
    board = request_data['data']['board']

    # Revisa que las dimensiones del tablero sean correctas, sino tira un error en el mensaje    
    try:
        columns = board.find('|', 1) - 1
        rows = board.count('\n') - 1
    except ValueError as e:
        print(f'Error al obtener las dimensiones del tablero: {e}')

    # Consigue el numero de columnas y filas que hay en el tablero
    columns = board.find('|', 1) - 1
    rows = board.count('\n') - 1
    
    # Analiza el tablero en busca de 2 o mas piezas que tengan el mismo color
    move_col = analyze_board(board, columns, rows, request_data['data']['side'])
    
    # Si no hay movimiento optimo simplemente hara un movimiento al azar
    if move_col is None:
        move_col = randint(0, columns)
    
    await send(websocket, 'move', {'game_id': game_id, 'turn_token': turn_token, 'col': move_col})
    
def analyze_board(board, columns, rows, player):
    # Analiza el tablero en busca del movimiento optimo
    
    for col in range(columns):
        if is_optimal_move(board, col, rows, columns,player):
            return col
    
    # Si no hay tal movimiento no regresa nada
    return None

def is_optimal_move(board, col, rows, columns, player):
    # Esto revisa si el movimiento en dicha columna es optimo en realidad
    if col < 0 or col >= columns:
        return False
    
    # Verifica si hay espacio suficiente en la columna para colocar la ficha
    if board[col + 2] != ' ':
        return False
    # Cuenta de manera consecutiva las piezas del mismo color en la columna especificada
    count = 0
    for row in range(rows - 1, -1, -1):  # Empieza desde el fondo de la columna hasta el principio
        color_ficha = board[row * (columns + 1) + col + 2] #Este comando recibe todo del por parte de analyze_board y sirve para analizar el color de la ficha del jugador
        if player == 'N' and color_ficha == 'N':
            count +=1   
        elif player == 'S' and color_ficha == 'S':
            count +=1
        else: 
            count = 0

        if count >= 2 and randint(0, 1):  # Esto detecta el movimiento óptimo aunque con 50% de probabilidad de pasar
                return True
        
        # Verifica si cortaría sus propias fichas
        if count >= 2 and row - 1 >= 0 and board[(row - 1) * (columns + 1) + col + 2] == ' ':
            return False
        if count >= 2:  # Retorna True si hay al menos 2 fichas del mismo color en la columna
            return True

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        auth_token = sys.argv[1]
        asyncio.get_event_loop().run_until_complete(start(auth_token))
    else:
        print('Por favor provee tu auth_token')