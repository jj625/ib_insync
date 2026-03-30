import zmq
import sys
import time

def main():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    try:
        while True:
            try:
                message = input("Enter a message: ")
                socket.send_string(message)
                
                while True:
                    socks = dict(poller.poll(1000))  # Poll with a timeout of 1000 ms
                    if socket in socks and socks[socket] == zmq.POLLIN:
                        reply = socket.recv_string()
                        print(f"Received reply: {reply}")
                        break
                    else:
                        print("Waiting for reply...")
            except KeyboardInterrupt:
                print("\nExiting ...")
                break
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()