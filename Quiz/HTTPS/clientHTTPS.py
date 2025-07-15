import threading
import time
import random
import re
import ssl # Importar o módulo SSL
from socket import socket, AF_INET, SOCK_STREAM

HOST = 'localhost'
PORT = 9596 # A mesma porta do servidor HTTPS
NUM_FIXED_CLIENTS = 8

client_threads = []
global_running = True


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.load_verify_locations(cafile="server.crt") # O cliente confia no server.crt
ssl_context.check_hostname = True 


def send_http_request(path, client_n):
    try:
        # 1. Cria um socket TCP normal
        with socket(AF_INET, SOCK_STREAM) as s:
            # 2. Conecta ao servidor
            s.connect((HOST, PORT))
            
            # 3. Envolve o socket TCP com SSL/TLS para criar uma conexão segura
            # server_hostname é crucial para a verificação de hostname em TLS
            secure_socket = ssl_context.wrap_socket(s, server_hostname=HOST)
            
            # 4. Agora, use o secure_socket para enviar e receber dados HTTP (criptografados)
            request = f'GET {path} HTTP/1.1\r\n' \
                      f'Host: {HOST}:{PORT}\r\n' \
                      f'Connection: close\r\n\r\n'
            secure_socket.send(request.encode())

            data = b""
            secure_socket.settimeout(10) # Timeout para a resposta do servidor
            while True:
                part = secure_socket.recv(2048)
                if not part:
                    break
                data += part

            response = data.decode(errors='ignore')

            if "\r\n\r\n" in response:
                return response.split("\r\n\r\n", 1)[1]
            return response
    except ssl.SSLError as e:
        print(f"[{client_n}] Erro SSL na requisição HTTPS para {path}: {e}")
        # Erros SSL comuns: CERTIFICATE_VERIFY_FAILED (certificado não confiável)
        # HOSTNAME_MISMATCH (hostname no certificado não corresponde)
        return None
    except Exception as e:
        print(f"[{client_n}] Erro na requisição HTTP para {path}: {e}")
        return None

def handle_auto_client(client_id):
    global global_running
    client_name = f"AutoPlayer_{client_id}_{random.randint(100, 999)}"
    
    print(f"[{client_name}] Iniciando...")

    last_question_index = -1 
    has_answered_current_round = False

    while global_running:
        try:
            path = f"/?name={client_name}"
            html_response = send_http_request(path, client_name)

            if html_response is None:
                print(f"[{client_name}] Nenhuma resposta do servidor ou erro de conexão. Tentando novamente...")
                time.sleep(2)
                continue

            if "Quiz Finalizado" in html_response or "placar final" in html_response.lower():
                print(f"[{client_name}] Quiz finalizado. Conteúdo: \n{html_response}")
                break

            match = re.search(r"<h1>Pergunta (\d+)</h1>", html_response)
            if match:
                current_question_index = int(match.group(1)) - 1
                
                if current_question_index > last_question_index:
                    last_question_index = current_question_index
                    has_answered_current_round = False
                    print(f"[{client_name}] Recebeu Pergunta {current_question_index + 1}. Preparando resposta...")

                if not has_answered_current_round:
                    answer = random.choice(["A", "B", "C", "D"])
                    time.sleep(random.uniform(0.5, 2.0))
                    
                    answer_path = f"/?name={client_name}&answer={answer}"
                    send_http_request(answer_path, client_name)
                    
                    print(f"[{client_name}] Respondeu: {answer}")
                    has_answered_current_round = True
                else:
                    print(f"[{client_name}] Já respondeu a Pergunta {last_question_index + 1}. Aguardando...")
            else:
                print(f"[{client_name}] Estado do quiz: {html_response.strip().splitlines()[0]}...")
            
            time.sleep(random.uniform(1.0, 3.0))

        except Exception as e:
            print(f"[{client_name}] Erro inesperado na lógica do cliente: {e}")
            break

    print(f"[{client_name}] Finalizado.")

if __name__ == "__main__":
    print(f"\nIniciando {NUM_FIXED_CLIENTS} clientes automáticos via socket HTTPS...\n")

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
        print("\nEncerrando clientes...")
    finally:
        for t in client_threads:
            if t.is_alive():
                t.join(timeout=2)
                if t.is_alive():
                    print(f"Aviso: Cliente {t.name} não encerrou completamente.")
        print("\nTodos os clientes socket-HTTPS finalizados.")