import io
from fastapi.testclient import TestClient
from PIL import Image
from main import app

def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "FastAPI server is running!"}

def test_detect_image_invalid_type():
    with TestClient(app) as client:
        files = {"file": ("test.txt", b"Day la file text", "text/plain")}
        response = client.post("/api/detect/image", files=files)
        assert response.status_code == 400
        assert "Chỉ hỗ trợ file JPG, JPEG hoặc PNG" in response.json()["detail"]

def test_detect_image_success():
    with TestClient(app) as client:
        # Tạo ảnh giả lập màu đỏ 100x100 pixels
        image = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        files = {"file": ("test.jpg", img_byte_arr, "image/jpeg")}
        response = client.post("/api/detect/image", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "object_count" in data
        assert "detections" in data

def test_detect_image_find_dog():
    with TestClient(app) as client:
        try:
            with open("sample_dog.jpg", "rb") as image_file:
                files = {"file": ("sample_dog.jpg", image_file, "image/jpeg")}
                response = client.post("/api/detect/image", files=files)
        except FileNotFoundError:
            assert False, "Không tìm thấy file sample_dog.jpg"
        
    
        assert response.status_code == 200
        data = response.json()
        
        detected_classes = [item["detected_class"] for item in data["detections"]]
        
        assert "dog" in detected_classes, f"Test thất bại: Không tìm thấy chó! YOLO chỉ thấy: {detected_classes}"
