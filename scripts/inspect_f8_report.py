"""Dump an F8 professional report for inspection (stabilization pass)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.f8_serializers import professional_report_contract
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.evidence.lineage import build_evidence_lineage
from src.research.report.professional import build_professional_report

symbol = sys.argv[1] if len(sys.argv) > 1 else "HDFCBANK"
out = sys.argv[2] if len(sys.argv) > 2 else "/var/folders/2h/_420gyfx2f5bk8mhw3wmmf1r0000gn/T/opencode/f8_report.json"

service = RecordedCompanyResearchService()
result = service.run(symbol)

intel = result.intelligence
intel_items = intel.items if intel is not None else ()

lineage = build_evidence_lineage(
    symbol=result.company,
    as_of=result.as_of,
    evidence_items=result.evidence_items,
    intel_items=intel_items,
    pit_filter=True,
)

research_gaps = getattr(intel, "research_gaps", None) if intel is not None else None

report = build_professional_report(
    lineage=lineage,
    company_name=service.company_name(result.company),
    intel_items=intel_items,
    intelligence=intel,
    research_gaps=research_gaps,
    acquisition=result.acquisition,
)

payload = professional_report_contract(report, company_name=service.company_name(result.company))

Path(out).write_text(json.dumps(payload, indent=2, default=str))
print(f"wrote {out} ({len(json.dumps(payload, default=str))} bytes)")
