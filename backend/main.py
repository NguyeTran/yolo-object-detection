import io
import base64
import time
import numpy as np
import cv2
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO
from prometheus_fastapi_instrumentator import Instrumentator

# 1. Khởi tạo lifespan trước
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Đang khởi tạo mô hình YOLOv8n...")
    ml_models["yolo"] = YOLO("yolov8n.pt")
    yield
    ml_models.clear()

# 2. Khởi tạo app DUY NHẤT (bao gồm lifespan và title)
app = FastAPI(title="YOLO Detection API", lifespan=lifespan)
ml_models = {}

# 3. Gắn "ống nghe" vào đúng đối tượng app này
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 4. Middleware CORS (Thêm link Render vào danh sách allow_origins sau này)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tạm thời để * để test, sau này nên thay bằng domain chính thức
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI server is running!"}

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
