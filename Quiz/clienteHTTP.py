import threading
import time
import random
import re
from socket import socket, AF_INET, SOCK_STREAM

HOST = 'localhost'
PORT = 9595
NUM_FIXED_CLIENTS = 8
client_threads = []
global_running = True

def send_http_request(path):
    """Cria uma conexão HTTP via socket e retorna o corpo da resposta."""
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        request = f'GET {path} HTTP/1.1\r\n' \
                  f'Host: {HOST}:{PORT}\r\n' \
                  f'Connection: close\r\n\r\n'
        s.send(request.encode())

        data = b""
        while True:
            part = s.recv(2048)
            if not part:
                break
            data += part

    response = data.decode(errors='ignore')

    # Remove cabeçalho HTTP
    if "\r\n\r\n" in response:
        return response.split("\r\n\r\n", 1)[1]
    return response

def handle_auto_client(client_id):
    global global_running
    client_name = f"AutoPlayer_{client_id}"
    question_index = 0

    print(f"[{client_name}] Iniciando...")

    while global_running:
        try:
            html = send_http_request(f"/?name={client_name}")
            if not html:
                print(f"[{client_name}] Nenhuma resposta do servidor.")
                break

            # Detectar fim de jogo
            if "Quiz Finalizado" in html or "fim do quiz" in html.lower():
                print(f"[{client_name}] Quiz finalizado.")
                break

            # Detectar pergunta
            if "Sua resposta" in html or re.search(r"[A-D]\)", html):
                print(f"[{client_name}] Recebeu pergunta {question_index + 1}. Respondendo...")
                answer = random.choice(["A", "B", "C", "D"])
                time.sleep(random.uniform(0.5, 2.0))
                response = send_http_request(f"/?name={client_name}&answer={answer}")
                print(f"[{client_name}] Respondeu: {answer}")
                question_index += 1
                continue

            time.sleep(1)

        except Exception as e:
            print(f"[{client_name}] Erro: {e}")
            break

    print(f"[{client_name}] Finalizado.")

# Início do programa principal
if __name__ == "__main__":
    print(f"\nIniciando {NUM_FIXED_CLIENTS} clientes automáticos via socket HTTP...\n")

    for i in range(NUM_FIXED_CLIENTS):
        t = threading.Thread(target=handle_auto_client, args=(i + 1,))
        t.daemon = True
        t.start()
        client_threads.append(t)
        time.sleep(0.2)

    try:
        while global_running and any(t.is_alive() for t in client_threads):
            time.sleep(1)
    except KeyboardInterrupt:
        global_running = False
        print("\n[!] Encerrando clientes...")
    finally:
        for t in client_threads:
            t.join(timeout=2)
        print("\n[✓] Todos os clientes socket-HTTP finalizados.")
