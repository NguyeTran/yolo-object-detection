import io
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO
import time
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

# 4. Middleware CORS (Thêm link Render của bạn vào danh sách allow_origins sau này)
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
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JPG, JPEG hoặc PNG")

    start_time = time.time()
    
    # 1. Đọc file ảnh dưới dạng byte
    image_bytes = await file.read()
    
    # 2. Chuyển byte thành định dạng ảnh PIL mà YOLO có thể đọc được
    image = Image.open(io.BytesIO(image_bytes))
    
    # 3. Đưa ảnh qua mô hình YOLO để nhận diện
    results = ml_models["yolo"](image)
    
    # YOLO trả về một list kết quả (vì có thể truyền nhiều ảnh), ta lấy ảnh đầu tiên
    result = results[0]
    
    # 4. Trích xuất siêu dữ liệu (metadata)
    detections = []
    for box in result.boxes:
        # Tọa độ khung [x_min, y_min, x_max, y_max]
        coords = box.xyxy[0].tolist()
        
        # Lớp vật thể và độ tin cậy
        class_id = int(box.cls[0].item())
        class_name = result.names[class_id]
        confidence = box.conf[0].item()
        
        detections.append({
            "detected_class": class_name,
            "confidence_score": round(confidence, 2),
            "bounding_box": [round(c, 1) for c in coords]
        })
    
    process_time = time.time() - start_time
    
    # 5. Trả về kết quả JSON
    return {
        "filename": file.filename,
        "object_count": len(detections),
        "processing_time_seconds": round(process_time, 3),
        "detections": detections
    }