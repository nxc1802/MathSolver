## TC-2D-Easy — Tam giác và đường cao

**Đề bài trên ảnh:**

> Cho tam giác \(ABC\) vuông tại \(A\), biết \(AB=6\), \(AC=8\).
> Gọi \(H\) là chân đường cao từ \(A\) xuống \(BC\).
> Tính \(BC\), \(AH\) và diện tích tam giác \(ABC\).

**Hình cần vẽ:**

* Tam giác \(ABC\)
* \(AB \perp AC\)
* Đường cao \(AH\)
* Điểm \(H\in BC\)
* Ký hiệu góc vuông tại \(A\)
* Label: \(6,8,BC,AH\)

**Expected:**

$$
BC=10
$$

$$
AH=\frac{AB\cdot AC}{BC}=4.8
$$

$$
S_{ABC}=\frac12\cdot6\cdot8=24
$$

**Khoảng 3–4 bước animation.**

→ Đây là baseline để kiểm tra pipeline **OCR → parse → geometry → render** mà không tạo quá nhiều nhiễu.

---

## TC-3D-Easy — Hình hộp chữ nhật

**Đề bài trên ảnh:**

> Cho hình hộp chữ nhật \(ABCD.A'B'C'D'\) có
> \(AB=4,\ AD=3,\ AA'=5\).
> Tính độ dài đường chéo \(AC'\).

**Hình cần vẽ:**

* Hình hộp chữ nhật
* 8 đỉnh \(A,B,C,D,A',B',C',D'\)
* Các cạnh
* Đường chéo không gian \(AC'\)
* Label \(4,3,5\)
* Đường khuất biểu diễn bằng nét đứt

**Expected:**

$$
AC'=\sqrt{AB^2+AD^2+AA'^2}
$$

$$
AC'=\sqrt{4^2+3^2+5^2}=5\sqrt2
$$

**Khoảng 3–4 bước animation.**

→ Test khả năng chuyển từ mô tả toán học sang **3D Geometry DSL**, đúng với phạm vi 3D/Oxyz của proposal. 

---

# TC-2D-Hard — Đường tròn, tiếp tuyến và hình trong hình

Đây nên là **case stress-test OCR 2D chính**.

**Đề bài trên ảnh:**

> Cho đường tròn \((O)\) có đường kính \(AB\).
> Lấy điểm \(C\in (O)\), \(C\ne A,B\). Tiếp tuyến tại \(A\) và \(C\) cắt nhau tại \(M\).
> Gọi \(H\) là hình chiếu vuông góc của \(C\) lên \(AB\), \(N\) là giao điểm của \(CM\) và \(AB\).
> Chứng minh rằng
>
> $$
> MA^2=MH\cdot MN
> $$
>
> và
>
> $$
> \angle AMC=2\angle ABC.
> $$

### Hình phải chứa

* Đường tròn \((O)\)
* Đường kính \(AB\)
* Điểm \(C\) trên đường tròn
* Tiếp tuyến tại \(A\)
* Tiếp tuyến tại \(C\)
* Điểm \(M\)
* \(CM\)
* \(CH\perp AB\)
* \(H\in AB\)
* \(N=CM\cap AB\)
* Các góc được đánh dấu
* Ký hiệu:

  * \((O)\)
  * \(\perp\)
  * \(MA^2\)
  * \(\angle AMC\)
  * \(\angle ABC\)
  * \(H,N,M,O,A,B,C\)

### Vì sao case này khó?

Nó tạo ra **nhiều lớp thông tin không gian trong cùng một hình**

Thực tế hình sẽ phức tạp hơn vì có **đường tròn + tiếp tuyến + tam giác + đường vuông góc + giao điểm + nhiều label**.

Pipeline phải đồng thời nhận ra:

**text → LaTeX → geometric entities → spatial relations → construction order.**

Đặc biệt, OCR phải phân biệt được:

$$
(O),\quad \perp,\quad \angle,\quad ^2,\quad H,N,O
$$

→ Đây là case rất tốt để kiểm tra **Math OCR + Problem Parser**, thay vì chỉ kiểm tra khả năng đọc text. Proposal cũng xác định Math OCR phải xử lý đồng thời chữ, công thức và ký hiệu toán. 

---

# TC-3D-Hard — Hình chóp, mặt phẳng và hình chiếu

Đây nên là **case khó nhất toàn bộ benchmark**.

**Đề bài trên ảnh:**

> Cho hình chóp \(S.ABCD\) có đáy \(ABCD\) là hình vuông cạnh \(a\),
> \(SA\perp(ABCD)\), \(SA=a\).
> Gọi \(M,N\) lần lượt là trung điểm của \(AB,CD\).
> Gọi \(H\) là hình chiếu vuông góc của \(A\) lên \(SM\).
>
> 1. Xác định giao tuyến của hai mặt phẳng \((SMN)\) và \((SAD)\).
> 2. Tính khoảng cách từ \(A\) đến đường thẳng \(SM\).
> 3. Tính góc giữa \(SM\) và mặt phẳng \((ABCD)\).

### Hình phải chứa

**Khối chính:**

* Hình chóp \(S.ABCD\)
* Hình vuông đáy \(ABCD\)
* Các cạnh bên \(SA,SB,SC,SD\)

**Các đối tượng phụ:**

* \(M\in AB\)
* \(N\in CD\)
* \(SM\)
* \(SN\)
* \(H\in SM\)
* \(AH\perp SM\)
* Mặt phẳng \((SMN)\)
* Mặt phẳng \((SAD)\)

**Ký hiệu toán học:**

$$
SA\perp(ABCD)
$$

$$
AB=BC=CD=DA=a
$$

$$
M\in AB,\qquad N\in CD
$$

$$
AH\perp SM
$$

$$
d(A,SM)
$$

$$
\widehat{(SM,(ABCD))}
$$

### Điểm khó

Case này ép hệ thống phải xử lý **nhiều tầng hình học**. Nó phải tạo lần lượt:

1. Đáy \(ABCD\)
2. Đỉnh \(S\)
3. Các cạnh bên
4. \(M,N\)
5. \(SM,SN\)
6. \(H\)
7. \(AH\)
8. Các ký hiệu vuông góc
9. Các mặt phẳng cần xét
10. Highlight các đối tượng phục vụ từng câu hỏi

→ **~8–12 animation steps**.

---

# Bộ test cuối cùng

Tôi sẽ chốt benchmark thành:

### 🟢 Easy

**TC-2D-Easy:**
**Tam giác vuông + đường cao**
→ ít đối tượng, 3–4 bước.

**TC-3D-Easy:**
**Hình hộp chữ nhật + đường chéo không gian**
→ một solid đơn giản, 3–4 bước.

### 🔴 Hard

**TC-2D-Hard:**
**Đường tròn + tiếp tuyến + hình chiếu + nhiều giao điểm**
→ stress **OCR ký hiệu + hình trong hình + spatial relation**.

**TC-3D-Hard:**
**Hình chóp + mặt phẳng + hình chiếu + góc + khoảng cách**
→ stress **3D parsing + construction + multi-step rendering**.
