import os
from fastapi.testclient import TestClient
from main import app

def test_detect_specific_object_accuracy():
    # 1. Khai báo file
    image_path = "sample_dog.jpg"
    assert os.path.exists(image_path), f"Lỗi: Không tìm thấy file {image_path} để test!"

    # 2. QUAN TRỌNG: Mở Client bằng 'with' để bắt buộc FastAPI khởi động mô hình AI
    with TestClient(app) as client:
        with open(image_path, "rb") as f:
            response = client.post(
                "/api/detect/image",
                files={"file": ("sample_dog.jpg", f, "image/jpeg")}
            )

    # 3. Kiểm tra kết quả
    assert response.status_code == 200
    data = response.json()
    
    detected_classes = [obj["detected_class"] for obj in data["detections"]]
    assert "dog" in detected_classes, f"YOLO nhận diện SAI! Không thấy chó đâu, chỉ thấy: {detected_classes}"   