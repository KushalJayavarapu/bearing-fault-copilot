"""Stand-in for Santos's retrieval (contract section 2) until it is connected.

Same request and response shape as the contract. The passages are short general statements written for development,
labeled [STUB] in the title and in the text, so nobody can mistake them for a real source.
"""

_TAG = "Stub text for development only. "
_P = {
    "normal": [("monitor", "Healthy bearings show low, steady vibration with no repeating impacts. Keep routine condition monitoring and trend the readings over time.")],
    "inner_race": [
        ("defect", "An inner ring defect shows as repeating impacts at the inner-race fault frequency. Common causes are fatigue, overload, too tight a fit on the shaft, poor lubrication and contamination."),
        ("action", "Before opening a bearing housing, stop the machine and isolate the power. Inspect the raceway and shaft seat, check lubricant and fit, and replace the bearing if damage is confirmed.")],
    "outer_race": [
        ("defect", "An outer ring defect shows as a repeating impact at the outer-race fault frequency. Common causes are fatigue, misalignment, poor lubrication, contamination and a wrong fit in the housing."),
        ("action", "Before opening a bearing housing, stop the machine and isolate the power. Inspect the outer raceway, check alignment, lubricant and housing fit, and replace the bearing if damage is confirmed.")],
    "ball": [
        ("defect", "Damage to the rolling elements is the hardest bearing fault to confirm from vibration alone. Common causes are wear, contamination in the lubricant and shock loading."),
        ("action", "Before opening a bearing housing, stop the machine and isolate the power. Inspect the balls and cage, check the lubricant, and replace the bearing if damage is confirmed.")],
}


def retrieve(request: dict) -> dict:
    ft = request["fault_type"]
    passages = [{"chunk_id": f"stub-{ft}-{kind}", "text": _TAG + text, "source_title": "[STUB] Placeholder bearing guide",
                 "source_type": "guide", "page": n, "url": "https://example.com/stub"}
                for n, (kind, text) in enumerate(_P[ft], start=1)]
    return {"passages": passages[: request.get("top_k", 5)]}
