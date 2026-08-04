"""
Hash chain tự code từ đầu — bản comment tường minh từng dòng.
Hai kiểu:
  A) Pure hash chain : h_n = H(h_{n-1})  (dùng cho One-Time Password kiểu Lamport)
  B) Block hash chain: mỗi block link tới block trước qua prev_hash (khung của blockchain)
Chỉ dùng thư viện chuẩn -> không cần cài gì.
"""

import hashlib          # thư viện hash chuẩn của Python (có sẵn SHA-256)
import time             # để lấy timestamp cho mỗi block
import json             # để serialize nội dung block thành chuỗi cố định trước khi hash


def sha256(data: bytes) -> str:
    # Nhận vào bytes, trả ra digest SHA-256 dạng chuỗi hex 64 ký tự
    return hashlib.sha256(data).hexdigest()



# ═════════════════════════════════════════════════════════════════════
# A) PURE HASH CHAIN — áp hash lên chính output của nó nhiều lần
# ═════════════════════════════════════════════════════════════════════
def pure_hash_chain(seed: str, n: int):
    # chain[0] = H(seed): mắt xích đầu tiên sinh ra từ hạt giống
    chain = [sha256(seed.encode())]              # .encode() đổi str -> bytes cho hàm hash
    print(chain)

    # Lặp thêm (n-1) lần để tạo đủ n mắt xích
    for _ in range(n - 1):
        # Mắt xích mới = hash của mắt xích ngay trước đó (chain[-1] = phần tử cuối)
        chain.append(sha256(chain[-1].encode()))

    # Trả về toàn bộ chuỗi hash
    return chain


# ═════════════════════════════════════════════════════════════════════
# B) BLOCK HASH CHAIN — kiểu blockchain (bỏ Proof-of-Work cho gọn)
# ═════════════════════════════════════════════════════════════════════
class Block:
    def __init__(self, index, data, prev_hash):
        self.index = index                       # số thứ tự block trong chuỗi (0, 1, 2, ...)
        self.timestamp = time.time()             # thời điểm tạo block (giây, dạng float)
        self.data = data                         # nội dung block (vd: 1 giao dịch)
        self.prev_hash = prev_hash               # hash của block LIỀN TRƯỚC -> tạo liên kết
        self.hash = self.compute_hash()          # tự tính hash của chính block này khi khởi tạo

    def compute_hash(self):
        # Gom tất cả trường quan trọng vào 1 dict rồi serialize ra chuỗi
        payload = json.dumps({
            "index": self.index,                 # đưa index vào -> đổi vị trí là đổi hash
            "timestamp": self.timestamp,         # đưa thời gian vào
            "data": self.data,                   # đưa nội dung vào -> sửa data là đổi hash
            "prev_hash": self.prev_hash,         # QUAN TRỌNG: đưa prev_hash vào -> tạo xích
        }, sort_keys=True).encode()              # sort_keys=True để thứ tự key luôn cố định
        #                                          -> cùng nội dung luôn ra cùng chuỗi -> cùng hash
        return sha256(payload)                   # hash chuỗi vừa tạo


class HashChain:
    def __init__(self):
        # Genesis block = block gốc, không có block trước nên prev_hash quy ước = "0"*64
        self.blocks = [Block(0, "GENESIS", "0" * 64)]

    def add(self, data):
        prev = self.blocks[-1]                   # lấy block cuối cùng hiện tại làm block trước
        # Tạo block mới: index nối tiếp, prev_hash = hash của block trước
        self.blocks.append(Block(prev.index + 1, data, prev.hash))

    def is_valid(self):
        # Duyệt từ block thứ 1 trở đi (bỏ qua genesis vì không có block trước để so)
        for i in range(1, len(self.blocks)):
            cur = self.blocks[i]                 # block đang xét
            prev = self.blocks[i - 1]            # block liền trước nó

            # KIỂM TRA 1: hash lưu trong block có khớp nội dung hiện tại không?
            #   Nếu ai đó sửa data mà quên hash lại -> lệch -> phát hiện.
            if cur.hash != cur.compute_hash():
                return False, f"Block {i}: nội dung bị sửa (hash không khớp)"

            # KIỂM TRA 2: prev_hash của block này có đúng bằng hash của block trước không?
            #   Nếu kẻ tấn công sửa data + hash lại đúng block i, thì block i+1 vẫn
            #   giữ prev_hash cũ -> đứt xích -> phát hiện.
            if cur.prev_hash != prev.hash:
                return False, f"Block {i}: đứt liên kết với block trước"

        # Qua hết vòng lặp mà không lỗi -> chuỗi toàn vẹn
        return True, "Chain hợp lệ"


# ═════════════════════════════════════════════════════════════════════
# DEMO — chỉ chạy khi gọi trực tiếp file này (không chạy khi bị import)
# ═════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== A) PURE HASH CHAIN ===")
    # Tạo 5 mắt xích từ seed "my-secret-seed"
    for i, h in enumerate(pure_hash_chain("my-secret-seed", 5)):
        print(f"h[{i}] = {h}")                   # in từng mắt xích; mỗi cái là hash của cái trước

    print("\n=== B) BLOCK HASH CHAIN ===")
    chain = HashChain()                          # khởi tạo chuỗi (đã có sẵn genesis)
    chain.add("Henry nạp 100 USDT")              # thêm block 1
    chain.add("Henry mint 1 NFT")                # thêm block 2
    chain.add("Henry chuyển 5 USDT")             # thêm block 3

    # In tóm tắt từng block: cắt hash còn 12 ký tự đầu cho dễ nhìn
    for b in chain.blocks:
        print(f"#{b.index} data={b.data!r:25} prev={b.prev_hash[:12]}.. hash={b.hash[:12]}..")

    print("\nKiểm tra:", chain.is_valid())       # kỳ vọng: hợp lệ

    print("\n=== TAMPER: sửa data block #2, KHÔNG hash lại ===")
    chain.blocks[2].data = "Henry mint 999 NFT"  # sửa lén nội dung, để nguyên hash cũ
    print("Kiểm tra:", chain.is_valid())         # KIỂM TRA 1 bắt được ngay

    print("\n=== TAMPER thông minh: sửa data + hash lại đúng block #2 ===")
    chain.blocks[2].hash = chain.blocks[2].compute_hash()  # hash lại cho khớp data mới
    print("Kiểm tra:", chain.is_valid(),         # KIỂM TRA 2 vẫn bắt được...
          "<- vẫn phát hiện vì block #3 giữ prev_hash cũ")