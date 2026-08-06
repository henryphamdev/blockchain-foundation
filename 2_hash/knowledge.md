1. (What) Hash là gì, Hash giúp mã hóa những gì , có bao nhiêu loại mã hóa

- Hash là dữ liệu đầu ra của một hàm hash (hash function), với đầu vào là text, file, number, ... và đầu ra là chuỗi kí tự với chiều dài bất biến dù dữ liệu chỉ 1 kí tự hay 1 GB, (ví dụ sha256 chuỗi 256 bit dài 64 kí tự)
- Có bao nhiêu loại hash:
  - nhóm hash không bảo mật:
    - sharding data, hash table, hash map: MurmurHash, xxHash, FNV, CityHash
  - hash mật mã (Cryptographic)
    - MD MD5 Đã vỡ — chỉ còn dùng checksum không quan trọng
    - SHA-1 SHA-1 Đã vỡ — bỏ
    - SHA-2 SHA-256, SHA-512 Chuẩn phổ biến nhất hiện nay
    - SHA-3 Keccak Chuẩn mới, cấu trúc khác SHA-2
    - BLAKE BLAKE2, BLAKE3 Nhanh, an toàn, BLAKE3 rất nhanh
    - RIPEMD-160, Whirlpool RIPEMD-160 dùng trong địa chỉ Bitcoin
  - Chia theo công dụng:
    - Hash toàn vẹn / chữ ký: SHA-256, BLAKE3 — cần nhanh.
    - Password hashing (KDF chậm, có salt): Argon2, bcrypt, scrypt,
    - PBKDF2 — cố tình chậm để chống brute-force. Đây là nhóm riêng, đừng nhầm với SHA-256.
    - Keyed hash / MAC: HMAC — hash + secret key để xác thực message/webhook.
  - Hash chuyên dụng:
    - Merkle tree — gộp nhiều hash thành 1 root (blockchain, NFT whitelist).
    - Perceptual hash (pHash, dHash) — so độ giống nhau của ảnh, không phải giống hệt.
    - Consistent hashing — phân bổ dữ liệu qua nhiều server (Redis cluster, load balancer).
    - Geohash — mã hóa tọa độ địa lý thành chuỗi.
- Hash có các đặc tính:
  - deterministic : cùng input luôn cùng output
  - fix-size : 1kb hay 1GB dữ liệu đều cho ra hash có chiều dài như nhau
  - one-way : không suy ngược được dữ liệu từ hash
  - Avalancher : đổi 1 bit input dẫn tới hash thay đổi ít nhất 50%
  - Colisition Resistance: rất khó để tìm 2 input có cùng hash

1. (Who) Những công cụ, nền tảng nào sử dụng hash

- blockchain, các công cụ download check-sum, what-app, git, docker,
- xác thực toàn vẹn : (TLS, JWT, HMAC, password, SRI
- phân bổ, tra cứu nhanh: HashMap, sharding, consistent hashing, Bloom filter
-

1. (Where) Hash được sử dụng ở đâu

### A. Theo vòng đời dữ liệu

- **Lúc lưu trữ (at rest)**: password hash trong DB, checksum file, dedup backup, verify integrity của secret trong Infisical.
- **Lúc truyền (in transit)**: bắt tay TLS, chữ ký HMAC cho webhook/API, JWT, checksum gói tin mạng.
- **Lúc xử lý (in use, trong RAM)**: HashMap, cache key, Bloom filter, hash để sharding/định tuyến.

### B. Theo tầng mạng

- **Tầng link/transport**: CRC checksum trong Ethernet/TCP (non-crypto, chỉ dò lỗi).
- **Tầng bảo mật (TLS)**: MAC cho mỗi record, fingerprint chứng chỉ, ký số.
- **Tầng ứng dụng**: JWT (HS256 = HMAC-SHA256), HMAC verify webhook, HTTP `ETag`, SRI `integrity="sha384-..."`.

2. (When) Hash được sử dụng khi nào

### Nhóm 1 — Theo sự kiện người dùng (compute rồi verify về sau)

| Khi nào                     | Hash gì                    | Compute / Verify                    |
| --------------------------- | -------------------------- | ----------------------------------- |
| User đăng ký / đổi mật khẩu | bcrypt/argon2 password     | **compute** → lưu DB                |
| User đăng nhập              | hash lại password nhập vào | **verify** so với hash đã lưu       |
| Nhận webhook NAPAS/cổng TT  | HMAC của raw body          | **verify** chữ ký                   |
| Mỗi request kèm token       | chữ ký JWT (HMAC/RSA)      | **verify** ở gateway                |
| Upload / tải file           | checksum SHA-256           | compute lúc up, **verify** lúc down |
| Ký giao dịch on-chain       | keccak256 message          | compute lúc ký, verify on-chain     |

Đặc điểm: compute một lần, verify **nhiều lần về sau** — có thể sau vài mili-giây (login) hoặc vài tháng (checksum backup).

### Nhóm 2 — Mỗi thao tác, tần suất rất cao (gần như liên tục)

Những chỗ này hash chạy **hàng nghìn–triệu lần/giây**, bạn không thấy vì nó ẩn trong hạ tầng: mỗi lần truy cập HashMap/dict trong code, mỗi cache lookup (Redis key), mỗi lần định tuyến sharding `hash(key) % N`, mỗi record TLS được ký MAC khi truyền. Đây là hash "nhanh, non-crypto hoặc HMAC nhẹ" — ưu tiên tốc độ.

### Nhóm 3 — Theo lịch / chạy nền (định kỳ)

Kích hoạt theo thời gian chứ không theo request: dedup backup (so digest để bỏ file trùng), integrity scan định kỳ (phát hiện file bị sửa), rotate chứng chỉ SSL (Certbot tính lại fingerprint), và **audit/log chain** — nối các bản ghi log bằng hash chain để phát hiện log bị chỉnh sửa hồi tố.

### Nhóm 4 — Sự kiện DevOps / hệ thống

Mỗi **git commit** (sinh commit hash), mỗi **CI build** (verify lockfile integrity), mỗi **docker build** (digest layer), mỗi **deploy** (K8s pin digest), và trong blockchain là mỗi **block được đào** (proof-of-work) + mỗi **Merkle proof** được verify khi claim/mint. 3. (Why) Vì sao phải hash

- Đây là câu chốt của cả loạt 5W — và câu trả lời gọn nhất: **hash tồn tại vì nó làm được ba việc mà không công cụ nào khác làm được cùng lúc** — chứng minh mà không lộ, phát hiện thay đổi, và định danh bằng nội dung. Mỗi "vì sao" gắn với một tính chất của hash:
  ### 1. Vì cần chứng minh "biết" mà không được lộ (tính một chiều)
  Bài toán password: bạn phải verify user biết mật khẩu, nhưng **không được lưu mật khẩu**. Nếu lưu plaintext, một lần lộ DB là mất trắng. Hash một chiều giải đúng nghịch lý này: lưu `H(password)`, verify được, mà kẻ trộm DB không lần ngược ra password. Không có tính một chiều thì không có cách nào "kiểm tra mà không giữ bản gốc".
  ### 2. Vì cần một "dấu vân tay" cố định để so sánh/tra cứu rẻ (kích thước cố định)
  So sánh hai file 10GB tốn kém; so hai chuỗi 64 ký tự thì tức thì. Hash biến dữ liệu bất kỳ thành fingerprint cố định → cho phép **so sánh, đánh index, dedup, tra cứu O(1)** ở quy mô lớn. Đây là lý do HashMap, sharding, cache key đều dựa trên hash: biến key bất kỳ thành vị trí phân bố đều.
  ### 3. Vì cần phát hiện mọi thay đổi (avalanche + kháng va chạm)
  Đổi 1 bit → digest đổi ~50% → **bất kỳ tamper nào cũng lộ ngay**. Đây là "vì sao" của checksum, Docker digest, Git commit, log chain: bạn có một dấu niêm phong mà kẻ tấn công không thể sửa dữ liệu rồi làm cho digest khớp lại (vì kháng va chạm). Không có tính này thì không có khái niệm "toàn vẹn".
  ### 4. Vì cần định danh bằng chính nội dung (tính xác định)
  Cùng input → cùng hash → dùng **hash làm địa chỉ**. Địa chỉ tự xác minh: tải về, hash lại, khớp thì chắc chắn đúng nội dung. Đây là "vì sao" của content-addressing (IPFS, Git, Docker layer, blockchain) — định danh gắn chặt vào nội dung, khác hẳn một ID ngẫu nhiên (ID ngẫu nhiên không nói gì về nội dung, không tự kiểm được).
  ### 5. Vì cần cam kết ràng buộc, không thể chối (binding)
  Công bố `H(dữ liệu)` trước, tiết lộ dữ liệu sau → chứng minh "tôi đã biết điều này từ trước" mà không lộ sớm. Đây là nền của chữ ký số (ký hash thay vì ký cả file), commitment, Merkle proof, proof-of-work.
  ### Vì sao là hash, không phải cách khác?
  - **Không dùng mã hóa**: mã hóa đảo ngược được và phải quản lý khóa — thừa và nguy hiểm cho việc chỉ-cần-verify. Với password/integrity, bạn _không muốn_ khả năng giải ngược tồn tại.
  - **Không lưu plaintext / so trực tiếp**: lộ dữ liệu là thảm họa, và so dữ liệu lớn thì đắt.
  - **Không dùng ID ngẫu nhiên**: không tự xác minh nội dung, không dedup được.

1. (How) Sử dụng như thế nào
2. Thực hành cốt lõi

```
Binance Smart Chain sử dụng thuật toán mã hóa Keccak-256 (dựa trên phiên bản gốc của SHA-3)
```
