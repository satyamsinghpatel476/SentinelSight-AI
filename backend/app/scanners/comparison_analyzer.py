from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.core.config import Settings
from app.core.enums import FindingSeverity
from app.models.scan import Scan
from app.scanners.header_analyzer import PassiveFinding, finding
from app.scanners.visual_comparison import VisualComparisonResult, compare_screenshots

SUSPICIOUS_PHRASES = (
    "hacked by",
    "owned by",
    "site defaced",
    "database leaked",
    "unauthorized access",
    "bitcoin giveaway",
    "send cryptocurrency",
    "crypto recovery",
    "system compromised",
    "security breached",
)


@dataclass(frozen=True)
class ComparisonResult:
    baseline_scan_id: str
    title_changed: bool
    baseline_title: str | None
    current_title: str | None
    text_similarity_percent: float
    visual_result: VisualComparisonResult | None
    comparison_error: str | None
    baseline_external_script_domains: list[str]
    current_external_script_domains: list[str]
    new_external_script_domains: list[str]
    baseline_external_iframe_domains: list[str]
    current_external_iframe_domains: list[str]
    new_external_iframe_domains: list[str]
    suspicious_phrases: list[str]
    findings: list[PassiveFinding]


def compare_scan_to_baseline(
    baseline_scan: Scan,
    current_scan: Scan,
    settings: Settings,
) -> ComparisonResult:
    """Compare current scan metadata and screenshot evidence with the active baseline."""

    findings: list[PassiveFinding] = []
    title_changed = normalize_text(baseline_scan.page_title) != normalize_text(
        current_scan.page_title
    )
    if title_changed:
        title_evidence = (
            f"Baseline: {baseline_scan.page_title or 'not captured'}; "
            f"current: {current_scan.page_title or 'not captured'}"
        )
        findings.append(
            finding(
                "page_title_changed",
                "Page title changed",
                "The current scan page title differs from the approved baseline.",
                FindingSeverity.moderate,
                title_evidence,
                (
                    "Review the website deployment history and confirm the title "
                    "change was authorized."
                ),
                8,
            )
        )

    similarity = text_similarity(
        baseline_scan.visible_text or "",
        current_scan.visible_text or "",
        settings.scan_visible_text_max_chars,
    )
    if similarity < 75:
        severity = FindingSeverity.high if similarity < 50 else FindingSeverity.moderate
        findings.append(
            finding(
                "visible_text_changed",
                "Visible page text changed",
                "The visible text differs materially from the approved baseline.",
                severity,
                f"Visible-text similarity: {similarity:.2f}%",
                "Compare the change with an authorized release or restore the expected content.",
                15 if similarity < 50 else 8,
            )
        )

    suspicious_phrases = detect_suspicious_phrases(current_scan.visible_text or "")
    for phrase in suspicious_phrases:
        findings.append(
            finding(
                "suspicious_defacement_phrase",
                "Suspicious defacement phrase detected",
                "A phrase often associated with defacement appeared in visible page text.",
                FindingSeverity.high,
                f"Detected phrase: {phrase}",
                (
                    "Inspect the page content, deployment logs and access logs "
                    "before declaring compromise."
                ),
                25,
            )
        )

    baseline_scripts = sorted(set(baseline_scan.external_script_domains or []))
    current_scripts = sorted(set(current_scan.external_script_domains or []))
    new_scripts = sorted(set(current_scripts) - set(baseline_scripts))
    if new_scripts:
        findings.append(
            finding(
                "new_external_script_domain",
                "New external JavaScript domain detected",
                "The current scan references an external script domain absent from the baseline.",
                FindingSeverity.high,
                ", ".join(new_scripts),
                (
                    "Review the introduced script domain and remove it unless it "
                    "is expected and trusted."
                ),
                15,
            )
        )

    baseline_iframes = sorted(set(baseline_scan.external_iframe_domains or []))
    current_iframes = sorted(set(current_scan.external_iframe_domains or []))
    new_iframes = sorted(set(current_iframes) - set(baseline_iframes))
    if new_iframes:
        findings.append(
            finding(
                "new_external_iframe_domain",
                "New external iframe domain detected",
                "The current scan embeds an iframe domain absent from the baseline.",
                FindingSeverity.moderate,
                ", ".join(new_iframes),
                (
                    "Review the introduced iframe domain and remove it unless it "
                    "is expected and trusted."
                ),
                12,
            )
        )

    visual_result: VisualComparisonResult | None = None
    comparison_error: str | None = None
    if baseline_scan.screenshot_filename and current_scan.screenshot_filename:
        try:
            visual_result = compare_screenshots(
                baseline_scan.screenshot_filename,
                current_scan.screenshot_filename,
                settings,
            )
            if visual_result.visual_change_level in {"moderate", "major"}:
                severity = (
                    FindingSeverity.high
                    if visual_result.visual_change_level == "major"
                    else FindingSeverity.moderate
                )
                remediation = (
                    "Review the highlighted difference image and confirm whether "
                    "the visual change was authorized."
                )
                findings.append(
                    finding(
                        "visual_change",
                        "Visual page change detected",
                        "The current screenshot differs from the approved baseline.",
                        severity,
                        f"{visual_result.visual_change_percent:.2f}% meaningful screenshot change",
                        remediation,
                        35 if visual_result.visual_change_level == "major" else 20,
                    )
                )
        except Exception:
            comparison_error = "Visual comparison failed safely"

    return ComparisonResult(
        baseline_scan_id=baseline_scan.id,
        title_changed=title_changed,
        baseline_title=baseline_scan.page_title,
        current_title=current_scan.page_title,
        text_similarity_percent=similarity,
        visual_result=visual_result,
        comparison_error=comparison_error,
        baseline_external_script_domains=baseline_scripts,
        current_external_script_domains=current_scripts,
        new_external_script_domains=new_scripts,
        baseline_external_iframe_domains=baseline_iframes,
        current_external_iframe_domains=current_iframes,
        new_external_iframe_domains=new_iframes,
        suspicious_phrases=suspicious_phrases,
        findings=findings,
    )


def text_similarity(baseline_text: str, current_text: str, max_chars: int) -> float:
    baseline = baseline_text[:max_chars]
    current = current_text[:max_chars]
    if not baseline and not current:
        return 100.0
    return round(SequenceMatcher(None, baseline, current).ratio() * 100, 2)


def detect_suspicious_phrases(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in SUSPICIOUS_PHRASES if phrase in lowered]


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())
