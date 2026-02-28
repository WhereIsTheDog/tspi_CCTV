"""
CCTV Monitor GUI Application
Full-screen 2x2 grid display for 4 video streams.
Supports hardware-accelerated decoding (CUDA, OpenCL/Mali, MPP/RK3566, VAAPI, DXVA).
Auto-reconnects when a stream drops.
"""
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import platform
from datetime import datetime
import os
import subprocess
import pytz


class CCTVMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Monitor")

        # Full-screen setup
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', self.exit_fullscreen)   # ESC exits fullscreen
        self.root.bind('<F11>', self.toggle_fullscreen)    # F11 toggles fullscreen

        # Screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Background colour
        self.root.configure(bg='#1a1a1a')

        # Detect hardware-acceleration support
        self.gpu_available = self.check_gpu_support()
        self.use_hardware_decode = True

        print("=== Hardware Acceleration Status ===")
        print(f"CUDA:          {self.gpu_available['cuda']}")
        print(f"OpenCL (Mali): {self.gpu_available['opencl']}")
        print(f"HW Decode:     {self.gpu_available['hw_decode']}")
        print(f"RK3566:        {self.gpu_available['rk3566']}")
        print(f"MPP:           {self.gpu_available['mpp']}")
        print(f"HW Type:       {self.gpu_available['hw_type']}")
        print(f"Platform:      {platform.system()}")
        print("====================================")

        # RTSP stream URLs — edit these to match your cameras
        self.video_sources = [
            "rtsp://admin:QMXEVX@192.168.95.247:554/h264/ch1/main/av_stream",  # Camera 1
            "",              # Camera 2
            "",              # Camera 3
            ""               # Camera 4
        ]

        # State
        self.captures = [None, None, None, None]
        self.frames = [None, None, None, None]
        self.connection_status = ["Connecting...", "Connecting...", "No Signal", "No Signal"]
        self.running = True

        # Auto-reconnect settings
        self.auto_reconnect = True
        self.reconnect_delay = 3          # seconds between reconnect attempts
        self.frame_timeout = 10           # seconds without a frame = disconnected
        self.last_frame_time = [time.time()] * 4

        # CUDA GPU frame buffers (only used when CUDA is available)
        self.gpu_frames = [None, None, None, None] if self.gpu_available['cuda'] else None

        # Build UI
        self.create_ui()

        # Start per-camera capture threads
        self.start_video_threads()

        # Start periodic UI refresh
        self.update_ui()

        # Start clock update
        self.update_time()

    # ------------------------------------------------------------------
    # Hardware detection
    # ------------------------------------------------------------------

    def check_gpu_support(self):
        """Detect available hardware-acceleration backends."""
        gpu_info = {
            'cuda': False,
            'opencl': False,
            'hw_decode': False,
            'cuda_device_count': 0,
            'mpp': False,
            'rk3566': False,
            'hw_type': 'none'
        }

        # OpenCL (Mali GPU, etc.)
        try:
            if cv2.ocl.haveOpenCL():
                cv2.ocl.setUseOpenCL(True)
                gpu_info['opencl'] = True
                print("OpenCL detected (Mali GPU)")
                if not gpu_info['cuda']:
                    gpu_info['hw_type'] = 'opencl'
        except Exception as e:
            print(f"OpenCL detection failed: {e}")

        # CUDA (NVIDIA)
        try:
            if hasattr(cv2, 'cuda') and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                gpu_info['cuda'] = True
                gpu_info['cuda_device_count'] = cv2.cuda.getCudaEnabledDeviceCount()
                gpu_info['hw_type'] = 'cuda'
                print(f"CUDA detected: {gpu_info['cuda_device_count']} device(s)")
        except Exception as e:
            print(f"CUDA detection failed: {e}")

        # RK3566 / MPP (Linux only)
        if platform.system() == 'Linux':
            try:
                if os.path.exists('/proc/device-tree/compatible'):
                    with open('/proc/device-tree/compatible', 'r') as f:
                        compatible = f.read()
                        if 'rk3566' in compatible.lower():
                            gpu_info['rk3566'] = True
                            gpu_info['hw_type'] = 'mpp'
                            print("RK3566 platform detected")

                # Check for mpp_info_test utility
                try:
                    result = subprocess.run(['which', 'mpp_info_test'],
                                            capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        gpu_info['mpp'] = True
                        print("MPP library detected (mpp_info_test)")
                except Exception as e:
                    print(f"MPP tool check: {e}")

                # Check MPP device node
                if os.path.exists('/dev/mpp_service'):
                    gpu_info['mpp'] = True
                    print("MPP device node /dev/mpp_service detected")

                if gpu_info['rk3566'] or gpu_info['mpp']:
                    gpu_info['hw_decode'] = True
                    gpu_info['hw_type'] = 'mpp'
                else:
                    gpu_info['hw_decode'] = True
                    gpu_info['hw_type'] = 'vaapi'

            except Exception as e:
                print(f"RK3566/MPP detection failed: {e}")

        # Windows DXVA
        try:
            if platform.system() == 'Windows':
                gpu_info['hw_decode'] = True
                gpu_info['hw_type'] = 'dxva'
        except Exception as e:
            print(f"Hardware-decode detection failed: {e}")

        return gpu_info

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def create_ui(self):
        """Build the main user interface."""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        main_container = tk.Frame(self.root, bg='#1a1a1a')
        main_container.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        main_container.grid_rowconfigure(0, weight=0)   # title bar — fixed height
        main_container.grid_rowconfigure(1, weight=1)   # video area — fills remainder
        main_container.grid_columnconfigure(0, weight=1)

        # ---- Title bar ----
        title_frame = tk.Frame(main_container, bg='#2a2a2a', height=50)
        title_frame.grid(row=0, column=0, sticky='ew', padx=0, pady=(0, 10))
        title_frame.grid_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="CCTV Monitor",
            font=('Arial', 20, 'bold'),
            bg='#2a2a2a',
            fg='white'
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # China time (green)
        self.china_time_label = tk.Label(
            title_frame,
            text="",
            font=('Arial', 14),
            bg='#2a2a2a',
            fg='#00ff00'
        )
        self.china_time_label.pack(side=tk.LEFT, padx=20, pady=10)

        # UK time (blue)
        self.uk_time_label = tk.Label(
            title_frame,
            text="",
            font=('Arial', 14),
            bg='#2a2a2a',
            fg='#00bfff'
        )
        self.uk_time_label.pack(side=tk.LEFT, padx=20, pady=10)

        # Quit button
        exit_btn = tk.Button(
            title_frame,
            text="Quit",
            font=('Arial', 12),
            bg='#d32f2f',
            fg='white',
            command=self.close_application,
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        exit_btn.pack(side=tk.RIGHT, padx=20, pady=10)

        # ---- 2x2 video grid ----
        video_container = tk.Frame(main_container, bg='#1a1a1a')
        video_container.grid(row=1, column=0, sticky='nsew')

        video_container.grid_rowconfigure(0, weight=1, minsize=0)
        video_container.grid_rowconfigure(1, weight=1, minsize=0)
        video_container.grid_columnconfigure(0, weight=1, minsize=0)
        video_container.grid_columnconfigure(1, weight=1, minsize=0)

        self.video_labels = []
        camera_names = ["Camera 1", "Camera 2", "Camera 3", "Camera 4"]

        for i in range(4):
            row = i // 2
            col = i % 2

            camera_frame = tk.Frame(
                video_container,
                bg='#2a2a2a',
                highlightbackground='#444444',
                highlightthickness=2
            )
            camera_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            camera_frame.grid_propagate(False)

            camera_frame.grid_rowconfigure(0, weight=0)   # camera label — fixed
            camera_frame.grid_rowconfigure(1, weight=1)   # video area — fills
            camera_frame.grid_columnconfigure(0, weight=1)

            name_label = tk.Label(
                camera_frame,
                text=camera_names[i],
                font=('Arial', 14, 'bold'),
                bg='#2a2a2a',
                fg='white'
            )
            name_label.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

            video_frame = tk.Frame(camera_frame, bg='#000000')
            video_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=(0, 5))
            video_frame.grid_propagate(False)

            video_frame.grid_rowconfigure(0, weight=1)
            video_frame.grid_columnconfigure(0, weight=1)

            video_label = tk.Label(
                video_frame,
                bg='#000000',
                text=self.connection_status[i],
                font=('Arial', 16),
                fg='#666666',
                anchor='center'
            )
            video_label.grid(row=0, column=0, sticky='nsew')

            self.video_labels.append(video_label)

    # ------------------------------------------------------------------
    # Video capture
    # ------------------------------------------------------------------

    def capture_video(self, index):
        """
        Per-camera capture thread.
        Continuously reads frames and automatically reconnects if the stream drops.
        """
        source = self.video_sources[index]

        if source is None:
            self.connection_status[index] = "No Signal"
            return

        reconnect_count = 0

        while self.running:
            cap = None
            try:
                if reconnect_count == 0:
                    self.connection_status[index] = "Connecting..."
                else:
                    self.connection_status[index] = f"Reconnecting... (attempt {reconnect_count})"

                print(f"Camera {index + 1}: connecting (attempt {reconnect_count + 1})")

                # Open stream — prefer MPP hardware decode on RK3566
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)

                if self.gpu_available['mpp'] or self.gpu_available['rk3566']:
                    # Enable MPP hardware-accelerated decode via FFmpeg backend
                    cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
                    cap.set(cv2.CAP_PROP_HW_DEVICE, 0)
                    print(f"Camera {index + 1}: MPP hardware decode requested")

                if self.use_hardware_decode and self.gpu_available['hw_decode']:
                    try:
                        hw = self.gpu_available['hw_type']
                        if hw in ('mpp', 'vaapi', 'dxva'):
                            cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
                            print(f"Camera {index + 1}: HW decode enabled ({hw.upper()})")
                    except Exception as e:
                        print(f"Camera {index + 1}: HW decode setup failed: {e}")

                # Buffer and frame-rate hints
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 25)

                if not cap.isOpened():
                    print(f"Camera {index + 1}: failed to open, retrying in {self.reconnect_delay}s")
                    self.connection_status[index] = "Connection failed — retrying..."
                    reconnect_count += 1
                    time.sleep(self.reconnect_delay)
                    continue

                print(f"Camera {index + 1}: connected")
                self.connection_status[index] = "Connected"
                self.captures[index] = cap
                reconnect_count = 0
                self.last_frame_time[index] = time.time()

                consecutive_failures = 0
                max_consecutive_failures = 10

                while self.running:
                    ret, frame = cap.read()

                    if not ret:
                        consecutive_failures += 1
                        print(f"Camera {index + 1}: read failed ({consecutive_failures} consecutive)")

                        if consecutive_failures >= max_consecutive_failures:
                            print(f"Camera {index + 1}: stream lost — will reconnect")
                            self.connection_status[index] = "Disconnected — reconnecting..."
                            break

                        time.sleep(0.1)
                        continue

                    consecutive_failures = 0
                    self.frames[index] = frame.copy()
                    self.last_frame_time[index] = time.time()

                    time.sleep(0.033)   # ~30 fps

                # Release the dead capture object
                if cap is not None:
                    cap.release()
                    self.captures[index] = None

            except Exception as e:
                print(f"Camera {index + 1}: error — {e}")
                self.connection_status[index] = f"Error: {str(e)[:30]}"
                reconnect_count += 1

                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    self.captures[index] = None

                if self.running and self.auto_reconnect:
                    print(f"Camera {index + 1}: reconnecting in {self.reconnect_delay}s")
                    time.sleep(self.reconnect_delay)

            if not self.auto_reconnect:
                break

        # Thread cleanup
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        self.captures[index] = None
        self.frames[index] = None
        print(f"Camera {index + 1}: thread stopped")

    def start_video_threads(self):
        """Launch one capture thread per camera."""
        for i in range(4):
            if self.video_sources[i] is not None:
                t = threading.Thread(target=self.capture_video, args=(i,), daemon=True)
                t.start()

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def resize_with_aspect_ratio(self, frame, target_width, target_height):
        """
        Scale a frame to fit target_width x target_height while preserving aspect ratio.
        Letterbox (black bars) fill any remaining space.
        Uses GPU acceleration when available:
          - CUDA  → cv2.cuda
          - OpenCL / Mali → cv2.UMat
          - Fallback → CPU
        """
        h, w = frame.shape[:2]
        scale = min(target_width / w, target_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        if self.gpu_available['cuda']:
            try:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                gpu_resized = cv2.cuda.resize(gpu_frame, (new_w, new_h))
                resized = gpu_resized.download()
            except Exception as e:
                print(f"CUDA resize failed, falling back to CPU: {e}")
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        elif self.gpu_available['opencl']:
            try:
                frame_umat = cv2.UMat(frame)
                resized_umat = cv2.resize(frame_umat, (new_w, new_h), interpolation=cv2.INTER_AREA)
                resized = cv2.UMat.get(resized_umat)
            except Exception as e:
                print(f"OpenCL resize failed, falling back to CPU: {e}")
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Place the resized frame in the centre of a black canvas
        canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        x_offset = (target_width - new_w) // 2
        y_offset = (target_height - new_h) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    # ------------------------------------------------------------------
    # UI update loops
    # ------------------------------------------------------------------

    def update_ui(self):
        """Refresh all camera panels at ~30 fps."""
        if not self.running:
            return

        for i in range(4):
            if self.frames[i] is not None:
                try:
                    lw = self.video_labels[i].winfo_width()
                    lh = self.video_labels[i].winfo_height()

                    if lw > 1 and lh > 1:
                        frame = self.resize_with_aspect_ratio(self.frames[i], lw, lh)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        img_tk = ImageTk.PhotoImage(image=img)
                        self.video_labels[i].configure(image=img_tk, text="")
                        self.video_labels[i].image = img_tk   # keep reference

                except Exception as e:
                    print(f"Camera {i + 1}: display update error — {e}")
            else:
                try:
                    self.video_labels[i].configure(
                        image='',
                        text=self.connection_status[i],
                        font=('Arial', 16),
                        fg='#666666'
                    )
                    self.video_labels[i].image = None
                except Exception as e:
                    print(f"Camera {i + 1}: status display error — {e}")

        self.root.after(33, self.update_ui)   # ~30 fps

    def update_time(self):
        """Update the China/UK clock labels once per second."""
        if not self.running:
            return

        china_tz = pytz.timezone('Asia/Shanghai')
        uk_tz = pytz.timezone('Europe/London')
        utc_now = datetime.now(pytz.utc)

        china_time = utc_now.astimezone(china_tz)
        uk_time = utc_now.astimezone(uk_tz)

        self.china_time_label.config(
            text="CN  " + china_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        self.uk_time_label.config(
            text="UK  " + uk_time.strftime('%Y-%m-%d %H:%M:%S')
        )

        self.root.after(1000, self.update_time)

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode."""
        self.root.attributes('-fullscreen', False)

    def close_application(self):
        """Cleanly shut down the application."""
        self.running = False

        for cap in self.captures:
            if cap is not None:
                cap.release()

        self.root.quit()
        self.root.destroy()


def main():
    """Entry point."""
    root = tk.Tk()
    app = CCTVMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.close_application)
    root.mainloop()


if __name__ == "__main__":
    main()
