"""Fictional product contexts, not empirical calibration parameters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    category: str
    icon: str
    context: str
    metric: str
    definition: str
    proposed_baseline: float | None
    interventions: tuple[str, ...]


SCENARIOS = (
    Scenario(
        "retention", "Improve D7 Retention", "SOCIAL PRODUCT", "↗",
        "Help people find a reason to return to a new community app.",
        "D7 retention", "Share of new users active on day 7 after signup.", 0.24,
        ("Interest-based welcome feed", "First-week community digest", "Follow recommendations",
         "Small-group introductions", "Topic discovery prompts", "Return-to-conversation shortcut",
         "Friend activity highlights", "New member discussion", "Saved-post reminders",
         "Community welcome notes", "Weekly interest roundup", "Simplified notification settings"),
    ),
    Scenario(
        "acquisition", "Grow Acquisition", "GROWTH", "◎",
        "Turn more first-time visitors into signed-up users of a creator platform.",
        "Signup conversion", "Share of eligible first-time visitors who sign up within 7 days.", 0.08,
        ("Creator-led landing page", "Shorter signup form", "Social proof near signup",
         "Interactive product preview", "Clearer signup call to action", "Mobile landing redesign",
         "Creator story carousel", "Email-first signup", "Benefit-led page headline",
         "Visitor FAQ placement", "Referral welcome page", "Preview before signup"),
    ),
    Scenario(
        "onboarding", "Improve Onboarding", "ACTIVATION", "◇",
        "Help new teams reach their first useful moment in a collaboration tool.",
        "Activation rate", "Share of new workspaces completing a first shared task within 7 days.", 0.36,
        ("Guided first task", "Starter workspace templates", "Contextual setup checklist",
         "Invite-a-teammate prompt", "Sample project walkthrough", "Simplified workspace setup",
         "Role-based first session", "First-task success message", "Template recommendations",
         "Inline help prompts", "Team kickoff checklist", "Getting-started email"),
    ),
    Scenario(
        "monetization", "Improve Monetization", "PAID CONVERSION", "◈",
        "Help trial users discover enough value to become paid subscribers.",
        "Paid conversion", "Share of new trial accounts becoming paid within 30 days.", 0.05,
        ("Plan comparison redesign", "In-product value recap", "Trial milestone reminders",
         "Annual plan explanation", "Simplified upgrade flow", "Usage-based value message",
         "Team plan preview", "Billing FAQ placement", "Paid feature walkthrough",
         "Trial progress dashboard", "Upgrade confirmation clarity", "End-of-trial summary"),
    ),
)

SCENARIO_BY_KEY = {scenario.key: scenario for scenario in SCENARIOS}
ARCHIVE_SCENARIO = Scenario(
    "upworthy_ctr", "Explore headline CTR", "ARCHIVE LABORATORY", "◉",
    "Explore synthetic pairs of headline packages using Upworthy-derived traffic and effect assumptions.",
    "Click-through rate", "Share of assigned impressions that result in a click.", None,
    ("Headline framing", "Image and headline pairing", "Specificity in the headline", "Question-led headline",
     "Story preview", "Concise headline", "Human-interest framing", "Curiosity-led headline",
     "Context in the headline", "Headline readability", "Image emphasis", "Alternative story angle"))
SCENARIO_BY_KEY[ARCHIVE_SCENARIO.key] = ARCHIVE_SCENARIO
