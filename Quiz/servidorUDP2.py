import socket
import time

HOST = '127.0.0.1'
PORT = 12345

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((HOST, PORT))
print(f"[*] Servidor UDP aguardando em {HOST}:{PORT}...")

# Estruturas para armazenar estado dos jogadores
players = {}      # addr => name
scores = {}       # name => pontuação
MAX_PLAYERS = 8   # mínimo para iniciar jogo
TIME_TO_WAIT = 10 # tempo de espera antes de iniciar o jogo (segundos)

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

def broadcast(message):
    for addr in players:
        try:
            server.sendto(message.encode(), addr)
        except Exception as e:
            print(f"Erro ao enviar para {addr}: {e}")

def game_loop():
    print(f"\n[*] Esperando jogadores (máximo {MAX_PLAYERS})... Você tem {TIME_TO_WAIT}s.")
    start_time = time.time()
    
    while time.time() - start_time < TIME_TO_WAIT and len(players) < MAX_PLAYERS:
        try:
            msg, addr = server.recvfrom(1024)
            decoded = msg.decode().strip()
            if addr not in players:
                players[addr] = decoded
                scores[decoded] = 0.0
                print(f"[+] Jogador '{decoded}' conectado de {addr}")
        except Exception as e:
            print(f"Erro ao registrar jogador: {e}")

    if len(players) == 0:
        print("Nenhum jogador conectado. Encerrando.")
        return

    print("\n[*] Iniciando o quiz!")
    broadcast("O quiz vai começar em 5 segundos!")
    time.sleep(5)

    for idx, q in enumerate(questions):
        print(f"\n[Rodada {idx+1}] Enviando pergunta.")
        broadcast(f"{q['question']}\nSua resposta (A, B, C ou D):")

        answers = {}  # name => resposta
        round_start = time.time()
        ROUND_TIME = 10

        while time.time() - round_start < ROUND_TIME:
            try:
                server.settimeout(0.5)
                msg, addr = server.recvfrom(1024)
                decoded = msg.decode().strip()
                if addr in players:
                    name = players[addr]
                    if ":" in decoded:
                        part_name, answer = decoded.split(":")
                        if part_name == name and name not in answers:
                            answers[name] = answer.strip().upper()
                            print(f"[{name}] respondeu: {answer.strip().upper()}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Erro ao receber resposta: {e}")
                continue

        # Corrige pontuação
        correct_players = [name for name, ans in answers.items() if ans == q["answer"]]
        for i, name in enumerate(correct_players):
            score = max(1.0 - i * 0.1, 0)
            scores[name] += score
        
        print(f"\n Gabarito:  {q["answer"]}")
        print(f"Corretos nesta rodada: {correct_players}")
        placar = "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
        print(f"\n--- Placar parcial ---\n{placar}")
        broadcast(f"\n--- Placar Parcial ---\n{placar}")
        time.sleep(3)

    print("\n[+] Fim do quiz!")
    final_score = "\n--- Placar Final ---\n" + "\n".join([f"{p}: {s:.1f} pontos" for p, s in scores.items()])
    broadcast("O quiz acabou!\n" + final_score)
    print(final_score)

# Execução principal
try:
    game_loop()
except KeyboardInterrupt:
    print("\n[!] Encerrado manualmente.")
finally:
    server.close()
    print("[*] Servidor encerrado.")