import socket
import threading
import time
import random
import sys

HOST = '127.0.0.1'
PORT = 12345

NUM_FIXED_CLIENTS = 3
clients_threads = []
global_running = True

def handle_client(client_id):
    client_name = f"UDPPlayer_{client_id}_{random.randint(100, 999)}"
    server_addr = (HOST, PORT)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)

    try:
        # Envia o nome ao servidor
        sock.sendto(client_name.encode(), server_addr)

        def listen():
            global global_running
            while global_running:
                try:
                    data, _ = sock.recvfrom(1024)
                    msg = data.decode().strip()
                    print(f"\n[{client_name} - SERVIDOR]: {msg}")
                    sys.stdout.flush()

                    if "Sua resposta" in msg:
                        print(f"[{client_name}] Respondendo...")
                        time.sleep(random.uniform(0.5, 2.0))
                        answer = random.choice(["A", "B", "C", "D"])
                        sock.sendto(f"{client_name}:{answer}".encode(), server_addr)
                        print(f"[{client_name}] Respondeu: {answer}")

                    if "Fim do quiz" in msg or "O quiz acabou" in msg:
                        print(f"[{client_name}] Encerrando após fim do quiz.")
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[{client_name}] Erro ao escutar: {e}")
                    break

        listen_thread = threading.Thread(target=listen)
        listen_thread.daemon = True
        listen_thread.start()

        while global_running and listen_thread.is_alive():
            time.sleep(0.5)

    finally:
        sock.close()
        print(f"[{client_name}] Cliente encerrado.")

if __name__ == "__main__":
    print(f"\nIniciando {NUM_FIXED_CLIENTS} clientes automáticos UDP...")

    try:
        for i in range(NUM_FIXED_CLIENTS):
            t = threading.Thread(target=handle_client, args=(i + 1,))
            t.daemon = True
            clients_threads.append(t)
            t.start()
            time.sleep(0.1)

        while any(t.is_alive() for t in clients_threads):
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Interrupção detectada. Finalizando...")
        global_running = False
        for t in clients_threads:
            t.join(timeout=2)

    print("\nSimulação finalizada.")
