import asyncio
import zmq
import zmq.asyncio

# https://stackoverflow.com/questions/57389579/use-zmq-poller-to-add-timeout-for-my-req-rep-zmqclient-but-the-function-does

async def main():
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

    try:
        while True:
            try:
                message = input("Enter a message: ")
                await socket.send_string(message)
                reply = await socket.recv_string()
                print(f"Received reply: {reply}")
            except KeyboardInterrupt:
                print("\nExiting ...")
                break
            except asyncio.CancelledError as e:
                if e.__context__ is not None:
                    if isinstance(e.__context__, zmq.error.ZMQError):
                        print("\nTask was cancelled during ZMQ operation.")
                    else:
                        print("\nTask was cancelled.")
                else:
                    print("\nTask was cancelled.")
                break
            except Exception as e:
                print(f"Error: {e}")
                break
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        print("Main task was cancelled.")
