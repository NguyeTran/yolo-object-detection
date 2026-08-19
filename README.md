# 🚀 YOLO Object Detection Backend & Cloud Deployment

Hệ thống API nhận diện vật thể sử dụng **YOLOv8** và **FastAPI**, được đóng gói bằng **Docker**, triển khai trên **Render Cloud** và tích hợp hệ thống giám sát thời gian thực với **Prometheus & Grafana**.

---

## 🏗️ 1. Kiến trúc tổng quan
Hệ thống hoạt động theo mô hình RESTful API:
* **Backend:** FastAPI (Python), sử dụng mô hình YOLOv8 (`yolov8n.pt`) để xử lý và nhận diện vật thể trong ảnh.
* **Deployment & CI/CD:** Đóng gói qua Dockerfile, tự động triển khai lên Render Cloud thông qua GitHub.
* **Monitoring:** Tích hợp Prometheus (thông qua thư viện `prometheus-fastapi-instrumentator`) để thu thập metrics và trực quan hóa qua Grafana Cloud.

---

## 🛠️ 2. Hướng dẫn vận hành & Endpoints
Dưới đây là các đường dẫn (endpoints) chính của hệ thống khi chạy trên Production:

| Chức năng | Phương thức | Đường dẫn (URL) | Mô tả chi tiết |
| :--- | :---: | :--- | :--- |
| **API Docs** | `GET` | `/docs` | Giao diện Swagger UI tự động giúp kiểm tra và test API trực tiếp trên trình duyệt. |
| **Health Check** | `GET` | `/health` | Kiểm tra trạng thái hoạt động của server (trả về JSON xác nhận sống). |
| **Object Detection** | `POST` | `/api/detect/image` | Nhận file ảnh tải lên (`multipart/form-data`) và trả về kết quả tọa độ, tên vật thể nhận diện. |
| **System Metrics** | `GET` | `/metrics` | Cung cấp dữ liệu thô theo chuẩn Prometheus dùng để kết nối với Grafana. |

---

## ⚠️ 3. Các lỗi thường gặp & Cách xử lý thực chiến

* **Lỗi 503 Service Unavailable (`hibernate-wake-error`):**
  * *Nguyên nhân:* Do sử dụng gói Free trên Render, server sẽ tự động "ngủ đông" (hibernate) sau một khoảng thời gian không có request.
  * *Cách khắc phục:* Kiên nhẫn chờ từ 30 đến 50 giây để server khởi động lại ở lần gọi đầu tiên. Khuyên dùng dịch vụ **UptimeRobot** để ping tự động vào `/health` mỗi 5 phút nhằm giữ server luôn "tỉnh táo".
* **Hiện tượng "Loading" xoay vòng khi gọi API (`Execute`):**
  * *Nguyên nhân:* Ở lần gọi đầu tiên sau khi thức dậy, mô hình AI cần thời gian để tải trọng số (weights) vào bộ nhớ RAM.
  * *Cách khắc phục:* Nên sử dụng các file ảnh có dung lượng nhỏ, tối ưu kích thước (ví dụ dưới vài trăm KB) để tăng tốc độ phản hồi.
* **Lỗi 422 Validation Error:**
  * *Nguyên nhân:* Dữ liệu gửi lên không khớp với định dạng yêu cầu của API (ví dụ: thiếu file hoặc gửi sai định dạng file ảnh hỗ trợ như JPG/PNG).

---

## 📈 4. Thiết lập Giám sát Hệ thống (Monitoring)
Để theo dõi hiệu suất và sức khỏe hệ thống thời gian thực:
1. Thêm thư viện đo lường vào file `requirements.txt`:
   ```text
   prometheus-fastapi-instrumentator

### To run the docker
1. Run docker compose up --build
