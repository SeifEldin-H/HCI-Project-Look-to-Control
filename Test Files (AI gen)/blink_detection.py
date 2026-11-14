"""
Blink Detection and Gaze Tracking
Python translation of the supplied HTML + JavaScript application.


Run:
    python3 -m venv test_venv
    source test_venv/bin/activate  # Linux/macOS
    test_venv\Scripts\activate  # Windows
    pip install opencv-python mediapipe pillow
    python3 blink_detection.py


On first run, the MediaPipe face-landmarker model is downloaded automatically.
A working webcam and a graphical desktop session are required.
"""

import os
import time
import urllib.request
import tkinter as tk
from tkinter import messagebox

import cv2
import mediapipe as mp
from PIL import Image, ImageTk


# Match the JavaScript thresholds
BLINK_THRESHOLD = 0.65
MIN_BLINK_DURATION_MS = 500
MAX_BLINK_DURATION_MS = 1200
CLICK_COOLDOWN_MS = 900

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "face_landmarker.task")


def ensure_model():
    """Download the Face Landmarker model if it is not already present."""
    if not os.path.exists(MODEL_PATH):
        print("Downloading MediaPipe face model...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


class BlinkDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blink Detection")
        self.root.configure(bg="#171717")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.cap = None
        self.landmarker = None
        self.running = False

        self.closed_since = None
        self.last_blink_time = 0.0
        self.selected_index = 0

        self.status = tk.StringVar(value="Initializing...")
        self.option_buttons = []

        title = tk.Label(
            root, text="Blink Detection",
            font=("Arial", 24, "bold"),
            bg="#171717", fg="white"
        )
        title.pack(pady=(18, 12))

        self.video_label = tk.Label(root, bg="#171717")
        self.video_label.pack(padx=20, pady=8)

        self.status_label = tk.Label(
            root, textvariable=self.status,
            font=("Arial", 15),
            bg="#171717", fg="white",
            wraplength=600
        )
        self.status_label.pack(pady=14)

        button_frame = tk.Frame(root, bg="#171717")
        button_frame.pack(pady=10)

        for i in range(3):
            button = tk.Button(
                button_frame,
                text=f"Option {i + 1}",
                font=("Arial", 15),
                padx=18, pady=14,
                command=lambda index=i: self.option_clicked(index),
                relief="raised",
                bd=2
            )
            button.pack(side=tk.LEFT, padx=8)
            self.option_buttons.append(button)

        self.select_option(0)
        self.root.after(100, self.start_app)

    def set_status(self, message):
        self.status.set(message)

    def select_option(self, index):
        self.selected_index = index
        for i, button in enumerate(self.option_buttons):
            if i == index:
                button.configure(
                    bg="#22c55e", fg="white",
                    activebackground="#16a34a",
                    activeforeground="white",
                    highlightbackground="white",
                    highlightthickness=3
                )
            else:
                button.configure(
                    bg="#e5e5e5", fg="black",
                    activebackground="#d5d5d5",
                    highlightthickness=0
                )

    def option_clicked(self, index):
        self.select_option(index)
        self.set_status(f"Option {index + 1} selected!")

    def initialize_landmarker(self):
        model_path = ensure_model()
        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True
        )
        self.landmarker = FaceLandmarker.create_from_options(options)

    def start_app(self):
        try:
            self.set_status("1. Loading MediaPipe...")
            self.root.update_idletasks()
            self.initialize_landmarker()

            self.set_status("2. Starting webcam...")
            self.root.update_idletasks()
            self.cap = cv2.VideoCapture(0)

            if not self.cap.isOpened():
                raise RuntimeError(
                    "Could not open webcam. Check camera permissions "
                    "and whether another application is using it."
                )

            self.running = True
            self.set_status("3. Starting eye tracking...")
            self.update_frame()

        except Exception as exc:
            self.set_status(f"Initialization failed: {exc}")
            messagebox.showerror("Initialization error", str(exc))
            self.close_resources()

    @staticmethod
    def calculate_gaze(landmarks):
        """Translate the original JavaScript iris/eye landmark calculation."""
        if len(landmarks) < 478:
            return None

        left_iris = landmarks[468]
        right_iris = landmarks[473]

        left_outer, left_inner = landmarks[33], landmarks[133]
        right_outer, right_inner = landmarks[362], landmarks[263]

        left_top, left_bottom = landmarks[159], landmarks[145]
        right_top, right_bottom = landmarks[386], landmarks[374]

        left_width = abs(left_outer.x - left_inner.x)
        right_width = abs(right_outer.x - right_inner.x)
        left_height = abs(left_top.y - left_bottom.y)
        right_height = abs(right_top.y - right_bottom.y)

        if min(left_width, right_width, left_height, right_height) < 0.001:
            return None

        horizontal = (
            (left_iris.x - min(left_outer.x, left_inner.x)) / left_width
            + (right_iris.x - min(right_outer.x, right_inner.x)) / right_width
        ) / 2

        vertical = (
            (left_iris.y - left_top.y) / (left_bottom.y - left_top.y)
            + (right_iris.y - right_top.y) / (right_bottom.y - right_top.y)
        ) / 2

        # The original page mirrors the webcam and reverses the horizontal dot.
        x = max(0.02, min(0.98, 1.0 - horizontal))
        y = max(0.02, min(0.98, 1.0 - vertical))
        return x, y

    def process_result(self, result, frame):
        if not result.face_landmarks:
            self.closed_since = None
            self.set_status("No face detected")
            return

        landmarks = result.face_landmarks[0]
        gaze = self.calculate_gaze(landmarks)

        if gaze is not None:
            height, width = frame.shape[:2]
            gx = int(gaze[0] * width)
            gy = int(gaze[1] * height)
            cv2.circle(frame, (gx, gy), 10, (0, 255, 255), -1)
            cv2.circle(frame, (gx, gy), 15, (255, 255, 255), 2)

        if not result.face_blendshapes:
            self.closed_since = None
            self.set_status("Face detected | Tracking eyes...")
            return

        categories = result.face_blendshapes[0]
        scores = {item.category_name: item.score for item in categories}

        left = scores.get("eyeBlinkLeft", 0.0)
        right = scores.get("eyeBlinkRight", 0.0)
        both_closed = left > BLINK_THRESHOLD and right > BLINK_THRESHOLD

        now = time.perf_counter() * 1000.0

        if both_closed:
            if self.closed_since is None:
                self.closed_since = now
            self.set_status("Eyes closed...")
            return

        if self.closed_since is not None:
            duration = now - self.closed_since
            self.closed_since = None

            if (
                MIN_BLINK_DURATION_MS <= duration <= MAX_BLINK_DURATION_MS
                and now - self.last_blink_time > CLICK_COOLDOWN_MS
            ):
                self.last_blink_time = now
                self.activate_selection()

        self.set_status("Face detected | Gaze tracking active")

    def activate_selection(self):
        if self.selected_index is not None:
            self.option_clicked(self.selected_index)
            self.set_status("Blink click detected!")

    def update_frame(self):
        if not self.running or self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.set_status("Unable to read from webcam")
            self.root.after(30, self.update_frame)
            return

        # Match CSS transform: scaleX(-1)
        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )
        timestamp_ms = int(time.perf_counter() * 1000)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        self.process_result(result, frame)

        # Display the webcam frame in the Tkinter window.
        rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_display)
        image.thumbnail((640, 480))
        photo = ImageTk.PhotoImage(image=image)

        self.video_label.configure(image=photo)
        self.video_label.image = photo

        self.root.after(15, self.update_frame)

    def close_resources(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def close(self):
        self.close_resources()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    app = BlinkDetectionApp(window)
    window.mainloop()
