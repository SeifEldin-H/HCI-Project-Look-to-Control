# this file was made with chatgpt
"""
Blink Detection and Gaze Tracking
Python translation of the supplied HTML + JavaScript application.


Run:
    python3 -m venv test_venv
    source test_venv/bin/activate  # Linux/macOS
    test_venv\Scripts\activate  # Windows
    pip install opencv-python mediapipe pillow numpy
    python3 blink_detection.py


On first run, the MediaPipe face-landmarker model is downloaded automatically.
A working webcam and a graphical desktop session are required.

The gaze dot is mapped to positions within the webcam preview. Click
'Calibrate gaze' and follow the five targets while keeping your head fairly still.
"""
import os
import time
import urllib.request
import tkinter as tk
from tkinter import messagebox

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

BLINK_THRESHOLD = 0.65
MIN_BLINK_DURATION_MS = 500
MAX_BLINK_DURATION_MS = 1200
CLICK_COOLDOWN_MS = 900
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")
PREVIEW_W, PREVIEW_H = 640, 480
TARGETS = [(x, y) for y in (0.08, 0.50, 0.92) for x in (0.08, 0.50, 0.92)]
SETTLE_SECONDS = 1.0
SAMPLE_SECONDS = 1.8


def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading MediaPipe face model...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


class BlinkDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Blink Detection and Calibrated Gaze Tracking")
        self.root.configure(bg="#171717")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.cap = None
        self.landmarker = None
        self.running = False
        self.closed_since = None
        self.last_blink_time = 0.0
        self.selected_index = 0

        self.calibrating = False
        self.calibration_index = 0
        self.calibration_phase_start = 0.0
        self.calibration_samples = []
        self.calibration_features = []
        self.calibration_targets = []
        self.gaze_model_x = None
        self.gaze_model_y = None
        self.last_gaze = None
        self.app_x = 0
        self.app_y = 0
        self.app_w = 800
        self.app_h = 600
        self.calibration_window = None
        self.calibration_canvas = None
        self.gaze_window = None
        self.gaze_canvas = None

        tk.Label(root, text="Blink Detection", font=("Arial", 24, "bold"),
                 bg="#171717", fg="white").pack(pady=(16, 8))
        self.video_label = tk.Label(root, bg="#171717")
        self.video_label.pack(padx=16, pady=6)
        self.status = tk.StringVar(value="Initializing...")
        tk.Label(root, textvariable=self.status, font=("Arial", 13),
                 bg="#171717", fg="white", wraplength=650).pack(pady=8)

        controls = tk.Frame(root, bg="#171717")
        controls.pack(pady=8)
        self.calibrate_button = tk.Button(controls, text="Calibrate gaze",
            font=("Arial", 12, "bold"), padx=12, pady=9,
            command=self.start_calibration)
        self.calibrate_button.pack(side=tk.LEFT, padx=6)
        self.option_buttons = []
        for i in range(3):
            b = tk.Button(controls, text=f"Option {i + 1}", font=("Arial", 13),
                padx=14, pady=10, command=lambda n=i: self.option_clicked(n))
            b.pack(side=tk.LEFT, padx=6)
            self.option_buttons.append(b)
        self.select_option(0)
        self.root.after(100, self.start_app)

    def set_status(self, msg):
        self.status.set(msg)

    def select_option(self, index):
        self.selected_index = index
        for i, b in enumerate(self.option_buttons):
            if i == index:
                b.configure(bg="#22c55e", fg="white", activebackground="#16a34a",
                             activeforeground="white", highlightbackground="white", highlightthickness=2)
            else:
                b.configure(bg="#e5e5e5", fg="black", activebackground="#d5d5d5", highlightthickness=0)

    def option_clicked(self, index):
        self.select_option(index)
        self.set_status(f"Option {index + 1} selected!")

    def initialize_landmarker(self):
        opts = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=ensure_model()),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

    def start_app(self):
        try:
            self.set_status("Loading face tracking model...")
            self.root.update_idletasks()
            self.initialize_landmarker()
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Could not open webcam. Check camera permissions.")
            self.running = True
            self.set_status("Camera ready. Click 'Calibrate gaze' to begin.")
            self.update_frame()
        except Exception as exc:
            self.set_status(f"Initialization failed: {exc}")
            messagebox.showerror("Initialization error", str(exc))
            self.close_resources()

    @staticmethod
    def extract_features(landmarks):
        """Four iris positions normalized to each eye's width and height."""
        if len(landmarks) < 478:
            return None
        li, ri = landmarks[468], landmarks[473]
        # Use min/max x corners so both eyes share the same image direction.
        l_outer, l_inner = landmarks[33], landmarks[133]
        r_inner, r_outer = landmarks[362], landmarks[263]
        l_top, l_bottom = landmarks[159], landmarks[145]
        r_top, r_bottom = landmarks[386], landmarks[374]
        lmin, lmax = min(l_outer.x, l_inner.x), max(l_outer.x, l_inner.x)
        rmin, rmax = min(r_outer.x, r_inner.x), max(r_outer.x, r_inner.x)
        lden, rden = l_bottom.y - l_top.y, r_bottom.y - r_top.y
        if min(lmax-lmin, rmax-rmin, abs(lden), abs(rden)) < 1e-4:
            return None
        return np.array([
            (li.x-lmin)/(lmax-lmin),
            (ri.x-rmin)/(rmax-rmin),
            (li.y-l_top.y)/lden,
            (ri.y-r_top.y)/rden,
        ], dtype=np.float64)

    @staticmethod
    def design_row(features):
        # Affine model: four eye features -> screen x/y.
        return np.array([1.0, *features], dtype=np.float64)

    def start_calibration(self):
        if not self.running:
            return
        self.root.update_idletasks()
        self.app_x = self.root.winfo_rootx()
        self.app_y = self.root.winfo_rooty()
        self.app_w = max(400, self.root.winfo_width())
        self.app_h = max(300, self.root.winfo_height())
        self.calibrating = True
        self.calibration_index = 0
        self.calibration_phase_start = time.perf_counter()
        self.calibration_samples = []
        self.calibration_features = []
        self.calibration_targets = []
        self.gaze_model_x = None
        self.gaze_model_y = None
        self.last_gaze = None
        self.hide_gaze_marker()

        # Display calibration targets across the application window.
        self.calibration_window = tk.Toplevel(self.root)
        self.calibration_window.configure(bg="#101010")
        self.calibration_window.overrideredirect(True)
        self.calibration_window.attributes("-topmost", True)
        self.calibration_window.geometry(
            f"{self.app_w}x{self.app_h}+{self.app_x}+{self.app_y}"
        )
        self.calibration_canvas = tk.Canvas(
            self.calibration_window, bg="#101010", highlightthickness=0, cursor="none"
        )
        self.calibration_canvas.pack(fill=tk.BOTH, expand=True)
        self.calibration_window.bind("<Escape>", self.cancel_calibration)
        self.draw_calibration_target()
        self.set_status("Application-window calibration started. Follow the targets inside this window. Press Esc to cancel.")

    def draw_calibration_target(self):
        if self.calibration_canvas is None:
            return
        canvas = self.calibration_canvas
        canvas.delete("all")
        nx, ny = TARGETS[self.calibration_index]
        x, y = int(nx * self.app_w), int(ny * self.app_h)
        canvas.create_text(self.app_w // 2, 38,
            text=f"APPLICATION WINDOW CALIBRATION - Point {self.calibration_index + 1}/{len(TARGETS)}",
            fill="white", font=("Arial", 18, "bold"))
        canvas.create_text(self.app_w // 2, 72,
            text="Look at the yellow target inside this application window",
            fill="#cccccc", font=("Arial", 13))
        canvas.create_oval(x-22, y-22, x+22, y+22,
            fill="#ffff00", outline="white", width=3)
        canvas.create_oval(x-5, y-5, x+5, y+5, fill="#111111", outline="#111111")
        canvas.create_text(self.app_w // 2, self.app_h - 34,
            text="Targets cover this application window - press Esc to cancel",
            fill="#aaaaaa", font=("Arial", 11))

    def cancel_calibration(self, _event=None):
        self.calibrating = False
        if self.calibration_window is not None:
            self.calibration_window.destroy()
            self.calibration_window = None
            self.calibration_canvas = None
        self.set_status("Calibration cancelled.")

    def show_gaze_marker(self, x, y):
        # A separate topmost marker positioned in full-screen coordinates.
        if self.gaze_window is None:
            self.gaze_window = tk.Toplevel(self.root)
            self.gaze_window.overrideredirect(True)
            self.gaze_window.attributes("-topmost", True)
            self.gaze_window.attributes("-alpha", 0.88)
            self.gaze_window.configure(bg="#ff00ff")
            try:
                self.gaze_window.attributes("-transparentcolor", "#ff00ff")
            except tk.TclError:
                pass
            self.gaze_canvas = tk.Canvas(self.gaze_window, width=30, height=30,
                bg="#ff00ff", highlightthickness=0)
            self.gaze_canvas.pack()
            self.gaze_canvas.create_oval(4, 4, 26, 26,
                fill="#00ffff", outline="white", width=2)
        # Follow the app if the user moves or resizes its window.
        self.root.update_idletasks()
        app_x = self.root.winfo_rootx()
        app_y = self.root.winfo_rooty()
        app_w = max(1, self.root.winfo_width())
        app_h = max(1, self.root.winfo_height())
        px = app_x + max(0, min(app_w - 30, int(x * app_w) - 15))
        py = app_y + max(0, min(app_h - 30, int(y * app_h) - 15))
        self.gaze_window.geometry(f"30x30+{px}+{py}")
        self.gaze_window.lift()

    def hide_gaze_marker(self):
        if self.gaze_window is not None:
            self.gaze_window.destroy()
            self.gaze_window = None
            self.gaze_canvas = None

    def advance_calibration(self, features, now):
        if not self.calibrating:
            return
        elapsed = now - self.calibration_phase_start
        if elapsed >= SETTLE_SECONDS:
            if features is not None:
                self.calibration_samples.append(features)
        if elapsed >= SETTLE_SECONDS + SAMPLE_SECONDS:
            if len(self.calibration_samples) < 8:
                self.calibration_samples = []
                self.calibration_phase_start = now
                self.set_status("Couldn't see your irises clearly. Keep your face in view and look at the target.")
                return
            average = np.mean(np.stack(self.calibration_samples), axis=0)
            self.calibration_features.append(self.design_row(average))
            self.calibration_targets.append(np.array(TARGETS[self.calibration_index]))
            self.calibration_index += 1
            self.calibration_samples = []
            self.calibration_phase_start = now
            if self.calibration_index >= len(TARGETS):
                X = np.stack(self.calibration_features)
                Y = np.stack(self.calibration_targets)
                # Least-squares linear mapping, fitted separately for x and y.
                self.gaze_model_x = np.linalg.lstsq(X, Y[:, 0], rcond=None)[0]
                self.gaze_model_y = np.linalg.lstsq(X, Y[:, 1], rcond=None)[0]
                self.calibrating = False
                if self.calibration_window is not None:
                    self.calibration_window.destroy()
                    self.calibration_window = None
                    self.calibration_canvas = None
                self.set_status("Application-window calibration complete! The gaze marker is active inside this window.")
            else:
                self.draw_calibration_target()
                self.set_status(f"Screen calibration point {self.calibration_index + 1}/{len(TARGETS)}: look at the next target.")

    def predict_gaze(self, features):
        if features is None or self.gaze_model_x is None:
            return None
        row = self.design_row(features)
        x = float(row @ self.gaze_model_x)
        y = float(row @ self.gaze_model_y)
        # Keep the marker within the application and damp frame-to-frame jitter.
        x = float(np.clip(x, 0.01, 0.99))
        y = float(np.clip(y, 0.01, 0.99))
        if self.last_gaze is not None:
            alpha = 0.28
            x = alpha*x + (1-alpha)*self.last_gaze[0]
            y = alpha*y + (1-alpha)*self.last_gaze[1]
        self.last_gaze = (x, y)
        return self.last_gaze

    def process_blink(self, result):
        if not result.face_landmarks:
            self.closed_since = None
            return
        if not result.face_blendshapes:
            self.closed_since = None
            return
        scores = {c.category_name: c.score for c in result.face_blendshapes[0]}
        both_closed = (scores.get("eyeBlinkLeft", 0.0) > BLINK_THRESHOLD and
                       scores.get("eyeBlinkRight", 0.0) > BLINK_THRESHOLD)
        now_ms = time.perf_counter() * 1000
        if both_closed:
            if self.closed_since is None:
                self.closed_since = now_ms
            return
        if self.closed_since is not None:
            duration = now_ms - self.closed_since
            self.closed_since = None
            if MIN_BLINK_DURATION_MS <= duration <= MAX_BLINK_DURATION_MS and now_ms-self.last_blink_time > CLICK_COOLDOWN_MS:
                self.last_blink_time = now_ms
                self.option_clicked(self.selected_index)
                self.set_status("Blink click detected!")

    def update_frame(self):
        if not self.running or self.cap is None:
            return
        ok, raw_frame = self.cap.read()
        if not ok:
            self.set_status("Unable to read from webcam")
            self.root.after(30, self.update_frame)
            return

        # Detect on raw camera frame. The preview is mirrored only for display.
        rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.perf_counter() * 1000)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        features = self.extract_features(result.face_landmarks[0]) if result.face_landmarks else None
        now = time.perf_counter()
        self.advance_calibration(features, now)
        gaze = self.predict_gaze(features) if not self.calibrating else None
        self.process_blink(result)

        display = cv2.flip(raw_frame, 1)
        display = cv2.resize(display, (PREVIEW_W, PREVIEW_H))

        if gaze is not None and not self.calibrating:
            self.show_gaze_marker(*gaze)
        elif self.calibrating:
            self.hide_gaze_marker()
        elif result.face_landmarks and self.gaze_model_x is None:
            cv2.putText(display, "Click Calibrate gaze", (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0,255,255), 2, cv2.LINE_AA)

        if not result.face_landmarks:
            self.set_status("No face detected - move into the camera view.")
        elif self.calibrating:
            self.set_status(f"Application calibration point {self.calibration_index+1}/{len(TARGETS)}. Keep looking at the yellow target.")
        elif self.gaze_model_x is None:
            self.set_status("Face detected. Click 'Calibrate gaze' to calibrate across this application window.")
        elif gaze is not None:
            self.set_status("Calibrated gaze tracking active. The cyan marker follows your estimated gaze inside this application window.")

        #photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(display, cv2.COLOR_BGR2RGB)))
        #self.video_label.configure(image=photo)
        #self.video_label.image = photo
        self.root.after(15, self.update_frame)

    def close_resources(self):
        self.running = False
        if self.calibration_window is not None:
            self.calibration_window.destroy()
            self.calibration_window = None
            self.calibration_canvas = None
        self.hide_gaze_marker()
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
    root = tk.Tk()
    app = BlinkDetectionApp(root)
    root.mainloop()