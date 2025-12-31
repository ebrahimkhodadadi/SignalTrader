"""Action type detection for trading signals"""

import re
from enum import Enum


class TradeType(Enum):
    """Enumeration of trading action types"""
    Buy = 1
    Sell = 2


class ActionDetector:
    """Detects buy/sell actions from trading signal messages"""

    # Keywords for buy actions
    BUY_KEYWORDS = [
        'buy', 'بخر', 'خرید', 'بای'
    ]

    # Keywords for sell actions
    SELL_KEYWORDS = [
        'sell', 'selll', 'بفروش', 'فروش', 'selling', "𝐒𝐞𝐥𝐥", 'سل'
    ]

    @staticmethod
    def detect_action_type(sentence):
        """Detect the main trading action (buy/sell) from a sentence"""
        if not sentence:
            return None

        words = sentence.split()

        # Check each word for buy/sell keywords
        for word in words:
            # Check buy keywords
            if word.lower() in ActionDetector.BUY_KEYWORDS or re.search(r"buy", word, re.IGNORECASE):
                return TradeType.Buy

            # Check sell keywords
            elif word.lower() in ActionDetector.SELL_KEYWORDS or re.search(r"sell", word, re.IGNORECASE):
                return TradeType.Sell

        return None