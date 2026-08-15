# Restaurant Waiter Agent — Requirements Specification

## 1. Product Overview

Restaurant Waiter Agent adalah sistem pemesanan restoran berbasis percakapan yang memungkinkan pelanggan memesan makanan melalui Telegram setelah melakukan scan QR code pada meja.

Sistem menyediakan AI waiter yang membantu pelanggan:

* menentukan makanan yang ingin dipesan;
* memahami preferensi dan ketidaksukaan pelanggan;
* memberikan rekomendasi;
* menyimpan menu favorit;
* menggunakan informasi pelanggan untuk personalisasi;
* membuat pesanan.

Sistem juga menyediakan dashboard restoran untuk mengelola menu, pesanan, meja, pembayaran, customer memory, dan analytics.

---

# 2. Problem Statement

Dalam proses pemesanan restoran, pelanggan dapat mengalami kesulitan dalam:

* menentukan makanan yang ingin dipesan;
* mengetahui menu yang sesuai dengan preferensi mereka;
* mendapatkan rekomendasi yang personal;
* melakukan pemesanan tanpa menunggu waiter.

Di sisi restoran, diperlukan sistem yang dapat membantu:

* mengelola pesanan secara terpusat;
* mengetahui status setiap pesanan;
* mengelola penggunaan meja;
* mempertahankan informasi preferensi pelanggan;
* memahami pola pemesanan pelanggan dan penggunaan meja.

---

# 3. Goals

Sistem harus:

1. menyediakan conversational ordering melalui Telegram;
2. menghubungkan customer dengan meja melalui QR code;
3. langsung melakukan reservation/occupancy meja ketika customer berhasil melakukan QR scan;
4. menyediakan rekomendasi menu yang dipersonalisasi;
5. menyimpan customer preferences, dislikes, favorites, dan order history;
6. memungkinkan customer membuat dan mengelola pesanan;
7. menyediakan pengelolaan pesanan untuk restaurant admin;
8. mendukung konfirmasi pembayaran secara manual;
9. mengelola lifecycle dining session;
10. menyediakan automatic session termination setelah periode inactivity yang ditentukan;
11. menyediakan payment timeout untuk unpaid order;
12. menyediakan analytics dasar untuk restoran.

---

# 4. Actors

## 4.1 Customer

Customer adalah pelanggan restoran yang berinteraksi dengan sistem melalui Telegram.

## 4.2 Restaurant Admin

Restaurant Admin adalah pengguna yang mengelola restoran melalui dashboard.

---

# 5. Customer Requirements

## CR-001 — Table QR Entry and Reservation

Customer harus dapat memulai dining session dengan melakukan scan QR code yang tersedia pada meja.

QR code harus mengidentifikasi meja yang digunakan customer.

Setelah QR code berhasil divalidasi:

1. sistem memeriksa status meja;
2. jika meja tersedia, sistem langsung membuat active dining session;
3. meja berubah menjadi `OCCUPIED`;
4. customer dapat mulai berinteraksi dengan AI waiter.

Reservation/occupancy meja terjadi pada saat QR scan berhasil, bukan setelah customer membuat order.

---

## CR-002 — Occupied Table

Jika customer melakukan scan QR pada meja yang sedang memiliki active dining session:

* sistem tidak boleh membuat session kedua;
* customer harus mendapatkan informasi bahwa meja sedang digunakan;
* customer diarahkan untuk menggunakan meja yang tersedia atau menghubungi staff.

---

## CR-003 — Telegram Session Entry

Setelah scan QR code, customer harus dapat membuka percakapan dengan restaurant bot melalui Telegram.

Sistem harus mengasosiasikan Telegram identity customer dengan dining session yang sesuai.

Customer yang tidak memiliki active dining session harus memulai session melalui QR code sebelum dapat membuat order.

---

## CR-004 — Dining Session

Sistem harus membuat dining session yang menghubungkan:

* customer;
* meja;
* waktu session dimulai;
* pesanan customer;
* order terakhir yang telah selesai;
* status session.

Sebuah meja tidak boleh memiliki lebih dari satu active dining session pada waktu yang sama.

---

## CR-005 — Food Discovery

AI waiter harus dapat membantu customer menentukan apa yang ingin dipesan.

AI waiter dapat menanyakan informasi seperti:

* makanan yang sedang diinginkan;
* kategori makanan;
* preferensi rasa;
* makanan yang tidak disukai;
* dietary preference apabila relevan.

AI waiter tidak perlu menanyakan informasi yang sudah diketahui dari conversation atau customer memory.

---

## CR-006 — Menu Recommendation

AI waiter harus dapat memberikan rekomendasi menu berdasarkan konteks customer.

Rekomendasi dapat mempertimbangkan:

* keinginan customer saat ini;
* preference;
* dislikes;
* favorite;
* order history;
* menu availability.

Rekomendasi tidak boleh menawarkan menu yang tidak tersedia.

---

## CR-007 — Customer Memory

Sistem harus mempertahankan informasi customer antar dining session.

Memory dapat mencakup:

* preference;
* dislikes;
* dietary preference;
* favorite;
* order history;
* informasi lain yang relevan untuk personalisasi.

Customer memory harus dapat memiliki deskripsi tekstual agar informasi yang disimpan tidak terbatas pada struktur key-value sederhana.

Contoh:

```text
Type:
preference

Description:
Customer menyukai makanan gurih dan tidak terlalu pedas.
```

Memory harus terasosiasi dengan customer, bukan dengan dining session tertentu.

---

## CR-008 — Favorite Menu

Customer harus dapat menandai menu sebagai favorite melalui conversational interaction.

Customer juga harus dapat menghapus menu dari favorite.

Favorite harus persistent antar dining session.

---

## CR-009 — Create Order

Customer harus dapat membuat order melalui AI waiter.

Order harus memiliki:

* customer;
* dining session;
* meja;
* menu items;
* quantity;
* order status;
* payment status;
* timestamps.

Customer harus dapat meninjau order sebelum melakukan konfirmasi.

Customer harus memberikan konfirmasi eksplisit sebelum order dikirim ke restaurant.

---

## CR-010 — Order Status

Order harus memiliki lifecycle:

```text
ORDERED
   ↓
IN_PROGRESS
   ↓
DONE
```

Restaurant Admin dapat mengubah status order.

---

## CR-011 — Order Completion and Session Timeout

Session timeout **tidak dimulai ketika order dibuat**.

Session timeout mulai dihitung setelah order terakhir customer mencapai status `DONE`.

Setiap kali sebuah order customer mencapai status `DONE`, timestamp tersebut menjadi referensi aktivitas terakhir untuk session.

Default session inactivity timeout:

```text
30 minutes
```

Timeout harus configurable.

Jika tidak terdapat order yang pernah dibuat dalam session, automatic session timeout dihitung dari waktu session dibuat.

---

# 6. Payment Requirements

## PR-001 — Manual Payment

MVP tidak menyediakan online payment gateway.

Customer melakukan pembayaran secara manual.

---

## PR-002 — Payment Confirmation

Restaurant Admin harus dapat mengonfirmasi pembayaran melalui dashboard.

Payment status:

```text
UNPAID
PAID
```

Admin harus dapat melakukan:

```text
UNPAID → PAID
```

---

## PR-003 — Payment Timeout

Unpaid order memiliki payment timeout.

Payment timeout mulai dihitung ketika order mencapai status `DONE`.

Default payment timeout:

```text
10 minutes
```

Timeout harus configurable.

Jika payment timeout tercapai dan order masih `UNPAID`:

* order tetap berstatus `UNPAID`;
* payment tidak otomatis dianggap `PAID`;
* order tidak otomatis dihapus;
* sistem harus menandai kondisi tersebut sebagai overdue untuk kebutuhan admin.

Automatic cancellation akibat payment timeout bukan bagian dari MVP.

---

# 7. Dining Session Requirements

## SR-001 — Active Session

Dining session memiliki status aktif selama customer masih menggunakan meja.

---

## SR-002 — Manual Termination

Customer harus dapat mengakhiri dining session menggunakan:

```text
/done
```

Jika terdapat unpaid order, sistem harus memberikan warning kepada customer.

Contoh:

```text
Masih ada pesanan yang belum dibayar.
Yakin ingin menyelesaikan sesi?
```

Customer harus memberikan konfirmasi sebelum session ditutup.

Setelah session berakhir:

* session tidak lagi aktif;
* meja menjadi available;
* session tidak boleh menerima order baru.

---

## SR-003 — Automatic Termination

Sistem harus dapat mengakhiri active dining session secara otomatis.

Automatic session termination menggunakan waktu order terakhir yang telah mencapai `DONE`.

Default:

```text
30 minutes
```

Jika session belum pernah memiliki order, timeout dihitung dari waktu session dibuat.

---

## SR-004 — Session Activity

Ketika order customer mencapai status `DONE`, sistem harus memperbarui timestamp aktivitas terakhir session.

Order yang masih:

```text
ORDERED
IN_PROGRESS
```

belum menjadi anchor untuk session inactivity timeout.

---

## SR-005 — Session Safety

Session yang telah selesai tidak boleh kembali menjadi active secara otomatis.

Sistem harus mencegah lebih dari satu active session menggunakan meja yang sama.

---

## SR-006 — Customer Session Exclusivity

Customer tidak boleh memiliki lebih dari satu active dining session secara bersamaan.

Jika customer mencoba menggunakan QR meja lain ketika masih memiliki active session:

* sistem harus memberi tahu customer bahwa mereka masih memiliki active session;
* sistem tidak langsung membuat session kedua.

---

# 8. Restaurant Dashboard Requirements

## DR-001 — Authentication

Dashboard hanya dapat diakses oleh authenticated Restaurant Admin.

---

## DR-002 — Menu Management

Admin harus dapat:

* melihat menu;
* membuat menu;
* mengubah menu;
* menghapus/deactivate menu;
* mengubah harga;
* mengubah availability;
* mengelola category;
* mengelola menu description.

---

## DR-003 — Order Management

Admin harus dapat:

* melihat order;
* melihat detail order;
* melihat status order;
* mengubah status order;
* melihat payment status;
* menandai order sebagai paid;
* melihat unpaid order yang telah melewati payment timeout.

Admin harus dapat melihat order berdasarkan status:

```text
ORDERED
IN_PROGRESS
DONE
```

---

## DR-004 — Table Management

Admin harus dapat mengelola layout meja restoran melalui dashboard.

Admin dapat:

* melihat seluruh meja dalam bentuk visual floor layout;
* menambahkan meja;
* mengubah nomor meja;
* mengubah kapasitas meja;
* melakukan drag-and-drop meja untuk mengatur posisi pada layout;
* melihat QR code meja;
* menonaktifkan meja;
* melihat status meja;
* melihat active dining session;
* melihat customer yang sedang menggunakan meja;
* melihat waktu order terakhir yang telah selesai.

Setiap meja pada floor layout minimal menampilkan:

* nomor meja;
* kapasitas;
* status meja.

Table status minimal:

```text
AVAILABLE
OCCUPIED
```

## DR-005 — Customer Memory

Admin harus dapat melihat customer memory.

Informasi yang dapat ditampilkan:

* preferences;
* dislikes;
* favorites;
* memory descriptions;
* order history;
* active/recent dining session.

---

# 9. Analytics Requirements

## AR-001 — Popular Menu

Dashboard harus menampilkan menu yang paling sering dipesan.

---

## AR-002 — Table Usage

Dashboard harus menampilkan meja yang paling sering digunakan.

---

## AR-003 — Order Statistics

Dashboard harus menyediakan statistik dasar mengenai order.

Minimal sistem harus dapat menghasilkan data yang diperlukan untuk:

* jumlah order;
* jumlah order per menu;
* menu paling sering dipesan;
* order berdasarkan periode.

---

## AR-004 — Table Statistics

Dashboard harus menyediakan data yang diperlukan untuk mengetahui:

* jumlah penggunaan setiap meja;
* meja yang paling sering digunakan;
* penggunaan meja berdasarkan periode.

---

# 10. Customer Experience Requirements

AI waiter harus:

* menggunakan informasi conversation yang relevan;
* memanfaatkan customer memory ketika relevan;
* tidak mengarang menu yang tidak tersedia;
* tidak membuat order tanpa konfirmasi customer;
* memberikan informasi order yang jelas sebelum confirmation;
* memungkinkan customer meminta menu atau informasi secara langsung tanpa mengikuti recommendation flow.

Telegram inline keyboard/button confirmation dapat ditambahkan sebagai improvement setelah MVP.

---

# 11. Data Persistence Requirements

Sistem harus mempertahankan:

* customer;
* Telegram identity;
* menu;
* menu category;
* table;
* dining session;
* order;
* order item;
* payment status;
* payment timeout information;
* customer preferences;
* customer dislikes;
* customer favorites;
* customer memory descriptions;
* order history.

---

# 12. MVP Scope

## Included

* Telegram-based customer interaction.
* QR-based table identification.
* Immediate table reservation/occupancy after valid QR scan.
* Dining session.
* AI waiter conversation.
* Food preference discovery.
* Menu recommendation.
* Customer personalization.
* Customer memory.
* Descriptive customer memory.
* Favorite menu.
* Order creation and confirmation.
* Order status management.
* Manual payment confirmation.
* Payment timeout.
* `/done` session termination.
* Automatic session termination.
* Configurable session timeout.
* Configurable payment timeout.
* Menu CRUD.
* Table management.
* Order management.
* Customer memory dashboard.
* Basic restaurant analytics.
* Admin authentication.

## Out of Scope / Future Improvements

* Telegram inline keyboard confirmation.
* Online payment gateway.
* Automatic payment verification.
* Automatic cancellation after payment timeout.
* Food delivery.
* Multi-restaurant tenancy.
* Advanced inventory management.
* Kitchen display system.
* Voice interaction.
* Advanced ML recommendation model.
* Multi-channel customer interaction selain Telegram.
* Complex staff role/permission management.

---

# 13. Acceptance Criteria

1. Customer can scan a table QR code.
2. A valid QR scan immediately reserves/occupies an available table.
3. QR code opens the restaurant Telegram interaction.
4. System identifies the correct table.
5. System creates an active dining session.
6. An occupied table cannot create a second active session.
7. A customer cannot have multiple active dining sessions.
8. Customer can interact with the AI waiter.
9. AI waiter can understand current food preferences.
10. AI waiter can consider customer dislikes.
11. AI waiter can provide available menu recommendations.
12. Customer can save a menu as favorite.
13. Customer can create an order draft.
14. Customer must explicitly confirm the order before submission.
15. Admin can see the submitted order.
16. Admin can change order status.
17. When the order becomes `DONE`, its completion time becomes the session activity timestamp.
18. Session inactivity timeout starts from the last completed (`DONE`) order.
19. If there has been no order, session timeout starts from session creation.
20. Admin can manually mark payment as paid.
21. Payment timeout starts when the order becomes `DONE`.
22. An unpaid order remains `UNPAID` after payment timeout and is marked overdue.
23. Customer receives a warning before manually terminating a session with unpaid orders.
24. Customer can terminate the session using `/done`.
25. The table becomes available after session termination.
26. Session automatically terminates after the configured inactivity timeout.
27. Customer preferences and favorites persist across sessions.
28. Admin can inspect customer memory and descriptions.
29. Admin can manage menu CRUD including descriptions.
30. Admin can see popular menu statistics.
31. Admin can see table usage statistics.
32. Dashboard authentication is protected by JWT.
