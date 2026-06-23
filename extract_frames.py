import cv2
import os

cap = cv2.VideoCapture(r'c:\ee200_q3\EE200_finalproject_2026_demo_video.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs(r'c:\ee200_q3\frames', exist_ok=True)

# Capture frames every ~5 seconds
sample_times = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
for t in sample_times:
    frame_idx = int(t * fps)
    if frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(fr'c:\ee200_q3\frames\frame_{t:03d}s.jpg', frame)
            print(f"Saved frame at {t}s")

cap.release()
print("Done!")
