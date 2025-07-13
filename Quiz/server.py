import socket
import threading
import time

# O servidor envia uma pergunta a todos os clientes. As perguntas devem ser configuradas previamente no código e deve ser escolhido como multipla-escolha entre as opções [A, B, C e D].
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

# Dicionário para armazenar conexões de clientes e seus nomes
clients_data = {}
scores = {}

lock = threading.Lock()

def broadcast(msg):
    # Envia uma mensagem para todos os clientes conectados
    for conn in clients_data:
        try:
            conn.sendall(msg.encode())
        except Exception as e:
            print(f"Erro ao enviar mensagem para um cliente: {e}")
            remove_client(conn)

def remove_client(conn):
    # Remove um cliente da lista de clientes ativos
    with lock:
        if conn in clients_data:
            name = clients_data[conn]
            print(f"[-] {name} desconectado.")
            del clients_data[conn]
            if name in scores:
                del scores[name]
            conn.close()

def handle_client(conn, addr, name):
    print(f"[+] {name} conectado de {addr}")
    scores[name] = 0.0 

    try:
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Erro na comunicação com {name}: {e}")
    finally:
        remove_client(conn)

def game_round():
    # Inicia o jogo após um pequeno atraso para que os clientes se preparem
    print("\n[+] Jogo começando em 5 segundos...")
    broadcast("O quiz vai começar em 5 segundos! Prepare-se para responder.")
    time.sleep(5)

    for i, q in enumerate(questions):
        print(f"\n--- [Rodada {i+1}] ---")
        question_msg = f"\n{q['question']}\nSua resposta (A, B, C ou D): "
        broadcast(question_msg) # Envia a pergunta para todos os clientes

        round_answers = {} # Para coletar as respostas desta rodada {name: answer}
        start_time = time.time()
        round_duration = 15 # Tempo para responder cada pergunta (em segundos)

        # Coleta respostas dos clientes por um tempo limitado
        while time.time() - start_time < round_duration:
            with lock:
                for conn, name in list(clients_data.items()):
                    try:
                        # Timeout para a operação de recebimento
                        conn.settimeout(0.1)
                  
                        data = conn.recv(1024).decode().strip()
                        if data:
                            parts = data.split(":", 1) 
                            if len(parts) == 2:
                                client_name, answer = parts
                                if client_name == name and answer.upper() in ["A", "B", "C", "D"] and name not in round_answers:
                                    round_answers[name] = answer.upper()
                            else:
                                print(f"Formato de dado inválido de {name}: {data}")
                    except socket.timeout:
                        continue # Não há dados no momento, tenta o próximo cliente
                    except Exception as e:
                        print(f"Erro ao receber dados de {name}: {e}")
                        remove_client(conn) # Remove cliente "problemático"
        
        # Avalia as respostas após o tempo limite
        correct_answers_in_round = []
        for name, ans in round_answers.items():
            if ans == q["answer"]:
                correct_answers_in_round.append(name)
        
        # Atribui pontos. O primeiro a responder corretamente ganha mais.
        for idx, name in enumerate(correct_answers_in_round):
            score_to_add = max(1.0 - idx * 0.1, 0)
            scores[name] += score_to_add
            
        print(f"Respostas corretas nesta rodada: {correct_answers_in_round}")
        
        # Envia o placar parcial
        placar = "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
        broadcast(f"\n--- Placar Parcial ---\n{placar}\n")
        
        # Aguarda um pouco antes da próxima pergunta
        print(f"Aguardando 5s para a próxima rodada...")
        time.sleep(5)

    print("\n[+] Fim do quiz!")
    final_score_msg = "O quiz acabou! Placar Final:\n" + "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
    broadcast(final_score_msg)

    for conn in list(clients_data.keys()):
        conn.close()
    print("Servidor encerrado.")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5) 

    print("[*] Servidor ouvindo em %s:%d" % (HOST, PORT))
    print("[*] Aguardando conexões de jogadores...")

    start_wait = time.time()
    
    while True:
        try:
            conn, addr = server.accept()
            conn.settimeout(10) # Tempo para o cliente enviar o nome
            name = conn.recv(1024).decode().strip()
            
            if name:
                with lock:
                    clients_data[conn] = name
                # Inicia uma thread para lidar com o cliente recém-conectado
                thread = threading.Thread(target=handle_client, args=(conn, addr, name))
                thread.daemon = True # A thread será encerrada quando a principal for encerrada
                thread.start()
                print(f"[+] Jogador '{name}' ({addr}) conectado.")
            else:
                print(f"[-] Conexão de {addr} recusada: Nome não fornecido.")
                conn.close()
        except socket.timeout:
            print("[*] Tempo limite para receber nome excedido para uma conexão.")
            continue
        except Exception as e:
            print(f"Erro ao aceitar conexão: {e}")
            break

        if len(clients_data) >= 1 and (time.time() - start_wait > 10 or len(clients_data) >= 2):
            print("\n[*] Número mínimo de jogadores ou tempo limite atingido. Iniciando o jogo!\n")
            # Agora, o jogo rodará em uma nova thread para não bloquear a aceitação de novas conexões
            game_thread = threading.Thread(target=game_round)
            game_thread.start()
            break 
    
    game_thread.join() # Aguarda o término do quiz antes de encerrar o servidor

# Chamada para iniciar o servidor
start_server()