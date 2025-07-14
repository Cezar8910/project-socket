import socket
import threading
import time

questions = [
    {
        "question": "1) Qual camada do modelo OSI é responsável pelo roteamento dos pacotes?\n"
                    "A) Enlace\nB) Transporte\nC) Rede\nD) Aplicação",
        "answer": "C"
    },
    {
        "question": "2) Qual protocolo é utilizado para resolução de nomes de domínio (como www.google.com)?\n"
                    "A) FTP\nB) DNS\nC) HTTP\nD) DHCP",
        "answer": "B"
    },
    {
        "question": "3) O que o protocolo TCP garante em relação à comunicação?\n"
                    "A) Baixa latência\nB) Alta largura de banda\nC) Entrega confiável e ordenada\nD) Endereçamento físico",
        "answer": "C"
    },
    {
        "question": "4) Qual dos seguintes dispositivos opera na camada de enlace do modelo OSI?\n"
                    "A) Roteador\nB) Hub\nC) Switch\nD) Firewall",
        "answer": "C"
    },
    {
        "question": "5) O que é necessário para dois dispositivos se comunicarem via endereço IP?\n"
                    "A) Estarem na mesma VLAN\nB) Terem o mesmo endereço MAC\nC) Terem uma rota entre si\nD) Usarem portas iguais",
        "answer": "C"
    },
]

HOST = '127.0.0.1'
PORT = 12345
NUM_FIXED_CLIENTS = 8

clients_data = {}  # {conn: name}
scores = {}
server_running = True
lock = threading.Lock()

def broadcast(msg):
    for conn in list(clients_data.keys()):
        try:
            conn.sendall(msg.encode())
        except:
            continue

def remove_client(conn):
    with lock:
        if conn in clients_data:
            name = clients_data[conn]
            print(f"[-] {name} desconectado.")
            del clients_data[conn]
            if name in scores:
                del scores[name]
            try:
                conn.close()
            except:
                pass

def handle_client(conn, addr, name):
    print(f"[+] {name} conectado de {addr}")
    scores[name] = 0.0
    try:
        while server_running:
            time.sleep(1)
    except:
        pass
    finally:
        remove_client(conn)

def game_round():
    global server_running
    broadcast("O quiz vai começar em 5 segundos!")
    print("[+] Iniciando o quiz em 5s...")
    time.sleep(5)

    for i, q in enumerate(questions):
        if not server_running:
            break

        print(f"\n--- [Rodada {i+1}] ---")
        broadcast(f"\n{q['question']}\nSua resposta (A, B, C ou D):")

        round_answers = {}
        start_time = time.time()

        while time.time() - start_time < 15:
            time.sleep(0.01)
            with lock:
                for conn, name in list(clients_data.items()):
                    try:
                        conn.settimeout(0.2)
                        data = conn.recv(1024).decode().strip()
                        if data:
                            parts = data.split(":", 1)
                            if len(parts) == 2:
                                client_name, answer = parts
                                if client_name == name and answer.upper() in ["A", "B", "C", "D"]:
                                    if name not in round_answers:
                                        round_answers[name] = answer.upper()
                                        print(f"[+] {name} respondeu: {answer.upper()}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[!] Erro com {name} (ignorado): {e}")

        correct = [name for name, ans in round_answers.items() if ans == q["answer"]]
        for idx, name in enumerate(correct):
            scores[name] += max(1.0 - idx * 0.1, 0)

        placar = "\n".join([f"{n}: {s:.1f} pontos" for n, s in scores.items()])
        print(f"\n Gabarito:  {q["answer"]}")
        print(f"\n>>> Respostas corretas: {correct}")
        print(f"\n--- Placar parcial ---\n{placar}")
        broadcast(f"\n--- Placar parcial ---\n{placar}")
        time.sleep(5)

    print("\n[+] Fim do quiz!")
    broadcast("O Quiz acabou! Placar final:\n" + "\n".join([f"{n}: {s:.1f} pontos" for n, s in scores.items()]))
    server_running = False
    time.sleep(1)
    for conn in list(clients_data.keys()):
        try:
            conn.close()
        except:
            pass
    print("[*] Servidor finalizado.")

def start_server():
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(NUM_FIXED_CLIENTS)

    print(f"[*] Servidor ouvindo em {HOST}:{PORT}")
    print("[*] Aguardando conexões...")

    game_thread = None

    try:
        while server_running:
            try:
                server.settimeout(0.5)
                conn, addr = server.accept()
                conn.settimeout(10)
                name = conn.recv(1024).decode().strip()
                if name:
                    with lock:
                        clients_data[conn] = name
                    thread = threading.Thread(target=handle_client, args=(conn, addr, name))
                    thread.daemon = True
                    thread.start()
                    print(f"[+] '{name}' conectado.")
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[!] Erro na aceitação: {e}")


            if len(clients_data) == NUM_FIXED_CLIENTS:
                print("[*] Iniciando jogo!")
                game_thread = threading.Thread(target=game_round)
                game_thread.start()
                break

    except KeyboardInterrupt:
        print("\n[!] Interrompido manualmente.")
        server_running = False
    finally:
        if game_thread:
            game_thread.join()
        server.close()

start_server()