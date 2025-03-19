# Hệ Thống Điều Khiển LED Tape Light

Phần mềm điều khiển LED tape light có khả năng mở rộng cao, hỗ trợ xử lý hàng triệu LED với hiệu suất tối ưu. Hệ thống hỗ trợ nhiều thiết bị (ESP32) và nhiều segment LED độc lập.

## Tính năng

- **Điều khiển nhiều thiết bị**: Hỗ trợ nhiều ESP32 hoặc thiết bị điều khiển khác nhau
- **Quản lý segment**: Điều khiển nhiều segment LED được điều khiển độc lập trên mỗi thiết bị
- **Hiệu ứng phong phú**: Hỗ trợ nhiều hiệu ứng ánh sáng khác nhau
- **Chuyển đổi & kết hợp hiệu ứng**: Khả năng chuyển đổi mượt mà giữa các hiệu ứng 
- **Timeline**: Lập trình chuỗi hiệu ứng theo thời gian
- **Giao diện responsive**: Thích ứng với kích thước màn hình khác nhau
- **Điều khiển từ xa**: Điều khiển qua giao thức OSC
- **Mô phỏng trực quan**: Xem trước trên màn hình trước khi triển khai thực tế
- **Tối ưu hiệu suất**: Hỗ trợ tăng tốc GPU và phân bố tính toán

## Yêu cầu hệ thống

- Python 3.7 trở lên
- Pygame 2.1.0 trở lên
- Pygame GUI 0.6.9 trở lên 
- NumPy 1.20.0 trở lên
- Python-OSC 1.8.0 trở lên
- GPU (tùy chọn) để tăng tốc xử lý khi sử dụng số lượng LED lớn

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

### Chạy với giao diện mô phỏng cơ bản

```bash
python main.py
```

### Chạy với giao diện xem trước quy mô lớn

```bash
python main.py --preview
```

### Chạy với giao diện đa thiết bị

```bash
python main.py --multi-device
```

### Chạy không có giao diện (headless mode)

```bash
python main.py --headless
```

### Sử dụng file cấu hình

```bash
# Chạy với file cấu hình thiết bị
python main.py --multi-device --device-config devices.json

# Chạy với file cấu hình layout
python main.py --multi-device --layout-config layout.json

# Chạy với file cấu hình timeline
python main.py --multi-device --timeline-config timeline.json
```

### Các tùy chọn khác

```
usage: main.py [-h] [--no-gui] [--preview] [--multi-device] [--headless]
               [--osc-ip OSC_IP] [--osc-port OSC_PORT] [--led-count LED_COUNT]
               [--fps FPS] [--workers WORKERS] [--device-config DEVICE_CONFIG]
               [--layout-config LAYOUT_CONFIG] [--timeline-config TIMELINE_CONFIG]
               [--skip-gpu-check] [--show-config]

LED Tape Light System

optional arguments:
  -h, --help            Hiển thị thông báo trợ giúp này và thoát
  --no-gui              Chạy không có GUI
  --preview             Chạy với large-scale preview
  --multi-device        Chạy với multi-device preview
  --headless            Chạy ở chế độ headless
  --osc-ip OSC_IP       Địa chỉ IP máy chủ OSC
  --osc-port OSC_PORT   Cổng máy chủ OSC
  --led-count LED_COUNT Số lượng LED
  --fps FPS             Frames per second
  --workers WORKERS     Số lượng worker threads
  --device-config DEVICE_CONFIG
                        File cấu hình thiết bị
  --layout-config LAYOUT_CONFIG
                        File cấu hình layout
  --timeline-config TIMELINE_CONFIG
                        File cấu hình timeline
  --skip-gpu-check      Bỏ qua kiểm tra tăng tốc GPU
  --show-config         Hiển thị cấu hình và thoát
```

## Các tính năng chính

### Chế độ xem đa thiết bị

Chế độ xem đa thiết bị cho phép bạn:

1. **Quản lý nhiều thiết bị**: Tạo, chỉnh sửa và xóa thiết bị
2. **Quản lý segment**: Phân chia các dải LED thành các segment độc lập
3. **Bố trí không gian**: Đặt vị trí thiết bị và segment trong không gian 2D
4. **Áp dụng hiệu ứng**: Gán hiệu ứng khác nhau cho từng segment
5. **Lưu/tải layout**: Lưu và tải cấu hình bố trí

### Điều khiển timeline

Timeline cho phép bạn:

1. **Lập trình chuỗi hiệu ứng**: Thiết lập các hiệu ứng chạy tuần tự hoặc chồng lên nhau
2. **Tạo chuyển cảnh**: Tạo hiệu ứng chuyển cảnh (fade, crossfade) giữa các hiệu ứng
3. **Lặp lại**: Thiết lập chương trình lặp lại
4. **Lưu/tải timeline**: Lưu và tải cấu hình timeline

### Giao diện Responsive

Giao diện responsive của phần mềm có các tính năng:

1. **Thích ứng với kích thước màn hình**: Tự động điều chỉnh khi thay đổi kích thước cửa sổ
2. **Panel có thể thu gọn**: Các panel có thể thu gọn để tăng không gian làm việc
3. **Panel có thể di chuyển**: Kéo thả các panel đến vị trí mong muốn
4. **Zoom và pan**: Phóng to, thu nhỏ và di chuyển khung nhìn

## Điều khiển qua OSC

Hệ thống có thể nhận lệnh điều khiển thông qua OSC messages với định dạng:

```
/effect/{effect_ID}/segment/{segment_ID}/{param_name} {value}
```

Ví dụ:
- `/effect/1/segment/1/move_speed 20.0` - Thay đổi tốc độ di chuyển
- `/effect/2/segment/3/color 16711680` - Thay đổi màu sắc (đỏ)
- `/effect/3/segment/2/transparency 0.5` - Thay đổi độ trong suốt

Ngoài ra, có thể điều khiển thiết bị và segment:

```
/device/{device_ID}/{command} {value}
/device/{device_ID}/segment/{segment_ID}/{command} {value}
```

Ví dụ:
- `/device/dev1/brightness 0.8` - Thay đổi độ sáng của thiết bị
- `/device/dev1/segment/seg1/effect 2` - Gán hiệu ứng ID 2 cho segment seg1

## Các hiệu ứng có sẵn

1. **Rainbow**: Hiệu ứng cầu vồng với gradient màu sắc
2. **Pulse**: Hiệu ứng nhấp nháy với tốc độ và màu sắc tùy chỉnh
3. **Chase**: Hiệu ứng chạy đuổi với nhiều segment
4. **Tùy chỉnh**: Tạo hiệu ứng mới bằng cách kế thừa lớp LightEffect

## Tùy chỉnh hệ thống

Bạn có thể tùy chỉnh hệ thống bằng cách chỉnh sửa `config.py` hoặc tạo file cấu hình tùy chỉnh:

```bash
python main.py --device-config mydevices.json --layout-config mylayout.json --timeline-config mytimeline.json
```

## Tích hợp với phần cứng

Để kết nối với phần cứng thực tế, cần phải:

1. Flash mã ESP32_LED_Controller (không bao gồm trong repo này) lên thiết bị ESP32
2. Kết nối thiết bị ESP32 với dải LED (WS2812B, SK6812, v.v.)
3. Kết nối thiết bị ESP32 với mạng WiFi cùng với máy tính chạy phần mềm
4. Cấu hình thiết bị trong phần mềm với địa chỉ IP và cổng chính xác

## Hiệu suất

Hệ thống được tối ưu hóa để xử lý số lượng lớn LED:

- Khoảng 10,000 LED trên CPU trung bình
- Lên đến 1,000,000 LED với tăng tốc GPU
- Hỗ trợ phân phối tải trên nhiều luồng
- Quản lý bộ nhớ thông minh để giảm thiểu bộ nhớ sử dụng

## Giải quyết sự cố

Nếu gặp sự cố, hãy kiểm tra log trong thư mục `~/.led_tape_system/logs/`.

### Sự cố phổ biến

1. **ImportError**: Cài đặt thiếu dependencies. Chạy `python system_checker.py` để kiểm tra.
2. **OSError với port OSC**: Port bị sử dụng. Thử port khác với `--osc-port`.
3. **Hiệu suất kém**: Giảm số lượng LED hoặc bật tăng tốc GPU.
4. **Kết nối thiết bị**: Kiểm tra kết nối mạng, địa chỉ IP và cổng.

## Đóng góp

Đóng góp vào dự án là rất được hoan nghênh! Hãy tạo issue hoặc pull request trên GitHub.

## Giấy phép

Dự án này được cấp phép theo giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.