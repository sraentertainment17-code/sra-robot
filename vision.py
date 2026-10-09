#!/usr/bin/env python3
"""
SRA Robot — Vision (vision.py)
==============================
Pi Camera Module 3 integration for the robot.
- Take photos
- Stream video
- Face detection (using OpenCV)
- Obstacle detection (basic)

Usage:
    from vision import RobotVision
    cam = RobotVision()
    photo_path = cam.capture("test.jpg")
    faces = cam.detect_faces()
    cam.cleanup()

Or run directly to test:
    python3 vision.py
"""

import os
import time
import subprocess

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("⚠️ OpenCV not found — vision will use basic capture only")


class RobotVision:
    """Camera vision using Pi Camera Module 3."""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.face_cascade = None

        if HAS_CV2:
            # Load face detection model (built into OpenCV)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)

        print("📷 Vision system ready" + (" (basic — no OpenCV)" if not HAS_CV2 else ""))

    def _open_camera(self):
        """Open the camera connection."""
        if self.cap is None or not self.cap.isOpened():
            if HAS_CV2:
                self.cap = cv2.VideoCapture(self.camera_index)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self.cap

    def capture(self, filename="photo.jpg"):
        """Take a single photo and save it."""
        save_path = os.path.join(os.path.expanduser("~"), "ai-robot", "captures", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        if HAS_CV2:
            self._open_camera()
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    cv2.imwrite(save_path, frame)
                    print(f"📸 Photo saved: {save_path}")
                    return save_path
            print("❌ Failed to capture photo")
            return None
        else:
            # Fallback: use libcamera (Pi 5 native)
            result = subprocess.run(
                ["libcamera-still", "-o", save_path, "--width", "640", "--height", "480"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                print(f"📸 Photo saved: {save_path}")
                return save_path
            print("❌ Failed to capture photo")
            return None

    def detect_faces(self):
        """Detect faces in current camera frame. Returns list of (x, y, w, h) tuples."""
        if not HAS_CV2 or self.face_cascade is None:
            print("⚠️ Face detection requires OpenCV")
            return []

        self._open_camera()
        if not self.cap or not self.cap.isOpened():
            print("❌ Camera not available")
            return []

        ret, frame = self.cap.read()
        if not ret:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) > 0:
            print(f"👤 Detected {len(faces)} face(s)")
        return faces

    def describe_scene(self):
        """Take a photo and return a basic description for the brain.
        In a full implementation, this would send the image to an LLM vision model.
        """
        photo_path = self.capture("scene.jpg")
        if photo_path is None:
            return "I can't see anything right now."

        faces = self.detect_faces()
        if len(faces) > 0:
            return f"I can see {len(faces)} person in front of me."
        return "I see the room but no people."

    def cleanup(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
        print("📷 Vision system shut down")


# --- Test mode ---
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════╗
║   📷 SRA ROBOT VISION TEST               ║
╚══════════════════════════════════════════╝
    """)

    cam = RobotVision()

    try:
        print("Test 1: Taking a photo...")
        photo = cam.capture("test_photo.jpg")

        if photo and os.path.exists(photo):
            print(f"✅ Photo saved to: {photo}")

            print("\nTest 2: Detecting faces...")
            faces = cam.detect_faces()
            print(f"   Faces found: {len(faces)}")

            print("\nTest 3: Scene description...")
            desc = cam.describe_scene()
            print(f"   Description: {desc}")
        else:
            print("❌ Camera not available (run on Pi 5 with camera connected)")

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        cam.cleanup()