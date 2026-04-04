from __future__ import annotations

import html
import json
import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SOURCE_DIR = Path("source_data")
OUTPUT_DIR = Path("docs/research")
DATA_DIR = OUTPUT_DIR / "data"
CONVERSATIONS_DIR = OUTPUT_DIR / "conversations"

LINE_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}),\s+(.+?)\s+-\s+(.*)$")
ATTACHMENT_RE = re.compile(r"([A-Za-z0-9._+\- ]+\.(?:jpg|jpeg|png|pdf|opus|mp4|vcf))", re.IGNORECASE)
PRICE_RE = re.compile(r"\$ ?([\d.]{3,})")
DIM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:x|por)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
DATE_FORMAT = "%d/%m/%Y %I:%M %p"

WELCOME_PATTERNS = ["gracias por escribirnos", "contanos qué estás buscando", "catalogo"]
OFF_HOURS_PATTERNS = [
    "ahora no estamos en la oficina",
    "horario de atención",
    "ni bien volvamos te respondemos",
    "ni bien veamos tu mensaje te respondemos",
]
QUOTE_PATTERNS = ["presupuesto por cerramiento", "precio con descuento", "otras formas de pago"]
CONFIRMATION_PATTERNS = ["trabajo confirmado", "te pedimos que chequees la info"]
FOLLOW_UP_PATTERNS = ["te paso el presupuesto", "en la brevedad posible", "cuando puedas", "apenas tengamos un horario"]

MANUAL_NOTES: dict[str, dict[str, Any]] = {
    "chat-de-whatsapp-con-44-7484-335536": {
        "headline": "A price-sensitive DIY lead that was converted into a full installation sale.",
        "estimated_jobs": 1,
        "thread_model": "Single job thread with negotiated price change before scheduling.",
        "qualitative_summary": "The customer opens with a clear material-only request and already has hooks installed, which is the kind of lead an automated system might be tempted to route out of scope. Instead, EnRed uses a consultative move: they acknowledge the partial DIY setup, explain why installation is still non-trivial, quote both the material-only path and the full service, then keep the thread alive with budget-sensitive follow-up. The sale closes only after explicit price negotiation and a later confirmation message.",
        "sales_observations": [
            "This is a strong example of converting a lower-value DIY inquiry into a higher-value full-service job without sounding pushy.",
            "The operator adapts tone well to the customer's informal style and uses negotiation language naturally.",
            "The conversation reveals that customers may think of price in components ('red + instalación') even when EnRed thinks in bundled value."
        ],
        "workflow_risks": [
            "The negotiated final price had to be manually remembered later; the planning confirmation briefly reused the old $100.000 balance before being corrected.",
            "A future automated system needs an explicit negotiated-price state, not just a base quote state.",
            "The thread also shows why 'material only' should not be treated as an automatic disqualification."
        ],
        "product_implications": [
            "Capture whether the lead asks for materials only, full installation, or is undecided.",
            "Track negotiated price overrides separately from the original quote template.",
            "Preserve technical objections like existing hooks, closed fixations, and extra rope needs in the handoff payload."
        ],
    },
    "chat-de-whatsapp-con-azoomate-rosario": {
        "headline": "A technically complex balcony job where recommendations changed because of building rules.",
        "estimated_jobs": 1,
        "thread_model": "Single job with multiple stakeholders: buyer, final resident, and building approval process.",
        "qualitative_summary": "This thread is valuable because it shows a real constraint cascade: the operator initially recommends a stronger solution based on safety and geometry, then the customer's mother/consorcio approval process forces the conversation back toward transparent nylon. It also shows a proxy buyer dynamic: the person writing is not the final resident and later passes the installer contact to the mother, which matters for both planning and communication design.",
        "sales_observations": [
            "EnRed adds real engineering judgment here instead of blindly quoting from dimensions; they discuss drainage channels, cleaning implications, and inside-vs-outside installation tradeoffs.",
            "The customer is not simply shopping on price; she is balancing child safety, aesthetics, and building permission.",
            "The business handles this well by offering a stronger recommendation first, then gracefully falling back to the compliant option."
        ],
        "workflow_risks": [
            "A future agent must support third-party stakeholders such as consorcio administrators, family members, and final occupants.",
            "The recommendation changes mid-thread, so the system must preserve quote version history rather than overwrite context.",
            "Scheduling is slightly unstable: the job is first proposed for Wednesday, then moved to Friday."
        ],
        "product_implications": [
            "Add explicit fields for regulatory or consorcio constraints.",
            "Support a 'decision-maker differs from onsite contact' workflow.",
            "Make it easy to attach rationale when the recommended material changes for non-price reasons."
        ],
    },
    "chat-de-whatsapp-con-cecilia-pellegrini-326": {
        "headline": "A batch B2B-style sale with six identical units and a more operational buyer.",
        "estimated_jobs": 6,
        "thread_model": "One coordinator thread representing a multi-unit installation batch.",
        "qualitative_summary": "This conversation is one of the clearest examples that EnRed does not only sell to end-consumers. The buyer is an architect representing a company, asking about six similar units and already anticipating the site-visit requirement. The sales flow becomes more operational: per-unit pricing, access logistics, invoice vs cash clarification, and centralized coordination with one keyholder instead of multiple residents.",
        "sales_observations": [
            "The generic welcome template is slightly redundant here because the buyer already provided a structured and qualified request.",
            "Once a human takes over, the flow becomes much stronger: EnRed clarifies scope, confirms that pricing is per unit, and resolves payment method nuances.",
            "The post-install receipt and satisfaction follow-up show a more complete back-office pattern than in some of the consumer threads."
        ],
        "workflow_risks": [
            "The customer had to nudge twice before scheduling happened, which suggests batch jobs can fall through the cracks if they are not surfaced distinctly.",
            "Business buyers may need different confirmation fields than retail leads, such as CUIT, company name, attention/contact person, and invoice mode.",
            "One WhatsApp thread may represent multiple installations with shared specs but one coordinator."
        ],
        "product_implications": [
            "Detect and branch early for multi-unit / company-managed jobs.",
            "Treat per-unit pricing and total job scope as separate structured values.",
            "Include a scheduling mode for one coordinator with keys/access instead of one resident per unit."
        ],
    },
    "chat-de-whatsapp-con-julieta-potalivo-924": {
        "headline": "A long-lived WhatsApp relationship that actually contains multiple projects over time.",
        "estimated_jobs": 2,
        "thread_model": "Persistent customer thread reused for at least two distinct projects across years.",
        "qualitative_summary": "This is the most important transcript for understanding why a conversation thread is not the same thing as a single sales opportunity. The export spans a 2024 technical-balcony bird-control job, later follow-up/scheduling/payment exchanges, and then a much later 2026 job with different geometry and destination. The customer reuses the same thread as an ongoing business relationship rather than as a one-job channel.",
        "sales_observations": [
            "EnRed is good at asking the one technical question that unlocks execution: access path to the balcony técnico.",
            "The company also uses a clear job-confirmation checklist before installation, which is one of the strongest repeatable patterns in the whole corpus.",
            "The later 2026 exchange shows that even an already-converted customer may still require updated measurement and pricing work for a new job."
        ],
        "workflow_risks": [
            "If the product assumes one conversation equals one job, this thread will contaminate metrics, lead times, and extraction state.",
            "Scheduling drift is visible in the first project; the customer has to ask when they are actually coming.",
            "The later thread includes revised measurements and address corrections, so the system needs job-level versioning inside the same chat."
        ],
        "product_implications": [
            "Introduce explicit job objects within a persistent contact thread.",
            "Reset or fork extraction state when a new project starts in an existing WhatsApp conversation.",
            "Preserve historical jobs for context, but do not let old measurements or quotes bleed into the new one."
        ],
    },
    "chat-de-whatsapp-con-mariana-nanni-cl-226": {
        "headline": "A high-signal two-job conversation with strong customer engagement and real scheduling complexity.",
        "estimated_jobs": 2,
        "thread_model": "Single thread managing two parallel jobs with independent scheduling and material decisions.",
        "qualitative_summary": "This is probably the richest single transcript in the corpus. The customer is articulate, provides detailed context, asks thoughtful technical questions, and ends up moving both jobs forward while weather, noise restrictions, painters, and household logistics keep reshaping the schedule. It shows EnRed operating as both advisor and scheduler, not just as a quote bot.",
        "sales_observations": [
            "The customer gives unusually high-quality input, which lets EnRed move quickly into material recommendations and nuanced tradeoffs.",
            "The conversation shows the value of consultative explanation: resistance comparisons, visibility tradeoffs, and recommendation by use case clearly help the buyer decide.",
            "The customer gives positive feedback after the first installation and confirms the second material choice, which makes this a strong trust-building example."
        ],
        "workflow_risks": [
            "The cancellation wording around rain is ambiguous enough that the customer explicitly asks whether the work is canceled.",
            "This thread contains two separate jobs with different statuses, so a single global stage would be misleading.",
            "Availability constraints are unusually detailed: building noise windows, painter dependency, childcare/birthday timing, indoor vs outdoor weather sensitivity."
        ],
        "product_implications": [
            "Support per-job status tracking inside one conversation.",
            "Use explicit, unambiguous rescheduling language when weather or safety conditions cancel an appointment.",
            "Capture reasoned recommendation notes because they directly influence the customer's final material selection."
        ],
    },
    "chat-de-whatsapp-con-pablo-molina-226": {
        "headline": "A weak ad-driven lead that went cold, reactivated months later, and still converted.",
        "estimated_jobs": 1,
        "thread_model": "Single job thread with long dormancy and later reactivation.",
        "qualitative_summary": "This thread starts with the lowest-quality opener in the corpus: '¿Precio?'. It then goes dormant for nearly a year before the lead reappears with a promotion-oriented message and eventually converts. That makes it a very useful example of lead resurrection, progressive qualification, and how much missing context EnRed is willing to fill in over time.",
        "sales_observations": [
            "EnRed is willing to send an explicit 'estimativo sin fotos' quote to keep momentum, while still asking for the missing evidence needed to finalize the job.",
            "The operator uses photos to identify a hidden durability issue (hot metal railing contact) and upsells an optional protective layer in a credible way.",
            "The customer is unsure about material choice until the child-safety use case is made explicit; advisory framing helps close the deal."
        ],
        "workflow_risks": [
            "The expired promotion becomes a pricing objection, so a future system needs promotion state and expiration awareness.",
            "The thread reaches a 'trabajo confirmado' message before the missing photos are fully resolved, which could create premature certainty in an automated pipeline.",
            "Old inbound ad leads may return after long gaps, so stale context must be revisited instead of assumed current."
        ],
        "product_implications": [
            "Support estimate-first flows with a clearly marked provisional quote state.",
            "Track promo source and expiry so follow-up messages stay commercially consistent.",
            "Prompt for final-photo verification before locking operational details if a quote started as estimate-only."
        ],
    },
}

AGGREGATE_QUALITATIVE = {
    "cross_conversation_insights": [
        "EnRed is not just qualifying leads; it is actively consulting on material choice, installation method, and operational tradeoffs.",
        "Many threads only become understandable when you separate commercial stages: intake, quote shaping, confirmation, scheduling, installation, payment, and post-service follow-up.",
        "Several conversations show that one WhatsApp thread can contain multiple jobs, revised quotes, or a whole customer relationship over time.",
        "The strongest sales moves are consultative explanations tied to the customer's real use case, not generic product descriptions.",
        "The weakest moments are usually operational: delayed follow-up, ambiguous scheduling language, or state that has to be manually remembered."
    ],
    "design_recommendations": [
        "Model persistent contact threads and nested job records separately.",
        "Separate provisional estimates, final quotes, negotiated prices, and scheduled jobs as distinct states.",
        "Treat attachments and stakeholder constraints as first-class structured inputs.",
        "Add explicit reschedule/cancel reasons so weather, building rules, and access issues do not get lost in free text.",
        "Preserve rationale in the handoff: why this material was recommended, what objections appeared, and what was finally agreed."
    ],
}


@dataclass
class Message:
    timestamp_raw: str
    sender: str
    content: str
    timestamp_iso: str | None
    role: str
    is_system: bool
    is_attachment: bool
    attachment_name: str | None


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\u200e", "")
    if any(token in text for token in ("Ã", "â€", "ðŸ", "Â")):
        try:
            text = text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "conversation"


def redact_display_name(index: int) -> str:
    return f"Conversation {index:02d}"


def parse_timestamp(date_part: str, time_part: str) -> str | None:
    clean = normalize_text(time_part)
    clean = clean.replace("\u202f", " ").replace("\u00a0", " ")
    clean = clean.replace("a. m.", "AM").replace("p. m.", "PM")
    clean = clean.replace("a. m", "AM").replace("p. m", "PM")
    clean = clean.replace("a.m.", "AM").replace("p.m.", "PM")
    clean = clean.replace("a.m", "AM").replace("p.m", "PM")
    clean = clean.replace("am", "AM").replace("pm", "PM")
    clean = re.sub(r"\s+", " ", clean).strip()
    try:
        return datetime.strptime(f"{date_part} {clean}", DATE_FORMAT).isoformat()
    except ValueError:
        return None


def classify_sender(sender: str, content: str) -> tuple[str, bool]:
    lower_sender = sender.strip().lower()
    lower_content = content.lower()
    if "los mensajes y las llamadas" in lower_content or "es un contacto" in lower_content or "respondió a tu anuncio" in lower_content:
        return "system", True
    if lower_sender == "enred rosario":
        if any(pattern in lower_content for pattern in OFF_HOURS_PATTERNS):
            return "enred_auto", False
        return "enred", False
    return "client", False


def parse_transcript(path: Path) -> list[Message]:
    raw = normalize_text(path.read_text(encoding="utf-8", errors="replace"))
    messages: list[Message] = []
    current: Message | None = None
    for line in raw.splitlines():
        match = LINE_RE.match(line)
        if match:
            date_part, time_part, remainder = match.groups()
            if ": " in remainder:
                sender, content = remainder.split(": ", 1)
            else:
                sender, content = "system", remainder
            content = normalize_text(content)
            role, is_system = classify_sender(sender, content)
            attachment_match = ATTACHMENT_RE.search(content)
            current = Message(
                timestamp_raw=f"{date_part}, {normalize_text(time_part)}",
                sender=normalize_text(sender),
                content=content,
                timestamp_iso=parse_timestamp(date_part, time_part),
                role=role,
                is_system=is_system,
                is_attachment="archivo adjunto" in content.lower() or "<multimedia omitido>" in content.lower(),
                attachment_name=attachment_match.group(1) if attachment_match else None,
            )
            messages.append(current)
        elif current is not None:
            continuation = normalize_text(line)
            current.content = f"{current.content}\n{continuation}" if continuation else current.content
            if current.attachment_name is None:
                attachment_match = ATTACHMENT_RE.search(current.content)
                if attachment_match:
                    current.attachment_name = attachment_match.group(1)
            current.is_attachment = current.is_attachment or "archivo adjunto" in continuation.lower() or "<multimedia omitido>" in continuation.lower()
    return messages


def infer_service_types(text: str) -> list[str]:
    lower = text.lower()
    themes: list[str] = []
    if ("techo" in lower or "azotea" in lower) and "piso a techo" not in lower:
        themes.append("roof")
    mapping = [
        ("balcón", "balcony"),
        ("balcon", "balcony"),
        ("escalera", "stairwell"),
        ("entrepiso", "mezzanine"),
        ("paloma", "bird_control"),
        ("aves", "bird_control"),
        ("murciél", "bird_control"),
        ("murciel", "bird_control"),
        ("menor", "child_safety"),
        ("niño", "child_safety"),
        ("niña", "child_safety"),
        ("gato", "pet_safety"),
        ("perro", "pet_safety"),
        ("instalo yo", "diy_material_only"),
        ("solo necesito la red", "diy_material_only"),
        ("6 dptos", "bulk_multi_unit"),
        ("2 trabajos", "multi_job"),
        ("balcon tecnico", "technical_balcony"),
    ]
    for needle, label in mapping:
        if needle in lower and label not in themes:
            themes.append(label)
    return themes


def extract_dimensions(text: str) -> list[str]:
    return [f"{a.replace(',', '.')} x {b.replace(',', '.')}" for a, b in DIM_RE.findall(text)]


def collect_prices(text: str) -> list[str]:
    return ["$" + value for value in PRICE_RE.findall(text)]


def attachment_inventory(conv_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for category in ("images", "audio", "video", "docs", "contacts"):
        folder = conv_dir / category
        if not folder.exists():
            continue
        for file in sorted(folder.iterdir()):
            if file.is_file():
                items.append({"type": category, "name": file.name, "relative_path": str(file.as_posix())})
    return items


def shorten(text: str, limit: int = 220) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def top_quotes(messages: list[Message]) -> list[dict[str, str]]:
    patterns = ["presupuesto", "trabajo confirmado", "cuando puedan", "demora", "te confirmo", "definimos", "precio"]
    selected = []
    for message in messages:
        lower = message.content.lower()
        if any(pattern in lower for pattern in patterns):
            selected.append({
                "timestamp": message.timestamp_raw,
                "role": message.role,
                "quote": shorten(message.content, 260),
            })
    return selected[:6]


def response_gaps(messages: list[Message]) -> list[dict[str, Any]]:
    gaps = []
    previous: Message | None = None
    for message in messages:
        if message.timestamp_iso is None:
            previous = message
            continue
        if previous and previous.timestamp_iso and previous.role != message.role:
            start = datetime.fromisoformat(previous.timestamp_iso)
            end = datetime.fromisoformat(message.timestamp_iso)
            gaps.append({
                "from_role": previous.role,
                "to_role": message.role,
                "hours": round((end - start).total_seconds() / 3600, 2),
                "from_time": previous.timestamp_raw,
                "to_time": message.timestamp_raw,
            })
        previous = message
    return gaps


def summarize_findings(messages: list[Message], metrics: dict[str, Any]) -> list[str]:
    findings = []
    if metrics["has_quote"]:
        findings.append("EnRed repeatedly sends highly structured quote blocks with payment options, discount framing, and material alternatives.")
    if metrics["has_off_hours"]:
        findings.append("The conversation includes an off-hours autoresponse, which suggests after-hours traffic is common enough to automate explicitly.")
    if metrics["lead_time_days"] is not None and metrics["lead_time_days"] > 7:
        findings.append("The thread spans multiple days, showing that scheduling and follow-up friction are material parts of the sales flow.")
    if metrics["multi_job"]:
        findings.append("This thread bundles more than one job request, so future automation should handle multi-scope leads without forcing a single-job assumption.")
    if metrics["attachments_from_client"] > 0:
        findings.append("The customer relies on attachments as part of the qualification flow, so attachment-aware prompts and operator tooling will matter.")
    if metrics["prices"]:
        findings.append("Pricing is delivered inside the chat, often before full scheduling details are locked, which makes quote extraction a valuable structured output.")
    if metrics["has_confirmation"]:
        findings.append("The conversation moves beyond qualification into confirmation and scheduling, giving useful examples for post-quote workflow design.")
    return findings[:5] or ["This conversation is useful mainly as a qualification/data-gathering example rather than a full end-to-end sales workflow."]


def build_summary(messages: list[Message], metrics: dict[str, Any]) -> dict[str, str]:
    first_client = next(
        (
            m for m in messages
            if m.role == "client"
            and not m.is_attachment
            and m.content.strip()
            and "<multimedia omitido>" not in m.content.lower()
        ),
        None,
    )
    outcome = "Quote stage"
    if metrics["has_confirmation"]:
        outcome = "Confirmation / scheduling stage"
    elif metrics["has_quote"]:
        outcome = "Quoted but not fully confirmed"

    primary_need = ", ".join(metrics["themes"][:3]) if metrics["themes"] else "general safety-net inquiry"
    return {
        "summary": (
            f"{metrics['display_name']} is a {outcome.lower()} example centered on {primary_need}. "
            f"The thread contains {metrics['message_count']} non-system messages across "
            f"{metrics['lead_time_days'] if metrics['lead_time_days'] is not None else 0} day(s)."
        ),
        "customer_goal": shorten(first_client.content if first_client else "No clear opening message found.", 180),
        "likely_outcome": outcome,
    }


def build_patterns(messages: list[Message]) -> list[dict[str, str]]:
    combined = "\n".join(m.content.lower() for m in messages if m.role.startswith("enred"))
    patterns: list[dict[str, str]] = []
    if any(pattern in combined for pattern in WELCOME_PATTERNS):
        patterns.append({"pattern": "Welcome template", "detail": "EnRed uses a reusable intake opener asking for photos, measurements, purpose, and address."})
    if any(pattern in combined for pattern in OFF_HOURS_PATTERNS):
        patterns.append({"pattern": "Off-hours autoresponse", "detail": "After-hours traffic is acknowledged with a stock availability message before a human follow-up."})
    if any(pattern in combined for pattern in QUOTE_PATTERNS):
        patterns.append({"pattern": "Structured quote block", "detail": "Quotes are sent as multi-line commercial messages with materials, guarantees, cash discount, and installment pricing."})
    if any(pattern in combined for pattern in CONFIRMATION_PATTERNS):
        patterns.append({"pattern": "Manual confirmation checklist", "detail": "When the lead advances, EnRed requests name, exact address, availability, and payment mode in a checklist format."})
    if any(pattern in combined for pattern in FOLLOW_UP_PATTERNS):
        patterns.append({"pattern": "Soft follow-up language", "detail": "Human operators promise near-term responses and frequently request one more image, video, or clarification."})
    return patterns


def build_friction(metrics: dict[str, Any], messages: list[Message]) -> list[str]:
    points = []
    if metrics["long_gaps"]:
        longest = max(metrics["long_gaps"], key=lambda item: item["hours"])
        points.append(f"There is at least one long reply gap ({longest['hours']} hours), which could justify reminder logic or inbox prioritization.")
    if metrics["attachments_from_client"] > 0 and not metrics["dimensions"]:
        points.append("The customer sent attachments but did not provide fully extractable measurements in plain text, so attachment-aware follow-up would help.")
    if metrics["multi_job"]:
        points.append("The thread mixes multiple scopes in one conversation, which can complicate extraction and quoting if the system assumes one job per lead.")
    if any("no entiendo" in m.content.lower() for m in messages if m.role == "client"):
        points.append("At least one operator question confused the customer, suggesting some technical clarifications should be phrased more simply.")
    if any("demora" in m.content.lower() or "retraso" in m.content.lower() for m in messages if m.role.startswith("enred")):
        points.append("Scheduling delay management appears explicitly in the thread, so expectation-setting and proactive updates matter.")
    return points[:5]


def build_automation_notes(metrics: dict[str, Any], patterns: list[dict[str, str]], friction_points: list[str]) -> list[str]:
    notes = []
    if metrics["themes"]:
        notes.append(f"Extraction should capture nuanced intent tags, not just a generic installation type: {', '.join(metrics['themes'])}.")
    if metrics["dimensions"]:
        notes.append("Dimension parsing should support conversational formats like '2.7m', '1.20 x 3m', and perimeter-style descriptions.")
    if metrics["attachments_total"]:
        notes.append("The workflow should record attachments and ask targeted follow-up questions when media arrives without enough text context.")
    if any(pattern["pattern"] == "Structured quote block" for pattern in patterns):
        notes.append("Quote messages are structured enough to template or parse automatically for downstream CRM/handoff use.")
    if friction_points:
        notes.append("Follow-up automation should avoid asking for information the customer already supplied earlier in the thread.")
    return notes[:5]


def derive_conversation(conv_dir: Path, index: int) -> dict[str, Any]:
    transcript_path = next((conv_dir / "transcript").glob("*.txt"))
    messages = parse_transcript(transcript_path)
    attachments = attachment_inventory(conv_dir)
    message_counts = Counter(msg.role for msg in messages if not msg.is_system)
    attachments_from_client = sum(1 for msg in messages if msg.role == "client" and msg.is_attachment)
    attachments_from_enred = sum(1 for msg in messages if msg.role.startswith("enred") and msg.is_attachment)
    combined_text = "\n".join(msg.content for msg in messages)
    prices = sorted(set(collect_prices(combined_text)))
    dims = sorted(set(extract_dimensions(combined_text)))
    themes = infer_service_types(combined_text)
    gaps = response_gaps([m for m in messages if not m.is_system])
    long_gaps = [gap for gap in gaps if gap["hours"] >= 12]
    timestamps = [datetime.fromisoformat(m.timestamp_iso) for m in messages if m.timestamp_iso]
    start = min(timestamps) if timestamps else None
    end = max(timestamps) if timestamps else None

    metrics = {
        "folder_name": conv_dir.name,
        "display_name": redact_display_name(index),
        "slug": slugify(conv_dir.name),
        "message_count": sum(1 for m in messages if not m.is_system),
        "client_messages": message_counts.get("client", 0),
        "enred_messages": message_counts.get("enred", 0) + message_counts.get("enred_auto", 0),
        "auto_messages": message_counts.get("enred_auto", 0),
        "attachments_total": len(attachments),
        "attachments_from_client": attachments_from_client,
        "attachments_from_enred": attachments_from_enred,
        "date_start": start.date().isoformat() if start else None,
        "date_end": end.date().isoformat() if end else None,
        "lead_time_days": (end - start).days if start and end else None,
        "themes": themes,
        "dimensions": dims,
        "prices": prices,
        "has_quote": any(pattern in combined_text.lower() for pattern in QUOTE_PATTERNS),
        "has_off_hours": any(pattern in combined_text.lower() for pattern in OFF_HOURS_PATTERNS),
        "has_confirmation": any(pattern in combined_text.lower() for pattern in CONFIRMATION_PATTERNS),
        "multi_job": "multi_job" in themes or "2 trabajos" in combined_text.lower(),
        "long_gaps": long_gaps,
        "long_lived_thread": bool(start and end and (end - start).days >= 90),
    }
    patterns = build_patterns(messages)
    friction = build_friction(metrics, messages)
    manual = MANUAL_NOTES.get(metrics["slug"], {})
    metrics["estimated_jobs"] = manual.get("estimated_jobs", 1)
    metrics["thread_model"] = manual.get("thread_model", "Single job thread.")
    return {
        "conversation": metrics,
        "executive_summary": build_summary(messages, metrics),
        "repeated_patterns": patterns,
        "friction_points": friction,
        "automation_notes": build_automation_notes(metrics, patterns, friction),
        "key_quotes": top_quotes(messages),
        "important_findings": summarize_findings(messages, metrics),
        "manual_analysis": manual,
        "attachments": attachments,
        "messages": [asdict(msg) for msg in messages],
    }


def render_list(items: list[str]) -> str:
    return "<li>None noted.</li>" if not items else "\n".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_pattern_cards(items: list[dict[str, str]]) -> str:
    if not items:
        return "<p class='muted'>No repeated operator patterns were detected with the current heuristics.</p>"
    return "\n".join(
        f"<div class='card'><h4>{html.escape(item['pattern'])}</h4><p>{html.escape(item['detail'])}</p></div>"
        for item in items
    )


def render_quotes(quotes: list[dict[str, str]]) -> str:
    if not quotes:
        return "<p class='muted'>No standout evidence snippets selected.</p>"
    return "\n".join(
        "<blockquote><div class='meta-inline'>{timestamp} · {role}</div><p>{quote}</p></blockquote>".format(
            timestamp=html.escape(item["timestamp"]),
            role=html.escape(item["role"]),
            quote=html.escape(item["quote"]),
        )
        for item in quotes
    )


def render_attachments(items: list[dict[str, str]]) -> str:
    if not items:
        return "<p class='muted'>No files found in the normalized attachment folders.</p>"
    rows = []
    for item in items:
        rows.append(
            "<tr><td>{type}</td><td>{name}</td><td>{path}</td></tr>".format(
                type=html.escape(item["type"]),
                name=html.escape(item["name"]),
                path=html.escape(item["relative_path"]),
            )
        )
    return "<table><thead><tr><th>Type</th><th>Name</th><th>Relative path</th></tr></thead><tbody>{}</tbody></table>".format("".join(rows))


def render_timeline(messages: list[dict[str, Any]]) -> str:
    rows = []
    for message in messages:
        css = {"client": "client", "enred": "enred", "enred_auto": "auto", "system": "system"}.get(message["role"], "system")
        attachment = "<span class='badge'>attachment</span>" if message["is_attachment"] else ""
        rows.append(
            "<article class='message {css}' data-role='{role}'>"
            "<div class='meta'><span>{time}</span><span>{sender}</span>{attachment}</div>"
            "<pre>{content}</pre>"
            "</article>".format(
                css=css,
                role=html.escape(message["role"]),
                time=html.escape(message["timestamp_raw"]),
                sender=html.escape(message["sender"]),
                attachment=attachment,
                content=html.escape(message["content"]),
            )
        )
    return "\n".join(rows)


def conversation_html(report: dict[str, Any]) -> str:
    metrics = report["conversation"]
    theme_chips = "".join(f"<span class='chip'>{html.escape(theme)}</span>" for theme in metrics["themes"]) or "<span class='chip'>general_lead</span>"
    manual = report.get("manual_analysis", {})
    manual_headline = html.escape(manual.get("headline", ""))
    manual_summary = html.escape(manual.get("qualitative_summary", ""))
    sales_obs = render_list(manual.get("sales_observations", []))
    workflow_risks = render_list(manual.get("workflow_risks", []))
    product_impl = render_list(manual.get("product_implications", []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(metrics['display_name'])} · Conversation Research</title>
<style>
:root{{--bg:#f6f1e8;--panel:#fffdf8;--ink:#1d261f;--muted:#6a756b;--accent:#1d6b52;--accent-soft:#d6efe6;--client:#eef6ff;--enred:#f7efe1;--auto:#f0f2d8;--system:#f0f0f0;--line:#d8d0c2;}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Georgia,'Times New Roman',serif;background:linear-gradient(180deg,#ebe4d8,var(--bg));color:var(--ink)}}main{{max-width:1200px;margin:0 auto;padding:32px 24px 56px}}header{{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:24px}}.hero,.summary,.section{{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.04)}}h1,h2,h3,h4{{margin:0 0 12px;font-family:'Trebuchet MS',Arial,sans-serif}}h1{{font-size:2rem}}.subtitle{{color:var(--muted);line-height:1.5}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.stat{{background:#faf7f0;border-radius:14px;padding:12px;border:1px solid var(--line)}}.stat .label{{color:var(--muted);font-size:.82rem;text-transform:uppercase;letter-spacing:.06em}}.stat .value{{font:600 1.2rem/1.2 'Trebuchet MS',Arial,sans-serif;margin-top:6px}}.two-col{{display:grid;grid-template-columns:1.15fr .85fr;gap:16px;margin-top:16px}}.chips{{display:flex;flex-wrap:wrap;gap:8px}}.chip,.badge{{display:inline-flex;align-items:center;border-radius:999px;padding:6px 10px;font-size:.82rem}}.chip{{background:var(--accent-soft);color:var(--accent)}}.badge{{background:#e6ecff;color:#334c8c;margin-left:8px}}.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.card{{border:1px solid var(--line);border-radius:16px;padding:14px;background:#fffaf2}}.muted{{color:var(--muted)}}.toolbar{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}.toolbar button{{border:1px solid var(--line);background:white;border-radius:999px;padding:8px 14px;cursor:pointer}}.timeline{{display:grid;gap:10px;max-height:900px;overflow:auto;padding-right:4px}}.message{{border-radius:16px;border:1px solid var(--line);padding:12px 14px}}.message.client{{background:var(--client)}}.message.enred{{background:var(--enred)}}.message.auto{{background:var(--auto)}}.message.system{{background:var(--system)}}.message .meta,.meta-inline{{color:var(--muted);font:600 .78rem/1.3 'Trebuchet MS',Arial,sans-serif;display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}}pre{{margin:0;white-space:pre-wrap;font-family:inherit;line-height:1.45}}blockquote{{margin:0 0 12px;padding:12px 14px;border-left:4px solid var(--accent);background:#faf8f2;border-radius:0 12px 12px 0}}table{{width:100%;border-collapse:collapse;font-size:.92rem}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top}}footer{{margin-top:20px;color:var(--muted);font-size:.9rem}}@media (max-width:900px){{header,.two-col,.cards,.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><section class="hero"><h1>{html.escape(metrics["display_name"])}</h1><p class="subtitle">{html.escape(report["executive_summary"]["summary"])}</p><div class="chips">{theme_chips}</div></section><section class="summary"><h3>Key takeaways</h3><ul>{render_list(report["important_findings"])}</ul></section></header>
<section class="section"><div class="grid"><div class="stat"><div class="label">Messages</div><div class="value">{metrics["message_count"]}</div></div><div class="stat"><div class="label">Date range</div><div class="value">{html.escape(str(metrics["date_start"]))} → {html.escape(str(metrics["date_end"]))}</div></div><div class="stat"><div class="label">Attachments</div><div class="value">{metrics["attachments_total"]}</div></div><div class="stat"><div class="label">Estimated jobs</div><div class="value">{metrics["estimated_jobs"]}</div></div></div>
<div class="two-col"><div><h3>Executive summary</h3><p><strong>Customer goal:</strong> {html.escape(report["executive_summary"]["customer_goal"])}</p><p><strong>Likely outcome:</strong> {html.escape(report["executive_summary"]["likely_outcome"])}</p><p><strong>Dimensions spotted:</strong> {html.escape(", ".join(metrics["dimensions"]) if metrics["dimensions"] else "No clear text dimensions extracted")}</p><p><strong>Prices spotted:</strong> {html.escape(", ".join(metrics["prices"]) if metrics["prices"] else "No explicit prices spotted")}</p></div><div><h3>Automation notes</h3><ul>{render_list(report["automation_notes"])}</ul></div></div></section>
<section class="section"><h2>Qualitative read</h2><div class="two-col"><div><h3>{manual_headline}</h3><p>{manual_summary}</p></div><div><h3>Thread model</h3><p>{html.escape(metrics["thread_model"])}</p><p><strong>Long-lived thread:</strong> {"Yes" if metrics["long_lived_thread"] else "No"}</p><p><strong>Quote status:</strong> {"Yes" if metrics["has_quote"] else "No"}</p></div></div><div class="two-col"><div><h3>Sales observations</h3><ul>{sales_obs}</ul></div><div><h3>Workflow risks</h3><ul>{workflow_risks}</ul></div></div><div class="two-col"><div><h3>Product implications</h3><ul>{product_impl}</ul></div><div><h3>Data modeling implication</h3><p>{"This thread should be modeled as multiple jobs under one contact thread." if metrics["estimated_jobs"] > 1 else "This thread can likely be modeled as a single job, but it still needs explicit quote/schedule/payment state."}</p></div></div></section>
<section class="section"><h2>Repeated patterns</h2><div class="cards">{render_pattern_cards(report["repeated_patterns"])}</div></section>
<section class="section"><h2>Friction and opportunities</h2><ul>{render_list(report["friction_points"])}</ul></section>
<section class="section"><h2>Evidence snippets</h2>{render_quotes(report["key_quotes"])}</section>
<section class="section"><h2>Timeline</h2><div class="toolbar"><button onclick="filterRole('all')">All</button><button onclick="filterRole('client')">Client</button><button onclick="filterRole('enred')">EnRed human</button><button onclick="filterRole('enred_auto')">EnRed auto</button><button onclick="filterRole('system')">System</button></div><div class="timeline">{render_timeline(report["messages"])}</div></section>
<section class="section"><h2>Attachment inventory</h2>{render_attachments(report["attachments"])}</section>
<footer>Built from the normalized WhatsApp export folders under source_data/. Redacted conversation labels are used in this report; raw source paths remain in the JSON data artifacts.</footer>
</main><script>function filterRole(role){{for(const el of document.querySelectorAll('.message')){{el.style.display=(role==='all'||el.dataset.role===role)?'':'none';}}}}</script></body></html>"""


def aggregate_html(reports: list[dict[str, Any]], unassigned: list[str]) -> str:
    conversations = [report["conversation"] for report in reports]
    total_messages = sum(item["message_count"] for item in conversations)
    total_attachments = sum(item["attachments_total"] for item in conversations)
    theme_counter = Counter(theme for item in conversations for theme in item["themes"])
    pattern_counter = Counter(card["pattern"] for report in reports for card in report["repeated_patterns"])
    avg_messages = round(statistics.mean(item["message_count"] for item in conversations), 1) if conversations else 0
    rows = []
    for item in conversations:
        rows.append("<tr><td><a href='conversations/{slug}.html'>{name}</a></td><td>{themes}</td><td>{jobs}</td><td>{messages}</td><td>{attachments}</td><td>{thread_model}</td></tr>".format(
            slug=html.escape(item["slug"]), name=html.escape(item["display_name"]), themes=html.escape(", ".join(item["themes"]) if item["themes"] else "general_lead"),
            jobs=item["estimated_jobs"], messages=item["message_count"], attachments=item["attachments_total"], thread_model=html.escape(item["thread_model"])))
    recurring_intents = [f"{theme}: {count} conversation(s)" for theme, count in theme_counter.most_common()]
    recurring_patterns = [f"{pattern}: {count} conversation(s)" for pattern, count in pattern_counter.most_common()]
    product_implications = [
        "The intake flow should support attachments as first-class evidence, because customers frequently answer with media plus partial text.",
        "A single conversation may contain multiple scopes or jobs, so extraction and quoting should not assume one request per thread.",
        "Structured quote parsing is high value because commercial messages consistently include materials, guarantees, and payment ladders.",
        "After-hours autoresponses show up in the corpus, so blended human-plus-automation workflows should be explicit.",
        "Scheduling and delay communication deserve dedicated states or reminders, not just free-form chat messages.",
    ]
    qualitative_insights = AGGREGATE_QUALITATIVE["cross_conversation_insights"]
    qualitative_recommendations = AGGREGATE_QUALITATIVE["design_recommendations"]
    pills = "".join(f"<span class='pill'>{html.escape(item)}</span>" for item in recurring_intents) or "<span class='pill'>No themes detected</span>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Conversation Corpus Research</title><style>
:root{{--bg:#faf7ef;--ink:#1c2220;--panel:#ffffff;--line:#dbd1c2;--accent:#7b3f00;--accent-soft:#f3e5d2;--muted:#63706a;}}*{{box-sizing:border-box}}body{{margin:0;font-family:Georgia,'Times New Roman',serif;color:var(--ink);background:radial-gradient(circle at top,#f0e5d5,var(--bg) 55%)}}main{{max-width:1180px;margin:0 auto;padding:32px 24px 56px}}.hero,.section{{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.04);margin-bottom:16px}}h1,h2,h3{{margin:0 0 12px;font-family:'Trebuchet MS',Arial,sans-serif}}.subtitle{{color:var(--muted);max-width:70ch;line-height:1.55}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}}.stat{{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fffaf3}}.stat .label{{color:var(--muted);text-transform:uppercase;font-size:.78rem;letter-spacing:.05em}}.stat .value{{font:600 1.3rem/1.2 'Trebuchet MS',Arial,sans-serif;margin-top:6px}}.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}}ul{{margin:0;padding-left:20px}}a{{color:var(--accent)}}.pill{{display:inline-block;background:var(--accent-soft);color:var(--accent);padding:5px 10px;border-radius:999px;margin:4px 6px 0 0;font-size:.85rem}}@media (max-width:900px){{.stats,.two-col{{grid-template-columns:1fr}}}}</style></head><body><main>
<section class="hero"><h1>Conversation Corpus Research</h1><p class="subtitle">Static research pack generated from the normalized EnRed Rosario WhatsApp exports. The reports focus on recurring conversation patterns, qualification signals, quoting behavior, scheduling friction, and implications for Manager AI.</p><div class="stats"><div class="stat"><div class="label">Conversations</div><div class="value">{len(conversations)}</div></div><div class="stat"><div class="label">Estimated jobs</div><div class="value">{sum(item['estimated_jobs'] for item in conversations)}</div></div><div class="stat"><div class="label">Messages</div><div class="value">{total_messages}</div></div><div class="stat"><div class="label">Avg messages / thread</div><div class="value">{avg_messages}</div></div></div></section>
<section class="section"><h2>Recurring intents</h2><div>{pills}</div></section>
<section class="section two-col"><div><h2>Qualitative synthesis</h2><ul>{render_list(qualitative_insights)}</ul></div><div><h2>Design recommendations</h2><ul>{render_list(qualitative_recommendations)}</ul></div></section>
<section class="section two-col"><div><h2>Recurring EnRed behaviors</h2><ul>{render_list(recurring_patterns)}</ul></div><div><h2>Product implications</h2><ul>{render_list(product_implications)}</ul></div></section>
<section class="section"><h2>Thread vs job comparison</h2><table><thead><tr><th>Conversation</th><th>Themes</th><th>Estimated jobs</th><th>Messages</th><th>Attachments</th><th>Thread model</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<section class="section two-col"><div><h2>Common blockers and opportunities</h2><ul><li>Customers often provide photos or videos before they provide all of the structured fields EnRed ultimately needs.</li><li>Quote delivery is strong, but scheduling and expectation-setting can stretch over days or weeks.</li><li>Some conversations include technical clarifications that an AI could handle, but only if the agent can preserve job context and attachment references.</li><li>Off-hours autoresponses show up alongside human handling, which implies a blended workflow instead of a single continuous live chat.</li><li>There are examples of material-only / DIY requests, bird-control jobs, child-safety jobs, and bulk or multi-unit work, so qualification should be broader than a single balcony-safety script.</li></ul></div><div><h2>Unassigned evidence</h2><ul>{render_list(unassigned)}</ul></div></section>
</main></body></html>"""


def build_reports() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reports = []
    conversation_dirs = sorted(path for path in SOURCE_DIR.iterdir() if path.is_dir() and path.name != "unassigned")
    for index, conv_dir in enumerate(conversation_dirs, start=1):
        reports.append(derive_conversation(conv_dir, index))

    unassigned_files: list[str] = []
    unassigned_dir = SOURCE_DIR / "unassigned"
    if unassigned_dir.exists():
        for file in sorted(unassigned_dir.rglob("*")):
            if file.is_file():
                unassigned_files.append(str(file.relative_to(SOURCE_DIR).as_posix()))

    aggregate = {
        "generated_at": datetime.now(UTC).isoformat(),
        "conversation_count": len(reports),
        "unassigned_files": unassigned_files,
        "conversations": [report["conversation"] for report in reports],
    }
    return reports, aggregate


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def write_outputs(reports: list[dict[str, Any]], aggregate: dict[str, Any]) -> None:
    ensure_dirs()
    for report in reports:
        slug = report["conversation"]["slug"]
        (DATA_DIR / f"{slug}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        (CONVERSATIONS_DIR / f"{slug}.html").write_text(conversation_html(report), encoding="utf-8")

    aggregate_payload = {
        **aggregate,
        "theme_counts": dict(Counter(theme for item in aggregate["conversations"] for theme in item["themes"])),
    }
    (DATA_DIR / "aggregate.json").write_text(json.dumps(aggregate_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(aggregate_html(reports, aggregate["unassigned_files"]), encoding="utf-8")


def main() -> None:
    reports, aggregate = build_reports()
    write_outputs(reports, aggregate)
    print(json.dumps({
        "conversation_reports": len(reports),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "conversation_html_files": [f"conversations/{report['conversation']['slug']}.html" for report in reports],
        "aggregate_html": "index.html",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
