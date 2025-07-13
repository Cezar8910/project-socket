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


clients_data = {} 
scores = {}
current_round_answers = {} 
quiz_active = False 

lock = threading.Lock()

def send_udp(sock, msg, addr):
    try:
        sock.sendto(msg.encode(), addr)
    except Exception as e:
        print(f"Erro ao enviar UDP para {addr}: {e}")

def broadcast_udp(sock, msg):
    # Envia uma mensagem para todos os clientes registrados
    with lock:
        for addr in list(clients_data.keys()): 
            send_udp(sock, msg, addr)

def handle_udp_messages(server_sock):
    # Esta thread será responsável por receber todas as mensagens UDP
    global quiz_active

    while True:
        try:
            data, addr = server_sock.recvfrom(2048) # Buffer maior para perguntas
            message = data.decode().strip()
            
            parts = message.split(":", 2) # Divide em no máximo 3 partes
            msg_type = parts[0]
            
            if msg_type == "REGISTER" and len(parts) >= 2:
                name = parts[1]
                with lock:
                    if addr not in clients_data:
                        clients_data[addr] = name
                        scores[name] = 0.0
                        print(f"[+] Jogador '{name}' ({addr}) conectado via UDP.")
                        send_udp(server_sock, f"Bem-vindo, {name}! Aguarde o início do quiz.", addr)
                    else:
                        # Se o cliente já está registrado, apenas atualiza o nome (se mudou)
                  
                        old_name = clients_data[addr]
                        if old_name != name:
                             print(f"[*] Cliente {addr} mudou de nome de '{old_name}' para '{name}'.")
                             del scores[old_name] # Remove o score antigo
                             clients_data[addr] = name
                             scores[name] = 0.0 # Cria um novo score
                        send_udp(server_sock, f"Você já está conectado como {name}. Aguarde o quiz.", addr)
            
            elif msg_type == "ANSWER" and len(parts) == 3 and quiz_active:
                name = parts[1]
                answer = parts[2].upper()
                addr_of_sender = next((a for a, n in clients_data.items() if n == name), None)
                
                # Verifica se a resposta veio do endereço correto e se é uma resposta válida
                if addr_of_sender == addr and answer in ["A", "B", "C", "D"]:
                    with lock:
                        if name not in current_round_answers: # Aceita apenas a primeira resposta
                            current_round_answers[name] = answer
                            print(f"Recebida resposta de {name}: {answer}")
                            send_udp(server_sock, f"Sua resposta '{answer}' foi recebida.", addr)
                        else:
                            send_udp(server_sock, "Você já respondeu a esta pergunta.", addr)
                elif addr_of_sender != addr:
                    print(f"[*] Alerta: Resposta de '{name}' veio de endereço inesperado: {addr}")
                elif not quiz_active:
                    send_udp(server_sock, "O quiz não está ativo no momento para aceitar respostas.", addr)

            else:
                print(f"[*] Mensagem UDP desconhecida de {addr}: {message}")

        except socket.timeout:
            continue # Não há dados no momento
        except Exception as e:
            print(f"Erro ao receber mensagem UDP: {e}")
        


def game_round_udp(server_sock):
    global quiz_active, current_round_answers
    quiz_active = True
    print("\n[+] Jogo começando em 5 segundos...")
    broadcast_udp(server_sock, "O quiz vai começar em 5 segundos! Prepare-se para responder.")
    time.sleep(5)

    for i, q in enumerate(questions):
        print(f"\n--- [Rodada {i+1}] ---")
        question_msg = f"PERGUNTA:{i+1}:{q['question']}\nSua resposta (A, B, C ou D): "
        broadcast_udp(server_sock, question_msg) # Envia a pergunta para todos os clientes

        with lock:
            current_round_answers = {} # Limpa as respostas da rodada anterior

        start_time = time.time()
        round_duration = 15 # Tempo para responder cada pergunta (em segundos)

        # Espera pelo tempo de resposta
        while time.time() - start_time < round_duration:
            time.sleep(0.1) # Pequena pausa para não consumir CPU

        # Avalia as respostas após o tempo limite
        correct_answers_in_round = []
        with lock: # Bloqueia para garantir que current_round_answers não mude durante a avaliação
            for name, ans in current_round_answers.items():
                if ans == q["answer"]:
                    correct_answers_in_round.append(name)
            
            # Atribui pontos. O primeiro a responder corretamente ganha mais (precisa de timestamp)
            # Para UDP, como não sabemos a ordem exata de chegada sem timestamps complexos,
            # vamos simplificar: todos que acertaram ganham 1 ponto.
            for name in correct_answers_in_round:
                scores[name] += 1.0 # 1 ponto por resposta correta no UDP simplificado
            
            print(f"Respostas corretas nesta rodada: {correct_answers_in_round}")
            
            # Envia o placar parcial
            placar = "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
            broadcast_udp(server_sock, f"PLACAR:\n--- Placar Parcial ---\n{placar}\n--- Fim do Placar ---\n")
        
        print(f"Aguardando 5s para a próxima rodada...\n")
        time.sleep(5)

    print("\n[+] Fim do quiz!")
    final_score_msg = "FIM_QUIZ:O quiz acabou! Placar Final:\n" + "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
    broadcast_udp(server_sock, final_score_msg)
    quiz_active = False # Quiz terminou

def start_udp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # SOCK_DGRAM para UDP
    server_sock.bind((HOST, PORT))
    server_sock.settimeout(0.5) # Timeout para recvfrom para não bloquear infinitamente

    print("[*] Servidor UDP ouvindo em %s:%d" % (HOST, PORT))
    print("[*] Aguardando clientes UDP se registrarem...")

    # Thread para lidar com todas as mensagens UDP recebidas (registro e respostas)
    message_handler_thread = threading.Thread(target=handle_udp_messages, args=(server_sock,))
    message_handler_thread.daemon = True
    message_handler_thread.start()

    # Loop para aguardar clientes se registrarem antes de iniciar o quiz
    start_wait = time.time()
    min_players = 1 # Para testes, pode ser 1. Para jogo, 2+
    wait_time_for_players = 15 # Segundos para esperar por jogadores

    while True:
        with lock:
            current_players = len(clients_data)
        
        if current_players >= min_players and (time.time() - start_wait > wait_time_for_players or current_players >= 2):
            print(f"\n[*] {current_players} jogadores conectados. Iniciando o quiz em UDP!")
            game_thread = threading.Thread(target=game_round_udp, args=(server_sock,))
            game_thread.start()
            break # Sai do loop de espera e permite que o jogo continue

        print(f"[*] Esperando jogadores... {current_players} conectados. ({int(time.time() - start_wait)}/{wait_time_for_players}s)", end='\r')
        time.sleep(1)
    
    game_thread.join() # Aguarda o término do quiz

    print("[*] Servidor UDP encerrado.")
    server_sock.close()

start_udp_server()