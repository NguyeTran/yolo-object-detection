# Sử dụng môi trường Node.js siêu nhẹ
FROM node:20-alpine

# Đặt thư mục làm việc trong container
WORKDIR /app

# Copy các file quản lý thư viện vào trước để tận dụng cache
COPY package*.json ./

# Cài đặt toàn bộ thư viện
RUN npm install

# Copy toàn bộ mã nguồn frontend vào container
COPY . .

# Mở cổng 5173 (cổng mặc định của Vite)
EXPOSE 5173

# Lệnh khởi động Frontend
CMD ["npm", "run", "dev", "--", "--host"]