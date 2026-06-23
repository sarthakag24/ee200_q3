import cv2
import os

cap = cv2.VideoCapture(r'c:\ee200_q3\EE200_finalproject_2026_demo_video.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs(r'c:\ee200_q3\frames2', exist_ok=True)

# Capture frames every ~2 seconds between 18-35s to see the full identify result
sample_times = [18, 20, 22, 24, 26, 28, 30, 32, 34]
for t in sample_times:
    frame_idx = int(t * fps)
    if frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(fr'c:\ee200_q3\frames2\frame_{t:03d}s.jpg', frame)
            print(f"Saved frame at {t}s")

cap.release()
print("Done!")
