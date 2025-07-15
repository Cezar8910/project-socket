import socket
import threading
import time
import ssl 
from urllib.parse import urlparse, parse_qs

questions = [
    {"question": "1) Qual camada do modelo OSI é responsável pelo roteamento dos pacotes?", "options": "A) Enlace B) Transporte C) Rede D) Aplicação", "answer": "C"},
    {"question": "2) Qual protocolo é utilizado para resolução de nomes de domínio?", "options": "A) FTP B) DNS C) HTTP D) DHCP", "answer": "B"},
    {"question": "3) O que o protocolo TCP garante?", "options": "A) Baixa latência B) Alta largura de banda C) Entrega confiável e ordenada D) Endereçamento físico", "answer": "C"},
    {"question": "4) Qual dispositivo opera na camada de enlace?", "options": "A) Roteador B) Hub C) Switch D) Firewall", "answer": "C"},
    {"question": "5) O que é necessário para comunicação via IP?", "options": "A) Mesma VLAN B) Mesmo MAC C) Rota entre si D) Portas iguais", "answer": "C"},
]

HOST = 'localhost'
PORT = 9596

current_quiz_round = -1
quiz_started = False
quiz_finished = False
round_start_time = 0

clients_data = {}
current_round_answers_received = {}

lock = threading.Lock()
server_running = True

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")


def send_http_response(conn, status, body, content_type='text/html'):
    header = f'HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {len(body.encode())}\r\nConnection: close\r\n\r\n'
    conn.sendall((header + body).encode())

def handle_client_request(conn, addr):
    try:
        conn.settimeout(5)
        request_data = conn.recv(2048).decode()
        if not request_data:
            conn.close()
            return

        first_line = request_data.splitlines()[0]
        method, url_path, *_ = first_line.split()
        parsed_url = urlparse(url_path)
        params = parse_qs(parsed_url.query)
        
        name = params.get("name", [f"Guest_{threading.get_ident()}"])[0]
        answer_from_client = params.get("answer", [None])[0]

        with lock:
            if name not in clients_data:
                print(f"[+] Novo cliente '{name}' conectado de {addr}")
                clients_data[name] = {"conn": conn, "addr": addr, "score": 0.0, "last_activity": time.time()}
            else:
                clients_data[name]["last_activity"] = time.time()

        response_html = "<html><body><h1>Aguardando Quiz...</h1><p>Por favor, aguarde o início do quiz.</p>"

        if quiz_started:
            if quiz_finished:
                final_score_msg = "<h2>Quiz Finalizado!</h2><h3>Placar Final:</h3><ul>"
                with lock:
                    sorted_scores = sorted(clients_data.items(), key=lambda item: item[1]["score"], reverse=True)
                    for n, data in sorted_scores:
                        final_score_msg += f"<li>{n}: {data['score']:.1f} pontos</li>"
                final_score_msg += "</ul>"
                response_html = f"<html><body>{final_score_msg}</body></html>"
            elif current_quiz_round >= 0 and current_quiz_round < len(questions):
                q = questions[current_quiz_round]
                
                if answer_from_client and answer_from_client.upper() in ["A", "B", "C", "D"]:
                    with lock:
                        if name not in current_round_answers_received:
                            current_round_answers_received[name] = {"answer": answer_from_client.upper(), "timestamp": time.time()}
                            print(f"[SERVE] {name} respondeu '{answer_from_client.upper()}' na rodada {current_quiz_round + 1}")
                            response_html = f"<html><body><h1>Resposta Registrada!</h1><p>Sua resposta '{answer_from_client.upper()}' para a Pergunta {current_quiz_round + 1} foi recebida.</p><p>Aguarde a próxima pergunta e o placar.</p></body></html>"
                        else:
                            response_html = f"<html><body><h1>Já Respondeu!</h1><p>Você já enviou uma resposta para a Pergunta {current_quiz_round + 1}.</p><p>Aguarde a próxima pergunta e o placar.</p></body></html>"
                
                else:
                    response_html = f"<html><body><h1>Pergunta {current_quiz_round + 1}</h1>" \
                                    f"<p>{q['question']}</p><p>{q['options']}</p>" \
                                    f"<p>Tempo restante para responder: {max(0, int(round_start_time + 15 - time.time()))}s</p>" \
                                    f"<p>Para responder, use: /?name={name}&answer=A|B|C|D</p>" \
                                    f"<p>Seu placar atual: {clients_data[name]['score']:.1f}</p>" \
                                    f"</body></html>"
            else:
                response_html = "<html><body><h1>Quiz em Transição...</h1><p>Aguarde a próxima rodada ou o resultado final.</p></body></html>"
        
        send_http_response(conn, "200 OK", response_html)

    except socket.timeout:
        print(f"[*] Timeout ao receber requisição de {addr}. Conexão fechada.")
    except ssl.SSLError as e:
        print(f"[!] Erro SSL na conexão com {addr}: {e}")
    except Exception as e:
        print(f"[!] Erro ao lidar com cliente {addr}: {e}")
    finally:
        conn.close()

def game_loop_manager():
    global current_quiz_round, quiz_started, quiz_finished, round_start_time, server_running

    print("\n[+] Gerenciador do Quiz: Aguardando jogadores...")
    while not quiz_started and server_running: # Adicionar verificação de server_running
        time.sleep(1) 

    if not server_running: # Se o loop foi interrompido antes de iniciar
        print("[*] Gerenciador do Quiz: Servidor encerrado antes do início do jogo.")
        return

    print("[+] Gerenciador do Quiz: Quiz iniciado!")

    for i, q in enumerate(questions):
        if not server_running:
            print("[*] Gerenciador do Quiz: Servidor encerrado, parando jogo.")
            break

        current_quiz_round = i
        round_start_time = time.time()
        print(f"\n--- Gerenciador do Quiz: Rodada {i+1} iniciada ---")
        print(f"Pergunta: {q['question']} | Resposta: {q['answer']}")
        print(f"Aguardando respostas por 15 segundos.")
        
        time.sleep(15)

        print(f"\n--- Gerenciador do Quiz: Fim da Rodada {i+1} ---")
        
        correct_answers_in_order = [] 
        with lock:
            sorted_answers = sorted(current_round_answers_received.items(), 
                                    key=lambda item: item[1]["timestamp"])
            
            for name, ans_data in sorted_answers:
                if ans_data["answer"] == q["answer"]:
                    correct_answers_in_order.append(name)
            
            for idx, name in enumerate(correct_answers_in_order):
                score_to_add = max(1.0 - idx * 0.1, 0)
                clients_data[name]["score"] += score_to_add
                print(f"[{name}] Acertou! Recebeu {score_to_add:.1f} pontos.")
            
            current_round_answers_received.clear() 

        print("\n[*] Placar parcial:")
        with lock:
            sorted_scores = sorted(clients_data.items(), key=lambda item: item[1]["score"], reverse=True)
            for name, data in sorted_scores:
                print(f" - {name}: {data['score']:.1f} pontos")

        if i < len(questions) - 1: 
            print(f"Gerenciador do Quiz: Aguardando 5s para a próxima rodada...\n")
            time.sleep(5)
    
    print("\n[+] Gerenciador do Quiz: Fim do quiz!")
    quiz_finished = True
    current_quiz_round = len(questions) 
    
    time.sleep(10) 
    print("[*] Gerenciador do Quiz: Encerrado.")
    server_running = False

def start_server():
    global quiz_started, server_running
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
 
    print(f"[*] Servidor HTTPS ouvindo em https://{HOST}:{PORT}")
    
    game_manager_thread = threading.Thread(target=game_loop_manager, daemon=True)
    game_manager_thread.start()

    try:
        while server_running:
            try:
                server_socket.settimeout(1.0) 
                conn, addr = server_socket.accept()
                
                secure_conn = ssl_context.wrap_socket(conn, server_side=True, do_handshake_on_connect=True)
                
                with lock:
                    if not quiz_started and len(clients_data) >= 1:
                        quiz_started = True 
                        print("[*] Servidor: Quiz marcado para iniciar com o primeiro cliente!")

                threading.Thread(target=handle_client_request, args=(secure_conn, addr), daemon=True).start()
            
            except socket.timeout:
                continue 
            except ssl.SSLError as e: # Captura erros de handshake SSL
                print(f"[!] Erro SSL ao aceitar ou negociar conexão: {e}")
                if 'PROTOCOL_VERSION' in str(e) or 'WRONG_VERSION_NUMBER' in str(e):
                    print("    Verifique se o cliente está usando TLS/SSL e o protocolo correto.")
                conn.close() # Fechar o socket subjacente em caso de erro SSL
            except Exception as e:
                if server_running: 
                    print(f"[!] Erro ao aceitar conexão: {e}")
                server_running = False 
                break
            
    except KeyboardInterrupt:
        print("\n[!] Servidor interrompido por Ctrl+C.")
        server_running = False 
    finally:
        if game_manager_thread and game_manager_thread.is_alive():
            game_manager_thread.join(timeout=5) 
        
        if server_socket:
            server_socket.close()
            print("[*] Socket do servidor fechado. Servidor encerrado.")

start_server()