import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import io
import base64
import time
import threading
import subprocess
import uuid
import tempfile
from pathlib import Path
from collections import Counter
from contextlib import asynccontextmanager

import numpy as np
import cv2
import torch
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator
from ultralytics import YOLO

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
cv2.setNumThreads(1)

# ==============================
# Config (override via env vars on Render)
# ==============================
MAX_VIDEO_SIZE = int(os.getenv("MAX_VIDEO_SIZE_MB", 20)) * 1024 * 1024   # default 20 MB
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION", 15))            # default 15s
FRAME_SKIP = int(os.getenv("FRAME_SKIP", 4))                             # infer every Nth frame
INFER_IMGSZ = int(os.getenv("INFER_IMGSZ", 320))                         # smaller = faster on CPU

# ==============================
# Model (loaded once at startup, protected by a lock)
# ==============================
model = None
model_lock = threading.Lock()


def load_model():
    global model
    if model is None:
        print("Đang khởi tạo mô hình YOLOv8n...")
        model = YOLO("yolov8n.pt")
        print("YOLOv8n đã sẵn sàng.")
    return model

def warmup_model():
    """
    Chạy 1 lần inference "giả" trên ảnh đen lúc startup.
    Lần inference đầu tiên của PyTorch/YOLO luôn chậm hơn hẳn các lần sau
    (phải khởi tạo kernel/graph nội bộ). Làm việc này lúc startup thay vì
    để user đầu tiên phải gánh chi phí đó.
    """
    m = load_model()
    dummy = np.zeros((INFER_IMGSZ, INFER_IMGSZ, 3), dtype=np.uint8)
    m(dummy, imgsz=INFER_IMGSZ, verbose=False)
    print("Model đã warm-up xong.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload model once when the container starts, not on the first request.
    load_model()
    yield
    # (no teardown needed)

# Khởi tạo FastAPI app với lifespan để preload model
app = FastAPI(title="YOLO Detection API", lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: thay bằng domain frontend thật khi deploy production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
RESULT_DIR = BASE_DIR / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/results/{filename}")
def get_result_video(filename: str):
    file_path = RESULT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Result video not found.")
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI server is running!"}


@app.post("/api/detect/image")
def detect_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JPG, JPEG hoặc PNG")

    start_time = time.time()
    image_bytes = file.file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    with model_lock:
        m = load_model()
        results = m(image, imgsz=INFER_IMGSZ)

    # Lấy kết quả từ frame đầu tiên (chỉ có 1 frame cho ảnh)
    result = results[0]
    detections = []
    for box in result.boxes:
        coords = box.xyxy[0].tolist()
        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]
        confidence = box.conf[0].item()
        detections.append({
            "detected_class": class_name,
            "confidence_score": round(confidence, 2),
            "bounding_box": [round(c, 1) for c in coords],
        })

    # Chuyển đổi ảnh sang BGR để vẽ bounding box bằng OpenCV
    annotated_image = np.array(image)
    annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

    # Vẽ bounding box và label lên ảnh
    for box in result.boxes:
        coords = box.xyxy[0].tolist()
        x1, y1, x2, y2 = map(int, coords)
        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]
        confidence = box.conf[0].item()

        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"{class_name} {confidence:.2f}"
        cv2.putText(
            annotated_image, label, (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
        )

    annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
    annotated_image = Image.fromarray(annotated_image)

    # Chuyển đổi ảnh đã annotate sang base64 để trả về JSON
    buffer = io.BytesIO()
    annotated_image.save(buffer, format="JPEG", quality=90)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    process_time = time.time() - start_time

    return {
        "filename": file.filename,
        "object_count": len(detections),
        "processing_time_seconds": round(process_time, 3),
        "detections": detections,
        "annotated_image": image_base64,
    }


@app.post("/api/detect/video")
def detect_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có file video.")

    extension = Path(file.filename).suffix.lower()
    if extension != ".mp4":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ video MP4.")

    if file.content_type not in ["video/mp4", "application/mp4", "video/mpeg"]:
        raise HTTPException(status_code=400, detail="File phải là video MP4.")

    temp_path = None
    cap = None
    writer = None
    raw_output_path = None

    try:
        # --- Lưu video tạm thời ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_path = temp_file.name
            total_size = 0
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_VIDEO_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video quá lớn. Giới hạn là {MAX_VIDEO_SIZE // (1024*1024)} MB.",
                    )
                temp_file.write(chunk)

        cap = cv2.VideoCapture(temp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Không thể mở video.")

        success, first_frame = cap.read()
        if not success:
            raise HTTPException(status_code=400, detail="Không thể đọc frame đầu tiên của video.")

        height, width = first_frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = (total_frames / fps) if total_frames > 0 else 0

        if duration > MAX_VIDEO_DURATION:
            raise HTTPException(
                status_code=400,
                detail=f"Video quá dài. Giới hạn là {MAX_VIDEO_DURATION} giây.",
            )

        output_id = uuid.uuid4().hex
        raw_output_path = RESULT_DIR / f"{output_id}_raw.mp4"
        output_filename = f"{output_id}.mp4"
        output_path = RESULT_DIR / output_filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(raw_output_path), fourcc, fps, (width, height))
        if not writer.isOpened():
            raise HTTPException(status_code=500, detail="Không thể tạo video output.")

        class_counts = Counter()
        frames_processed = 0
        frames_written = 0
        start_time = time.time()
        max_frames = int(MAX_VIDEO_DURATION * fps)

        last_annotated_frame = None

        while True:
            if frames_processed == 0:
                frame = first_frame
                success = True
            else:
                success, frame = cap.read()

            if not success or frames_processed >= max_frames:
                break

            # Chỉ chạy YOLO trên mỗi FRAME_SKIP frame để giảm tải CPU trên Render free.
            # Các frame bị skip dùng lại kết quả (bounding box) của frame gần nhất
            # để video output không bị "giật" mất box.
            run_inference = (frames_processed % FRAME_SKIP == 0) or (last_annotated_frame is None)

            if run_inference:
                with model_lock:
                    m = load_model()
                    results = m(frame, imgsz=INFER_IMGSZ, verbose=False)
                result = results[0]

                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = result.names[class_id]
                    class_counts[class_name] += 1

                annotated_frame = result.plot(conf=True, labels=True, boxes=True)

                if annotated_frame.shape[1] != width or annotated_frame.shape[0] != height:
                    annotated_frame = cv2.resize(annotated_frame, (width, height))

                last_annotated_frame = annotated_frame
            else:
                annotated_frame = last_annotated_frame

            writer.write(annotated_frame)
            frames_processed += 1
            frames_written += 1

        cap.release()
        writer.release()
        cap = None
        writer = None

        if not raw_output_path.exists() or raw_output_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="OpenCV failed to create a valid raw output video.")

        if frames_written == 0:
            raise HTTPException(status_code=400, detail="No frames were written.")

        # --- Convert sang H.264 để trình duyệt phát được ---
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(raw_output_path.resolve()),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(output_path.resolve()),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="FFmpeg is not installed trên server.")
        except subprocess.CalledProcessError as error:
            print("FFmpeg ERROR:", error.stderr)
            raise HTTPException(status_code=500, detail="Failed to convert output video to H.264.")
        finally:
            if raw_output_path.exists():
                raw_output_path.unlink()

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Output H.264 video was not created.")

        process_time = time.time() - start_time
        processed_duration = frames_processed / fps

        return {
            "filename": file.filename,
            "message": "Video processed successfully.",
            "video_url": f"/api/results/{output_filename}",
            "summary_counts": dict(class_counts),
            "frames_processed": frames_processed,
            "fps": round(fps, 2),
            "duration_seconds": round(processed_duration, 2),
            "processing_time_seconds": round(process_time, 3),
        }

    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()
        if raw_output_path is not None and raw_output_path.exists():
            raw_output_path.unlink()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)