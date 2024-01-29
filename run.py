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
    websocket_mock = Mock()

    # Llamada a la función send
    await send(websocket_mock, action, data)

    # Verificar que se llamó a websocket.send con el mensaje JSON esperado
    expected_message = json.dumps({'action': action, 'data': data})
    websocket_mock.send.assert_called_once_with(expected_message)

class TestBot(unittest.TestCase):

    def test_send(self):
        # Ejecutar el bucle de eventos asíncronos para completar la tarea asincrónica
        asyncio.run(test_send(Mock(), 'move', {'game_id': '123', 'turn_token': '456', 'col': 2}))

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

    move_col = analyze_board(board, columns, rows, player)
    if move_col is None:
        # Decide si matar una fila, columna o diagonal
        kill_action = choose_kill_action(board, columns, rows, player, 'N' if player == 'S' else 'S')
        await send(websocket, 'kill', {'game_id': game_id, 'turn_token': turn_token, **kill_action})
    else:
        await send(websocket, 'move', {'game_id': game_id, 'turn_token': turn_token, 'col': move_col})


def choose_kill_action(board, columns, rows, player, enemy_player):
    # Decide si matar una fila, columna o diagonal cuando el enemigo está a punto de completar 3 fichas
    for row in range(rows):
        for col in range(columns):
            if should_kill_row(board, columns, rows, row, col, enemy_player, 3):
                return {'row': row}
            elif should_kill_column(board, columns, rows, row, col, enemy_player, 3):
                return {'col': col}

    # Si no hay necesidad de matar una fila, columna o diagonal, elige según algún criterio específico
    if prefer_kill_row_over_column(player):  # Función hipotética para determinar la preferencia
        # Prioriza matar fila
        for row in range(rows):
            if should_kill_row(board, columns, rows, row, 0, enemy_player, 2):
                return {'row': row}
    else:
        # Prioriza matar columna
        for col in range(columns):
            if should_kill_column(board, columns, rows, 0, col, enemy_player, 2):
                return {'col': col}

    # Si no hay necesidad de matar una fila o columna, elige aleatoriamente
    if randint(0, 1):  # Decide aleatoriamente entre matar fila o columna
        kill_row = randint(0, rows - 1)  # Elige aleatoriamente una fila
        return {'row': kill_row}
    else:
        kill_col = randint(0, columns - 1)  # Elige aleatoriamente una columna
        return {'col': kill_col}

def prefer_kill_row_over_column(player):
    return True if player == 'N' else False
    
def should_kill_row(board, columns, rows, row, col, player, consecutive_count):
    # Verifica si es necesario matar la fila
    count = 0
    for c in range(col, col + consecutive_count):
        if c < columns and board[row * (columns + 1) + c + 2] == player:
            count += 1
    return count == consecutive_count

def should_kill_column(board, columns, rows, row, col, player, consecutive_count):
    # Verifica si es necesario matar la columna
    count = 0
    for r in range(row, row + consecutive_count):
        if r < rows and board[r * (columns + 1) + col + 2] == player:
            count += 1
    return count == consecutive_count
    


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
    
    return False  # Regresa a nada si no hay tal movimiento

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        auth_token = sys.argv[1]
        asyncio.get_event_loop().run_until_complete(start(auth_token))
    else:
        print('Por favor provee tu auth_token')