#!/usr/bin/env python3
"""
Multi-Class Customer Intent & Sentiment Classifier with Buying Urgency Detection.
Analyzes Vietnamese eCommerce customer queries into 7 distinct intents, 3 sentiments,
and a 0-100 buying urgency score without external heavy NLP dependencies.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from ai_inbox.engine.semantic_matcher import normalize_vietnamese

@dataclass
class IntentResult:
    primary_intent: str
    confidence: float
    intent_scores: Dict[str, float]
    sentiment: str  # "positive", "neutral", "negative"
    urgency_score: int  # 0 to 100
    is_urgent: bool
    signals: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_intent": self.primary_intent,
            "confidence": round(self.confidence, 3),
            "intent_scores": {k: round(v, 3) for k, v in self.intent_scores.items()},
            "sentiment": self.sentiment,
            "urgency_score": self.urgency_score,
            "is_urgent": self.is_urgent,
            "signals": self.signals,
            "entities": self.entities
        }

class IntentClassifier:
    """
    Classifies Vietnamese eCommerce customer messages into 7 intent categories:
    1. READY_TO_ORDER
    2. SIZING_CONSULT
    3. STOCK_INQUIRY
    4. PRICE_CHECK
    5. BARGAIN_REQUEST
    6. SHIPPING_POLICY
    7. COMPLAINT
    """

    INTENT_CLASSES = [
        "READY_TO_ORDER",
        "SIZING_CONSULT",
        "STOCK_INQUIRY",
        "PRICE_CHECK",
        "BARGAIN_REQUEST",
        "SHIPPING_POLICY",
        "COMPLAINT"
    ]

    # Weighted regex patterns (checked against unaccented & normalized text)
    PATTERNS: Dict[str, List[Tuple[str, float]]] = {
        "READY_TO_ORDER": [
            (r"\b(chot\b|chot don|dat hang|mua ngay|lay cho minh|gui cho minh|ship cho minh|minh lay|minh muon mua)\b", 4.5),
            (r"\b(thanh toan|cod|dia chi|sdt|so dien thoai|nhan hang tai)\b", 2.5),
            (r"\b(cho minh \d+|cho \d+ cai|lay \d+ cai|mua \d+ cai|cho 1 cai|lay 1 cai)\b", 4.0),
            (r"0\d{8,10}", 3.0),
        ],
        "SIZING_CONSULT": [
            (r"\b(tu van size|chon size|mac size|size gi|sz gi|vua khong|vua ko)\b", 4.5),
            (r"\b(nang\s+\d+|cao\s+\d+|\d+\s*kg|\d+m\d*|\d+\s*cm)\b", 3.5),
            (r"\b(form rong|form om|form rong ko|bang size|size chart|co vua)\b", 3.0),
            (r"\b(size s|size m|size l|size xl|size xxl|sz s|sz m|sz l|sz xl)\b", 2.0),
        ],
        "STOCK_INQUIRY": [
            (r"\b(con hang khong|con hang ko|con ko|con khong|het hang chua|het chua)\b", 4.5),
            (r"\b(con mau|con size|san hang|co san khong|co san ko|san kho)\b", 3.5),
            (r"\b(mau den con|mau trang con|mau xanh con|size l con|size m con)\b", 3.0),
        ],
        "PRICE_CHECK": [
            (r"\b(gia bao nhieu|gia sao|bao nhieu tien|nhieu tien|bao nhieu vay|bn tien|bao gia|xin gia|cho.*xin gia)\b", 5.0),
            (r"\b(gia\b|price|cost|\bbn\b|gia the nao|nhieu vay)\b", 2.5),
        ],
        "BARGAIN_REQUEST": [
            (r"\b(co giam gia|duoc giam gia|giam gia khong|giam gia ko|co ma giam gia|co voucher|bot khong|bot ko|fix khong|fix gia)\b", 5.0),
            (r"\b(co khuyen mai|uu dai|chiet khau|giam them|co fix)\b", 3.5),
        ],
        "SHIPPING_POLICY": [
            (r"\b(phi ship|ship bao lau|freeship|mien phi ship|bao gio toi|bao lau nhan)\b", 4.0),
            (r"\b(giao hang|van chuyen|ship ve|ship den|phi van chuyen|giao tinh)\b", 3.0),
        ],
        "COMPLAINT": [
            (r"\b(sao lau the|sao cham the|chua thay giao|hang loi|hang rach|hang kem|khong giong anh)\b", 4.5),
            (r"\b(lua dao|that vong|te qua|hoan tien|doi tra|khong rep|sao khong tra loi|lam an)\b", 4.0),
            (r"\b(bực|kho chiu|tuc|bua)\b", 2.5),
        ]
    }

    # Sentiment Patterns
    POSITIVE_WORDS = [
        r"\b(tuyet voi|dep qua|ung y|nhiet tinh|cam on|thanks|thich qua|tot lam|de thuong|chat luong)\b"
    ]
    NEGATIVE_WORDS = [
        r"\b(te qua|that vong|lua dao|sao lau the|kem|lau qua|buc|kem chat luong|kieu gi|doi tra|hoan tien)\b"
    ]

    # Urgency Triggers
    URGENT_WORDS = [
        r"\b(gap|ngay|hom nay|ngay mai|kip khong|can gap|chieu nay|sang mai|tang sinh nhat|di tiec)\b"
    ]

    def classify(self, text: str) -> IntentResult:
        """
        Classifies incoming text into primary intent, intent distribution,
        sentiment label, and buying urgency score.
        """
        if not text or not text.strip():
            return IntentResult(
                primary_intent="STOCK_INQUIRY",
                confidence=0.0,
                intent_scores={c: 0.0 for c in self.INTENT_CLASSES},
                sentiment="neutral",
                urgency_score=0,
                is_urgent=False
            )

        norm_text = normalize_vietnamese(text.lower())
        raw_scores: Dict[str, float] = {c: 0.1 for c in self.INTENT_CLASSES}
        signals: List[str] = []
        entities: Dict[str, Any] = {}

        # 1. Evaluate Intent Patterns
        for intent_cls, patterns in self.PATTERNS.items():
            for pattern, weight in patterns:
                matches = re.findall(pattern, norm_text)
                if matches:
                    raw_scores[intent_cls] += weight * len(matches)
                    signals.append(f"{intent_cls}:{pattern}")

        # 2. Extract Entities (Phone, Height, Weight, Size)
        phone_match = re.search(r"\b(0\d{8,10})\b", norm_text)
        if phone_match:
            entities["phone"] = phone_match.group(1)
            raw_scores["READY_TO_ORDER"] += 3.0
            signals.append("entity:phone")

        h_w_match = re.search(r"(\d+\s*m\d*|\d+\s*cm|\d+\s*kg)", norm_text)
        if h_w_match:
            entities["metrics"] = h_w_match.group(1)
            raw_scores["SIZING_CONSULT"] += 2.0
            signals.append("entity:metrics")

        # 3. Disambiguation priority
        # If order intent is strong with phone or address, ready to order dominates
        if "phone" in entities and raw_scores["READY_TO_ORDER"] >= 3.0:
            raw_scores["READY_TO_ORDER"] += 3.0

        # Shipping fee inquiries ("phi ship bao nhieu") dominate general price check
        if re.search(r"\b(phi ship|tien ship|phi van chuyen)\b", norm_text):
            raw_scores["SHIPPING_POLICY"] += 4.0
            raw_scores["PRICE_CHECK"] = min(raw_scores["PRICE_CHECK"], 1.5)

        # Discount / Bargain inquiries dominate tentative purchase words (e.g., "Mua 2 áo có được giảm giá không")
        if raw_scores["BARGAIN_REQUEST"] >= 4.0 and "phone" not in entities:
            raw_scores["BARGAIN_REQUEST"] += 3.0
            raw_scores["READY_TO_ORDER"] = min(raw_scores["READY_TO_ORDER"], 1.5)

        # Complaint phrases override general price/sizing
        if any(re.search(p, norm_text) for p in self.NEGATIVE_WORDS) and raw_scores["COMPLAINT"] > 2.0:
            raw_scores["COMPLAINT"] += 4.0

        # Normalize intent probability distribution
        total = sum(raw_scores.values())
        prob_dist = {c: raw_scores[c] / total for c in self.INTENT_CLASSES}

        primary_intent = max(prob_dist, key=prob_dist.get)
        confidence = prob_dist[primary_intent]

        # 4. Sentiment Detection
        pos_score = sum(len(re.findall(p, norm_text)) for p in self.POSITIVE_WORDS)
        neg_score = sum(len(re.findall(p, norm_text)) for p in self.NEGATIVE_WORDS)

        if neg_score > 0 or primary_intent == "COMPLAINT":
            sentiment = "negative"
        elif pos_score > 0:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        # 5. Urgency Score Calculation (0 - 100)
        urgency = 10
        if "phone" in entities:
            urgency += 40
        if primary_intent == "READY_TO_ORDER":
            urgency += 35
        elif primary_intent == "COMPLAINT":
            urgency += 30
        elif primary_intent in ("SIZING_CONSULT", "STOCK_INQUIRY"):
            urgency += 15

        if any(re.search(p, norm_text) for p in self.URGENT_WORDS):
            urgency += 25
            signals.append("urgency:time_sensitive")

        urgency_score = min(100, max(0, urgency))
        is_urgent = urgency_score >= 65

        return IntentResult(
            primary_intent=primary_intent,
            confidence=confidence,
            intent_scores=prob_dist,
            sentiment=sentiment,
            urgency_score=urgency_score,
            is_urgent=is_urgent,
            signals=signals,
            entities=entities
        )
