import socket
import threading
import sys
import time

HOST = '127.0.0.1'
PORT = 12345

name = "" # Variável global para armazenar o nome do cliente

def listen(sock):
    while True:
        try:
            data = sock.recv(2048).decode() 
            if not data:
                print("\n[!] Servidor desconectado. Encerrando cliente!")
                break
            
            # Limpa a linha de entrada para exibir a mensagem do servidor
            sys.stdout.write("\r" + " " * 80 + "\r") # Limpa a linha atual
            print(f"\n[SERVER]: {data}")
            sys.stdout.flush()

            if "Sua resposta (A, B, C ou D):" in data:
                pass

            if "O quiz acabou!" in data:
                print("Digite 'sair' para sair.")
                break 

        except Exception as e:
            print(f"\n[!] Erro na escuta do servidor: {e}")
            break

def send_answer(sock, answer):
    # Função auxiliar para enviar a resposta
    try:
        sock.sendall(f"{name}:{answer}".encode())
    except Exception as e:
        print(f"[!] Erro ao enviar resposta: {e}")

# Início do cliente
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        
        # Pede o nome do usuário ANTES de enviar qualquer coisa
        name = input("Digite seu nome aqui: ").strip()
        if not name:
            print("Nome não pode ser vazio. Saindo.")
            sys.exit(1)
            
        s.sendall(name.encode())

        print(f"[*] Conectado ao servidor {HOST}:{PORT} como {name}")

        # Inicia a thread para ESCUTAR o servidor
        listen_thread = threading.Thread(target=listen, args=(s,))
        listen_thread.daemon = True 
        listen_thread.start()

        # Loop principal para enviar respostas 
        while True:
            time.sleep(0.1) 

            # Input do usuário para a resposta
            user_input = input(" > ").strip()
            
            if user_input.lower() in ["a", "b", "c", "d"]:
                send_answer(s, user_input.upper())
            elif user_input.lower() == "sair":
                print("Saindo do quiz...")
                break
            elif "O quiz acabou!" in user_input:
                break
            else:
                print("Entrada inválida. Por favor, digite A, B, C, D ou 'sair'.")

        listen_thread.join(timeout=1) 
        
    except ConnectionRefusedError:
        print(f"[!] Erro: Conexão recusada. Certifique-se de que o servidor está rodando em {HOST}:{PORT}")
    except Exception as e:
        print(f"[!] Ocorreu um erro inesperado: {e}")
    finally:
        s.close()