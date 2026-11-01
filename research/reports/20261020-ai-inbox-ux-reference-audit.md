# AI Inbox Pro — UI reference audit

**Ngày rà soát:** 2026-10-20  
**Phạm vi:** 5 trang chính thức về AI chatbot, helpdesk, CRM và omnichannel. Đây là phân tích pattern, không sao chép layout/brand assets.

## Năm tham chiếu

1. **Intercom — Fin AI Agent** ([trang sản phẩm](https://www.intercom.com/ai-chatbot))
   - Hero đưa ra một kết quả cụ thể: agent không chỉ trả lời mà còn hoàn tất tác vụ và bàn giao có đủ ngữ cảnh.
   - Hình sản phẩm hội thoại xuất hiện ngay đầu trang, sau đó là logo khách hàng, các năng lực theo tình huống, bảng so sánh, chứng thực, giá và FAQ.
   - Bài học: kể một luồng end-to-end bằng sản phẩm thật; chứng minh “AI xử lý → con người tiếp quản” thay vì các claim tốc độ rời rạc.

2. **Zendesk — AI for customer service** ([trang sản phẩm](https://www.zendesk.com/service/ai/))
   - Dùng giao diện sản phẩm trong hero, rồi phân rã giải pháp thành knowledge, AI agents, copilot và quality assurance.
   - Mỗi khối có ảnh giao diện phù hợp với đúng năng lực; kết quả khách hàng và case study xuất hiện trước phần FAQ/CTA.
   - Bài học: mỗi capability phải có một bằng chứng UI tương ứng; tách rõ AI cho khách, AI hỗ trợ nhân viên và quản trị chất lượng.

3. **Crisp — AI customer support platform** ([trang chủ](https://crisp.chat/en/))
   - Định vị một nền tảng thống nhất, nêu rõ inbox, widget, AI, knowledge và các phần vận hành; sản phẩm xuất hiện sớm thay vì chỉ có abstract art.
   - Lợi ích, tín hiệu tin cậy, trải nghiệm sản phẩm và CTA dùng thử tạo thành một hành trình ngắn, dễ quét.
   - Bài học: trình bày hệ thống đa kênh như một workspace thống nhất; tránh biến từng chức năng thành các card giống nhau.

4. **Tidio — Lyro AI Agent** ([trang Lyro](https://www.tidio.com/ai-agent/))
   - Đóng gói AI thành một agent có tên và job cụ thể, cho thấy hỗ trợ khách hàng/bán hàng trong ngữ cảnh thương mại điện tử.
   - Trang nối lợi ích với cách hoạt động và các điểm tích hợp/use case thay vì giới thiệu “AI” chung chung.
   - Bài học: đặt bot của AI Inbox Pro vào một hành trình shop thực tế (hỏi size/tồn kho → tư vấn → lấy thông tin → chuyển sales), và cho phép xem/chơi thử.

5. **HubSpot Service Hub — Omnichannel Customer Service** ([trang sản phẩm](https://www.hubspot.com/products/service/omnichannel-customer-service))
   - Trang bắt đầu bằng giá trị omnichannel, đặt ảnh inbox thật ở phần mở đầu và liên kết hỗ trợ với hồ sơ CRM.
   - Các đoạn nội dung luân phiên giải thích hợp nhất kênh, bối cảnh khách hàng và tích hợp; có proof, tài nguyên và FAQ.
   - Bài học: hồ sơ khách hàng là ngữ cảnh hành động ngay trong workspace, không phải sidebar trang trí; tách page/route theo nhu cầu người mua.

## Tiêu chuẩn rút ra cho AI Inbox Pro

- **Bắt đầu bằng outcome:** gom hội thoại đa kênh, trả lời dựa trên sản phẩm/tồn kho thật, nhận diện lead nóng, tạo đơn hoặc bàn giao có ngữ cảnh.
- **Bằng chứng trước lời hứa:** ưu tiên giao diện thật có dữ liệu mẫu nhất quán, transcript có logic, trạng thái kênh rõ; không bịa số liệu hiệu quả.
- **Một trang, một mục tiêu:** Landing bán giá trị; Product giải thích năng lực; Solutions nói theo use case/ngành; Pricing giúp so sánh và chọn; Resources phục vụ học; Admin vận hành; Demo kể một hành trình mua hàng.
- **Thiết kế có nhịp:** headline editorial, câu chữ ngắn, khoảng trắng có chủ đích, typography hỗ trợ tiếng Việt, thay đổi bố cục theo từng chương; hạn chế card-soup, badge ngẫu nhiên, emoji, glow và gradient nền.
- **Sticker đúng vai trò:** đặt rail kênh dọc, gọn, logo/nhãn có khoảng cách, màu thương hiệu tiết chế; không để sticker ngang đè lên robot hoặc nội dung.
- **Motion phục vụ trạng thái:** chỉ dùng để làm rõ agent đang xử lý, message tới, kênh online, mở panel; hỗ trợ `prefers-reduced-motion` và không làm giảm khả năng đọc.

## Backlog và cổng chuyển task

### P0 — Landing, hoàn thiện trước khi chuyển
- Tái cấu trúc hero thành narrative rõ ràng, copy ngắn và phân cấp typography sắc nét; bố trí proof sản phẩm thật trong first viewport.
- Làm mới preview inbox, activity AI, trạng thái kết nối/kênh; nội dung demo thống nhất với shop thời trang hiện có.
- Thiết kế lại mascot và rail sticker dọc Messenger/Zalo/Facebook; xử lý đúng z-index, khoảng cách, kích thước và mobile.
- Tối ưu các phần problem → workflow → outcomes → proof → pricing/CTA; bỏ phần lặp hoặc chỉ “trang trí”.
- Hoàn thiện header/footer, nav đến page riêng, CTA rõ, responsive, keyboard/focus/contrast, motion có reduced-motion.
- **Cổng nghiệm thu:** kiểm tra trực quan ở 1440/1024/390px; không tràn/cắt/chồng, mọi CTA và link hoạt động, ticker không gây rung hoặc che nội dung, các section có nhịp và bằng chứng, không còn biểu hiện AI-template. Chỉ chuyển khi tất cả đạt.

### P1 — Admin Inbox
- Đặt conversation ở trung tâm; điều hướng một lần; customer context mở có chủ ý; phân tầng metadata và hành động.
- Nâng chất lượng channel health, agent activity, priority/handoff, unread/assigned states; bổ sung empty/loading/error states có thể hiểu và hành động.
- Bảo đảm danh sách → hội thoại → hồ sơ/đơn hàng tương ứng; điều khiển composer và quick replies dùng được.
- Review desktop/tablet/mobile, focus, keyboard, contrast, reduced-motion; loại bỏ chỗ chen chúc và khung không có vai trò.

### P2 — Các trang riêng + Demo
- Product, Solutions, Pricing, Resources phải là route độc lập thật sự, mỗi trang có hierarchy, nội dung, CTA và navigation riêng; không dùng một mẫu trang thay tiêu đề.
- Demo đi theo một kịch bản hoàn chỉnh: khách hỏi → agent xác minh sản phẩm/tồn kho → tư vấn → thu thập thông tin → lead đủ điều kiện → sales tiếp quản/chốt đơn.
- Validate các route, liên kết qua lại và breakpoint; chỉ chuẩn bị preview Vercel sau khi UI được review-ready, không deploy khi chưa được duyệt.

## Tình trạng hiện tại và lưu ý

- Repo hiện có thay đổi chưa commit ở Landing, Admin, marketing routes và assets. Các task mới phải tiếp tục trên worktree hiện tại, không reset/revert các chỉnh sửa này.
- Task cũ `INBOX-20261019-019` đã nằm trong `tasks/review/`; không lấy kết quả test cũ làm bằng chứng cho chất lượng hình ảnh hiện tại.
- Automation tiếp tục hoạt động ở chế độ checkpoint 5 phút; công việc phải tiến liên tục trong task, không đợi checkpoint để bắt đầu.

## Nhật ký thực hiện — 2026-10-20

- Đã rà trực tiếp trang chính thức của cả năm nền tảng ở trên, tập trung vào thứ tự nội dung, cách đưa giao diện sản phẩm vào hero, cách chia năng lực, proof và luồng CTA.
- P0 đang **tiến hành, chưa nghiệm thu**: đưa UI hội thoại/Customer 360 lên first viewport; thay số liệu headline chưa có nguồn bằng mô tả năng lực; thay logo mũi tên bằng monogram; thay robot ảnh hoạt hình bằng SVG gọn; dựng rail Messenger/Zalo/Facebook theo chiều dọc; sửa ticker kênh chạy theo track lặp có hỗ trợ giảm chuyển động.
- Đã nhìn trực tiếp Landing tại local ở desktop mặc định, 1024×768 và 390×844. Hero/điều hướng di động và rail kênh không còn lỗi xuống dòng chính; còn phải rà toàn bộ các section, CTA/điều hướng bằng thao tác, focus/contrast và các lỗi thị giác trước khi mở task Admin.
- Preview đang chạy ở `http://127.0.0.1:8083/landing`; server 8080 cũ không được dùng làm nguồn kiểm chứng trong lượt này.

### Cập nhật kiểm tra Landing — 2026-10-20 13:11 (+07:00)

- Đã bỏ trạng thái kết nối giả `6/6 kênh sẵn sàng`; rail hiện là danh sách tĩnh các kênh có thể cấu hình tích hợp, không lặp ticker và không ngụ ý chúng đang kết nối.
- Đã gắn nhãn dữ liệu mô phỏng cho UI inbox, hồ sơ khách hàng và AI activity; sửa nút gửi/tiếp quản giả thành liên kết mở Admin, và sửa nhãn footer `Bảo mật` vốn trỏ tới trang Tài nguyên.
- Kiểm tra lại accessibility tree trên local: nhãn mô phỏng được đọc, các liên kết demo/admin trỏ đúng `/admin`, danh mục kênh có nhãn rõ. Desktop hero và activity section đã xem trực tiếp; focus bàn phím nhìn thấy rõ trên logo/nav.
- Rà phần kết trang phát hiện dock mascot che mục `Command Center` ở footer; đã dành khoảng đệm an toàn, kiểm tra lại desktop thấy đủ cả ba liên kết. Chuyển động sticker chỉ lộ khi hover/focus; nhãn `LIVE` đổi thành `KÊNH` và keyboard focus làm rail dọc hiện ra.
- Đã bấm CTA hero trên local: URL tới `/admin` và trang Command Center tải được; CTA cuộn trong trang cập nhật đúng `#how-it-works`.
- Tinh chỉnh hero từ thông điệp chung sang vai trò cụ thể của AI và đội sale; dùng Newsreader làm tương phản biên tập cho dòng thứ hai. Kiểm tra trực quan desktop thấy cả hai dòng vừa cột, đoạn mô tả và CTA không đè lên product proof.
- Kiểm tra link Storefront: mở đúng `/demo`. Đã tìm thấy focus ring vàng chỉ đạt khoảng 2.20:1 trên nền trắng; đổi sang brand blue và xác nhận vòng focus nhìn rõ trên logo.
- Khi mở dock ở cuối trang, rail dọc vẫn che một phần footer; tăng vùng đệm phải, mở lại dock và xác nhận desktop không còn chồng link.
- Cổng nghiệm thu vẫn **chưa đạt**: cần kiểm tra toàn trang ở 1440/1024/390px sau các thay đổi, toàn bộ CTA/route và sticker rail khi focus, contrast/reduced-motion, lỗi console/network và test liên quan. Chưa chấm điểm; chưa được chuyển task.
- Responsive/mobile chưa thể tái nghiệm thu trong in-app browser hiện tại: chỉ có viewport desktop và không có điều khiển đổi kích thước; cơ chế thử qua trang `data:`/iframe bị trình duyệt chặn. Không tìm cách lách giới hạn này. Cần mở trang local trong viewport mobile thật hoặc có công cụ viewport được cấp phép. Console/network log cũng chưa đọc được qua giao diện CUA hiện có.
### Nghiên cứu bổ sung: BizChatAI / Bizfly

- Nguồn chính thức được mở trực tiếp: https://bizfly.vn/giai-phap/chat-bot-ai.html (20/10/2026).
- Nội dung công khai thể hiện thứ tự: định vị và lời hứa về hiểu ngữ cảnh; minh họa sản phẩm; năng lực; use case theo ngành với cặp vấn đề → giải pháp; tiếp đến social proof, FAQ và CTA tư vấn.
- Trang công khai liệt kê các nhóm năng lực gồm agent, cơ sở tri thức, phân loại hội thoại, live chat đa kênh, hồ sơ khách hàng, đơn hàng và báo cáo. Đây là nội dung Bizfly tự công bố, không phải xác nhận độc lập về hiệu quả.
- Pattern có thể học: nối thông điệp sản phẩm với hình ảnh sản phẩm sớm; diễn đạt tính năng qua tác vụ cụ thể; dùng use case để giải thích vấn đề nào được giải quyết; kéo dài hành trình tin cậy bằng proof, FAQ và CTA phù hợp.
- Suy luận áp dụng cho AI Inbox Pro: làm rõ hành trình một hội thoại từ nhận diện nhu cầu đến đối chiếu dữ liệu, đề xuất, rồi bàn giao. Quy trình cần có nhịp thị giác và thứ tự rõ thay vì bốn cột cao, rỗng. Không sao chép logo, claim, awards hay use case của Bizfly; không thêm số liệu hoặc khách hàng chưa được xác thực cho AI Inbox Pro.
- Thay đổi triển khai: tăng tương phản và cỡ chữ hero; giảm chiều cao tối thiểu; chuyển quy trình thành section nền navy, tiêu đề lớn, divider, thứ tự 01–04 và mô tả dễ đọc; mobile xếp dọc và giảm cỡ chữ để tránh ngắt dòng vụn.
- Kiểm tra local trong lượt này: accessibility tree còn đủ bốn bước; ảnh viewport hẹp cho thấy section nền tối với từng bước được phân tách rõ. Đây chỉ là kiểm tra lát cắt, chưa nghiệm thu toàn Landing; chưa chấm điểm và chưa chuyển task. Còn phải rà đủ Desktop/Tablet/Mobile, links, focus, reduced motion, console/network và test.
