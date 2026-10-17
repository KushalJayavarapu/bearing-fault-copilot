# lablab.ai submission text

Check every claim against the README before pasting. Fill the `[...]` items.

**Title:** Bearing Fault Copilot

**Tagline:** Detect, explain, act: a bearing-maintenance assistant that says how sure it is and keeps a human in charge of safety-critical steps.

**Track:** Track 1, Intelligent Industry

**Short description (about 50 words):**
Pick a vibration recording and Bearing Fault Copilot identifies the bearing fault, retrieves maintenance guidance, and has an LLM served on AMD GPUs explain what is wrong and what to do, with citations. It shows its uncertainty and requires human confirmation before any safety-critical step.

**Long description:**
Unplanned bearing failures stop production, and the people deciding what to do often have a vibration trace and no quick way to turn it into an action.

Our pipeline has four steps. (1) A random-forest classifier reads a window of vibration data from the CWRU bearing dataset and predicts fault type, severity and confidence, plus a check of which characteristic fault frequency shows a peak. (2) That result becomes a hybrid keyword and embedding search over our maintenance knowledge base. (3) An LLM, DeepSeek-V4-Flash-Vision-Exp served through AMD Token Factory on AMD GPUs, writes the explanation, likely causes and recommended actions. (4) A person confirms or escalates before any safety-critical step is accepted.

Trust is built into the design. The model writes only the explanation, causes and actions; the sensor result, uncertainty, citations and confirm flags are filled in by code. Invented citations are dropped. Steps that involve stopping, isolating, opening or restarting the machine are flagged safety-critical by code even if the model misses them. When the classifier is unsure, the answer says so and puts manual inspection first. If the LLM is unavailable, the app still returns the sensor result and citations.

**Honest limits:** On a motor load it has not seen, accuracy is 0.990. On bearing fault sizes it has not seen, it drops to 0.50 to 1.00 depending on size. The data is a lab rig with EDM-seeded faults. Our knowledge base is team-written notes, a curated table and synthetic maintenance logs, not vendor manuals. Retrieval hit rates come from our own test questions.

**How AMD is used:** LLM inference runs on AMD Radeon GPUs through the AMD Token Factory OpenAI-compatible endpoint. We call this service; we did not host or fine-tune the model. [Add anything else that is true, e.g. what Karthiik deploys.]

**Built with:** Python, FastAPI, Streamlit, scikit-learn, BM25 + BAAI/bge-small-en-v1.5 (fastembed), AMD Token Factory, DeepSeek-V4-Flash-Vision-Exp.

**Links:** Repo https://github.com/KushalJayavarapu/bearing-fault-copilot · Video [...] · Slides [...] · Live demo [... or "run locally, see README"]

**Data credit:** Case Western Reserve University Bearing Data Center (Loparo); fault-frequency analysis after Smith and Randall (2015), MSSP 64-65.
