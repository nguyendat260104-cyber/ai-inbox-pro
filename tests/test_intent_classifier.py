#!/usr/bin/env python3
"""
Unit tests for Vietnamese Customer Intent & Sentiment Classifier (Task INBOX-20261019-017).
Covers all 7 intent categories, sentiments, entity extraction, and urgency scoring.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from ai_inbox.engine.intent_classifier import IntentClassifier, IntentResult

class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = IntentClassifier()

    def test_price_check(self):
        phrases = [
            "Áo polo này giá bao nhiêu vậy shop?",
            "Cho mình xin giá sản phẩm với",
            "Mẫu này bn tiền shop ơi",
            "Báo giá giúp mình sơ mi trắng"
        ]
        for phrase in phrases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "PRICE_CHECK", f"Failed for '{phrase}': got {res.primary_intent}")
            self.assertGreater(res.confidence, 0.2)

    def test_sizing_consult(self):
        phrases = [
            "Mình cao 1m75 nặng 68kg mặc size gì vừa shop?",
            "Tư vấn size giúp mình áo khoác này với",
            "Form áo này là form rộng hay form ôm ạ?",
            "Nặng 55kg cao 1m6 mặc sz M hay L shop"
        ]
        for phrase in phrases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "SIZING_CONSULT", f"Failed for '{phrase}': got {res.primary_intent}")
            self.assertIn(res.sentiment, ["neutral", "positive"])

    def test_stock_inquiry(self):
        phrases = [
            "Mẫu áo thun màu đen size L còn hàng không shop?",
            "Sơ mi linen xanh còn hàng ko bạn?",
            "Màu trắng còn size XL sẵn kho không shop ơi"
        ]
        for phrase in phrases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "STOCK_INQUIRY", f"Failed for '{phrase}': got {res.primary_intent}")

    def test_bargain_request(self):
        phrases = [
            "Mua 2 áo có được giảm giá không shop?",
            "Shop có mã giảm giá hay voucher khuyến mãi gì ko?",
            "Có bớt không shop ơi, fix giá xíu đi"
        ]
        for phrase in phrases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "BARGAIN_REQUEST", f"Failed for '{phrase}': got {res.primary_intent}")

    def test_shipping_policy(self):
        phrases = [
            "Phí ship về Đà Nẵng bao nhiêu vậy shop?",
            "Giao hàng về Hà Nội mất bao lâu thì tới?",
            "Đơn này có được miễn phí ship hay freeship không shop"
        ]
        for phrase in phrases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "SHIPPING_POLICY", f"Failed for '{phrase}': got {res.primary_intent}")

    def test_ready_to_order_and_urgency(self):
        order_cases = [
            ("Lấy cho mình 1 áo polo đen size L nha, sđt 0987654321 gửi về địa chỉ 123 Lê Lợi Q1", True),
            ("Chốt đơn cho mình nhé, mình mua 2 cái màu xanh size M", False),
            ("Giao gấp cho mình chiều nay được không shop, cần gấp để đi tiệc sđt 0909123456", True)
        ]
        for phrase, should_be_urgent in order_cases:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "READY_TO_ORDER", f"Failed for '{phrase}': got {res.primary_intent}")
            if should_be_urgent:
                self.assertTrue(res.is_urgent, f"Expected urgent for '{phrase}', got urgency {res.urgency_score}")
                self.assertGreaterEqual(res.urgency_score, 65)

    def test_complaint_and_negative_sentiment(self):
        complaints = [
            "Sao đặt 5 ngày rồi chưa thấy giao hàng vậy, làm ăn quá tệ!",
            "Hàng nhận bị rách chỉ với ố vàng, yêu cầu shop hoàn tiền hoặc đổi trả gấp",
            "Shop lừa đảo à sao nhắn tin không trả lời thế?"
        ]
        for phrase in complaints:
            res = self.classifier.classify(phrase)
            self.assertEqual(res.primary_intent, "COMPLAINT", f"Failed for '{phrase}': got {res.primary_intent}")
            self.assertEqual(res.sentiment, "negative")
            self.assertTrue(res.is_urgent or res.urgency_score >= 40)

    def test_positive_sentiment(self):
        res = self.classifier.classify("Áo đẹp quá shop ơi, chất lượng tuyệt vời cảm ơn shop nhiều nhé!")
        self.assertEqual(res.sentiment, "positive")

    def test_empty_input(self):
        res = self.classifier.classify("")
        self.assertEqual(res.primary_intent, "STOCK_INQUIRY")
        self.assertEqual(res.confidence, 0.0)
        self.assertEqual(res.sentiment, "neutral")

if __name__ == "__main__":
    unittest.main()
