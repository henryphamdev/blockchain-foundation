Chữ ký số & mật mã khóa công khai: Elliptic Curve (secp256k1), ECDSA, vì sao private key → public key → address là một chiều.

### 1. WHAT — Là gì?

- **Mật mã khóa công khai (asymmetric crypto)**: cặp khóa private/public — ký bằng private, verify bằng public
- **Elliptic Curve Cryptography (ECC)**: mật mã dựa trên toán học đường cong elliptic `y² = x³ + ax + b` trên trường hữu hạn
- **secp256k1**: đường cong cụ thể (`y² = x³ + 7`) mà Bitcoin/Ethereum/BSC dùng
- **ECDSA**: thuật toán ký số trên đường cong elliptic — output là cặp `(r, s)` (+ `v` recovery id trong Ethereum)
- **Address**: dạng rút gọn của public key qua hash (Ethereum: `keccak256(pubkey)[12:]`, Bitcoin: `RIPEMD160(SHA256(pubkey))`)

### 2. WHY — Tại sao cần?

- Chứng minh **quyền sở hữu** mà không lộ private key (authentication)
- Đảm bảo **toàn vẹn** giao dịch — sửa 1 byte là chữ ký invalid (integrity)
- **Chống chối bỏ** — chỉ người giữ private key mới ký được (non-repudiation)
- Vì sao chọn ECC thay RSA: cùng độ an toàn nhưng khóa ngắn hơn nhiều (256-bit ECC ≈ 3072-bit RSA) → nhẹ, nhanh, hợp blockchain

#### Vì sao một chiều (trọng tâm)

- **Private → Public**: `pubkey = privkey × G` (nhân điểm trên đường cong). Chiều ngược lại là bài toán **ECDLP (Elliptic Curve Discrete Logarithm Problem)** — không có thuật toán hiệu quả, brute-force 2²⁵⁶ khả năng
- **Public → Address**: qua hàm hash (keccak256/SHA256) — hash là one-way theo định nghĩa (preimage resistance, nối tiếp module hash bạn đã học)
- Kết luận: 2 tầng một chiều độc lập → biết address không suy ra pubkey, biết pubkey không suy ra privkey

### 3. WHO — Ai dùng, ai phát minh?

- Nền tảng: Diffie–Hellman (1976), Koblitz & Miller đề xuất ECC (1985)
- secp256k1: chuẩn hóa bởi SECG (Standards for Efficient Cryptography Group), Satoshi chọn cho Bitcoin
- Người dùng: ví crypto (MetaMask, hardware wallet), node validator, CA/chính phủ (chữ ký số pháp lý — VN có USB token theo Luật Giao dịch điện tử), TLS/SSH

### 4. WHERE — Dùng ở đâu?

- Blockchain: ký transaction (Bitcoin, Ethereum, BSC — liên quan trực tiếp NFT/smart contract của bạn)
- Web: TLS certificate, JWT (ES256)
- Hệ thống: SSH key, git commit signing, code signing
- Pháp lý: hóa đơn điện tử, hợp đồng điện tử tại VN

### 5. WHEN — Khi nào xảy ra trong flow?

- **Keygen**: 1 lần khi tạo ví — random 256-bit privkey → derive pubkey → hash ra address
- **Signing**: mỗi lần gửi transaction — hash message → ký bằng privkey → `(r, s, v)`
- **Verification**: mỗi node khi nhận tx — recover pubkey từ chữ ký, so với address người gửi
- Lưu ý lịch sử: khi nào ECDSA "vỡ"? — nonce `k` trùng lặp (vụ hack PS3 2010), RNG yếu

### 6. HOW — Cơ chế hoạt động?

- **Keygen**: chọn `d` ngẫu nhiên ∈ [1, n-1] → `Q = d × G`
- **Sign**: chọn nonce `k` ngẫu nhiên → `r = (k×G).x mod n` → `s = k⁻¹(hash + r·d) mod n`
- **Verify**: tính `u₁ = hash·s⁻¹`, `u₂ = r·s⁻¹` → kiểm tra `(u₁G + u₂Q).x ≟ r`
- **Point addition & double-and-add**: cách nhân điểm hiệu quả O(log n) — lý do derive xuôi thì nhanh, ngược thì bất khả thi
- Thực hành gợi ý: dùng `ethers.js` / `noble-secp256k1` tự tạo key, ký message, recover address

