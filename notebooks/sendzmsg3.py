import zmq
from zmq.utils import win32

def main():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    # with win32.enable_ctrl_c_workaround():
    with win32.allow_interrupt():
        try:
            while True:
                try:
                    message = input("Enter a message: ")
                    socket.send_string(message)
                    reply = socket.recv_string(timeout=1000)
                    print(f"Received reply: {reply}")
                except KeyboardInterrupt:
                    print("\nExiting ...")
                    break
        finally:
            socket.close()
            context.term()

if __name__ == "__main__":
    main()