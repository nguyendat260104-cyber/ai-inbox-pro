# Kế Hoạch Triển Khai: AI Inbox & Sales Management Platform

> **Định vị sản phẩm**: Nền tảng quản lý hội thoại tập trung và chuyển đổi Lead bằng AI cho Shop bán hàng và Agency tại Việt Nam — Tự động trả lời chuẩn xác theo kho dữ liệu, chấm điểm khách nóng, phân quyền nhân viên và đo lường doanh thu trên từng kênh.

---

## 1. Phân Chia Trách Nhiệm & Khả Năng Tự Động Hóa

Bạn hỏi: *"Giờ theo hướng này thì mình cần làm gì, bạn hỗ trợ được mình tự động hóa hết không?"*

Dưới đây là bảng phân định ranh giới tự động hóa 100% và phần việc duy nhất người vận hành cần làm:

| Hạng mục | Khả năng tự động hóa (Antigravity & Codex) | Việc Người Vận Hành cần làm |
| :--- | :--- | :--- |
| **Kiến trúc & Cơ sở dữ liệu** | **100% Tự động**: Thiết kế schema đa người dùng (Multi-tenant), quan hệ Customer - Conversation - Lead - Order - Staff. | Không cần làm gì. |
| **Chatbot Bán hàng (Core AI)** | **100% Tự động**: Xây dựng thuật toán 5 bước: Hiểu câu hỏi -> Truy vấn sản phẩm (Grounded RAG) -> Hỏi thêm nhu cầu -> Chấm điểm Lead -> Trigger Human Handoff. | Không cần làm gì. |
| **Quy tắc Chống Bịa Đặt (Zero-Hallucination)** | **100% Tự động**: Code bộ lọc cứng: Chặn hoàn toàn AI tự bịa giá, tồn kho, phí ship hoặc tự giảm giá ngoài danh mục. | Cung cấp danh mục sản phẩm mẫu (hoặc file Excel). |
| **Hệ thống Quản lý Lead (Kanban Pipeline)** | **100% Tự động**: Tự động chuyển đổi hội thoại thành Lead Card, phân loại New ➔ AI Qualified ➔ Assigned ➔ Won/Lost. | Nhân viên kéo thẻ hoặc chốt đơn thực tế. |
| **Website Chat Widget** | **100% Tự động**: Viết widget nhúng 1 dòng mã (JavaScript/CSS), hỗ trợ WebSockets/REST API chat trực tiếp. | Dán mã widget vào website nếu muốn test live. |
| **Dashboard UI (Command Center)** | **100% Tự động**: Giao diện trực quan gồm Unified Inbox (hộp thư tập trung), Kanban Lead Board, Quản lý sản phẩm, Báo cáo phễu. | Sử dụng và đưa ra feedback giao diện. |
| **Kết nối Facebook Page / Zalo OA** | **Hệ thống code sẵn API Adapter & Webhook receiver**. | Cấp App ID / Page Token chính thức từ Meta & Zalo (theo chính sách bảo mật). |

---

## 2. Kiến Trúc Luồng Dữ Liệu & State Machine

```mermaid
flowchart TD
    subgraph Ingestion["1. Tầng Kết Nối Đa Kênh"]
        WEB["Website Chat Widget"] --> GW["Unified Ingestion Gateway"]
        FB["Facebook Messenger API"] --> GW
        CSV["CSV / Manual Import"] --> GW
        API["REST Ingestion Endpoint"] --> GW
    end

    subgraph Engine["2. Tầng Hội Thoại & AI Bán Hàng"]
        GW --> NORM["Chuẩn hóa tin nhắn & Hội thoại"]
        NORM --> RAG["Grounded Knowledge & Product Catalog<br/>(Kiểm tra Giá, Tồn kho, Phí ship)"]
        RAG --> INTENT["Intent Classifier & Lead Scorer<br/>(COLD / WARM / HOT)"]
        INTENT --> RESP["Phản hồi tự động theo kịch bản"]
        INTENT --> HANDOFF{"Cần Nhân Viên?"}
    end

    subgraph Management["3. Tầng Quản Trị & Lead Pipeline"]
        HANDOFF -- "HOT Lead / Khách muốn đặt" --> KANBAN["Kanban Lead Pipeline<br/>(New ➔ AI Qualified ➔ Assigned ➔ Closed)"]
        HANDOFF -- "Hỏi đáp thông thường" --> BOT_CONTINUE["Bot tiếp tục hỗ trợ"]
        KANBAN --> STAFF["Nhân viên Sale chốt đơn & Takeover"]
        STAFF --> REV["Báo cáo Doanh Thu & Hiệu Suất Nhân Viên"]
    end
```

---

## 3. Thiết Kế 5 Bước Của Chatbot Bán Hàng (Sales AI Engine)

Chatbot được đóng gói logic nghiêm ngặt để đạt tỷ lệ chốt tối đa mà không gây rủi ro bán hàng:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Khách Hàng
    participant Bot as Chatbot Bán Hàng (AI Engine)
    participant DB as Kho Dữ Liệu Shop (Catalog & Policy)
    participant Staff as Nhân Viên Bán Hàng (Sale)

    Customer->>Bot: "Áo này còn size M không, ship Đà Nẵng bao nhiêu?"
    Bot->>DB: 1. Truy vấn sản phẩm & chính sách ship Đà Nẵng
    DB-->>Bot: Tồn kho: Size M còn 5 chiếc. Ship ĐN: 25.000đ (đồng giá)
    Note over Bot: 2. Bắt buộc đối chiếu dữ liệu thật (Không tự bịa)
    Bot->>Customer: "Dạ áo này size M bên em còn hàng ạ. Phí ship về Đà Nẵng là 25k. Bạn muốn chọn màu Trắng hay Đen ạ?"
    Note over Bot: 3. Hỏi thêm nhu cầu (Màu sắc, số lượng)
    Customer->>Bot: "Cho mình 1 chiếc màu Đen nhé, thanh toán khi nhận hàng."
    Note over Bot: 4. Chấm điểm ý định mua: Gắn nhãn HOT LEAD (Điểm: 95/100)
    Bot->>Staff: 5. Kích hoạt Human Handoff: Tạo Lead HOT trên Kanban & bắn chuông cho Sale
    Staff->>Customer: "Chào bạn, mình là nhân viên shop, mình xin địa chỉ & SĐT để tạo đơn gửi ngay cho bạn nhé!"
```

---

## 4. Lộ Trình Triển Khai 4 Tuần (MVP Delivery Roadmap)

```mermaid
gantt
    title Kế Hoạch Triển Khai AI Inbox & Sales Management Platform
    dateFormat  YYYY-MM-DD
    section Sprint 1: Nền Tảng Dữ Liệu & Core Engine
    Thiết kế SQLite Multi-tenant Database       :a1, 2026-10-18, 4d
    Xây dựng Bounded Product Retrieval Engine   :a2, after a1, 3d
    Xây dựng Lead Intent Scorer & State Machine :a3, after a1, 3d
    Automated Test Suite (Giao dịch mẫu)        :a4, after a2, 2d

    section Sprint 2: Web Widget & Unified Inbox API
    Xây dựng Embeddable Chat Widget (JS/CSS)    :b1, 2026-10-25, 4d
    REST API & Ingestion Webhooks               :b2, after b1, 3d
    Luồng Human Takeover thời gian thực         :b3, after b2, 3d

    section Sprint 3: Dashboard V2 (Kanban & Inbox)
    Giao diện Hộp thư hợp nhất (Inbox UI)       :c1, 2026-11-01, 4d
    Kanban Lead Board kéo thả                   :c2, after c1, 4d
    Bộ lọc Nhân viên, Kênh, Sản phẩm            :c3, after c2, 2d

    section Sprint 4: Báo Cáo Doanh Thu & Pilot
    Báo cáo tỷ lệ chuyển đổi & Response Time    :d1, 2026-11-10, 4d
    Thử nghiệm Pilot trên 1-3 Shop thật         :d2, after d1, 5d
```

### Chi tiết các Sprint:
1. **Sprint 1 (Ngay hôm nay)**:
   - Data Layer: Workspaces, Customers, Conversations, Messages, Products, Leads, Staff.
   - Core Engine: Bounded Product Search, Rule-based Intent/Score Classifier, Lead Generator.
   - Unit tests chứng minh 100% độ chính xác: Test câu hỏi có hàng, câu hỏi không có hàng, câu hỏi đòi giảm giá.
2. **Sprint 2**:
   - Widget nhúng web 1 dòng code: Khách bấm vào chat, gửi tin nhắn, nhận phản hồi ngay lập tức.
   - Ingestion API: Cho phép nhận tin nhắn từ Facebook/Zalo qua Webhook.
3. **Sprint 3**:
   - Dashboard giao diện đẹp:
     - Cột 1: Danh sách hội thoại (lọc khách HOT, khách chờ phản hồi).
     - Cột 2: Cửa sổ chat 2 chiều (Bot trả lời hoặc Sale nhảy vào takeover).
     - Cột 3: Hồ sơ khách & Lead Pipeline trực tiếp.
4. **Sprint 4**:
   - Báo cáo số liệu thực: Số lead tạo ra, tỷ lệ chốt, nhân viên nào phản hồi nhanh nhất, doanh thu ghi nhận.

---

## 5. Quy Tắc Kỹ Thuật Bất Di Bất Dịch (Core Guardrails)
1. **Zero Hallucination**: AI không bao giờ được tự sinh ra giá, số lượng tồn kho hay hứa hẹn giao hàng nếu không có trong cơ sở dữ liệu.
2. **Deterministic Attribution**: Mọi đơn hàng / Lead Won phải truy vết được bắt nguồn từ kênh nào và hội thoại nào.
3. **Local-First & Lightweight**: Khởi chạy bằng Python chuẩn, không đòi hỏi hạ tầng cồng kềnh, chi phí vận hành siêu rẻ.
