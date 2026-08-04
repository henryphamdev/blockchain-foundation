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

-

1. (Where) Mã hóa hash được sử dụng ở đâu
2. (When) Mã hóa hash được sử dụng khi nào
3. (Why) Vì sao phải hash
4. (How) Sử dụng như thế nào
5. Thực hành cốt lõi

```
Binance Smart Chain sử dụng thuật toán mã hóa Keccak-256 (dựa trên phiên bản gốc của SHA-3)
```
