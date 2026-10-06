### Hai kỹ thuật gốc của mọi mã hóa cổ điển

**1. Hoán vị (transposition)** — giữ nguyên chữ, xáo trộn vị trí.  
Ví dụ cổ nhất: **Scytale** của người Sparta (~500 TCN) — quấn dải da quanh một cây gậy, viết dọc theo thân gậy, tháo ra thì chữ thành vô nghĩa. **Khóa = đường kính cây gậy**: người nhận phải có gậy cùng cỡ mới đọc được.

**2. Thay thế (substitution)** — giữ nguyên vị trí, đổi chữ.  
Nổi tiếng nhất: **mật mã Caesar** (~50 TCN) — dịch mỗi chữ cái đi 3 bậc: A→D, B→E. Khóa = số bậc dịch. Julius Caesar dùng gửi lệnh quân sự. Cực yếu theo chuẩn nay: chỉ có 25 khóa khả dĩ, thử hết trong vài phút bằng tay.

### Cuộc chạy đua tấn công – phòng thủ (phần hay nhất của lịch sử)

**Thế kỷ 9 — Al-Kindi (học giả Ả Rập) phát minh phân tích tần suất**, khai sinh ngành phá mã: trong mỗi ngôn ngữ, tần suất chữ cái là cố định (tiếng Anh: E ~13%, T ~9%...). Mã thay thế đơn giản chỉ "đeo mặt nạ" cho chữ cái chứ không đổi tần suất → đếm tần suất trong bản mã là lột được mặt nạ. Từ đây, mọi mã thay thế đơn coi như chết — dù người ta vẫn dùng thêm 700 năm. Cái giá đắt nhất: năm 1587, **nữ hoàng Mary xứ Scotland bị xử tử** vì thư mưu phản mã hóa của bà bị phá bằng đúng kỹ thuật này.

**Thế kỷ 16 — Vigenère phản đòn bằng mã đa bảng thế**: dùng một từ khóa (ví dụ `KEY`) để mỗi chữ cái bị dịch một lượng khác nhau, lặp theo chu kỳ. Một chữ E lúc mã thành X, lúc thành M → tần suất bị san phẳng. Được mệnh danh "le chiffre indéchiffrable" (mật mã không thể phá) suốt **300 năm**, đến giữa thế kỷ 19 mới bị Babbage và Kasiski hạ: tìm chu kỳ lặp của từ khóa, rồi cắt bản mã thành từng lớp — mỗi lớp lại là... mã Caesar, phá bằng tần suất như cũ.

**Song song — giấu thay vì mã (steganography)**: Herodotus kể chuyện xăm mật thư lên da đầu nô lệ rồi chờ tóc mọc; mực vô hình từ nước chanh; thư giấu trong trứng luộc. Và **codebook/nomenclator** của giới ngoại giao: sổ tay quy ước cả từ/cụm từ thành ký hiệu — tổ tiên của "shared secret".

**Thời cơ khí — Alberti (1467) chế đĩa mã xoay**, cho phép đổi bảng thế giữa chừng; Jefferson làm trục 26 bánh xe; đỉnh cao là **Enigma** của Đức — về bản chất vẫn là mã đa bảng thế kiểu Vigenère, nhưng chu kỳ dài ~17.000 ký tự nhờ 3 rotor cơ khí. Và vẫn bị phá — bởi Turing và Bletchley Park, khai sinh luôn máy tính hiện đại.

### Sợi chỉ nối về đúng thứ bạn đang học

Ba bài học từ 2500 năm đó vẫn là nền của SSH lab bạn vừa làm:

1. **Tách khóa khỏi thuật toán**: từ cây gậy Sparta đến rotor Enigma, cái cần giữ bí mật dần chuyển từ *cách làm* sang *khóa* — được Kerckhoffs phát biểu thành nguyên lý năm 1883: hệ mã phải an toàn kể cả khi đối phương biết toàn bộ thuật toán. Đúng như log tcpdump của bạn: hai bên công khai trao đổi cả "menu" thuật toán, chỉ khóa là bí mật.
2. **Mọi mã cổ điển đều đối xứng** — hai bên phải gặp nhau trao khóa trước (cây gậy cùng cỡ, từ khóa Vigenère, codebook, bảng rotor Enigma in hàng tháng). Bài toán "trao khóa an toàn qua kênh không an toàn" bế tắc suốt 2500 năm, đến **1976 Diffie-Hellman** mới giải — chính là packet type 30/31 trong capture của bạn.
3. **Kẻ phá mã luôn thắng về dài hạn** với mã cổ điển, vì chúng dựa trên "obscurity". Mã hiện đại đảo thế cờ: dựa trên bài toán toán học một chiều (ECDLP) — kẻ tấn công biết hết mọi thứ trừ một con số 256-bit, và chừng đó là đủ.

Nói cách khác: người xưa mã hóa bằng sự khéo léo, người nay mã hóa bằng độ khó của toán học — và ranh giới giữa hai thời đại chính là Diffie-Hellman mà bạn vừa bắt được trên dây.