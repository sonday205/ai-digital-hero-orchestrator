# Danh sách 48 nhân vật

Nguồn cấu hình: `data/characters.json`. Giữ nguyên mapping 001–014; bổ sung các nhân vật khác; mã 019 là Lê Đức Thúy, nguyên Thống đốc Ngân hàng Nhà nước.
Các mã media là mapping mặc định, không chứng minh file ảnh/giọng đã tồn tại trên server.

| Nhân vật | character_id LLM | voice_id TTS | image_id LipSync |
| --- | --- | --- | --- |
| Tô Vĩnh Diện | `to_vinh_dien` | `001` | `001` |
| Võ Thị Sáu | `vo_thi_sau` | `002` | `002` |
| Kim Đồng | `kim_dong` | `003` | `003` |
| Lê Văn Tám | `le_van_tam` | `004` | `004` |
| Nguyễn Văn Trỗi | `nguyen_van_troi` | `005` | `005` |
| Lê Hồng Phong | `le_hong_phong` | `006` | `006` |
| Nguyễn Bỉnh Khiêm | `nguyen_binh_khiem` | `007` | `007` |
| Nguyễn Bá Ngọc | `nguyen_ba_ngoc` | `008` | `008` |
| Nữ tướng Lê Chân | `le_chan` | `009` | `009` |
| Công chúa Lê Ngọc Hân | `le_ngoc_han` | `010` | `010` |
| Anh hùng Núp (Đinh Núp) | `dinh_nup` | `011` | `011` |
| Ngô Quyền | `ngo_quyen` | `012` | `012` |
| Quang Trung - Nguyễn Huệ | `quang_trung_nguyen_hue` | `013` | `013` |
| Lê Lợi | `le_loi` | `014` | `014` |
| Đại tá Phạm Ngọc Thảo | `pham_ngoc_thao` | `015` | `015` |
| Thiếu tướng Vũ Ngọc Nhạ | `vu_ngoc_nha` | `016` | `016` |
| Thiếu tướng Đặng Trần Đức | `dang_tran_duc` | `017` | `017` |
| Thiếu tướng Phạm Xuân Ẩn | `pham_xuan_an` | `018` | `018` |
| Lê Đức Thúy (nguyên Thống đốc) | `le_duc_thuy` | `019` | `019` |
| Đại tá Lê Hữu Thúy | `le_huu_thuy` | `020` | `020` |
| Hùng Vương | `hung_vuong` | `021` | `021` |
| An Dương Vương | `an_duong_vuong` | `022` | `022` |
| Hai Bà Trưng | `hai_ba_trung` | `023` | `023` |
| Bà Triệu | `ba_trieu` | `024` | `024` |
| Lý Nam Đế | `ly_nam_de` | `025` | `025` |
| Triệu Quang Phục | `trieu_quang_phuc` | `026` | `026` |
| Phùng Hưng | `phung_hung` | `027` | `027` |
| Mai Thúc Loan | `mai_thuc_loan` | `028` | `028` |
| Khúc Thừa Dụ | `khuc_thua_du` | `029` | `029` |
| Dương Đình Nghệ | `duong_dinh_nghe` | `030` | `030` |
| Đinh Bộ Lĩnh | `dinh_bo_linh` | `031` | `031` |
| Lê Hoàn | `le_hoan` | `032` | `032` |
| Lý Thái Tổ | `ly_thai_to` | `033` | `033` |
| Lý Thường Kiệt | `ly_thuong_kiet` | `034` | `034` |
| Trần Hưng Đạo | `tran_hung_dao` | `035` | `035` |
| Nguyễn Trãi | `nguyen_trai` | `036` | `036` |
| Thánh Thiên | `thanh_thien` | `037` | `037` |
| Dương Vân Nga | `duong_van_nga` | `038` | `038` |
| Ỷ Lan | `y_lan` | `039` | `039` |
| Trần Thị Dung | `tran_thi_dung` | `040` | `040` |
| Lý Chiêu Hoàng | `ly_chieu_hoang` | `041` | `041` |
| An Tư | `an_tu` | `042` | `042` |
| Huyền Trân | `huyen_tran` | `043` | `043` |
| Nguyễn Thị Anh | `nguyen_thi_anh` | `044` | `044` |
| Nguyễn Thị Duệ | `nguyen_thi_due` | `045` | `045` |
| Đoàn Thị Điểm | `doan_thi_diem` | `046` | `046` |
| Hồ Xuân Hương | `ho_xuan_huong` | `047` | `047` |
| Lý Tự Trọng | `ly_tu_trong` | `048` | `048` |

Hùng Vương là nhóm vua Hùng; Hai Bà Trưng là một hồ sơ chung. Lê Hữu Thúy dùng ID `le_huu_thuy` (không tạo ID theo tên bị ghi nhầm trong tài liệu Word).

019 được cấu hình qua `LE_DUC_THUY_VOICE_ID` / `LE_DUC_THUY_IMAGE_ID`.
Dữ liệu xác định nhà kinh tế ngân hàng, không gán quân hàm Thiếu tướng.
Không gắn dữ liệu của Lê Hữu Thúy cho Lê Đức Thúy.
