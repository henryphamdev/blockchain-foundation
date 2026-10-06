**SSH key bảo vệ kết nối (transport), không phải bảo vệ từng commit.** Commit signing (`git commit -S`) là chuyện khác, nói ở cuối.

### Nguyên lý: Challenge–Response bằng chữ ký số

Khi bạn tạo key (`ssh-keygen -t ed25519`):

- **Private key** nằm ở `~/.ssh/id_ed25519` — **không bao giờ rời khỏi PC**
- **Public key** (`id_ed25519.pub`) — bạn paste lên GitLab/GitHub (Settings → SSH Keys)

Khi `git push` qua SSH:

V

visualize

V

visualize show_widget

Verify pass → bạn được nhận diện là chủ tài khoản → GitLab kiểm tra tiếp quyền trên repo (member, protected branch) → cho phép push.

### Vì sao an toàn?

**1. Private key không bao giờ đi qua mạng.** Thứ duy nhất được gửi là *chữ ký* của challenge. Kẻ nghe lén (MITM) bắt được chữ ký cũng vô dụng — vì lần sau server sinh challenge khác, chữ ký cũ không replay được.

**2. Toán một chiều — đúng bài ECDSA hôm trước.** Key mặc định hiện nay là **Ed25519** (đường cong Curve25519, anh em với secp256k1). Server giữ public key, nhưng public → private là bài toán discrete log — bất khả thi. Nên dù GitLab bị hack lộ toàn bộ public keys, không ai giả mạo được bạn.

**3. Mã hóa session là chuyện riêng.** Nhiều người tưởng SSH key dùng để mã hóa code khi push — không phải. Trình tự thực tế:

- Bước đầu tiên: client và server chạy **Diffie-Hellman key exchange** → tạo ra khóa đối xứng (AES/ChaCha20) dùng chung → mọi dữ liệu sau đó (code, refs, objects) được mã hóa bằng khóa này
- SSH key pair chỉ dùng cho **authentication** (bước challenge-response ở trên), diễn ra *bên trong* kênh đã mã hóa

**4. Chống giả mạo server (known_hosts).** Server cũng có cặp key riêng (host key). Lần đầu kết nối bạn thấy prompt "fingerprint... yes/no?" — đó là bạn xác nhận host key, nó được lưu vào `~/.ssh/known_hosts`. Lần sau nếu ai đó giả mạo GitLab server, host key không khớp → SSH chặn ngay với cảnh báo `REMOTE HOST IDENTIFICATION HAS CHANGED`.

### Lưu ý quan trọng: SSH key ≠ ký commit

- SSH key chứng minh **ai đang push** — nhưng `git commit` mặc định **không được ký**. Trường `Author:` chỉ là text trong config, ai cũng sửa được (`git config user.email ceo@company.com` là giả mạo được author)
- Muốn chứng minh **ai tạo commit** → dùng commit signing: `git commit -S` với GPG key hoặc chính SSH key (`git config gpg.format ssh`) → GitLab/GitHub hiện badge **Verified**

# Kịch bản: Chuyện gì thật sự xảy ra khi `git push` qua SSH đến GitLab

> Tài liệu kịch bản kỹ thuật, dùng để trực quan hóa. Nhân vật: **PC** (máy developer, giữ private key Ed25519) và **GITLAB** (server self-hosted, giữ public key). Mọi dữ liệu mẫu bên dưới là ví dụ đúng định dạng thật, có thể đối chiếu với output của `ssh -vvv`.

---

## Bối cảnh trước khi bắt đầu

- PC có cặp key tại `~/.ssh/id_ed25519` (private, 256-bit) và `~/.ssh/id_ed25519.pub` (public).
- Public key đã được paste lên GitLab (Settings → SSH Keys). GitLab lưu nó trong database, gắn với user `henry`, key_id = 42.
- Developer gõ: `git push origin main`. Git thấy remote là `git@gitlab.company.vn:group/repo.git` → gọi chương trình `ssh` làm "đường ống".

**Câu hỏi trung tâm của video:** private key không bao giờ rời PC, mật khẩu không tồn tại — vậy GitLab tin PC bằng cách nào?

---

## HỒI 1 — Bắt tay và thỏa thuận thuật toán (plaintext, ai cũng đọc được)

### Bước 1.1: Trao đổi banner

Hai bên gửi cho nhau một dòng text trần:

```
PC      → GITLAB : SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13
GITLAB  → PC     : SSH-2.0-OpenSSH_9.6p1
```

Đây là những bytes **duy nhất** trên toàn bộ kết nối mà kẻ nghe lén đọc được. Chạy `tcpdump -A port 22` sẽ thấy đúng 2 dòng này, sau đó toàn bộ là rác.

Dòng log tương ứng trong `ssh -vvv`:

```
debug1: Local version string SSH-2.0-OpenSSH_9.6p1
debug1: Remote protocol version 2.0, remote software version OpenSSH_9.6p1
```

### Bước 1.2: SSH_MSG_KEXINIT (message số 20) — "menu" thuật toán

Mỗi bên gửi danh sách thuật toán mình hỗ trợ, kèm 16 bytes ngẫu nhiên (cookie):

```
PC → GITLAB : KEXINIT {
  cookie: 16 bytes random
  kex_algorithms: sntrup761x25519-sha512, curve25519-sha256, ...
  host_key_algorithms: ssh-ed25519, rsa-sha2-512, ...
  ciphers: chacha20-poly1305@openssh.com, aes256-gcm, ...
  macs: hmac-sha2-256-etm, ...
}
GITLAB → PC : KEXINIT { ... danh sách của server ... }
```

Hai bên độc lập chọn thuật toán chung đầu tiên khớp nhau. Log:

```
debug1: kex: algorithm: curve25519-sha256
debug1: kex: host key algorithm: ssh-ed25519
debug1: kex: server->client cipher: chacha20-poly1305@openssh.com
```

**Ý nghĩa:** chưa có gì bí mật, nhưng cookie ngẫu nhiên của cả 2 bên sẽ được trộn vào phép tính ở Hồi 2 — đảm bảo mỗi kết nối là duy nhất.

---

## HỒI 2 — Diffie-Hellman: tạo bí mật chung mà không gửi bí mật (trái tim của mã hóa)

### Bước 2.1: Trao đổi giá trị công khai

Dùng đường cong Curve25519 (họ hàng với secp256k1 trong blockchain):

```
PC:     sinh số ngẫu nhiên a (ephemeral, dùng 1 lần) → tính A = a × G
GITLAB: sinh số ngẫu nhiên b (ephemeral)             → tính B = b × G

PC      → GITLAB : SSH_MSG_KEX_ECDH_INIT  { A }   (message 30)
GITLAB  → PC     : SSH_MSG_KEX_ECDH_REPLY { B, host_key, signature } (message 31)
```

### Bước 2.2: Hai bên tự tính ra CÙNG một bí mật

```
PC:     K = a × B = a × (b × G) = ab × G
GITLAB: K = b × A = b × (a × G) = ab × G     → K giống hệt nhau
```

Kẻ nghe lén thấy A và B nhưng không tính được K — vì suy ra `a` từ `A = a×G` là bài toán discrete log trên đường cong elliptic (một chiều, giống hệt lý do private key → public key trong blockchain là một chiều).

### Bước 2.3: Sinh SESSION ID — nhân vật quan trọng nhất của kịch bản

```
session_id = SHA256( banner_PC ‖ banner_GITLAB ‖ KEXINIT_PC ‖ KEXINIT_GITLAB
                     ‖ host_key ‖ A ‖ B ‖ K )
```

Ví dụ: `session_id = 7f3a9c21e8b4...d90f` (32 bytes).

**Ba tính chất then chốt:**

1. Mỗi kết nối một giá trị khác nhau (vì a, b, cookie đều random mỗi lần).
2. Cả 2 bên tính được, nhưng không bên thứ ba nào tính được (cần K).
3. **Đây chính là "challenge"** — SSH không cần server gửi challenge riêng, vì session_id đã là một số ngẫu nhiên tươi mà cả 2 bên cùng biết.

### Bước 2.4: Server tự chứng minh mình là GitLab thật (chống giả mạo server)

Trong REPLY ở bước 2.1, GitLab gửi kèm **host key** và **chữ ký của session_id bằng host private key**. PC verify rồi so host key với `~/.ssh/known_hosts`:

```
debug1: Server host key: ssh-ed25519 SHA256:kX8mP2vQ...
debug1: Host 'gitlab.company.vn' is known and matches the ED25519 host key.
```

Nếu ai đó giả GitLab (MITM), host key không khớp → SSH in cảnh báo `REMOTE HOST IDENTIFICATION HAS CHANGED!` và ngắt.

### Bước 2.5: SSH_MSG_NEWKEYS (message 21) — bật mã hóa

Từ K và session_id, hai bên derive ra khóa mã hóa đối xứng (ChaCha20) và khóa MAC. Từ điểm này, **mọi byte trên dây đều được mã hóa**. Log:

```
debug2: ssh_set_newkeys: mode 1
debug1: rekey out after 134217728 blocks
```

---

## HỒI 3 — Challenge-Response: PC chứng minh danh tính (trái tim của xác thực)

Toàn bộ hồi này diễn ra **bên trong kênh đã mã hóa** ở Hồi 2.

### Bước 3.1: Hỏi trước — "key này có được chấp nhận không?"

PC không ký ngay. Nó gửi một USERAUTH_REQUEST (message 50) dạng "query", **chưa có chữ ký**, chỉ chứa public key:

```
PC → GITLAB : USERAUTH_REQUEST {
  username:  "git"
  service:   "ssh-connection"
  method:    "publickey"
  signed:    FALSE          ← chỉ hỏi thôi
  algorithm: "ssh-ed25519"
  pubkey:    AAAAC3NzaC1lZDI1NTE5AAAAIGx7... (public key của Henry)
}
```

Log: `debug1: Offering public key: /home/henry/.ssh/id_ed25519 ED25519 SHA256:AbC1...`

### Bước 3.2: GitLab tra cứu key

sshd trên server GitLab **không** đọc file authorized_keys tĩnh. Nó được cấu hình `AuthorizedKeysCommand` → gọi vào GitLab internal API:

```
GET /api/v4/internal/authorized_keys?key=AAAAC3NzaC1lZDI1NTE5AAAAIGx7...
→ tìm thấy: key_id=42, thuộc user "henry"
→ trả về dòng authorized_keys kèm forced command:
  command="/opt/gitlab/embedded/service/gitlab-shell/bin/gitlab-shell key-42",
  no-port-forwarding,no-pty ssh-ed25519 AAAAC3...
```

Key hợp lệ → server trả về:

```
GITLAB → PC : SSH_MSG_USERAUTH_PK_OK (message 60)  — "key này OK, ký đi"
```

Log phía client: `debug1: Server accepts key: /home/henry/.ssh/id_ed25519`

### Bước 3.3: PC ký — khoảnh khắc private key được dùng (nhưng không rời máy)

PC dựng một blob dữ liệu rồi ký bằng **Ed25519 private key**:

```
data_to_sign = session_id ‖ SSH_MSG_USERAUTH_REQUEST ‖ "git"
               ‖ "ssh-connection" ‖ "publickey" ‖ TRUE
               ‖ "ssh-ed25519" ‖ pubkey_blob

signature = Ed25519_Sign(private_key, data_to_sign)
```

Rồi gửi lại request lần 2, lần này `signed: TRUE` kèm chữ ký:

```
PC → GITLAB : USERAUTH_REQUEST { ...như trên..., signed: TRUE, signature: 64 bytes }
```

**Vì sao chống replay:** chữ ký bao trùm session_id — kết nối sau session_id khác → chữ ký cũ vô giá trị. Kẻ nghe lén cũng chẳng thấy gì vì tất cả đã mã hóa từ Hồi 2.

### Bước 3.4: GitLab verify

```
Ed25519_Verify(pubkey_đã_lưu, data_to_sign, signature) → TRUE
GITLAB → PC : SSH_MSG_USERAUTH_SUCCESS (message 52)
```

Log client: `debug1: Authentication succeeded (publickey).`
Log server (`/var/log/auth.log`):

```
sshd: Accepted publickey for git from 118.69.x.x port 52344 ssh2: ED25519 SHA256:AbC1...
```

**Chốt hồi 3:** GitLab giờ biết chắc: "người ở đầu dây kia đang giữ private key ứng với key_id=42 = user henry". Không mật khẩu nào được gõ, không bí mật nào đi qua mạng.

---

## HỒI 4 — Sau xác thực: git protocol chạy bên trong kênh SSH

### Bước 4.1: Mở channel và exec lệnh

```
PC → GITLAB : SSH_MSG_CHANNEL_OPEN "session" (message 90)
PC → GITLAB : SSH_MSG_CHANNEL_REQUEST "exec" → "git-receive-pack 'group/repo.git'"
```

Nhưng nhớ forced command ở bước 3.2: sshd **không** chạy lệnh PC yêu cầu, mà chạy `gitlab-shell key-42` và đưa lệnh gốc vào biến `SSH_ORIGINAL_COMMAND`. gitlab-shell:

1. Gọi internal API: "key-42 (henry) có quyền push vào group/repo không?" (kiểm tra membership, protected branch).
2. Nếu có → mới thực thi `git-receive-pack` thật trên repo.

Đây là lý do mọi user đều SSH bằng cùng user hệ điều hành `git` nhưng GitLab vẫn phân quyền được từng người — danh tính đến từ **key**, không từ OS user.

### Bước 4.2: Ref negotiation (xem bằng GIT_TRACE_PACKET=1)

Hai tiến trình git nói chuyện qua stdin/stdout, đóng gói dạng pkt-line (4 ký tự hex độ dài + nội dung):

```
GITLAB → PC : 00a37d1b8c...9f2 refs/heads/main\0 report-status delete-refs ofs-delta
GITLAB → PC : 0000   (flush — hết danh sách)
PC     → GITLAB : 009b 7d1b8c...9f2 4e8a1d...c07 refs/heads/main\0 report-status
```

Nghĩa: "main của server đang ở commit 7d1b8c, tôi muốn cập nhật thành 4e8a1d".

### Bước 4.3: Truyền packfile

PC tính các object server còn thiếu (commit, tree, blob), nén thành 1 packfile, đẩy qua channel:

```
PC → GITLAB : PACK\x02\x00\x00... (binary, đã nén delta)
```

### Bước 4.4: Báo kết quả

```
GITLAB → PC : 000eunpack ok
GITLAB → PC : 0019ok refs/heads/main
```

Client in ra dòng quen thuộc: `main -> main`. Channel đóng, kết nối TCP đóng.

---

## HỒI 5 — Tổng kết: 3 tầng bảo vệ độc lập


| Tầng             | Cơ chế                                 | Bảo vệ khỏi                      |
| ---------------- | -------------------------------------- | -------------------------------- |
| Định danh server | Host key + known_hosts                 | Giả mạo GitLab (MITM)            |
| Mã hóa kênh      | DH (Curve25519) → ChaCha20             | Nghe lén nội dung code           |
| Định danh client | Ký session_id bằng Ed25519 private key | Giả mạo developer, replay attack |


**Ba câu chốt cho video:**

1. Private key chỉ làm đúng 1 việc: ký session_id — 64 bytes chữ ký là thứ duy nhất "đại diện" nó trên mạng.
2. Session_id vừa là sản phẩm của mã hóa (DH) vừa là challenge của xác thực — 2 hồi khóa vào nhau.
3. Toàn bộ an toàn đứng trên 1 nền toán duy nhất: hàm một chiều trên đường cong elliptic — cùng nền tảng với ví blockchain.

---

## Phụ lục: Lệnh lab đối chiếu từng hồi


| Hồi   | Lệnh                                          | Nhìn thấy gì                                                        |
| ----- | --------------------------------------------- | ------------------------------------------------------------------- |
| 1, 2  | `ssh -vvv git@gitlab.company.vn`              | banner, KEXINIT, thuật toán được chọn, host key, NEWKEYS            |
| 2     | `sudo tcpdump -i any -A 'port 22' -c 200`     | chỉ đọc được banner, sau đó toàn rác → chứng minh mã hóa            |
| 3     | `ssh -vvv ...` (tiếp)                         | Offering public key → Server accepts key → Authentication succeeded |
| 3     | server: `sudo tail -f /var/log/auth.log`      | Accepted publickey ... ED25519 SHA256:...                           |
| 4     | `GIT_TRACE=1 GIT_TRACE_PACKET=1 git push`     | pkt-line: ref cũ/mới, PACK, unpack ok                               |
| 4     | server: `sudo gitlab-ctl tail gitlab-shell`   | key-42 → user henry → check quyền repo                              |
| Bonus | `ssh -vvv -o PubkeyAuthentication=no git@...` | luồng thất bại: server từ chối, không còn method nào                |


```
sudo tcpdump -A port 22
[sudo: authenticate] Password:                
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on enp2s0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
05:32:52.750570 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [S], seq 376620913, win 64240, options [mss 1460,sackOK,TS val 2400364666 ecr 0,nop,wscale 10], length 0
E..<..@.@............j...r.q...................
...z.......

05:32:52.785614 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [S.], seq 741148268, ack 376620914, win 65535, options [mss 1436,sackOK,TS val 3032637034 ecr 2400364666,nop,wscale 10], length 0
E..<..@.3.}............j,-.l.r.r...............
..^j...z...

05:32:52.785670 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 1, win 63, options [nop,nop,TS val 2400364701 ecr 3032637034], length 0
E..4..@.@............j...r.r,-.m...?.n.....
......^j
05:32:52.794346 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 1:43, ack 1, win 63, options [nop,nop,TS val 2400364710 ecr 3032637034], length 42: SSH: SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5
E..^..@.@............j...r.r,-.m...?w......
......^jSSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5

05:32:52.829439 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 43, win 64, options [nop,nop,TS val 3032637077 ecr 2400364710], length 0
E..47.@.3.E............j,-.m.r.....@.......
..^.....
05:32:53.264942 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 1:818, ack 43, win 64, options [nop,nop,TS val 3032637512 ecr 2400364710], length 817: SSH: SSH-2.0-b55c82e
E..e7.@.3.B............j,-.m.r.....@.u.....
..`H....SSH-2.0-b55c82e
....	...`...@.u(
.N".f....sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,kex-strict-s-v00@openssh.com...Assh-ed25519,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256,ssh-rsa...lchacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr...lchacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr...Whmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512,hmac-sha2-256...Whmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512,hmac-sha2-256....none,zlib@openssh.com....none,zlib@openssh.com......................
05:32:53.264987 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 818, win 66, options [nop,nop,TS val 2400365180 ecr 3032637512], length 0
E..4..@.@............j...r..,-	....B.S.....
...|..`H
05:32:53.270156 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], seq 43:1467, ack 818, win 66, options [nop,nop,TS val 2400365185 ecr 3032637512], length 1424
E.....@.@..i.........j...r..,-	....B.......
......`H......)..Oz....*;~'..!...^mlkem768x25519-sha256,sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,ext-info-c,kex-strict-c-v00@openssh.com....ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256...lchacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr...lchacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr....umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1....umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,u
05:32:53.270168 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 1467:1611, ack 818, win 66, options [nop,nop,TS val 2400365185 ecr 3032637512], length 144
E.....@.@..h.........j...r.,,-	....B.......
......`Hmac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1....none,zlib@openssh.com....none,zlib@openssh.com.................
05:32:53.307246 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 1611, win 68, options [nop,nop,TS val 3032637554 ecr 2400365185], length 0
E..47.@.3.E............j,-	..r.....D.......
..`r....
05:32:53.308105 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 1611:2819, ack 818, win 66, options [nop,nop,TS val 2400365223 ecr 3032637554], length 1208
E.....@.@..?.........j...r..,-	....BP......
......`r..........s.a.......k`....dUH.....)Jr.J.....5>.JpVc..y.g.D\O..xJ.pC^N.t(.......C..>"f.$,..L}.A%.y....:.W]..ml91.....NO.......o.,.@.Y......{...Zg....]...R......tO..`M*23u..!L...Qu.."&.=...............[.f.{........D.9.4"........FU.>.8..6/x......+..%..v.!J\.+.}.....i.A..9\......N|..&......!.DG.	.7pA..E9...,gMrG.6.V	.O..Z..v...}...N..r....EW.8....,...z8.@Z+6...*.K"..b...u9..'..o.E..".......[..E/8........<.@.]...e..o...y.K...r.o........}..."...*...1u&.a`....,.'X.c(.,s.o$X..L.!!U.oJ..ma......;(D?.H...j.H...y~[Z+N4..V4.^Q.1........GP`...L.<.jD..\to...5.^..UL..k....	..4Z.......Q....z.c..	.W..W7.'....@......3.}..x...z..b...h......3B..~H.d..gs...[t.]...O....J...H..?.K.B+...P.}.....?...A...@&.....Ym....C.D+6..r.C.<..a.O..P..0J>...Z...4.rv......4...;?..y.S.!?.N...x............q..%H.....b...`.2=......R.V.........../r.......K.......b.s.. XM.q..7.uwo.).8vf9C..Mwl....nK...7.9h0..z...W..O.V;...H....9......#....c....
 B/h.{.....9!-g.rwq.....W~.I^i.I	.J..P.............b......L..}..Fr.i(/mq.U{.z.{es..^7.^...!z>..*."..]..(..Wv...F#....... /D.....9.VB.DPZo8...5......D]..F5F.....#..B.#c...Y	.+qU...
K3.3.........q.{.D.....j.`..-_I.s.....]."...u.....u:Rk..O...=U.....8.D.......~n............Z......AZ...W..4........
05:32:53.343819 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 2819, win 70, options [nop,nop,TS val 3032637591 ecr 2400365223], length 0
E..47.@.3.E............j,-	..r.t...F.......
..`.....
05:32:53.575187 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2050:2066, ack 2819, win 70, options [nop,nop,TS val 3032637822 ecr 2400365223], length 16
E..D7.@.3.E............j,-.n.r.t...F.......
..a~........
...........
05:32:53.575234 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 818, win 68, options [nop,nop,TS val 2400365490 ecr 3032637591,nop,nop,sack 1 {2050:2066}], length 0
E..@..@.@............j...r.t,-	....D.......
......`....
,-.n,-.~
05:32:53.628623 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 818:2050, ack 2819, win 70, options [nop,nop,TS val 3032637876 ecr 2400365490], length 1232
E...7.@.3.@............j,-	..r.t...F.......
..a.........	....3....ssh-ed25519... .*.y....I..P.*(..n....$Z-..i}..e.../.?..=a$H..H@~z.2}...rO2aO0....+.....m....<..UZ.S..4R.,..%..~c..~.w..e.;..-...
.. .'~......D...p..{.j..p......N-.T.`A...J...i......Q.]'...	...x.....GU...N.rF..`......!$.".+.$..n.w8..F.j.e...^.L..@..o'.w<.@x*v..]..@m6W..<....$X..@x%.<...c...v.."........r..=G.7.....fl..V>....RbOV.[..)#.e $#2....i........	.w}.....b0..G.y.......N....@...\.F*yus6...N....KJ`....4d..h...)J....#........*..;..+..o.l..M..o<.eAq.%}wd.]...j.gvR,"..H..N.;y........i.?uK.V....j..\.. ...3.R...........v....B....V..t..U.ug.G.Pc.9%?;...JG..@.c...y']...&(.....I<.t.
.8[.)...........5Z2.m...rW.v...!...I.S9../L...c.Q..P.\&-O..,
...1[F...H&.).	..V....oy......Yo...M.D'Yo.`F^.W}.......$....8.rh_37..98.L.h...6Y....N..m...J..XW5.51
%..f.....2......QD[m..o......e.F..j...c.<]R.@le..,....
..b....=].G.V)O.....S0.+z.Utl.U....w.	.....e.'7.|:B	.-Z]......w.q....3...w[....K.~y.6.......5.:.@Q@$......z,c...c...-.../=.5./qQ...TS...	...|.k.........H.#.....
.....@.d.c..C..HNyMh.........F......'gI.S...c..T..|.W.....&.j!.|...@.................}..:.P...	..w....nX~E...$7...QjleG.|B6...........,.]A..MH..QR.g+Q/.>j#.^.M...S....ssh-ed25519...@.=..).. M.^S..N.n....e.p..|"......O.7cu..._..[.
....w._....&..t	.........
05:32:53.628680 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 2066, win 71, options [nop,nop,TS val 2400365544 ecr 3032637876], length 0
E..4..@.@............j...r.t,-.~...G.......
......a.
05:32:53.645946 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 2819:2835, ack 2066, win 71, options [nop,nop,TS val 2400365561 ecr 3032637876], length 16
E..D..@.@............j...r.t,-.~...G.t.....
......a.....
...........
05:32:53.681006 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 2835, win 70, options [nop,nop,TS val 3032637929 ecr 2400365561], length 0
E..47.@.3.E............j,-.~.r.....F.i.....
..a.....
05:32:53.681057 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 2835:2879, ack 2066, win 71, options [nop,nop,TS val 2400365596 ecr 3032637929], length 44
E..`..@.@............j...r..,-.~...Gf......
......a..q...g.1. @....(B-h".f.O..!.}.T.....&]....t2
05:32:53.716081 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 2879, win 70, options [nop,nop,TS val 3032637964 ecr 2400365596], length 0
E..47.@.3.E............j,-.~.r.....F.......
..b.....
05:32:53.902885 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2066:2662, ack 2879, win 70, options [nop,nop,TS val 3032638151 ecr 2400365596], length 596
E...7.@.3.Co...........j,-.~.r.....F.d.....
..b...../.~....b{..,BOl..q.Y....z.P.{...3..Eq.k....~....D.D.*M..C.....(.O.1....acP.f.........y....Z@3O./_.e .<..Qn./........._..$..-X.i.-\z.m..J/m(.e..9,..l.o.q..].....D.%..0..Y.	/.!.T...#...B.J...i.....!...n.b[.	k..(#.9pX.]~..1..B....D..5......1....L.P&'O.:....cj.@.]Xw.+..K....5....h}j...S..?9.Qp.~?.	F.%dA|Th[.b...2b..>.W..S].L.v3.K.x.B;...;...bm....0.?.4..9^7q*...<0.......Y." ..v}....Em.k.`h.WT7..^\....7o..	..:.n!..)C.]L.b..#.'....OA..=)^<
....k|.........	..ij....)O..:.....	O....b.9..(......#..&I...vF./..(..M..o.8.....ZQ.5.T....O...].H...7....K0..2.'..]-.*.....9."..LQ...=......T..Oh	.L^....9..0.
05:32:53.937142 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2662:2706, ack 2879, win 70, options [nop,nop,TS val 3032638185 ecr 2400365596], length 44
E..`7.@.3.E............j,-...r.....Fg......
..b.........#..`:.P..g....	k...1...;.s[ZT......tn|.

05:32:53.937191 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 2706, win 74, options [nop,nop,TS val 2400365852 ecr 3032638151], length 0
E..4..@.@............j...r..,-.....J.......
......b.
05:32:53.937376 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 2879:2939, ack 2706, win 74, options [nop,nop,TS val 2400365853 ecr 3032638151], length 60
E..p..@.@............j...r..,-.....Ju@.....
......b.._T.c._..9.......d)rrc..Y.^hS.......D...4.E.....a..t...
...g
05:32:53.973211 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 2939, win 70, options [nop,nop,TS val 3032638221 ecr 2400365853], length 0
E..47.@.3.E............j,-...r.....F.9.....
..c.....
05:32:54.194207 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2706:2750, ack 2939, win 70, options [nop,nop,TS val 3032638442 ecr 2400365853], length 44
E..`7.@.3.E............j,-...r.....F.......
..c.......3f.....c...f#S.mM..~.5V..
.WN>.Ie....+....
05:32:54.223863 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 2939:3079, ack 2750, win 74, options [nop,nop,TS val 2400366139 ecr 3032638442], length 140
E.....@.@..d.........j...r..,-.*...J.u.....
...;..c....$...(C.`....&....$c...'t.....)u.HW.....O"BT/..]%.v....)\..r.b....^A.C..........6-C.GQ.....i..x..%a[......C../.....u...S.Ti....4.AW..'...i
05:32:54.258818 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 3079, win 73, options [nop,nop,TS val 3032638507 ecr 2400366139], length 0
E..47.@.3.E............j,-.*.r.x...I.B.....
..d+...;
05:32:54.489233 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2750:2850, ack 3079, win 73, options [nop,nop,TS val 3032638736 ecr 2400366139], length 100
E...7.@.3.EZ...........j,-.*.r.x...I.......
..e....;..;-...F....AQi.....=.....j.....<......(...qm.M....O.0 .$..6....T....e%.]yz_...V%r/......
......'.IL
05:32:54.523538 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 3079:3387, ack 2850, win 74, options [nop,nop,TS val 2400366439 ecr 3032638736], length 308
E..h..@.@............j...r.x,-.....J'0.....
...g..e..j*..!....a?..Dd-sQ6..I.V.o.v. 3y.....t.....q.......I.j}H.}.}.=.~;...Q..;..>.=q.T....{.&<+..Je0.+...Ns....Vy......`................B=f...zk.[HHZ!....s...q.a.0.7...a..:XCZ..#k....~j..	.!..l...y.A!.....>..6....Q.w..Q|.h^z...q...1..i...IfWni........4..]...h.O....w.;.....wW..N..
 .[+...n.[.S.S.x.*.!.H..h.-o..$.
05:32:54.559258 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 3387, win 76, options [nop,nop,TS val 3032638807 ecr 2400366439], length 0
E..47.@.3.E............j,-...r.....L.O.....
..eW...g
05:32:54.782115 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2850:2878, ack 3387, win 76, options [nop,nop,TS val 3032639028 ecr 2400366439], length 28
E..P7.@.3.E............j,-...r.....L.......
..f4...g..!P..i4H..	..o..S.L...FH.b/
05:32:54.782238 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 2878:3506, ack 3387, win 76, options [nop,nop,TS val 3032639029 ecr 2400366439], length 628
E...7.@.3.CG...........j,-...r.....L.N.....
..f5...gjt..z.[.T....F).^.:...*...C..>$>..a|5#....b.Tc.z.j+.D....P...*..*TYh._vj}^.......Qi{r.y.CB..k.X....]...+1..k?$]..v
...F..r.$.+...Sqy]e.:OU..'..t..=.....K.....a"........@.j..X.F...M....v.)2..G.S[.lo.. ..u...Y..i*.QU...S[g...Fli5..lS.E#.......y6.@....Z.6...o..1e.u...".t...?...._.;.9Vt.W.......#..........l_....z-.@.o...PG~Q@..nw&...;!...5.....&....Z..ETIk.......dO|...w..F`gj.6Wn:..pq.....
.`..7....l%&...yX...{F.L.wh9.\...#...G6.	X2..Z.:
..g4..s.... .Z;.5.....G~w.\......4......H+R..=......G..!.5....s...ni"...FW..L.Lz.......e...	..Q...P..IQ.V.	."...W.+~.!.|T-u.i)..bLI.[t..K...9.....	....w.}FM..A..4RS..,cSN...........z.2...}M.
05:32:54.783011 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 3506, win 76, options [nop,nop,TS val 2400366698 ecr 3032639028], length 0
E..4..@.@............j...r..,-.....L.......
...j..f4
05:32:54.783075 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 3387:3439, ack 3506, win 76, options [nop,nop,TS val 2400366698 ecr 3032639028], length 52
E..h..@.@............j...r..,-.....L.......
...j..f4g..Vr......H@..:.(,...3..G.l..t...X.....5...B	
.,...
05:32:54.818957 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 3439, win 76, options [nop,nop,TS val 3032639066 ecr 2400366698], length 0
E..47.@.3.E............j,-...r.....L.......
..fZ...j
05:32:55.039809 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3506:3550, ack 3439, win 76, options [nop,nop,TS val 3032639288 ecr 2400366698], length 44
E..`7.@.3.E............j,-...r.....L)......
..g8...jR.&.,...	..I...9....s\.... ['x|K.a.LA..{....
05:32:55.040082 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 3439:3743, ack 3550, win 76, options [nop,nop,TS val 2400366955 ecr 3032639288], length 304
E..d..@.@..t.........j...r..,-.J...L.*.....
...k..g8...%......t.?.RF...*..2vL._....|..k..9.m....*7N{.g.....6b..p....R.6T..mo...&-#..q-.....C.F....p..,Dp.....b.].;..Y...2B..y..O...`.........Rb...s...ja..$.@....B}}.O.<.Y.ryL...(zB.NA.I.W....c...+Xm.a.[eJ..._....[..b.ZG....BWs:......-......@......\.W.......R.....V...(.LIZg.........._<....W=.0i"..Q..6\......
05:32:55.075585 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 3743, win 79, options [nop,nop,TS val 3032639324 ecr 2400366955], length 0
E..47.@.3.E............j,-.J.r.....O.#.....
..g\...k
05:32:55.297419 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3550:3586, ack 3743, win 79, options [nop,nop,TS val 3032639546 ecr 2400366955], length 36
E..X7.@.3.E............j,-.J.r.....O.......
..h:...k...O.q..K.E.........G.ha.....9..g...
05:32:55.329171 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3586:3678, ack 3743, win 79, options [nop,nop,TS val 3032639576 ecr 2400366955], length 92
E...7.@.3.EZ...........j,-.n.r.....OZ	.....
..hX...k......3..;2.|
..............d..].|,...?..F..0..9.....i...oa..O./k....r.+e..,.s...nP...Y../A.
05:32:55.329172 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3678:3738, ack 3743, win 79, options [nop,nop,TS val 3032639576 ecr 2400366955], length 60
E..p7.@.3.Ey...........j,-...r.....O.......
..hX...k......to.........B..\...$.....J_......-..zC...n...R..T9...Zh
05:32:55.329172 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3738:3862, ack 3743, win 79, options [nop,nop,TS val 3032639577 ecr 2400366955], length 124
E...7.@.3.E8...........j,-...r.....O.......
..hY...k.L......6h..4.(q....zG..>...	...'.A..,.O...r.....R..I.|_..pL...........Y....[(T&........6.....U.m.....&........M.rg......LD.
05:32:55.329229 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 3678, win 76, options [nop,nop,TS val 2400367244 ecr 3032639546], length 0
E..4..@.@............j...r..,-.....L.......
......h:
05:32:55.329387 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 3862, win 76, options [nop,nop,TS val 2400367245 ecr 3032639576], length 0
E..4..@.@............j...r..,-.....L~......
......hX
05:32:55.329753 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 3743:3995, ack 3862, win 76, options [nop,nop,TS val 2400367245 ecr 3032639576], length 252
E..0..@.@............j...r..,-.....L.......
......hX;..[..Z..	C..>v..-C.........|...fdnB..I...U........9@a../	.Xh..`.q?...(...Y.."X.....cm.r.&R.>...'.".../.R..R..SxE..0s...IO.-.u.H.@.TE."...=K..d./-..c.L..P..N.sgj.?.4..?4`P.?.n._.T-..X:	R.@.S.(.F.......&...m.9.a.W.j7..;.+s.........5l..F.....;.@p....O.m.
05:32:55.364973 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 3995, win 81, options [nop,nop,TS val 3032639613 ecr 2400367245], length 0
E..47.@.3.E............j,-...r.....Q}......
..h}....
05:32:55.586474 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3862:3898, ack 3995, win 81, options [nop,nop,TS val 3032639834 ecr 2400367245], length 36
E..X7.@.3.E............j,-...r.....Ql......
..iZ.....Z"TS@.R.....5.(.P[PPJrX..Z...T..j..
05:32:55.627325 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 3898, win 76, options [nop,nop,TS val 2400367543 ecr 3032639834], length 0
E..4..@.@............j...r..,-.....L{......
......iZ
05:32:55.633934 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 3898:4078, ack 3995, win 81, options [nop,nop,TS val 3032639882 ecr 2400367245], length 180
E...7.@.3.D............j,-...r.....Qc......
..i..........*...]...n...E..tA...(w~..	y..s~...)8R..!....O..u+^9.E.P....>..,...e....*.....m.K...D8.i...k2y..p...........w3o..]v*~......KXrQ..0:*d..V...E.b....1..m.......m..thF.95j..w.Z....
05:32:55.633987 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 4078, win 79, options [nop,nop,TS val 2400367549 ecr 3032639882], length 0
E..4..@.@............j...r..,-.Z...Oz......
......i.
05:32:55.638326 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 3995:4039, ack 4078, win 79, options [nop,nop,TS val 2400367554 ecr 3032639882], length 44
E..`..@.@..r.........j...r..,-.Z...O.......
......i.:K.h..6..h.h.%...2.V..EJ.......+.'...
......
05:32:55.638366 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 4039:4075, ack 4078, win 79, options [nop,nop,TS val 2400367554 ecr 3032639882], length 36
E..X..@.@..y.........j...r.8,-.Z...O.......
......i.Meg...:L!....
@....C........-.......
05:32:55.673931 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 4039, win 81, options [nop,nop,TS val 3032639922 ecr 2400367554], length 0
E..47.@.3.E............j,-.Z.r.8...Qz<.....
..i.....
05:32:55.673932 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 4075, win 81, options [nop,nop,TS val 3032639922 ecr 2400367554], length 0
E..47.@.3.E............j,-.Z.r.\...Qz......
..i.....
05:32:55.896117 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 4078:4130, ack 4075, win 81, options [nop,nop,TS val 3032640144 ecr 2400367554], length 52
E..h7.@.3.Ez...........j,-.Z.r.\...Q.......
..j.....p...........bL....0...4...PS...=k..9.Qq...w.h..9...#
05:32:55.896118 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [P.], seq 4130:4202, ack 4075, win 81, options [nop,nop,TS val 3032640144 ecr 2400367554], length 72
E..|7.@.3.Ee...........j,-...r.\...Q&{.....
..j.......f.....5..........
i.......[i......=`...kD............".........;...j..
05:32:55.896259 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 4202, win 79, options [nop,nop,TS val 2400367811 ecr 3032640144], length 0
E..4..@.@............j...r.\,-.....Ow......
......j.
05:32:55.896438 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 4075:4111, ack 4202, win 79, options [nop,nop,TS val 2400367812 ecr 3032640144], length 36
E..X..@.@............j...r.\,-.....O7......
......j.._.#. .*2B....
5........=.TO^.6.3...
05:32:55.896473 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [P.], seq 4111:4171, ack 4202, win 79, options [nop,nop,TS val 2400367812 ecr 3032640144], length 60
E..p..@.@............j...r..,-.....O8......
......j.&..8..,h.d..]V.h.....O......Y.Gd......q..OG(.k$...."Y.
4....
05:32:55.896498 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [F.], seq 4171, ack 4202, win 79, options [nop,nop,TS val 2400367812 ecr 3032640144], length 0
E..4..@.@............j...r..,-.....Ow].....
......j.
05:32:55.932703 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 4111, win 81, options [nop,nop,TS val 3032640179 ecr 2400367812], length 0
E..47.@.3.E............j,-...r.....Qwu.....
..j.....
05:32:55.932703 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 4171, win 81, options [nop,nop,TS val 3032640179 ecr 2400367812], length 0
E..47.@.3.E............j,-...r.....Qw9.....
..j.....
05:32:55.932703 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [.], ack 4172, win 81, options [nop,nop,TS val 3032640180 ecr 2400367812], length 0
E..47.@.3.E............j,-...r.....Qw7.....
..j.....
05:32:56.154567 IP 20.205.243.166.ssh > thanhpv-H81.41066: Flags [F.], seq 4202, ack 4172, win 81, options [nop,nop,TS val 3032640401 ecr 2400367812], length 0
E..47.@.3.E............j,-...r.....QvY.....
..k.....
05:32:56.154609 IP thanhpv-H81.41066 > 20.205.243.166.ssh: Flags [.], ack 4203, win 79, options [nop,nop,TS val 2400368070 ecr 3032640401], length 0
E..4..@.@.o..........j...r..,-.....OuY.....
......k.
```

ssh -vvv [git@github.com](mailto:git@github.com) 2>&1 | tee ssh_debug.log:

```
debug1: OpenSSH_10.2p1 Ubuntu-2ubuntu3.5, OpenSSL 3.5.5 27 Jan 2026
debug3: Running on Linux 7.0.0-28-generic #28-Ubuntu SMP PREEMPT_DYNAMIC Sun Jun 21 01:01:36 UTC 2026 x86_64
debug3: Started with: ssh -vvv git@github.com
debug1: Reading configuration data /etc/ssh/ssh_config
debug3: /etc/ssh/ssh_config line 19: Including file /etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf depth 0
debug1: Reading configuration data /etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf
debug1: /etc/ssh/ssh_config line 21: Applying options for *
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts' -> '/home/thanhpv/.ssh/known_hosts'
debug3: expanded UserKnownHostsFile '~/.ssh/known_hosts2' -> '/home/thanhpv/.ssh/known_hosts2'
debug2: resolving "github.com" port 22
debug3: resolve_host: lookup github.com:22
debug3: channel_clear_timeouts: clearing
debug3: ssh_connect_direct: entering
debug1: Connecting to github.com [20.205.243.166] port 22.
debug3: set_sock_tos: set socket 3 IP_TOS 0xb8
debug1: Connection established.
debug1: no pubkey loaded from /home/thanhpv/.ssh/id_rsa
debug1: identity file /home/thanhpv/.ssh/id_rsa type -1
debug1: no identity pubkey loaded from /home/thanhpv/.ssh/id_rsa
debug1: no pubkey loaded from /home/thanhpv/.ssh/id_ecdsa
debug1: identity file /home/thanhpv/.ssh/id_ecdsa type -1
debug1: no identity pubkey loaded from /home/thanhpv/.ssh/id_ecdsa
debug1: no pubkey loaded from /home/thanhpv/.ssh/id_ecdsa_sk
debug1: identity file /home/thanhpv/.ssh/id_ecdsa_sk type -1
debug1: no identity pubkey loaded from /home/thanhpv/.ssh/id_ecdsa_sk
debug1: loaded pubkey from /home/thanhpv/.ssh/id_ed25519: ED25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4
debug1: identity file /home/thanhpv/.ssh/id_ed25519 type 2
debug1: no identity pubkey loaded from /home/thanhpv/.ssh/id_ed25519
debug1: no pubkey loaded from /home/thanhpv/.ssh/id_ed25519_sk
debug1: identity file /home/thanhpv/.ssh/id_ed25519_sk type -1
debug1: no identity pubkey loaded from /home/thanhpv/.ssh/id_ed25519_sk
debug1: Local version string SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5
debug1: Remote protocol version 2.0, remote software version b55c82e
debug1: compat_banner: no match: b55c82e
debug2: fd 3 setting O_NONBLOCK
debug1: Authenticating to github.com:22 as 'git'
debug3: record_hostkey: found key type ED25519 in file /home/thanhpv/.ssh/known_hosts:1
debug3: record_hostkey: found key type RSA in file /home/thanhpv/.ssh/known_hosts:2
debug3: record_hostkey: found key type ECDSA in file /home/thanhpv/.ssh/known_hosts:3
debug3: load_hostkeys_file: loaded 3 keys from github.com
debug1: load_hostkeys: fopen /home/thanhpv/.ssh/known_hosts2: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts2: No such file or directory
debug3: order_hostkeyalgs: have matching best-preference key type ssh-ed25519-cert-v01@openssh.com, using HostkeyAlgorithms verbatim
debug3: send packet: type 20
debug1: SSH2_MSG_KEXINIT sent
debug3: receive packet: type 20
debug1: SSH2_MSG_KEXINIT received
debug2: local client KEXINIT proposal
debug2: KEX algorithms: mlkem768x25519-sha256,sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,ext-info-c,kex-strict-c-v00@openssh.com
debug2: host key algorithms: ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos: 
debug2: languages stoc: 
debug2: first_kex_follows 0 
debug2: reserved 0 
debug2: peer server KEXINIT proposal
debug2: KEX algorithms: sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,kex-strict-s-v00@openssh.com
debug2: host key algorithms: ssh-ed25519,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256,ssh-rsa
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
debug2: MACs ctos: hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512,hmac-sha2-256
debug2: MACs stoc: hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512,hmac-sha2-256
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos: 
debug2: languages stoc: 
debug2: first_kex_follows 0 
debug2: reserved 0 
debug3: kex_choose_conf: will use strict KEX ordering
debug1: kex: algorithm: sntrup761x25519-sha512
debug1: kex: host key algorithm: ssh-ed25519
debug1: kex: server->client cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug1: kex: client->server cipher: chacha20-poly1305@openssh.com MAC: <implicit> compression: none
debug3: send packet: type 30
debug1: expecting SSH2_MSG_KEX_ECDH_REPLY
debug3: receive packet: type 31
debug1: SSH2_MSG_KEX_ECDH_REPLY received
debug1: Server host key: ssh-ed25519 SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
debug3: record_hostkey: found key type ED25519 in file /home/thanhpv/.ssh/known_hosts:1
debug3: record_hostkey: found key type RSA in file /home/thanhpv/.ssh/known_hosts:2
debug3: record_hostkey: found key type ECDSA in file /home/thanhpv/.ssh/known_hosts:3
debug3: load_hostkeys_file: loaded 3 keys from github.com
debug1: load_hostkeys: fopen /home/thanhpv/.ssh/known_hosts2: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts: No such file or directory
debug1: load_hostkeys: fopen /etc/ssh/ssh_known_hosts2: No such file or directory
debug1: Host 'github.com' is known and matches the ED25519 host key.
debug1: Found key in /home/thanhpv/.ssh/known_hosts:1
debug3: send packet: type 21
debug1: ssh_packet_send2_wrapped: resetting send seqnr 3
debug2: ssh_set_newkeys: mode 1
debug1: rekey out after 134217728 blocks
debug1: SSH2_MSG_NEWKEYS sent
debug1: expecting SSH2_MSG_NEWKEYS
debug3: receive packet: type 21
debug1: ssh_packet_read_poll2: resetting read seqnr 3
debug1: SSH2_MSG_NEWKEYS received
debug2: ssh_set_newkeys: mode 0
debug1: rekey in after 134217728 blocks
debug2: KEX algorithms: mlkem768x25519-sha256,sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256,ext-info-c,kex-strict-c-v00@openssh.com
debug2: host key algorithms: ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,rsa-sha2-512,rsa-sha2-256
debug2: ciphers ctos: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: ciphers stoc: chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr
debug2: MACs ctos: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: MACs stoc: umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
debug2: compression ctos: none,zlib@openssh.com
debug2: compression stoc: none,zlib@openssh.com
debug2: languages ctos: 
debug2: languages stoc: 
debug2: first_kex_follows 0 
debug2: reserved 0 
debug3: send packet: type 5
debug3: receive packet: type 7
debug1: SSH2_MSG_EXT_INFO received
debug3: kex_input_ext_info: extension server-sig-algs
debug1: kex_ext_info_client_parse: server-sig-algs=<ssh-ed25519-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp256-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-rsa-cert-v01@openssh.com,sk-ssh-ed25519@openssh.com,sk-ecdsa-sha2-nistp256@openssh.com,ssh-ed25519,ecdsa-sha2-nistp521,ecdsa-sha2-nistp384,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256,ssh-rsa>
debug3: kex_input_ext_info: extension publickey-hostbound@openssh.com
debug1: kex_ext_info_check_ver: publickey-hostbound@openssh.com=<0>
debug3: receive packet: type 6
debug2: service_accept: ssh-userauth
debug1: SSH2_MSG_SERVICE_ACCEPT received
debug3: send packet: type 50
debug3: receive packet: type 51
debug1: Authentications that can continue: publickey
debug3: start over, passed a different list publickey
debug3: preferred gssapi-with-mic,publickey,keyboard-interactive,password
debug3: authmethod_lookup publickey
debug3: remaining preferred: keyboard-interactive,password
debug3: authmethod_is_enabled publickey
debug1: Next authentication method: publickey
debug3: ssh_get_authentication_socket_path: path '/run/user/1000/gcr/ssh'
debug1: get_agent_identities: bound agent to hostkey
debug1: get_agent_identities: agent returned 1 keys
debug1: Will attempt key: /home/thanhpv/.ssh/id_ed25519 ED25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4 agent
debug1: Will attempt key: /home/thanhpv/.ssh/id_rsa 
debug1: Will attempt key: /home/thanhpv/.ssh/id_ecdsa 
debug1: Will attempt key: /home/thanhpv/.ssh/id_ecdsa_sk 
debug1: Will attempt key: /home/thanhpv/.ssh/id_ed25519_sk 
debug2: pubkey_prepare: done
debug1: Offering public key: /home/thanhpv/.ssh/id_ed25519 ED25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4 agent
debug3: send packet: type 50
debug2: we sent a publickey packet, wait for reply
debug3: receive packet: type 60
debug1: Server accepts key: /home/thanhpv/.ssh/id_ed25519 ED25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4 agent
debug3: sign_and_send_pubkey: using publickey-hostbound-v00@openssh.com with ED25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4
debug3: sign_and_send_pubkey: signing using ssh-ed25519 SHA256:VbqgXESb4iSEsy/zudiKfbzx7qTuxQB8xu941FQXdf4
debug3: send packet: type 50
debug3: receive packet: type 52
Authenticated to github.com ([20.205.243.166]:22) using "publickey".
debug2: fd 5 setting O_NONBLOCK
debug1: channel 0: new session [client-session] (inactive timeout: 0)
debug3: ssh_session2_open: channel_new: 0 (tty)
debug2: channel 0: send open
debug3: send packet: type 90
debug1: Entering interactive session.
debug1: pledge: filesystem
debug3: client_repledge: enter
debug3: receive packet: type 80
debug1: client_input_global_request: rtype hostkeys-00@openssh.com want_reply 0
debug3: client_input_hostkeys: received RSA key SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s
debug3: client_input_hostkeys: received ECDSA key SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM
debug3: client_input_hostkeys: received ED25519 key SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
debug1: client_input_hostkeys: searching /home/thanhpv/.ssh/known_hosts for github.com / (none)
debug3: hostkeys_foreach: reading file "/home/thanhpv/.ssh/known_hosts"
debug3: hostkeys_find: found ssh-ed25519 key at /home/thanhpv/.ssh/known_hosts:1
debug3: hostkeys_find: found ssh-rsa key at /home/thanhpv/.ssh/known_hosts:2
debug3: hostkeys_find: found ecdsa-sha2-nistp256 key at /home/thanhpv/.ssh/known_hosts:3
debug1: client_input_hostkeys: searching /home/thanhpv/.ssh/known_hosts2 for github.com / (none)
debug1: client_input_hostkeys: hostkeys file /home/thanhpv/.ssh/known_hosts2 does not exist
debug3: client_input_hostkeys: 3 server keys: 0 new, 3 retained, 0 incomplete match. 0 to remove
debug1: client_input_hostkeys: no new or deprecated keys from server
debug3: client_repledge: enter
debug2: client_loop: session QoS is now interactive
debug2: fd 3 setting TCP_NODELAY
debug3: set_sock_tos: set socket 3 IP_TOS 0xb8
debug3: receive packet: type 91
debug2: channel_input_open_confirmation: channel 0: callback start
debug2: client_session2_setup: id 0
debug2: channel 0: request pty-req confirm 1
debug3: send packet: type 98
debug1: Sending environment.
debug3: Ignored env SHELL
debug3: Ignored env QT_ACCESSIBILITY
debug1: channel 0: setting env COLORTERM = "truecolor"
debug2: channel 0: request env confirm 0
debug3: send packet: type 98
debug3: Ignored env XDG_CONFIG_DIRS
debug3: Ignored env NVM_INC
debug3: Ignored env XDG_MENU_PREFIX
debug3: Ignored env GNOME_DESKTOP_SESSION_ID
debug3: Ignored env QT_IM_MODULES
debug3: Ignored env PTYXIS_PROFILE
debug3: Ignored env SSH_AUTH_SOCK
debug3: Ignored env MEMORY_PRESSURE_WRITE
debug3: Ignored env XMODIFIERS
debug3: Ignored env DESKTOP_SESSION
debug3: Ignored env GTK_MODULES
debug3: Ignored env DBUS_STARTER_BUS_TYPE
debug3: Ignored env PWD
debug3: Ignored env XDG_SESSION_DESKTOP
debug3: Ignored env LOGNAME
debug3: Ignored env XDG_SESSION_TYPE
debug3: Ignored env GPG_AGENT_INFO
debug3: Ignored env SYSTEMD_EXEC_PID
debug3: Ignored env XAUTHORITY
debug3: Ignored env HOME
debug3: Ignored env USERNAME
debug1: channel 0: setting env LANG = "en_US.UTF-8"
debug2: channel 0: request env confirm 0
debug3: send packet: type 98
debug3: Ignored env LS_COLORS
debug3: Ignored env XDG_CURRENT_DESKTOP
debug3: Ignored env MEMORY_PRESSURE_WATCH
debug3: Ignored env VTE_VERSION
debug3: Ignored env WAYLAND_DISPLAY
debug3: Ignored env INVOCATION_ID
debug3: Ignored env MANAGERPID
debug3: Ignored env NVM_DIR
debug3: Ignored env GNOME_SETUP_DISPLAY
debug3: Ignored env LESSCLOSE
debug3: Ignored env XDG_SESSION_CLASS
debug3: Ignored env TERM
debug3: Ignored env LESSOPEN
debug3: Ignored env USER
debug3: Ignored env DISPLAY
debug3: Ignored env SHLVL
debug3: Ignored env NVM_CD_FLAGS
debug3: Ignored env QT_IM_MODULE
debug3: Ignored env DBUS_STARTER_ADDRESS
debug3: Ignored env MANAGERPIDFDID
debug3: Ignored env XDG_RUNTIME_DIR
debug3: Ignored env DEBUGINFOD_URLS
debug3: Ignored env IM_CONFIG_ENTRY
debug3: Ignored env XDG_DATA_DIRS
debug3: Ignored env PATH
debug3: Ignored env GDMSESSION
debug3: Ignored env XDG_SESSION_EXTRA_DEVICE_ACCESS
debug3: Ignored env DBUS_SESSION_BUS_ADDRESS
debug3: Ignored env NVM_BIN
debug3: Ignored env PTYXIS_VERSION
debug3: Ignored env FLATPAK_TTY_PROGRESS
debug3: Ignored env _
debug2: channel 0: request shell confirm 1
debug3: send packet: type 98
debug3: client_repledge: enter
debug1: pledge: fork
debug2: channel_input_open_confirmation: channel 0: callback done
debug2: channel 0: open confirm rwindow 32000 rmax 35000
debug3: receive packet: type 100
debug2: channel_input_status_confirm: type 100 id 0
PTY allocation request failed on channel 0
debug3: receive packet: type 99
debug2: channel_input_status_confirm: type 99 id 0
debug2: shell request accepted on channel 0
debug2: channel 0: rcvd ext data 3
debug2: channel 0: rcvd ext data 12
debug2: channel 0: rcvd ext data 2
debug2: channel 0: rcvd ext data 76
debug2: channel 0: rcvd ext data 1
debug3: receive packet: type 98
debug1: client_input_channel_req: channel 0 rtype exit-status reply 0
debug3: receive packet: type 96
debug2: channel 0: rcvd eof
debug2: channel 0: output open -> drain
debug3: receive packet: type 97
debug2: channel 0: rcvd close
debug2: chan_shutdown_read: channel 0: (i0 o1 sock -1 wfd 4 efd 6 [write])
debug2: channel 0: input open -> closed
debug3: channel 0: will not send data after close
debug2: channel 0: obuf_empty delayed efd 6/(94)
Hi henryphamdev! You've successfully authenticated, but GitHub does not provide shell access.
debug2: channel 0: written 94 to efd 6
debug3: channel 0: will not send data after close
debug2: channel 0: obuf empty
debug2: chan_shutdown_write: channel 0: (i3 o1 sock -1 wfd 5 efd 6 [write])
debug2: channel 0: output drain -> closed
debug2: channel 0: almost dead
debug2: channel 0: gc: notify user
debug2: channel 0: gc: user detached
debug2: channel 0: send_close2
debug2: channel 0: send close for remote id 43
debug3: send packet: type 97
debug2: channel 0: is dead
debug2: channel 0: garbage collecting
debug1: channel 0: free: client-session, nchannels 1
debug3: channel 0: status: The following connections are open:
  #0 client-session (t4 [session] r43 nm0 i3/0 o3/0 e[write]/0 fd -1/-1/6 sock -1 cc -1 nc0 io 0x00/0x00 RTI)

Connection to github.com closed.
debug3: send packet: type 1
Transferred: sent 3844, received 3756 bytes, in 0.5 seconds
Bytes per second: sent 7466.8, received 7295.9
debug1: Exit status 1
```

# Phân tích `ssh -vvv git@github.com` — đối chiếu với tcpdump, khép kín vòng lab

> Nguồn 1: tcpdump (nhìn từ GIỮA DÂY — chỉ thấy bytes, sau NEWKEYS toàn rác).
> Nguồn 2: ssh -vvv (nhìn từ ĐẦU MÚT — thấy ý nghĩa từng message, trước khi mã hóa / sau khi giải mã).
> Ghép 2 nguồn: mỗi dòng `send/receive packet: type N` bên debug ứng với đúng 1 packet bên tcpdump.

## Bảng mã message SSH xuất hiện trong log (đọc bảng này trước)


| type          | Tên                                 | Vai trò                                             |
| ------------- | ----------------------------------- | --------------------------------------------------- |
| 20            | KEXINIT                             | Gửi menu thuật toán                                 |
| 30            | KEX_ECDH_INIT                       | Client gửi giá trị công khai DH                     |
| 31            | KEX_ECDH_REPLY                      | Server: giá trị DH + host key + chữ ký              |
| 21            | NEWKEYS                             | Bật mã hóa                                          |
| 5 / 6         | SERVICE_REQUEST / ACCEPT            | Xin mở dịch vụ ssh-userauth                         |
| 7             | EXT_INFO                            | Server khai báo extension                           |
| 50            | USERAUTH_REQUEST                    | Yêu cầu xác thực (none / publickey chưa ký / đã ký) |
| 51            | USERAUTH_FAILURE                    | "Chưa được, các method còn lại là..."               |
| 60            | USERAUTH_PK_OK                      | "Key hợp lệ, ký đi"                                 |
| 52            | USERAUTH_SUCCESS                    | Xác thực thành công                                 |
| 90 / 91       | CHANNEL_OPEN / CONFIRM              | Mở kênh làm việc                                    |
| 80            | GLOBAL_REQUEST                      | Server chủ động thông báo (hostkeys)                |
| 98 / 99 / 100 | CHANNEL_REQUEST / SUCCESS / FAILURE | pty, env, shell...                                  |
| 96 / 97       | CHANNEL_EOF / CLOSE                 | Đóng kênh                                           |
| 1             | DISCONNECT                          | Chào tạm biệt                                       |


---

## HỒI 0 — Chuẩn bị phía client (trước khi có byte nào lên mạng)

```
debug1: Reading configuration data /etc/ssh/ssh_config
debug1: Connecting to github.com [20.205.243.166] port 22.
debug1: Connection established.
```

**Comment:** đọc config → resolve DNS → TCP handshake (3 packet đầu bên tcpdump).

```
debug1: no pubkey loaded from /home/thanhpv/.ssh/id_rsa        (type -1 = không có)
debug1: loaded pubkey from /home/thanhpv/.ssh/id_ed25519: ED25519 SHA256:VbqgXESb4iSE...
```

**Comment:** ssh dò lần lượt các tên key mặc định (id_rsa, id_ecdsa, id_ecdsa_sk, id_ed25519, id_ed25519_sk). Máy này chỉ có đúng 1 key **Ed25519**, fingerprint `SHA256:Vbqg...` — đây là "nhân vật PC" của kịch bản. Ghi nhớ fingerprint này, nó sẽ xuất hiện lại ở Hồi 3.

---

## HỒI 1 — Banner + KEXINIT

```
debug1: Local version string SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5
debug1: Remote protocol version 2.0, remote software version b55c82e
debug1: compat_banner: no match: b55c82e
```

**Comment:** khớp 2 packet plaintext bên tcpdump (42 bytes và phần đầu packet 817 bytes). Dòng `compat_banner: no match` = OpenSSH tra bảng "phần mềm cũ có bug cần né" — không nhận ra `b55c82e` (vì là server tự viết của GitHub) → không áp workaround nào.

```
debug3: send packet: type 20      ← KEXINIT của PC     = packet 1424+144 bytes
debug3: receive packet: type 20   ← KEXINIT của GitHub = packet 817 bytes
debug2: local client KEXINIT proposal:  KEX: mlkem768x25519-sha256,sntrup761x25519-sha512,...
debug2: peer server KEXINIT proposal:   KEX: sntrup761x25519-sha512,...
```

**Comment:** ssh -vvv in nguyên văn 2 "menu" — chính là phần text đọc được trong tcpdump. Đối chiếu xong luật chọn:

```
debug3: kex_choose_conf: will use strict KEX ordering     ← cả 2 bật kex-strict (chống Terrapin)
debug1: kex: algorithm: sntrup761x25519-sha512            ← mlkem768 của client bị loại vì server không có
debug1: kex: host key algorithm: ssh-ed25519
debug1: kex: server->client cipher: chacha20-poly1305@openssh.com MAC: <implicit>
```

`MAC: <implicit>` = chacha20-poly1305 là AEAD, tự tích hợp xác thực, không cần HMAC riêng.

---

## HỒI 2 — Trao đổi khóa + xác minh server

```
debug3: send packet: type 30                     ← KEX_ECDH_INIT  = packet 1208 bytes (sntrup761 pubkey 1158B + x25519 32B)
debug3: receive packet: type 31                  ← KEX_ECDH_REPLY = packet 1232 bytes
debug1: Server host key: ssh-ed25519 SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU
```

**Comment:** fingerprint `SHA256:+DiY3...` chính là chuỗi `ssh-ed25519` LẦN 1 nhìn thấy trong tcpdump. Có thể kiểm chứng độc lập: đây đúng là Ed25519 host key mà GitHub công bố tại trang tài liệu fingerprints của họ. Chuỗi `ssh-ed25519` lần 2 (kèm `@` = 64 bytes) là chữ ký — debug không in riêng nhưng việc verify nằm ẩn trong bước tiếp:

```
debug3: record_hostkey: found key type ED25519 in file /home/thanhpv/.ssh/known_hosts:1
debug1: Host 'github.com' is known and matches the ED25519 host key.
debug1: Found key in /home/thanhpv/.ssh/known_hosts:1
```

**Comment — bước 2.4 kịch bản, chống MITM:** PC (1) verify chữ ký bằng host key server gửi, (2) so host key đó với dòng 1 của known_hosts → khớp → server là GitHub thật. Nếu không khớp, chỗ này sẽ là cảnh báo REMOTE HOST IDENTIFICATION HAS CHANGED.

```
debug3: send packet: type 21                     ← NEWKEYS của PC     = packet 16 bytes lúc 53.645
debug1: ssh_packet_send2_wrapped: resetting send seqnr 3
debug3: receive packet: type 21                  ← NEWKEYS của server = packet 16 bytes lúc 53.575
debug1: rekey in after 134217728 blocks
```

**Comment:** khớp chính xác 2 packet 16 bytes. `resetting seqnr` = hành vi của strict KEX (đánh lại số thứ tự message — chặn kiểu tấn công chèn message của Terrapin). `rekey after 134217728 blocks` = cứ truyền ~8GB sẽ tự thay khóa mã hóa mới. **Từ dòng này, tcpdump mù — nhưng ssh -vvv vẫn sáng.**

---

## HỒI 3 — Xác thực: xác nhận từng suy luận của bảng tcpdump

```
debug3: send packet: type 5                      ← = packet 44 bytes (53.681) ✓ đúng suy luận SERVICE_REQUEST
debug3: receive packet: type 7                   ← = packet 596 bytes (53.902) ✓ đúng suy luận EXT_INFO
debug1: kex_ext_info_client_parse: server-sig-algs=<...18 thuật toán...>
debug3: kex_input_ext_info: extension publickey-hostbound@openssh.com
```

**Comment:** packet 596 bytes to vì chứa danh sách 18 thuật toán chữ ký. Extension `publickey-hostbound` — chi tiết đắt giá, xem bước ký bên dưới.

```
debug3: receive packet: type 6                   ← = packet 44 bytes (53.937) ✓ SERVICE_ACCEPT
debug3: send packet: type 50                     ← = packet 60 bytes (53.937) ✓ auth method "none" (thăm dò)
debug3: receive packet: type 51                  ← = packet 44 bytes (54.194) ✓ FAILURE
debug1: Authentications that can continue: publickey
```

**Comment:** GitHub từ chối lịch sự và nói "tôi chỉ nhận publickey" — không hề có option password.

```
debug3: ssh_get_authentication_socket_path: path '/run/user/1000/gcr/ssh'
debug1: get_agent_identities: agent returned 1 keys
debug1: Will attempt key: /home/thanhpv/.ssh/id_ed25519 ED25519 SHA256:Vbqg... agent
```

**Comment — chi tiết mới mà tcpdump không thể thấy:** private key không do lệnh `ssh` trực tiếp cầm, mà nằm trong **ssh-agent** (ở đây là GNOME keyring, socket `/run/user/1000/gcr/ssh`). Lát nữa chữ ký sẽ do agent tạo — thêm 1 lớp cách ly: ngay cả tiến trình ssh cũng không chạm vào private key.

```
debug1: Offering public key: ... ED25519 SHA256:Vbqg... agent
debug3: send packet: type 50                     ← = packet 140 bytes (54.223) ✓ Bước 3.1: hỏi trước, CHƯA ký
debug2: we sent a publickey packet, wait for reply
debug3: receive packet: type 60                  ← = packet 100 bytes (54.489) ✓ Bước 3.2: PK_OK
debug1: Server accepts key: ... ED25519 SHA256:Vbqg...
```

```
debug3: sign_and_send_pubkey: using publickey-hostbound-v00@openssh.com with ED25519 SHA256:Vbqg...
debug3: sign_and_send_pubkey: signing using ssh-ed25519
debug3: send packet: type 50                     ← = packet 308 bytes (54.523) ✓ Bước 3.3: KHOẢNH KHẮC KÝ
```

**Comment — trái tim của toàn bộ lab:**

- Blob được ký = `session_id ‖ request ‖ ... ‖ HOST KEY CỦA SERVER` — vì dùng **publickey-hostbound**: chữ ký trói vào cả danh tính server, nên dù một server độc hại lừa được agent ký, chữ ký đó không dùng lại được với GitHub. Đây cũng là lý do packet 308 bytes (to hơn ước tính thông thường ~50 bytes — cộng thêm host key blob).
- Chữ ký do agent tạo, private key chưa từng rời keyring.

```
debug3: receive packet: type 52                  ← = packet 28 bytes (54.782) ✓ Bước 3.4
Authenticated to github.com ([20.205.243.166]:22) using "publickey".
```

**Comment:** dòng không có prefix debug — thông báo chính thức. Toàn bộ Hồi 3: 4 packet, đúng như bảng tcpdump `140 → 100 → 308 → 28`.

---

## HỒI 4 — Channel + "shell" + đóng kết nối

```
debug3: send packet: type 90                     ← = packet 52 bytes (54.783) ✓ CHANNEL_OPEN
debug3: receive packet: type 80                  ← = packet 628 bytes (54.782) ✓ GLOBAL_REQUEST
debug1: client_input_global_request: rtype hostkeys-00@openssh.com
debug3: client_input_hostkeys: received RSA / ECDSA / ED25519 key ...
debug3: client_input_hostkeys: 3 server keys: 0 new, 3 retained, 0 to remove
```

**Comment:** giải mã được bí ẩn packet 628 bytes — server gửi **cả 3 host key** (RSA, ECDSA, Ed25519) qua cơ chế hostkeys-00 để client cập nhật known_hosts nếu server sắp thay key. Máy này đã có đủ 3 → "0 new".

```
debug3: receive packet: type 91                  ← = packet 44 bytes (55.039) ✓ CHANNEL_OPEN_CONFIRMATION
debug2: channel 0: request pty-req confirm 1     ┐
debug1: Sending environment. (COLORTERM, LANG)   ├← = packet 304 bytes (55.040) ✓ pty + env + shell
debug2: channel 0: request shell confirm 1       ┘
debug3: receive packet: type 100
PTY allocation request failed on channel 0       ← GitHub TỪ CHỐI cấp terminal (type 100 = FAILURE)
debug3: receive packet: type 99                  ← nhưng CHẤP NHẬN shell request (type 99 = SUCCESS)
debug2: channel 0: rcvd ext data 3/12/2/76/1     ← tổng 94 bytes trên stderr
Hi henryphamdev! You've successfully authenticated, but GitHub does not provide shell access.
```

**Comment:** đúng chuỗi packet 36/92/60/124 bên tcpdump. "Shell" của GitHub chỉ làm 1 việc: in câu chào 94 bytes (map user từ key: fingerprint Vbqg... → henryphamdev) rồi thoát với exit status 1. `ext data` = stderr của channel — GitHub cố tình in ra stderr thay vì stdout.

```
debug3: receive packet: type 96 / 97             ← EOF + CLOSE
debug3: send packet: type 97 / type 1            ← CLOSE + DISCONNECT
Transferred: sent 3844, received 3756 bytes, in 0.5 seconds
```

**Comment:** tổng chỉ ~7.6KB cho toàn bộ màn kịch 5 hồi. Khớp phần FIN/ACK cuối tcpdump.

---

## Tổng kết vòng lab đã khép kín


| Suy luận từ tcpdump (theo kích thước) | Xác nhận từ ssh -vvv                                      | Kết quả            |
| ------------------------------------- | --------------------------------------------------------- | ------------------ |
| 44B = SERVICE_REQUEST                 | send type 5                                               | ✓                  |
| 596B = EXT_INFO danh sách dài         | receive type 7, server-sig-algs 18 mục                    | ✓                  |
| 60B = auth "none" thăm dò             | send type 50, rồi nhận FAILURE "publickey"                | ✓                  |
| 140B = offer key chưa ký              | Offering public key + send type 50                        | ✓                  |
| 100B = PK_OK                          | receive type 60, Server accepts key                       | ✓                  |
| 308B = request đã ký                  | sign_and_send_pubkey + send type 50 (to hơn vì hostbound) | ✓                  |
| 28B = SUCCESS                         | receive type 52, Authenticated                            | ✓                  |
| 628B = "thông tin server sau auth"    | type 80 hostkeys-00: server gửi 3 host key                | ✓ (rõ hơn dự đoán) |
| 92/124B = câu chào Hi username        | ext data 94 bytes trên stderr                             | ✓                  |


**3 kiến thức mới chỉ ssh -vvv mới lộ ra (tcpdump không bao giờ thấy được):**

1. **ssh-agent**: private key nằm trong GNOME keyring, chữ ký do agent tạo — tiến trình ssh cũng không đọc được key.
2. **publickey-hostbound**: chữ ký trói thêm host key của server → chống cả kịch bản server độc hại lừa agent ký hộ.
3. **hostkeys-00**: server chủ động gửi toàn bộ host key sau khi auth để client chuẩn bị cho việc xoay key trong tương lai.


# Phân tích tcpdump thực tế: PC ↔ GitHub qua SSH (map vào kịch bản 5 hồi)

> Log gốc: `sudo tcpdump -A port 22`, capture ngày chạy lab.
> Hai nhân vật: **PC** = `thanhpv-H81` (port 41066, OpenSSH 10.2p1 Ubuntu) và **SERVER** = `20.205.243.166` (port 22).

## Phát hiện số 0 — trước khi phân tích: server này là ai?

- IP `20.205.243.166` thuộc dải Azure Đông Nam Á mà **GitHub** dùng cho `github.com` — đây KHÔNG phải GitLab self-hosted.
- Banner server: `SSH-2.0-b55c82e` — GitHub không chạy OpenSSH mà chạy SSH frontend tự viết (nội bộ gọi là babeld); phần sau `SSH-2.0-` là **commit SHA của bản build**, thay vì tên phần mềm. So sánh: PC gửi `SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5` — khai rõ phần mềm + bản vá.
- Bài học phụ: banner là plaintext nên attacker luôn biết bạn chạy OpenSSH phiên bản nào → lý do nên vá OpenSSH đều đặn.

---

## GIAI ĐOẠN 0 — TCP 3-way handshake (chưa dính gì đến SSH)

```
05:32:52.750570  PC → SERVER   Flags [S]   seq 376620913          ← SYN
05:32:52.785614  SERVER → PC   Flags [S.]  seq 741148268, ack ...  ← SYN-ACK
05:32:52.785670  PC → SERVER   Flags [.]   ack 1                   ← ACK
```

**Comment:** TCP mở kênh truyền bytes tin cậy. RTT đo được ≈ 35ms (52.750 → 52.785). Mọi thứ của SSH chạy bên trên kênh này.

---

## HỒI 1 — Banner + KEXINIT (plaintext — đây là TẤT CẢ những gì đọc được)

### 1.1. Banner của PC (length 42)
```
05:32:52.794346  PC → SERVER  length 42:
SSH: SSH-2.0-OpenSSH_10.2p1 Ubuntu-2ubuntu3.5
```
**Comment:** đúng bước 1.1 kịch bản. Text trần, tcpdump -A đọc được nguyên văn.

### 1.2. Banner + KEXINIT của SERVER gộp chung 1 packet (length 817)
```
05:32:53.264942  SERVER → PC  length 817:
SSH-2.0-b55c82e
....sntrup761x25519-sha512,sntrup761x25519-sha512@openssh.com,
curve25519-sha256,...,kex-strict-s-v00@openssh.com
...ssh-ed25519,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256,ssh-rsa
...chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,...
...hmac-sha2-512-etm@openssh.com,...
...none,zlib@openssh.com
```
**Comment — đây là SSH_MSG_KEXINIT (message 20) của server, bước 1.2 kịch bản.** Đọc được nguyên văn "menu" của GitHub:
- **kex_algorithms:** ưu tiên `sntrup761x25519-sha512` (hậu lượng tử lai: NTRU Prime + X25519)
- **host_key:** hỗ trợ `ssh-ed25519` đứng đầu
- **cipher:** `chacha20-poly1305` đứng đầu
- `kex-strict-s-v00@openssh.com`: server bật strict KEX — bản vá lỗ hổng Terrapin (CVE-2023-48795)
- Các dấu `....` trước mỗi danh sách là bytes nhị phân: length prefix của SSH wire format + 16 bytes cookie ngẫu nhiên (không in ra được thành chữ)

### 1.3. KEXINIT của PC, bị TCP cắt làm 2 segment (1424 + 144 bytes)
```
05:32:53.270156  PC → SERVER  length 1424:
...mlkem768x25519-sha256,sntrup761x25519-sha512,...,curve25519-sha256,
...,ext-info-c,kex-strict-c-v00@openssh.com
...ssh-ed25519-cert-v01@openssh.com,...,ssh-ed25519,ecdsa-...,rsa-sha2-512,...
...chacha20-poly1305@openssh.com,...
05:32:53.270168  PC → SERVER  length 144:  (phần đuôi danh sách MAC + compression)
```
**Comment:**
- PC (OpenSSH 10.2) ưu tiên `mlkem768x25519-sha256` — hậu lượng tử chuẩn NIST ML-KEM. Nhưng server KHÔNG có trong menu → luật chọn: **thuật toán đầu tiên trong danh sách client mà server cũng hỗ trợ** → cả 2 chốt `sntrup761x25519-sha512`.
- `ext-info-c`: client báo "tôi hiểu message EXT_INFO" (server sẽ dùng sau NEWKEYS).
- `kex-strict-c-v00`: client cũng bật strict KEX → cả 2 bên chống Terrapin.
- Packet dài hơn MSS (1436) nên TCP tự cắt làm 2 — nhắc lại: SSH không quan tâm, nó chỉ thấy stream bytes.

**KẾT QUẢ THỎA THUẬN (suy ra từ 2 menu):** kex = `sntrup761x25519-sha512`, host key = `ssh-ed25519`, cipher = `chacha20-poly1305@openssh.com`.

---

## HỒI 2 — Trao đổi khóa (bắt đầu có bytes "rác" — nhưng rác CÓ CẤU TRÚC)

### 2.1. SSH_MSG_KEX_ECDH_INIT — PC gửi giá trị công khai (length 1208)
```
05:32:53.308105  PC → SERVER  length 1208:
..........s.a.......k`....dUH.....)Jr.J.....5>.JpVc..  (toàn bytes ngẫu nhiên)
```
**Comment — bước 2.1 kịch bản, phía PC.** Vì sao 1208 bytes trong khi X25519 thuần chỉ cần 32 bytes? Vì kex lai hậu lượng tử: public key **sntrup761 = 1158 bytes** + **x25519 = 32 bytes** + header ≈ 1208. Trông như rác vì key vốn dĩ LÀ số ngẫu nhiên — nhưng đây chưa phải mã hóa, chỉ là dữ liệu nhị phân.

### 2.2. SSH_MSG_KEX_ECDH_REPLY — server trả lời (length 1232) — packet quan trọng nhất log
```
05:32:53.628623  SERVER → PC  length 1232:
.....3....ssh-ed25519... .*.y....I..P.*(..n....   ← chuỗi "ssh-ed25519" lần 1
<~1000 bytes nhị phân>
...S....ssh-ed25519...@.=..).. M.^S..N.n....       ← chuỗi "ssh-ed25519" lần 2
```
**Comment — bước 2.1 + 2.4 kịch bản.** Đọc được 2 lần chuỗi ASCII `ssh-ed25519`, và đây chính là bằng chứng vàng:
1. **Lần 1** = header của **HOST KEY** — public key định danh server GitHub (32 bytes theo sau). Đây là key mà PC so với `~/.ssh/known_hosts`.
2. Khối nhị phân giữa = **KEM ciphertext** sntrup761 (1039 bytes) + giá trị x25519 của server → nguyên liệu để 2 bên cùng tính bí mật K.
3. **Lần 2** = header của **CHỮ KÝ Ed25519** (byte `@` = 0x40 = 64 = độ dài chữ ký) — server ký lên exchange hash (session_id) bằng host private key → chứng minh "tôi là chủ thật của host key này". Đúng cơ chế chống MITM ở bước 2.4.

Sau packet này, cả 2 bên đã tự tính ra `session_id` — nhân vật chính của Hồi 3.

### 2.3. SSH_MSG_NEWKEYS — 2 packet 16 bytes đối xứng
```
05:32:53.575187  SERVER → PC  length 16   ← NEWKEYS của server (đến TRƯỚC reply do mạng reorder!)
05:32:53.645946  PC → SERVER  length 16   ← NEWKEYS của PC
```
**Comment — bước 2.5 kịch bản.** Message NEWKEYS chỉ có 1 byte payload (số 21) + padding → 16 bytes. Chi tiết mạng hay: packet NEWKEYS của server đến sớm hơn packet REPLY 1232 bytes (xem dòng `sack 1 {2050:2066}` lúc 53.575234 — TCP của PC báo "tôi nhận được đoạn 2050-2066 nhưng còn thiếu đoạn trước") → TCP tự sắp xếp lại, SSH không hề biết.

**⚡ TỪ ĐÂY TRỞ XUỐNG: 100% ĐÃ MÃ HÓA ChaCha20-Poly1305. Không đọc được nội dung — chỉ suy luận từ chiều + kích thước + thứ tự.**

---

## HỒI 3 — Xác thực (mã hóa toàn bộ — suy luận theo kích thước)

| Thời điểm | Chiều | Bytes | Suy luận (theo giao thức chuẩn) | Map kịch bản |
|---|---|---|---|---|
| 53.681057 | PC → S | 44 | SERVICE_REQUEST "ssh-userauth" | mở dịch vụ xác thực |
| 53.902885 | S → PC | 596 | EXT_INFO — server gửi `server-sig-algs` (danh sách dài → packet to) | (mở rộng) |
| 53.937142 | S → PC | 44 | SERVICE_ACCEPT | |
| 53.937376 | PC → S | 60 | USERAUTH_REQUEST method **"none"** — thăm dò xem server cho phép method gì | |
| 54.194207 | S → PC | 44 | USERAUTH_FAILURE, kèm "publickey" — cách server nói "chỉ nhận key" | |
| 54.223863 | PC → S | **140** | **USERAUTH_REQUEST publickey, signed=FALSE** — gửi public key hỏi trước, CHƯA ký (packet vừa đủ chứa pubkey blob Ed25519 ~51 bytes + metadata) | **Bước 3.1** |
| 54.489233 | S → PC | **100** | **SSH_MSG_USERAUTH_PK_OK** — "key này có trong tài khoản, ký đi" (echo lại pubkey blob → ~100 bytes khớp) | **Bước 3.2** |
| 54.523538 | PC → S | **308** | **USERAUTH_REQUEST signed=TRUE** — chứa CHỮ KÝ Ed25519 64 bytes lên (session_id ‖ request). Private key vừa được dùng — ngay tại packet này — nhưng thứ đi qua dây chỉ là chữ ký | **Bước 3.3** |
| 54.782115 | S → PC | **28** | **USERAUTH_SUCCESS** — packet nhỏ nhất giai đoạn này, đúng đặc trưng: message SUCCESS chỉ có 1 byte payload | **Bước 3.4** |

**Comment tổng:** toàn bộ màn challenge-response gói trong ~0.56 giây (54.223 → 54.782), 4 packet, và kẻ nghe lén (chính là tcpdump của bạn) không đọc được một byte ý nghĩa nào — trong khi ở Hồi 1 đọc được tất cả. Đó là minh chứng trực quan nhất cho ranh giới NEWKEYS.

---

## HỒI 4 — Sau xác thực: mở channel và chạy lệnh

| Thời điểm | Chiều | Bytes | Suy luận | Map kịch bản |
|---|---|---|---|---|
| 54.782238 | S → PC | 628 | GLOBAL_REQUEST / thông tin server sau auth (không giải mã được) | |
| 54.783075 | PC → S | 52 | **CHANNEL_OPEN "session"** | Bước 4.1 |
| 55.039809 | S → PC | 44 | CHANNEL_OPEN_CONFIRMATION | |
| 55.040082 | PC → S | 304 | CHANNEL_REQUEST: pty-req + env + shell (bạn chạy `ssh` trần, không kèm lệnh git → client xin shell) | Bước 4.1 |
| 55.297–55.329 | S → PC | 36+92+60+124 | Phản hồi channel + **CHANNEL_DATA**: nhiều khả năng là dòng chào quen thuộc "Hi <username>! You've successfully authenticated, but GitHub does not provide shell access." (~90 ký tự, khớp cỡ packet 92/124) | Bước 4.2* |
| 55.329–55.638 | 2 chiều | 252/36/44/36... | CHANNEL_EOF, CHANNEL_REQUEST exit-status, CHANNEL_CLOSE 2 chiều | Bước 4.4 |
| 55.896–56.154 | 2 chiều | FIN/ACK | TCP đóng kết nối tử tế 4 bước | |

*Lưu ý: vì capture này là `ssh` trần (không phải `git push`), nên KHÔNG có ref negotiation / packfile của Hồi 4 kịch bản. Muốn thấy pkt-line và PACK, chạy lại tcpdump trong lúc `git push` — nhưng cũng sẽ chỉ thấy các packet CHANNEL_DATA to dần (packfile), toàn bộ vẫn mã hóa. Muốn ĐỌC nội dung git protocol thì dùng `GIT_TRACE_PACKET=1` (đọc ở 2 đầu, trước khi mã hóa) chứ không phải tcpdump (đọc giữa dây, sau khi mã hóa).

---

## Tổng kết 4 bằng chứng thực nghiệm thu được từ log

1. **Ranh giới plaintext/ciphertext nằm đúng tại NEWKEYS** (2 packet 16 bytes lúc 53.575 và 53.645): trước đó đọc được banner + toàn bộ menu thuật toán; sau đó 100% rác.
2. **Host key và chữ ký của server nhìn thấy được** (2 chuỗi `ssh-ed25519` trong packet 1232 bytes) — vì KEX_REPLY diễn ra TRƯỚC khi bật mã hóa. Public key vốn không cần giấu.
3. **Private key của bạn không xuất hiện ở bất kỳ đâu** — thứ gần nó nhất là packet 308 bytes lúc 54.523 (chứa chữ ký 64 bytes, đã mã hóa thêm một lớp ChaCha20).
4. **Kích thước packet tiết lộ cấu trúc dù nội dung bị giấu** (140 → 100 → 308 → 28 = hỏi key → OK → ký → thành công) — đây cũng chính là lý do tồn tại lĩnh vực traffic analysis: mã hóa giấu nội dung, không giấu hình dạng.