"""Price extraction utilities for trading signals"""

import re


class PriceExtractor:
    """Extracts various price levels from trading signal messages"""

    # Pre-compiled regex patterns for performance
    _first_price_patterns = [
        re.compile(r'(\d+(?:\.\d+)?)'),  # General number pattern
        re.compile(r'(\d+\.\d+)'),       # Decimal number
        re.compile(r'@ (\d+\.\d+)'),     # @ symbol followed by price
    ]

    _second_price_patterns = [
            (re.compile(r'(\d+\.?\d*)[_\uFF3F]+(\d+\.?\d*)'), 2),      # 4220_4224 (underscore or fullwidth underscore)
            (re.compile(r'(\d+\.?\d*)\s*[:\-]\s*(\d+\.?\d*)'), 2),     # 4220-4224 or 4220:4224
            (re.compile(r'\b\d+\.?\d*///(\d+\.?\d*)'), 1),
            (re.compile(r'@\d+\.?\d*\s*-\s*(\d+\.?\d*)'), 1),
            (re.compile(r'2(?:nd)?\s+limit\s*@\s*(\d+\.?\d*)', re.IGNORECASE), 1),
            (re.compile(r'\b\d+\.?\d*__+(\d+\.?\d*)'), 1),
            (re.compile(r'@\s*\d+\.?\d*\s*-\s*(\d+\.?\d*)'), 1),
            (re.compile(r'@\s*\d+\.?\d*\s*-\s*(\d+\.?\d*)|:\s*\d+\.?\d*\s*-\s*(\d+\.?\d*)'), [1, 2]),
            (re.compile(r'\b\d+\.?\d*\s*-\s*(\d+\.?\d*)'), 1),
            (re.compile(r'\b\d+\b\s*و\s*(\d+)\s*فروش'), 1),
            (re.compile(r'\b\d+\b\s*و\s*(\d+)\s*خرید'), 1),
            (re.compile(r'\b\d+\.?\d*/(\d+\.?\d*)'), 1),
            (re.compile(r'=\s*(\d+\.?\d*)'), 1),
            (re.compile(r'(?:\d+\.\d+)[^\d]+(\d+\.\d+)'), 1),
            # as a last resort: find *two* numbers near each other separated by non-digit (but keep it conservative)
            (re.compile(r'(\d+\.?\d*)\D{1,3}(\d+\.?\d*)'), 2),
        ]

    _tp_patterns = [
        re.compile(r'tp\s*\d*\s*[@:.\-]?\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'tp\s*(?:\d*\s*:\s*)?(\d+\.\d+)', re.IGNORECASE),
        re.compile(r'\btp\b\s*[:\-@.]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
        re.compile(r'tp\s*:\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'tp1\s*:\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'tp1\s*\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'tp\s*[-:]\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'tp\s*1\s*[-:]\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'checkpoint\s*1\s*:\s*(\d+\.?\d*|OPEN)', re.IGNORECASE),
        re.compile(r'takeprofit\s*1\s*=\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'take\s*profit\s*1\s*:\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'tp\d+\.\s*(\d+\.?\d*)', re.IGNORECASE),  # TP1. 4130, TP2. 4138, etc.
        re.compile(r'tp\.\s*(\d+\.?\d*)', re.IGNORECASE),  # TP. 4130 (after superscript removal)
        re.compile(r'tp\.(\d+\.?\d*)', re.IGNORECASE),  # TP.4130 (no space after dot)
        re.compile(r'تی پی\s*(\d+)', re.IGNORECASE),  # Persian
    ]

    _sl_patterns = [
        re.compile(r'sl\s*:\s*(\d+\.\d+)', re.IGNORECASE),
        re.compile(r'sl\s*:\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'(?i)stop\s*(\d+\.?\d*)'),
        re.compile(r'حد\s*(\d+\.\d+|\d+)', re.IGNORECASE),  # Persian
        re.compile(r'STOP LOSS\s*:\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'sl\s*[-:]\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'sl\s*[:\-]\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'stop\s*loss\s*[:\-]\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'sl\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'stop\s*loss\s*[@:]\s*(\d+\.?\d*)', re.IGNORECASE),
        re.compile(r'Stoploss\s*=\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'SL\s*@\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'(?i)stop\s*loss\s*(\d+)'),
        re.compile(r'استاپ\s*(\d+\.?\d*)', re.IGNORECASE),  # Persian
        re.compile(r'sl[\s.:]*([\d]+\.?\d*)', re.IGNORECASE),
        re.compile(r'stop\s*loss\s*(?:point)?\s*[:\-]?\s*(\d+\.\d+|\d+)', re.IGNORECASE),
        re.compile(r'sl\s*:::*(\d+\.?\d*)', re.IGNORECASE),  # SL:::4090 format
    ]

    _simple_price_pattern = re.compile(r'@[\s]*([0-9]+(?:\.[0-9]+)?)')

    @staticmethod
    def extract_first_price(message):
        """Extract the primary entry price from message"""
        try:
            # Replace US30 with DJIUSD for consistency
            message = message.upper().replace("US30", "DJIUSD")

            # Try pre-compiled patterns for first price
            for pattern in PriceExtractor._first_price_patterns:
                match = pattern.findall(message)
                if match:
                    return float(match[0])

            return None
        except Exception:
            return None

    @staticmethod
    def extract_second_price(message):
        """Extract the secondary entry price from message"""
        try:
            # Try pre-compiled patterns for second price detection
            for pattern, group in PriceExtractor._second_price_patterns:
                match = pattern.search(message)
                if match:
                    if isinstance(group, list):
                        return float(match.group(group[0]) or match.group(group[1]))
                    else:
                        return float(match.group(group))

            return None
        except Exception:
            return None

    @staticmethod
    def extract_take_profits(message):
        """Extract take profit levels from message"""
        try:
            if not message:
                return None

            tp_numbers = []
            sentences = re.split(r'\n+', message)

            for sentence in sentences:
                # Multiple patterns for TP extraction
                tp_patterns = [
                    r'tp\s*\d*\s*[@:.\-]?\s*(\d+\.\d+|\d+)',
                    r'tp\s*(?:\d*\s*:\s*)?(\d+\.\d+)',
                    r'\btp\b\s*[:\-@.]?\s*(\d+(?:\.\d+)?)',
                    r'tp\s*:\s*(\d+\.?\d*)',
                    r'tp1\s*:\s*(\d+\.?\d*)',
                    r'tp1\s*\s*(\d+\.?\d*)',
                    r'tp\s*[-:]\s*(\d+\.\d+|\d+)',
                    r'tp\s*1\s*[-:]\s*(\d+\.\d+|\d+)',
                    r'checkpoint\s*1\s*:\s*(\d+\.?\d*|OPEN)',
                    r'takeprofit\s*1\s*=\s*(\d+\.\d+|\d+)',
                    r'take\s*profit\s*1\s*:\s*(\d+\.\d+|\d+)',
                    r'tp\d+\.\s*(\d+\.?\d*)',  # TP1. 4130, TP2. 4138, etc.
                    r'tp\.\s*(\d+\.?\d*)',  # TP. 4130 (after superscript removal)
                    r'tp\.(\d+\.?\d*)',  # TP.4130 (no space after dot)
                    r'تی پی\s*(\d+)',  # Persian
                ]

                for pattern in tp_patterns:
                    matches = re.findall(pattern, sentence, re.IGNORECASE)
                    if matches:
                        tp_numbers.extend([float(tp) for tp in matches if tp != '0'])

                # Additional TP patterns
                tp_match_takeprofit = re.findall(
                    r'take\s*profit\s*\d+\s*[-:]\s*(\d+\.\d+|\d+)', sentence, re.IGNORECASE)
                if tp_match_takeprofit:
                    tp_numbers.extend([float(tp) for tp in tp_match_takeprofit])

                # TP2, TP3, TP4 patterns
                tp_match_2 = re.findall(
                    r'tp(\d+)\s*[:\-]?\s*(\d+\.\d+|\d+)', sentence, re.IGNORECASE)
                if tp_match_2:
                    for tp in tp_match_2:
                        tp_numbers.append(float(tp[1]))

                # Persian comma-separated TP values
                persian_tp_match = re.findall(r'تی پی\s*([\d\s,،]+)', sentence)
                if persian_tp_match:
                    persian_tp_numbers = []
                    for match in persian_tp_match:
                        numbers = [float(tp.strip()) for tp in re.split(r'[,\s،]+', match)
                                 if tp.strip().isdigit() and '/' not in tp]
                        persian_tp_numbers.extend(numbers)
                    return list(dict.fromkeys(persian_tp_numbers))
                
                target_matches = re.findall(r'(?:تارگت|هدف)\s*([\d\-–—\s]+)', sentence)
                if target_matches:
                    for match in target_matches:
                        nums = re.split(r'[-–—\s]+', match)
                        tp_numbers.extend([float(n) for n in nums if n.strip().isdigit()])
                        
            # Filter out invalid values
            if not tp_numbers or tp_numbers == [1.0]:
                return None

            # Remove duplicates and invalid values
            tp_numbers = list(dict.fromkeys(tp_numbers))
            return {tp for tp in tp_numbers if tp != 1.0}

        except Exception:
            return None

    @staticmethod
    def extract_stop_loss(message: str):
        """
        Extract Stop Loss (SL) value from Persian / English trading messages.
        Returns float or None
        """
        if not message:
            return None

        message = message.lower()

        # Unified SL keywords (Persian + English)
        sl_keywords = [
            r'sl',
            r'stop\s*loss',
            r'stoploss',
            r'stop',
            r'استاپ',
            r'حد\s*ضرر',
            r'ضرر',
            r'حد'
        ]

        # Build one strong regex
        sl_pattern = rf'''
            (?:{"|".join(sl_keywords)})      # SL keywords
            \s*                              # optional space
            [:@=\-]*                         # optional separators
            \s*
            (\d+(?:\.\d+)?)                  # price number
        '''

        matches = re.findall(sl_pattern, message, re.IGNORECASE | re.VERBOSE)

        if matches:
            try:
                return float(matches[0])
            except ValueError:
                return None

        # Fallback: number before 'sl'
        fallback = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:sl|stop)',
            message,
            re.IGNORECASE
        )

        if fallback:
            try:
                return float(fallback.group(1))
            except ValueError:
                return None

        return None
    
    @staticmethod
    def extract_simple_price(message):
        """Extract a simple price with @ symbol"""
        match = re.search(r'@[\s]*([0-9]+(?:\.[0-9]+)?)', message)
        if match:
            return float(match.group(1))
        return None