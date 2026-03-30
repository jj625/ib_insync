import cv2
import time

# Initialize the webcam
cap = cv2.VideoCapture(0)

# Initialize variables
recording = False
last_movement_time = time.time()
movement_threshold = 50  # Adjust this value based on your needs
no_movement_duration = 180  # 3 minutes in seconds

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = None

# Function to detect movement
def detect_movement(frame1, frame2):
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return len(contours) > movement_threshold

# Read the first frame
ret, frame1 = cap.read()
ret, frame2 = cap.read()

while cap.isOpened():
    if detect_movement(frame1, frame2):
        last_movement_time = time.time()
        if not recording:
            recording = True
            out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))
            print("Recording started")
        out.write(frame1)
    else:
        if recording and (time.time() - last_movement_time > no_movement_duration):
            recording = False
            out.release()
            print("Recording stopped")

    frame1 = frame2
    ret, frame2 = cap.read()

    if not ret:
        break

    cv2.imshow("Frame", frame1)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if recording:
    out.release()
cv2.destroyAllWindows()
