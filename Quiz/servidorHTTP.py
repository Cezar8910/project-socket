import socket
import threading
import time
from urllib.parse import urlparse, parse_qs

questions = [
    {"question": "1) Qual camada do modelo OSI é responsável pelo roteamento dos pacotes?", "options": "A) Enlace B) Transporte C) Rede D) Aplicação", "answer": "C"},
    {"question": "2) Qual protocolo é utilizado para resolução de nomes de domínio?", "options": "A) FTP B) DNS C) HTTP D) DHCP", "answer": "B"},
    {"question": "3) O que o protocolo TCP garante?", "options": "A) Baixa latência B) Alta largura de banda C) Entrega confiável e ordenada D) Endereçamento físico", "answer": "C"},
    {"question": "4) Qual dispositivo opera na camada de enlace?", "options": "A) Roteador B) Hub C) Switch D) Firewall", "answer": "C"},
    {"question": "5) O que é necessário para comunicação via IP?", "options": "A) Mesma VLAN B) Mesmo MAC C) Rota entre si D) Portas iguais", "answer": "C"},
]

HOST = 'localhost'
PORT = 9595
NUM_FIXED_CLIENTS = 8  

clients_data = {}  # {name: {"conn": socket, "addr": addr, "score": float}}
client_answers = {}
client_progress = {}
lock = threading.Lock()
server_running = True

def send_http_response(conn, body):
    header = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
    conn.sendall((header + body).encode())

def handle_client(conn, addr):
    try:
        data = conn.recv(2048).decode()
        if not data:
            conn.close()
            return

        # Parse da requisição HTTP
        first_line = data.splitlines()[0]
        method, url, *_ = first_line.split()
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        name = params.get("name", ["Guest"])[0]
        answer = params.get("answer", [None])[0]

        with lock:
            if name not in clients_data:
                print(f"[+] Cliente '{name}' conectado de {addr}")
                clients_data[name] = {"conn": conn, "addr": addr, "score": 0.0}
                client_progress[name] = 0
            else:
                clients_data[name]["conn"] = conn  # reusar conexão

        index = client_progress[name]

        if answer:
            if name not in client_answers:
                client_answers[name] = {}
            if index not in client_answers[name]:
                client_answers[name][index] = answer.upper()
                print(f"[+] {name} respondeu: {answer.upper()}")

        if index >= len(questions):
            score = clients_data[name]["score"]
            html = f"<html><body><h1>Quiz Finalizado</h1><p>{name}, sua pontuação final: {score:.1f}</p></body></html>"
            send_http_response(conn, html)
            conn.close()
            return

        q = questions[index]
        html = f"<html><body><h1>Pergunta {index + 1}</h1>" \
               f"<p>{q['question']}</p><p>{q['options']}</p>" \
               f"<p>Responda com: /?name={name}&answer=A|B|C|D</p>" \
               f"</body></html>"

        send_http_response(conn, html)
        conn.close()

    except Exception as e:
        print(f"[!] Erro: {e}")
        conn.close()

def game_loop():
    global server_running 
    print("[*] Esperando respostas...")
    for i, q in enumerate(questions):
        print(f"\n--- Rodada {i+1} ---")
        time.sleep(15)

        with lock:
            for name in clients_data:
                resposta = client_answers.get(name, {}).get(i, None)
                if resposta == q["answer"]:
                    idx = list(client_answers.get(name, {}).keys()).index(i)
                    clients_data[name]["score"] += max(1.0 - idx * 0.1, 0)
                client_progress[name] += 1

        print(f"\n Gabarito:  {q["answer"]}")
        print("\n[*] Placar parcial:")
        for name, data in clients_data.items():
            print(f" - {name}: {data['score']:.1f} pontos")

    print("[+] Quiz finalizado.")
    server_running = False

def start_server():
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(NUM_FIXED_CLIENTS)

    print(f"[*] Servidor HTTP ouvindo em http://{HOST}:{PORT}")
    game_started = False

    try:
        while server_running:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

            with lock:
                if not game_started and len(clients_data) >= NUM_FIXED_CLIENTS:
                    print("[*] Iniciando jogo!")
                    threading.Thread(target=game_loop, daemon=True).start()
                    game_started = True

    except KeyboardInterrupt:
        print("\n[!] Servidor encerrado.")
    finally:
        server.close()

start_server()
