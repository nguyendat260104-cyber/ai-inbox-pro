#!/usr/bin/env python3
"""
Lead Scoring & Buying Intent Intelligence Engine
Analyzes customer messages to score purchasing intent (0 - 100) and identify HOT leads.
"""

import re
from typing import Dict, Any, Tuple, List

class LeadScorer:
    # Buying intent keywords & regex patterns for Vietnamese eCommerce
    PRICE_PATTERNS = [r"giá", r"bao nhiêu", r"nhiêu tiền", r"bn", r"cost", r"price"]
    SIZE_PATTERNS = [r"\bsize\b", r"\bcỡ\b", r"\bm\b", r"\bl\b", r"\bxl\b", r"\bs\b", r"\bxxl\b", r"nặng .*kg", r"cao .*m"]
    COLOR_PATTERNS = [r"màu", r"mầu", r"đen", r"trắng", r"xanh", r"đỏ", r"vàng", r"hồng", r"be", r"xám"]
    SHIPPING_PATTERNS = [r"ship", r"giao hàng", r"vận chuyển", r"đà nẵng", r"hà nội", r"sài gòn", r"hcm", r"bao lâu", r"phí"]
    BUY_INTENT_PATTERNS = [
        r"mua", r"đặt", r"lấy", r"chốt", r"cho mình 1", r"cho mình 2", r"gửi cho", 
        r"thanh toán", r"cod", r"nhận hàng", r"địa chỉ", r"sđt", r"số điện thoại"
    ]
    HUMAN_REQUEST_PATTERNS = [r"gặp nhân viên", r"người thật", r"tư vấn viên", r"admin", r"chăm sóc khách hàng"]

    def analyze_message(self, text: str, current_score: int = 0) -> Tuple[int, str, List[str]]:
        """
        Analyze customer text and return (new_score, intent_label, detected_signals).
        Intent labels: 'HOT' (>=75), 'WARM' (40-74), 'COLD' (<40)
        """
        lower = text.lower()
        signals = []
        score_gain = 0

        # 1. Direct Purchase Intent Signals (+45 points)
        if any(re.search(p, lower) for p in self.BUY_INTENT_PATTERNS):
            score_gain += 45
            signals.append("ready_to_buy")

        # 2. Size / Fit Specification (+25 points)
        if any(re.search(p, lower) for p in self.SIZE_PATTERNS):
            score_gain += 25
            signals.append("specifying_size")

        # 3. Color Preference (+20 points)
        if any(re.search(p, lower) for p in self.COLOR_PATTERNS):
            score_gain += 20
            signals.append("specifying_color")

        # 4. Shipping / Delivery Destination (+20 points)
        if any(re.search(p, lower) for p in self.SHIPPING_PATTERNS):
            score_gain += 20
            signals.append("asking_shipping")

        # 5. Price Inquiry (+15 points)
        if any(re.search(p, lower) for p in self.PRICE_PATTERNS):
            score_gain += 15
            signals.append("asking_price")

        # 6. Explicit request for human staff (+35 points)
        if any(re.search(p, lower) for p in self.HUMAN_REQUEST_PATTERNS):
            score_gain += 35
            signals.append("human_request")

        # 7. Customer provided phone number or address (+50 points)
        phone_match = re.search(r"(0\d{9}|0\d{8})", lower)
        if phone_match:
            score_gain += 50
            signals.append("provided_phone")

        new_score = min(100, current_score + score_gain)
        if not signals:
            new_score = max(current_score, 10) # Base greeting / FAQ score

        if new_score >= 75:
            label = "HOT"
        elif new_score >= 40:
            label = "WARM"
        else:
            label = "COLD"

        return new_score, label, signals
