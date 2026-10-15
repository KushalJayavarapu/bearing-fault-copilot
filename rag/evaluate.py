"""
Evaluation test set and benchmarking script for Bearing Fault Copilot RAG pipeline.
Measures Top-5 hit rate and retrieval latency over 18 technician questions across 4 categories:
1. Causes (5 questions)
2. Symptoms and inspection (5 questions)
3. Actions and prevention (5 questions)
4. Safety and handling (3 questions)
"""

import time
import json
from typing import List, Dict, Any
from .interface import retrieve

TEST_QUESTIONS: List[Dict[str, Any]] = [
    # ---- 1. Causes (5 questions) ----
    {
        "id": "Q01",
        "category": "Causes",
        "question": "What causes fatigue flaking and spalling on the inner raceway of a ball bearing?",
        "fault_type": "inner_race",
        "severity": "small",
        "expected_pages": [12, 16],
        "keywords": ["fatigue", "cyclic", "stress", "spalling", "inner"],
    },
    {
        "id": "Q02",
        "category": "Causes",
        "question": "Why does an outer ring develop localized damage specifically in the 6 o'clock bottom zone?",
        "fault_type": "outer_race",
        "severity": "medium",
        "expected_pages": [34],
        "keywords": ["load zone", "6 o'clock", "radial", "spalling", "outer"],
    },
    {
        "id": "Q03",
        "category": "Causes",
        "question": "What causes balls to suffer smearing and sliding skid marks instead of rolling smoothly?",
        "fault_type": "ball",
        "severity": "small",
        "expected_pages": [24],
        "keywords": ["smearing", "skid", "minimum load", "sliding", "acceleration"],
    },
    {
        "id": "Q04",
        "category": "Causes",
        "question": "What produces transverse washboard fluting ridges and electrical erosion across raceways?",
        "fault_type": "inner_race",
        "severity": "medium",
        "expected_pages": [30, 31],
        "keywords": ["electrical", "fluting", "current", "vfd", "erosion"],
    },
    {
        "id": "Q05",
        "category": "Causes",
        "question": "What root cause creates false brinelling and reddish fretting corrosion while a machine is stationary?",
        "fault_type": "outer_race",
        "severity": "small",
        "expected_pages": [28],
        "keywords": ["false brinelling", "fretting", "vibration", "stationary", "standby"],
    },

    # ---- 2. Symptoms and inspection (5 questions) ----
    {
        "id": "Q06",
        "category": "Symptoms and inspection",
        "question": "What does a frosted or dull raceway surface indicate during visual bearing inspection?",
        "fault_type": "inner_race",
        "severity": "small",
        "expected_pages": [16, 19],
        "keywords": ["frosted", "dull", "peeling", "microspalling", "surface"],
    },
    {
        "id": "Q07",
        "category": "Symptoms and inspection",
        "question": "How do you distinguish true brinelling indentations from false brinelling during bearing inspection?",
        "fault_type": "outer_race",
        "severity": "large",
        "expected_pages": [28, 38],
        "keywords": ["true brinelling", "indentation", "raised", "rim", "grinding marks"],
    },
    {
        "id": "Q08",
        "category": "Symptoms and inspection",
        "question": "What visual evidence indicates excessive operating temperature and bearing overheating?",
        "fault_type": "ball",
        "severity": "large",
        "expected_pages": [44],
        "keywords": ["discoloration", "blue", "temperature", "overheating", "baked"],
    },
    {
        "id": "Q09",
        "category": "Symptoms and inspection",
        "question": "What vibration frequencies correspond to localized outer race defects versus inner race defects?",
        "fault_type": "outer_race",
        "severity": "medium",
        "expected_pages": [8],
        "keywords": ["bpfo", "bpfi", "vibration", "frequency", "harmonics"],
    },
    {
        "id": "Q10",
        "category": "Symptoms and inspection",
        "question": "What damage pattern appears when an outer ring is loose inside the bearing housing bore?",
        "fault_type": "outer_race",
        "severity": "small",
        "expected_pages": [32],
        "keywords": ["fretting", "housing", "bore", "loose", "seat"],
    },

    # ---- 3. Actions and prevention (5 questions) ----
    {
        "id": "Q11",
        "category": "Actions and prevention",
        "question": "How can motor bearing lubrication problems and over-greasing damage be prevented?",
        "fault_type": "normal",
        "severity": "none",
        "expected_pages": [15],
        "keywords": ["greasing", "drain plug", "over-greasing", "volume", "purge"],
    },
    {
        "id": "Q12",
        "category": "Actions and prevention",
        "question": "What corrective maintenance action must be taken if a single ball exhibits spalling or pitting?",
        "fault_type": "ball",
        "severity": "small",
        "expected_pages": [22],
        "keywords": ["replace", "entire", "assembly", "never replace individual", "assembly"],
    },
    {
        "id": "Q13",
        "category": "Actions and prevention",
        "question": "What measures prevent recurring shaft current damage from VFD inverter drives?",
        "fault_type": "inner_race",
        "severity": "medium",
        "expected_pages": [30, 31],
        "keywords": ["insulated", "ceramic", "grounding", "brush", "insocoat"],
    },
    {
        "id": "Q14",
        "category": "Actions and prevention",
        "question": "How should abrasive wear and contamination scoring on raceways be remediated?",
        "fault_type": "outer_race",
        "severity": "small",
        "expected_pages": [19],
        "keywords": ["flush", "seals", "purge", "abrasive", "cleanliness"],
    },
    {
        "id": "Q15",
        "category": "Actions and prevention",
        "question": "What alignment tolerance is required to prevent premature bearing load zone failure?",
        "fault_type": "outer_race",
        "severity": "medium",
        "expected_pages": [21, 34],
        "keywords": ["alignment", "laser", "0.05", "tolerance", "misalignment"],
    },

    # ---- 4. Safety and handling (3 questions) ----
    {
        "id": "Q16",
        "category": "Safety and handling",
        "question": "What safety precautions must be followed before dismounting a motor shaft or inspecting couplings?",
        "fault_type": "outer_race",
        "severity": "large",
        "expected_pages": [12, 21, 34],
        "keywords": ["lockout", "tagout", "loto", "safety", "de-energize", "rigging"],
    },
    {
        "id": "Q17",
        "category": "Safety and handling",
        "question": "Why must a hammer never be used directly to mount a bearing onto a shaft through the outer ring?",
        "fault_type": "outer_race",
        "severity": "small",
        "expected_pages": [38],
        "keywords": ["mounting", "hammer", "brinelling", "induction heater", "force"],
    },
    {
        "id": "Q18",
        "category": "Safety and handling",
        "question": "What burn safety precaution applies when handling an overheated seized bearing?",
        "fault_type": "ball",
        "severity": "large",
        "expected_pages": [44],
        "keywords": ["cool", "50", "burn", "temperature", "handling"],
    },
]


def evaluate():
    print("=" * 70)
    print("Bearing Fault Copilot - RAG Retrieval Evaluation Test Set")
    print("=" * 70)

    total_questions = len(TEST_QUESTIONS)
    hits_top5 = 0
    latencies = []

    print(f"\nEvaluating {total_questions} questions across 4 technical categories...\n")

    for q in TEST_QUESTIONS:
        t0 = time.perf_counter()
        res = retrieve(
            query=q["question"],
            fault_type=q["fault_type"],
            severity=q["severity"],
            top_k=5,
        )
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        retrieved = res.get("passages", [])
        
        # Check if any expected page appears, or keywords match
        is_hit = False
        hit_chunk = None

        for p in retrieved:
            p_page = p.get("page")
            p_text = p.get("text", "").lower()
            p_chunk_id = p.get("chunk_id", "")

            # Page match check
            if p_page in q["expected_pages"]:
                is_hit = True
                hit_chunk = p_chunk_id
                break

            # Or keyword match check in text
            matching_kw = [kw for kw in q["keywords"] if kw in p_text]
            if len(matching_kw) >= 2:
                is_hit = True
                hit_chunk = p_chunk_id
                break

        if is_hit:
            hits_top5 += 1
            status = "HIT "
        else:
            status = "MISS"

        print(f"[{status}] {q['id']} ({q['category']}): {q['question'][:55]}... -> {hit_chunk or 'None'} ({elapsed*1000:.1f}ms)")

    hit_rate = (hits_top5 / total_questions) * 100.0
    avg_latency = (sum(latencies) / len(latencies)) * 1000.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] * 1000.0

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS:")
    print(f"Total Test Questions: {total_questions}")
    print(f"Top-5 Hit Rate:       {hit_rate:.1f}% (Target: >= 80.0%)")
    print(f"Average Latency:      {avg_latency:.1f} ms (Target: < 1000 ms)")
    print(f"P95 Latency:          {p95_latency:.1f} ms")
    print("=" * 70)

    return {
        "total_questions": total_questions,
        "hits": hits_top5,
        "hit_rate_pct": hit_rate,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
    }


if __name__ == "__main__":
    evaluate()
