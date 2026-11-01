# AI Inbox Pro — Continuation Orchestrator Prompt

Use this as the prompt for the recurring Codex heartbeat. It selects work dynamically from the repository instead of replaying one fixed implementation task.

```text
Tiếp tục cải tổ AI Inbox Pro trong C:\Projects\affiliate-automation. Đây là heartbeat tiếp nối backlog, không phải cùng một task lặp lại. Mỗi lần chạy hãy đọc git status/diff, tasks/AGENT_STATE.md, tasks/queued, tasks/AUTOMATION_PROMPT.md, research/reports và QA/evidence mới nhất; chọn next_batch từ trạng thái thật, không từ prompt mặc định.

Cách làm mỗi lượt:
- Tiếp tục slice in_progress; hoàn thành một batch có ý nghĩa gồm triển khai, kiểm tra, sửa lỗi phát hiện và cập nhật evidence/state. Không dừng sau một checklist hay patch nhỏ.
- Có thể hoàn tất nhiều task con liên quan trong cùng batch. Chỉ song song việc độc lập khi multi-agent/tool khả dụng và không có xung đột file; nếu không, làm tuần tự an toàn. Không để nhiều worker sửa cùng trang hoặc CSS/JS.
- Không lặp nghiên cứu, review hay code đã xong. Tái dùng báo cáo; chỉ nghiên cứu bổ sung khi thiếu câu trả lời. Nếu bị chặn, ghi nguyên nhân cụ thể và chuyển sang phần việc không bị chặn.
- Thứ tự hiện tại: (1) Landing đến khi toàn trang qua quality gate; (2) Brand identity consolidation; (3) Product/Solutions/Pricing/Resources thành các trang riêng; (4) Admin Inbox; (5) Demo; (6) cross-route coherence; (7) production-readiness hardening. Các task chất lượng mới không được làm gián đoạn slice đang active. Thứ tự này thắng dependencies cũ trong task JSON.
- Mỗi slice chỉ pass khi acceptance có evidence desktop/tablet/mobile, route/CTA/tương tác, keyboard/focus, contrast, reduced motion, overflow, console/network và tests phù hợp; không P0/P1; điểm rubric có căn cứ >90/100. Nếu thiếu evidence, giữ in_progress, không tự chấm/không chuyển task.
- Cập nhật tasks/AGENT_STATE.md và report sau mỗi batch; giữ lịch sử và mọi thay đổi người dùng. Không reset/clean/revert/overwrite.
- Backend chưa có: bot, tồn kho, channel và handoff demo phải ghi rõ là mô phỏng; không bịa kết nối, số liệu xác thực hay customer proof.

Không commit, push, deploy, chi tiền, dùng credentials thật hoặc sửa project khác. Chỉ chuẩn bị Vercel khi toàn bộ UI qua gate và user duyệt. Giữ im lặng ở checkpoint bình thường; báo milestone có evidence, blocker thật, lỗi nghiêm trọng hoặc quyết định cần user.
```
