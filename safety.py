import re

EMERGENCY_LINE = (
    "Stop now. Move away from it. Only unplug it if that is safe. "
    "If anyone is in danger or there is a fire, call 112."
)

REFUSALS = [
    (r"\bmicrowave (oven )?(repair|capacitor|magnetron)\b|\b(fix|repair|open) (my |the |a )?microwave\b",
     "The capacitor inside a microwave can hold a lethal charge even when unplugged. This one needs a qualified technician."),
    (r"\b(fix|repair|install|replace|connect|disconnect)\b.*\bgas\b|\bgas (pipe|line|connection|boiler|leak)\b",
     "Gas work can cause explosions and poisoning. Please call a qualified gas engineer."),
    (r"\b(mains wiring|fuse box|consumer unit|control board|circuit breaker|wall socket)\b",
     "Mains electrics can kill. Please call a qualified electrician."),
    (r"\b(swollen|bulging|leaking|punctured|damaged) (lithium |phone |laptop |tablet )?batter(y|ies)\b",
     "Don't charge it or keep working on it. Take it to a battery collection point or repair shop."),
    (r"\b(brake pads?|brakes|airbags?|steering|fuel lines?|fuel pump)\b",
     "A mistake here can cause a serious crash or fire. Please use a qualified mechanic."),
    (r"\b(ev battery|electric car battery|hybrid battery|high voltage)\b",
     "High-voltage systems can kill. Please use a qualified technician."),
    (r"\b(under the car|jack up|jacking up)\b",
     "Working under a raised car can be fatal. Please use a garage."),
    (r"\b(medicine|medication) dos(e|age)\b|\boverdose\b",
     "Please ask a pharmacist or doctor about this."),
]

CAUTION_TERMS = [
    r"\b(phone|iphone|smartphone|tablet|ipad|laptop)\b.*\b(screen|display|battery)\b",
    r"\b(screen|display|battery)\b.*\b(phone|iphone|smartphone|tablet|ipad|laptop)\b",
]
CAUTION_LINE = (
    "This job means working next to a lithium battery, and a punctured battery can catch fire. "
    "It needs patience, steady hands and the right tools. Stop if the battery looks swollen. "
    "If you are comfortable with that, say I understand the risk. "
    "Otherwise, a repair shop is the safer choice."
)
CAUTION_CONFIRM = "i understand the risk"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text.lower())).strip()


def is_emergency(text: str, active: bool) -> bool:
    n = norm(text)
    if re.fullmatch(r"(please )?stop( now| it| stop)?", n):
        return True
    return active and re.search(
        r"\b(smoke|smoking|fire|burning|sparks?|sparking|shock|shocked|smell gas|gas leak)\b", n
    ) is not None


def check_refusal(text: str) -> str | None:
    n = norm(text)
    return next((reason for pattern, reason in REFUSALS if re.search(pattern, n)), None)


def needs_caution(text: str) -> bool:
    n = norm(text)
    return any(re.search(pattern, n) for pattern in CAUTION_TERMS)


def confirms_caution(text: str) -> bool:
    return CAUTION_CONFIRM in norm(text)