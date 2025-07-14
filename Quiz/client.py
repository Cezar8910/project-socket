import socket
import threading
import sys
import time
import random

HOST = '127.0.0.1'
PORT = 12345

NUM_FIXED_CLIENTS = 3
client_threads = []
global_running = True

def handle_single_client(client_id):
    client_name = f"AutoPlayer_{client_id}_{random.randint(100,999)}"

    def listen(sock):
        nonlocal client_name
        global global_running

        while global_running:
            try:
                sock.settimeout(0.5)
                data = sock.recv(2048).decode()
                if not data:
                    print(f"[{client_name}] Desconectado do servidor.")
                    global_running = False
                    break

                print(f"\n[{client_name} - SERVIDOR]: {data}")
                sys.stdout.flush()

                if "A)" in data and "Sua resposta" in data:
                    print(f"[{client_name}]: Respondendo...")
                    time.sleep(random.uniform(0.5, 2.0))
                    answer = random.choice(["A", "B", "C", "D"])
                    sock.sendall(f"{client_name}:{answer}".encode())
                    print(f"[{client_name}]: Enviou resposta: {answer}")

                if "O quiz acabou!" in data:
                    global_running = False
                    break

            except socket.timeout:
                continue
            except Exception as e:
                if "10038" not in str(e) and "10053" not in str(e) and "10054" not in str(e):
                    print(f"[{client_name}] Erro na escuta: {e}")
                global_running = False
                break

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            s.sendall(client_name.encode())
            print(f"[{client_name}] Conectado ao servidor.")
            thread = threading.Thread(target=listen, args=(s,))
            thread.daemon = True
            thread.start()

            while global_running and thread.is_alive():
                time.sleep(0.5)

        except ConnectionRefusedError:
            print(f"[{client_name}] Conexão recusada.")
        except Exception as e:
            print(f"[{client_name}] Erro: {e}")
        finally:
            print(f"[{client_name}] Cliente finalizado.")

if __name__ == "__main__":
    print(f"\nIniciando {NUM_FIXED_CLIENTS} clientes automáticos...")
    for i in range(NUM_FIXED_CLIENTS):
        t = threading.Thread(target=handle_single_client, args=(i+1,))
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
        print("\n[✓] Todos os clientes finalizados.")
