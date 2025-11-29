import re
import json
from datetime import datetime, timedelta


class ExtractionHelper:
    # Convert Chinese numbers to Integers (Simple mapping for 0-99)
    def cn_to_int(cn_str):
        if cn_str is None:
            return 0
        elif cn_str.isdigit():
            return int(cn_str)

        cn_map = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "两": 2,
        }
        if cn_str in cn_map:
            return cn_map[cn_str]
        # Handle '十一' to '十九'
        if len(cn_str) > 1 and cn_str.startswith("十"):
            return 10 + (cn_map.get(cn_str[1], 0) if len(cn_str) > 1 else 0)
        # Handle '二十' to '二十X'
        if len(cn_str) > 1 and cn_str.startswith("二") and "十" in cn_str:  # e.g. 二十
            val = 20
            if cn_str.endswith("十"):
                return val

            return val + cn_map.get(cn_str.split("十")[-1], 0)

        return 0

    def parse_text_to_event(user_text):
        now = datetime.now()
        # Note: Ignore scenario like 'reference_time' in Demo.
        target_date = now.date()

        if "明天" in user_text:
            target_date += timedelta(days=1)
        elif "大后天" in user_text:
            target_date += timedelta(days=3)
        elif "后天" in user_text:
            target_date += timedelta(days=2)
        elif "今天" in user_text:
            pass  # Do nothing.

        # 3. Extract Time Points (Looking for X点 or X:XX)
        # Pattern looks for digits or Chinese numbers followed by "点" or ":"
        regex_time = r"(上午|下午|晚上)?\s*([0-9]+|[一二三四五六七八九十]+)[:点]?([0-9]+)?"

        # We scan the text specifically for "X点" or time formats to identify start/end
        matches = list(re.finditer(regex_time, user_text))

        start_hour = 9  # Default start if not found (9 AM)
        end_hour = 10  # Default end
        start_minute = 0
        end_minute = 0

        if matches:
            # First match is Start Time
            s_num = matches[0].group(1)
            start_hour = ExtractionHelper.cn_to_int(s_num)

            # Handle "PM" logic loosely (if '下午' or '晚上' appears before the number)
            # A robust system would check the index of "下午" relative to the match
            if "下午" in user_text and start_hour < 12:
                start_hour += 12
            elif "晚上" in user_text and start_hour < 12:
                start_hour += 12

            # Determine End Time
            if len(matches) >= 2:
                # Case A: "10点到11点" (Explicit End Time)
                e_num = matches[1].group(1)
                end_hour = ExtractionHelper.cn_to_int(e_num)

                if (
                    end_hour < start_hour
                ):  # Assume PM if end is smaller (e.g. 10am to 2pm)
                    end_hour += 12
            else:
                # Case B: Check for Duration (e.g. "一个小时", "2 hours")
                dur_match = re.search(r"([0-9]+|[一二三四五六七八九十两]+)\s*个?小时", user_text)
                if dur_match:
                    duration = ExtractionHelper.cn_to_int(dur_match.group(1))
                    end_hour = start_hour + duration
                else:
                    # Default to 1 hour duration if only start time is given
                    end_hour = start_hour + 1

        # 4. Construct Datetime Objects
        start_dt = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            start_hour,
            start_minute,
        )
        end_dt = datetime(
            target_date.year, target_date.month, target_date.day, end_hour, end_minute
        )

        # 5. Extract Title (Remove time keywords from text to leave the subject)
        # This removes words like "明天", "10点", "到", etc. to clean up the title.
        clean_text = user_text
        remove_patterns = [
            r"明天|后天|今天",
            r"上午|下午|晚上",
            r"[0-9一二三四五六七八九十两]+\s*(点|:|：|个?小时)",
            r"\s*到\s*",
            r"日程安排",
            r"给我的.*加上",
        ]
        for p in remove_patterns:
            clean_text = re.sub(p, "", clean_text)

        # Clean up punctuation and whitespace
        title = clean_text.strip(" ,，.。")

        # 6. Build Result
        result = {
            "title": title,
            "start_time": start_dt.isoformat(),  # Returns format 'YYYY-MM-DDTHH:MM:SS'
            "end_time": end_dt.isoformat(),
        }

        return result


# --- Testing the function ---

# Test Case 1: Standard request
text1 = "给我的谷歌日历加上一个日程安排，明天上午十点到 11 点，和公司 CEO 会议。"
print(f"Input: {text1}")
print(
    json.dumps(
        ExtractionHelper.parse_text_to_event(text1), indent=2, ensure_ascii=False
    )
)

print("-" * 20)

# Test Case 2: Duration based ("One hour")
text2 = "明天十点开会一个小时，讨论产品架构"
print(f"Input: {text2}")
print(
    json.dumps(
        ExtractionHelper.parse_text_to_event(text2), indent=2, ensure_ascii=False
    )
)

print("-" * 20)

# Test Case 3: Informal / Mixed numbers ("明早十点")
text3 = "明早十点去见客户"
print(f"Input: {text3}")
print(
    json.dumps(
        ExtractionHelper.parse_text_to_event(text3), indent=2, ensure_ascii=False
    )
)
