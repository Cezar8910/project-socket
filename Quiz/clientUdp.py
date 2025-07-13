import socket
import threading
import sys
import time

HOST = '127.0.0.1'
PORT = 12345

name = ""
server_address = (HOST, PORT)

running = True
waiting_for_answer = False
question_received_event = threading.Event()
stop_listening_event = threading.Event()


def listen_udp(client_sock):
    global waiting_for_answer, running

    while running: # Loop continua enquanto 'running' for True
        try:
            # Tenta receber dados, mas verifica o evento de parada
            # Isso é crucial: se o evento for setado, ele não bloqueia aqui
            data, addr = client_sock.recvfrom(2048) 
            message = data.decode().strip()
            print(f"[DEBUG CLIENT] Recebido do servidor: '{message}'")

            # Limpa a linha de entrada antes de imprimir a mensagem do servidor
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

            parts = message.split(":", 1)
            msg_type = parts[0]
            content = parts[1] if len(parts) > 1 else ""

            if msg_type == "PERGUNTA":
                print(f"\n[QUIZ]: {content}")
                sys.stdout.flush()
                waiting_for_answer = True
                question_received_event.set() # Sinaliza que há uma pergunta
            elif msg_type == "PLACAR":
                print(f"\n[PLACAR]:\n{content}")
                sys.stdout.flush()
                waiting_for_answer = False
            elif msg_type == "FIM_QUIZ":
                print(f"\n[FIM QUIZ]:\n{content}")
                print("Pressione Enter para sair.")
                waiting_for_answer = False
                running = False # Define running como False para encerrar o loop principal
                break # Sai do loop de escuta
            else:
                print(f"\n[SERVER]: {message}")
                sys.stdout.flush()

        except socket.timeout:
            # Se ocorrer timeout, verifica se devemos parar antes de continuar
            if stop_listening_event.is_set():
                break # Sai do loop se o evento de parada for setado
            continue
        except Exception as e:
            # Se o erro for o 10038 (socket inválido), o que é comum ao fechar
            # tratamos isso como um sinal para parar
            if "10038" in str(e):
                print(f"\n[!] Socket encerrado. Encerrando escuta.")
            else:
                print(f"\n[!] Erro inesperado na escuta UDP do servidor: {e}")
            running = False # Define running como False para encerrar o loop principal
            break # Sai do loop de escuta

# Início do cliente UDP
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    # O timeout do socket precisa ser ajustado para ser compatível com a verificação de parada
    s.settimeout(1.0) # Aumenta o timeout para 1 segundo, dando tempo para verificar a flag de parada

    try:
        name = input("Digite seu nome aqui: ").strip()
        if not name:
            print("Nome não pode ser vazio. Saindo.")
            sys.exit(1)

        s.sendto(f"REGISTER:{name}:".encode(), server_address)
        print(f"[*] Enviando registro para o servidor {HOST}:{PORT} como {name}")

        listen_thread = threading.Thread(target=listen_udp, args=(s,))
        listen_thread.daemon = True # Torna a thread daemon para que ela não impeça o programa de sair
        listen_thread.start()

        # Loop principal para enviar respostas e interagir
        while running: # Loop continua enquanto 'running' for True
            # Espera até que uma pergunta seja recebida ou um timeout para verificar a flag 'running'
            question_received_event.wait(timeout=0.5)

            if not running: # Verifica se 'running' foi alterado para False por outra thread
                print("[DEBUG CLIENT] Flag 'running' definida como False. Encerrando loop principal.")
                break

            if waiting_for_answer:
                print(f"[DEBUG CLIENT] Aguardando input do usuário para a resposta...")
                try:
                    user_input = input(" > ").strip()
                    print(f"[DEBUG CLIENT] Input do usuário: '{user_input}'")

                    if user_input.lower() in ["a", "b", "c", "d"]:
                        s.sendto(f"ANSWER:{name}:{user_input.upper()}".encode(), server_address)
                        print(f"[*] Resposta '{user_input.upper()}' enviada.")
                        waiting_for_answer = False
                        question_received_event.clear() # Limpa o evento para a próxima pergunta
                    elif user_input.lower() == "sair":
                        print("Saindo do quiz...")
                        running = False # Sinaliza para parar
                        break
                    else:
                        print("Entrada inválida. Por favor, digite A, B, C, D ou 'sair'.")
                except EOFError: # Ctrl+Z no Windows, Ctrl+D no Linux/macOS
                    print("\n[!] Entrada inesperada (EOF). Encerrando.")
                    running = False
                    break
                except KeyboardInterrupt: # Ctrl+C
                    print("\n[!] Ctrl+C detectado. Encerrando cliente.")
                    running = False
                    break
            else:
  
                pass

    except KeyboardInterrupt: # Captura Ctrl+C se ocorrer antes de entrar no loop principal
        print("\n[!] Ctrl+C detectado durante a inicialização. Encerrando cliente.")
    except Exception as e:
        print(f"[!] Ocorreu um erro inesperado: {e}")
    finally:
        stop_listening_event.set() # Sinaliza para a thread de escuta parar
        listen_thread.join(timeout=2) # Espera no máximo 2 segundos pela thread de escuta
        if s:
            s.close() # Garante que o socket seja fechado
            print("[*] Socket do cliente fechado.")