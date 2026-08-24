import socket


def find_free_port(preferred):
    for porta in range(preferred, preferred + 100):
        prova = socket.socket()
        try:
            prova.bind(("", porta))
            return porta
        except OSError:
            continue
        finally:
            prova.close()
    raise RuntimeError(f"nenhuma porta livre a partir de {preferred}")
