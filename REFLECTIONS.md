1. Multi-account

Để chạy costctl trên nhiều AWS accounts khác nhau, em sẽ sử dụng cross-account IAM Role kết hợp với AWS STS AssumeRole. Sau đó tool sẽ loop qua danh sách account IDs để collect dữ liệu từ từng account và tổng hợp output thành CSV hoặc JSON để dễ dàng quản lý chi phí và tài nguyên.

2. idle vs Trusted Advisor

Em tin tưởng command idle hơn trong các trường hợp cần kiểm tra nhanh tài nguyên EC2 đang ít hoạt động trong thời gian ngắn, ví dụ môi trường test hoặc development. Vì command này sử dụng CPU average trong 24 giờ nên có thể phát hiện tài nguyên dư thừa nhanh hơn. Tuy nhiên, Trusted Advisor đáng tin cậy hơn cho việc tối ưu lâu dài vì nó phân tích dữ liệu trong 14 ngày, giúp giảm khả năng terminate nhầm các instance chỉ hoạt động theo chu kỳ.

3. clean --apply blast radius

Nếu vô tình chạy clean --tag Environment=dev --apply trong shared account với team khác, em sẽ muốn có thêm nhiều cơ chế bảo vệ hơn. Ví dụ như thêm bước confirm lần hai, giới hạn IAM permission, sử dụng AWS Organizations SCP hoặc chỉ cho phép chạy trong các account được chỉ định trước. Ngoài ra dry-run nên hiển thị rõ owner, số lượng resource và loại resource trước khi thực hiện xóa để giảm rủi ro.

4. AI assistance

AI hỗ trợ em trong việc giải thích yêu cầu của project, gợi ý cách sử dụng boto3 APIs và tạo cấu trúc code ban đầu cho các command như list, terminate, tag và clean. Tuy nhiên phần lớn công việc em vẫn phải tự thực hiện như đọc test cases, debug các lỗi pytest bị fail, chỉnh sửa output format để match với expected output và xử lý các edge cases theo đúng yêu cầu của đề bài. Ngoài ra em cũng phải tự kiểm tra logic giữa các AWS resources và sửa các lỗi syntax hoặc logic phát sinh trong quá trình chạy test.