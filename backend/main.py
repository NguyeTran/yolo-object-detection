import io
import base64
import time
import numpy as np
import cv2
import subprocess
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO
from prometheus_fastapi_instrumentator import Instrumentator
import os
import uuid
import tempfile
from pathlib import Path
from collections import Counter

ml_models = {}

# 1. Khởi tạo lifespan trước
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Đang khởi tạo mô hình YOLOv8n...")
    ml_models["yolo"] = YOLO("yolov8n.pt")
    yield
    ml_models.clear()

# 2. Khởi tạo app DUY NHẤT (bao gồm lifespan và title)
app = FastAPI(title="YOLO Detection API", lifespan=lifespan)

# 3. Gắn "ống nghe" vào đúng đối tượng app này
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 4. Middleware CORS (Thêm link Render của bạn vào danh sách allow_origins sau này)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tạm thời để * để test, sau này nên thay bằng domain chính thức
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Result directory
BASE_DIR = Path(__file__).resolve().parent

RESULT_DIR = BASE_DIR / "results"

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# 6. Save processed video
@app.get("/api/results/{filename}")
def get_result_video(filename: str):

    file_path = RESULT_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Result video not found."
        )

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )

# 7. Video upload limit
MAX_VIDEO_SIZE = 50 * 1024 * 1024      # 50 MB
MAX_VIDEO_DURATION = 30                # 30 seconds

# 8. Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI server is running!"}

# 9. Detect image endpoint
@app.post("/api/detect/image")
async def detect_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ file JPG, JPEG hoặc PNG"
        )

    start_time = time.time()

    # Đọc file ảnh
    image_bytes = await file.read()

    # Chuyển bytes -> PIL Image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # YOLO detection
    results = ml_models["yolo"](image)

    # Lấy kết quả đầu tiên
    result = results[0]

    # ==============================
    # Lấy thông tin detection
    # ==============================

    detections = []

    for box in result.boxes:

        coords = box.xyxy[0].tolist()

        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]

        confidence = box.conf[0].item()

        detections.append({
            "detected_class": class_name,
            "confidence_score": round(confidence, 2),
            "bounding_box": [
                round(c, 1) for c in coords
            ]
        })

    # ==============================
    # Vẽ bounding box màu đỏ
    # ==============================

    # PIL -> NumPy
    annotated_image = np.array(image)

    # RGB -> BGR để OpenCV xử lý
    annotated_image = cv2.cvtColor(
    annotated_image,
    cv2.COLOR_RGB2BGR
    )

    for box in result.boxes:

        coords = box.xyxy[0].tolist()

        x1, y1, x2, y2 = map(int, coords)

        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]

        confidence = box.conf[0].item()

        # Vẽ bounding box màu đỏ
        cv2.rectangle(
            annotated_image,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            3
        )

        # Tên class + confidence
        label = f"{class_name} {confidence:.2f}"

        cv2.putText(
            annotated_image,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )

    # BGR -> RGB
    annotated_image = cv2.cvtColor(
        annotated_image,
        cv2.COLOR_BGR2RGB
    )

    # NumPy -> PIL
    annotated_image = Image.fromarray(annotated_image)

    # ==============================
    # Chuyển ảnh thành Base64
    # ==============================

    buffer = io.BytesIO()

    annotated_image.save(
        buffer,
        format="JPEG",
        quality=90
    )

    image_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    process_time = time.time() - start_time

    # ==============================
    # Trả JSON
    # ==============================

    return {
        "filename": file.filename,
        "object_count": len(detections),
        "processing_time_seconds": round(process_time, 3),
        "detections": detections,

        # Ảnh đã được YOLO vẽ bounding box
        "annotated_image": image_base64
    }

# 10. Detect video endpoint
@app.post("/api/detect/video")
async def detect_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Không có file video."
        )

    extension = Path(file.filename).suffix.lower()

    if extension != ".mp4":
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ video MP4."
        )

    if file.content_type not in [
        "video/mp4",
        "application/mp4",
        "video/mpeg"
    ]:
        raise HTTPException(
            status_code=400,
            detail="File phải là video MP4."
        )

    temp_path = None

    try:

        # Lưu video tạm thời để xử lý
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4"
        ) as temp_file:

            temp_path = temp_file.name

            total_size = 0

            while True:

                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                # Check size
                if total_size > MAX_VIDEO_SIZE:

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Video quá lớn. "
                            "Giới hạn là 50 MB."
                        )
                    )

                temp_file.write(chunk)

        # Mở video bằng OpenCV
        cap = cv2.VideoCapture(temp_path)

        if not cap.isOpened():

            raise HTTPException(
                status_code=400,
                detail=(
                    "Không thể mở video."
                )
            )

        success, first_frame = cap.read()

        if not success:
            cap.release()

            raise HTTPException(
                status_code=400,
                detail="Không thể đọc frame đầu tiên của video."
            )

        height, width = first_frame.shape[:2]

        # Lấy thông tin video
        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 0:
            fps = 30.0

        total_frames = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        # Tính thời lượng video
        duration = 0

        if total_frames > 0:
            duration = (total_frames / fps)

        if duration > MAX_VIDEO_DURATION:
            cap.release()
            raise HTTPException(
                status_code=400,
                detail=(
                    "Video quá dài. "
                    "Giới hạn là 30 giây."
                )
            )

        print("================================")
        print("VIDEO INFO")
        print("WIDTH:", width)
        print("HEIGHT:", height)
        print("FPS:", fps)
        print("TOTAL FRAMES:", total_frames)
        print("================================")

        # Tạo tên file output duy nhất
        output_id = uuid.uuid4().hex

        raw_output_path = (RESULT_DIR / f"{output_id}_raw.mp4")

        output_filename = (f"{output_id}.mp4")

        output_path = (RESULT_DIR / output_filename)

        # Tạo VideoWriter để lưu video output
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        writer = cv2.VideoWriter(
            str(raw_output_path),
            fourcc,
            fps,
            (width, height)
        )

        print("WRITER OPENED:", writer.isOpened())

        if not writer.isOpened():
            cap.release()
            raise HTTPException(
                status_code=500,
                detail=(
                    "Không thể tạo video output."
                )
            )

        # Process video frame by frame
        model = ml_models["yolo"]

        class_counts = Counter()

        frames_processed = 0
        frames_written = 0

        start_time = time.time()

        max_frames = int(
            MAX_VIDEO_DURATION * fps
        )

        while True:

            if frames_processed == 0:
                frame = first_frame
                success = True

            else:
                success, frame = cap.read()
            
            if not success:
                break

            if frames_processed >= max_frames:
                break
                
            # YOLO detection
            results = model(frame , verbose=False)

            result = results[0]

            # Count detected classes
            for box in result.boxes:

                class_id = int(
                    box.cls[0].item()
                )

                class_name = (
                    result.names[class_id]
                )

                class_counts[
                    class_name
                ] += 1

            # Vẽ bounding box lên frame
            annotated_frame = result.plot(
                    conf=True,
                    labels=True,
                    boxes=True
                )

            if (
                annotated_frame.shape[1] != width
                or annotated_frame.shape[0] != height
            ):

                annotated_frame = cv2.resize(
                    annotated_frame,
                    (width, height)
                )

            # Write annotated frame to output video
            writer.write(annotated_frame)

            if frames_written == 0:
                print("FIRST FRAME WILL BE WRITTEN")
                print("FRAME SHAPE:", annotated_frame.shape)
                print("FRAME TYPE:", annotated_frame.dtype)

            frames_processed += 1
            frames_written += 1

        # Release resources
        cap.release()
        writer.release()

        print("FRAMES PROCESSED:", frames_processed)
        print("FRAMES WRITTEN:", frames_written)
        print("RAW VIDEO PATH:", raw_output_path.resolve())
        print("RAW VIDEO EXISTS:", raw_output_path.exists())

        if raw_output_path.exists():
            print(
                "RAW VIDEO SIZE:",
                raw_output_path.stat().st_size
            )

        if not raw_output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="OpenCV failed to create the raw output video."
            )

        if raw_output_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500,
                detail="Raw video was created but is empty."
            )

        if frames_written == 0:
            raise HTTPException(
                status_code=400,
                detail="No frames were written."
            )
        
        try:

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",

                    "-i",
                    str(raw_output_path.resolve()),

                    "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2",

                    "-c:v",
                    "libx264",

                    "-preset",
                    "veryfast",

                    "-pix_fmt",
                    "yuv420p",

                    "-movflags",
                    "+faststart",

                    str(output_path.resolve())
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        except FileNotFoundError:

            raise HTTPException(
                status_code=500,
                detail="FFmpeg is not installed."
            )

        except subprocess.CalledProcessError as error:

            print("FFmpeg ERROR:")
            print(error.stderr)
            
            if raw_output_path.exists():
                raw_output_path.unlink()

            raise HTTPException(
                status_code=500,
                detail="Failed to convert output video to H.264."
            )

        finally:

            if raw_output_path.exists():
                raw_output_path.unlink()

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Output H.264 video was not created."
            )
        
        process_time = (time.time() - start_time)

        processed_duration = (frames_processed / fps)

        # Trả JSON response
        return {

            "filename": file.filename,

            "message": (
                "Video processed successfully."
            ),

            "video_url": (
                f"/api/results/"
                f"{output_filename}"
            ),

            "summary_counts": dict(
                class_counts
            ),

            "frames_processed":
                frames_processed,

            "fps": round(
                fps,
                2
            ),

            "duration_seconds": round(
                processed_duration,
                2
            ),

            "processing_time_seconds": round(
                process_time,
                3
            )
        }

    finally:

        # Xóa file tạm thời nếu tồn tại
        if (temp_path and os.path.exists(temp_path)):
            os.remove(temp_path)
