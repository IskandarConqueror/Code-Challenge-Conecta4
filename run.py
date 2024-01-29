import asyncio
import json
from random import randint
import sys
import websockets
import time
import unittest
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

    def test_send(self):
        # Ejecutar el bucle de eventos asíncronos para completar la tarea asincrónica
        asyncio.run(test_send(mock.AsyncMock(), 'move', {'game_id': '123', 'turn_token': '456', 'col': 2}))
    
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

if __name__ == '__main__':
    unittest.main()

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
    player = request_data['data']['side']  # Corregir para obtener el jugador actual

    try:
        columns = board.find('|', 1) - 1
        rows = board.count('\n') - 1
    except ValueError as e:
        print(f'Error al obtener las dimensiones del tablero: {e}')

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        auth_token = sys.argv[1]
        asyncio.get_event_loop().run_until_complete(start(auth_token))
    else:
        print('Por favor provee tu auth_token')