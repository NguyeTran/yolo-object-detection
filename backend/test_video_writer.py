import cv2
from pathlib import Path

video_path = "sample_video.mp4"
output_path = "test_output.mp4"

cap = cv2.VideoCapture(video_path)

print("CAP OPENED:", cap.isOpened())

fps = cap.get(cv2.CAP_PROP_FPS)

success, frame = cap.read()

print("FIRST FRAME:", success)

if not success:
    cap.release()
    raise SystemExit("Cannot read first frame")

height, width = frame.shape[:2]

print("WIDTH:", width)
print("HEIGHT:", height)
print("FPS:", fps)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    output_path,
    fourcc,
    fps if fps > 0 else 25,
    (width, height)
)

print("WRITER OPENED:", writer.isOpened())

if not writer.isOpened():
    cap.release()
    raise SystemExit("VideoWriter cannot be opened")

while True:

    success, frame = cap.read()

    if not success:
        break

    writer.write(frame)

cap.release()
writer.release()

print("OUTPUT EXISTS:", Path(output_path).exists())

if Path(output_path).exists():
    print(
        "OUTPUT SIZE:",
        Path(output_path).stat().st_size
    )