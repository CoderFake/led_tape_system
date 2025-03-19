# Hệ Thống Điều Khiển LED Tape Light

Phần mềm điều khiển LED tape light có khả năng mở rộng cao, hỗ trợ xử lý hàng triệu LED với hiệu suất tối ưu.

## Tính năng

- Hỗ trợ nhiều hiệu ứng ánh sáng khác nhau
- Khả năng tạo gradient và blend màu sắc
- Điều khiển từ xa qua giao thức OSC
- Tối ưu hóa hiệu suất cho hàng triệu LED
- Dễ dàng tùy chỉnh và mở rộng
- Mô phỏng trực quan hiệu ứng LED

## Yêu cầu hệ thống

- Python 3.7 trở lên
- Pygame 2.1.0 trở lên
- NumPy 1.20.0 trở lên
- Python-OSC 1.8.0 trở lên
- CPU/GPU đủ mạnh để xử lý số lượng LED mong muốn

### Yêu cầu tùy chọn cho tăng tốc GPU

- NVIDIA GPU với CUDA Toolkit (cho Numba/CUDA)
- GPU hỗ trợ OpenCL với drivers (cho PyOpenCL)

## Cài đặt

### Cài đặt tự động

```bash
# Tải và chạy script cài đặt
python install.py
```

### Cài đặt thủ công

1. Clone repository:
```bash
git clone https://github.com/yourusername/led-tape-system.git
cd led-tape-system
```

2. Cài đặt dependencies:
```bash
# Kiểm tra và cài đặt dependencies
python system_checker.py

# Hoặc cài đặt trực tiếp
pip install -r requirements.txt
```

## Sử dụng

### Chạy với giao diện mô phỏng

```bash
python main.py
```

### Chạy với giao diện xem trước quy mô lớn

```bash
python main.py --preview
```

### Chạy không có giao diện (headless mode)

```bash
python main.py --headless
```

### Các tùy chọn khác

```
usage: main.py [-h] [--no-gui] [--preview] [--headless] [--osc-ip OSC_IP]
               [--osc-port OSC_PORT] [--led-count LED_COUNT] [--fps FPS]
               [--workers WORKERS] [--config-file CONFIG_FILE]
               [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
               [--skip-gpu-check]

LED Tape Light System

optional arguments:
  -h, --help            Hiển thị thông báo trợ giúp này và thoát
  --no-gui              Chạy không có GUI
  --preview             Chạy với large-scale preview
  --headless            Chạy ở chế độ headless
  --osc-ip OSC_IP       Địa chỉ IP máy chủ OSC
  --osc-port OSC_PORT   Cổng máy chủ OSC
  --led-count LED_COUNT Số lượng LED
  --fps FPS             Frames per second
  --workers WORKERS     Số lượng worker threads
  --config-file CONFIG_FILE
                        File cấu hình
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Mức độ ghi log
  --skip-gpu-check      Bỏ qua kiểm tra tăng tốc GPU
```

## Điều khiển qua OSC

Hệ thống có thể nhận lệnh điều khiển thông qua OSC messages với định dạng:
```
/effect/{effect_ID}/segment/{segment_ID}/{param_name} {value}
```

Ví dụ:
- `/effect/1/segment/1/move_speed 20.0` - Thay đổi tốc độ di chuyển
- `/effect/2/segment/3/color 16711680` - Thay đổi màu sắc (đỏ)
- `/effect/3/segment/2/transparency 0.5` - Thay đổi độ trong suốt

## Các hiệu ứng có sẵn

1. **Rainbow**: Hiệu ứng cầu vồng với gradient màu sắc
2. **Pulse**: Hiệu ứng nhấp nháy với tốc độ và màu sắc tùy chỉnh
3. **Chase**: Hiệu ứng chạy đuổi với nhiều segment

## Tùy chỉnh hệ thống

Bạn có thể tùy chỉnh hệ thống bằng cách chỉnh sửa `config.py` hoặc tạo file cấu hình tùy chỉnh:

```bash
python main.py --config-file myconfig.json
```

## Tích hợp với phần cứng

Hệ thống này hiện tại chỉ mô phỏng LED. Để kết nối với phần cứng thực tế, bạn cần triển khai một trình điều khiển tương thích với phần cứng của bạn.

## Hiệu suất

Hệ thống được tối ưu hóa để xử lý số lượng lớn LED:

- Khoảng 10,000 LED trên CPU trung bình
- Lên đến 1,000,000 LED với tăng tốc GPU
- Phân cụm tự động để cải thiện hiệu suất
- Quản lý bộ nhớ thông minh để giảm thiểu bộ nhớ sử dụng

## Giải quyết sự cố

Nếu gặp sự cố, hãy kiểm tra log trong thư mục `~/.led_tape_system/logs/`.

### Sự cố phổ biến

1. **ImportError**: Cài đặt thiếu dependencies. Chạy `python system_checker.py` để kiểm tra.
2. **OSError với port OSC**: Port bị sử dụng. Thử port khác với `--osc-port`.
3. **Hiệu suất kém**: Giảm số lượng LED hoặc bật tăng tốc GPU.


## Giấy phép

Dự án này được cấp phép theo giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.