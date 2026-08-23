"""
O-TRACK O7 — advanced screen output tests.

Pins:
- canonical screen result shape (selected filters, selected
  columns, per-column availability, name/sector context);
- deterministic results regardless of universe order;
- unsupported filters and unsupported columns are rejected with
  explicit, named errors;
- no score / ranking / winner / recommendation fields exist.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.recorded_research import (
    COMPANY_NAMES,
    COMPANY_SECTORS,
    RecordedCompanyResearchService,
)
from src.screener.engine import (
    InvalidScreenError,
    ScreenDefinition,
    execute_screen,
)
from src.screener.fields import extract_company_fields
from src.screener.results import ScreenExecutionOutput, build_screen_output

AS_OF = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

SYMBOLS = ("TCS", "RELIANCE", "INFY", "HDFCBANK", "SUNPHARMA", "M&M")

_DEFINITION = ScreenDefinition.from_dict(
    {
        "name": "Profitable large companies",
        "description": "Reported profitability above zero.",
        "combine": "AND",
        "groups": [
            {
                "logic": "AND",
                "filters": [
                    {
                        "field": "net_profit_latest",
                        "operator": "gt",
                        "value": "0",
                    }
                ],
            }
        ],
    }
)


@pytest.fixture(scope="module")
def universe(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("o7-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)

    rows = {}
    for symbol in SYMBOLS:
        if not service.research_available(symbol):
            continue
        result = service.run(symbol, as_of=AS_OF)
        rows[symbol] = extract_company_fields(result)

    return rows


def _run(universe, definition=_DEFINITION):
    execution = execute_screen(definition, universe)
    return build_screen_output(
        definition,
        execution,
        universe,
        requested_columns=(
            "net_profit_latest",
            "revenue_latest",
            "operating_margin_pct",
            "pit_checks_passed",
        ),
        company_names=dict(COMPANY_NAMES),
        sectors=dict(COMPANY_SECTORS),
    )


class TestScreenOutputShape:
    def test_echoes_selected_filters_and_columns(self, universe):
        output = _run(universe)

        assert output.selected_filters == _DEFINITION.to_dict()
        assert output.selected_columns == (
            "net_profit_latest",
            "revenue_latest",
            "operating_margin_pct",
            "pit_checks_passed",
        )
        assert output.definition_hash == _DEFINITION.definition_hash()

    def test_rows_carry_identity_and_column_availability(self, universe):
        output = _run(universe)

        assert output.rows
        assert output.matched_count == len(output.rows)
        assert output.universe_size == len(universe)

        for row in output.rows:
            assert row.symbol in universe
            assert row.company_name == COMPANY_NAMES.get(row.symbol)
            assert row.sector == COMPANY_SECTORS.get(row.symbol)
            assert [c.field for c in row.columns] == list(
                output.selected_columns
            )

            for column in row.columns:
                if column.value is None:
                    assert column.available is False
                else:
                    assert column.available is True

    def test_no_score_or_ranking_fields_exist(self, universe):
        output = _run(universe)
        payload = output.model_dump(mode="json")

        forbidden = {"score", "rank", "ranking", "winner", "recommendation"}

        def scan(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    assert key.lower() not in forbidden
                    scan(value)
            elif isinstance(node, list):
                for entry in node:
                    scan(entry)

        scan(payload)


class TestDeterminism:
    def test_same_universe_same_output(self, universe):
        first = _run(universe)
        second = _run(dict(universe))

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )

    def test_row_order_independent_of_universe_order(self, universe):
        forward = _run(dict(universe))
        reversed_universe = dict(reversed(list(universe.items())))
        backward = _run(reversed_universe)

        assert [r.symbol for r in forward.rows] == [
            r.symbol for r in backward.rows
        ]
        assert forward.model_dump(mode="json") == backward.model_dump(
            mode="json"
        )


class TestUnsupportedBehavior:
    def test_unknown_filter_field_rejected(self):
        with pytest.raises(InvalidScreenError) as excinfo:
            ScreenDefinition.from_dict(
                {
                    "name": "bad",
                    "groups": [
                        {
                            "filters": [
                                {
                                    "field": "no_such_field",
                                    "operator": "gt",
                                    "value": "1",
                                }
                            ]
                        }
                    ],
                }
            )

        assert "no_such_field" in str(excinfo.value)

    def test_unavailable_filter_field_rejected_with_note(self):
        from src.screener.fields import UNAVAILABLE_FIELDS

        assert UNAVAILABLE_FIELDS, (
            "registry must declare unavailable fields explicitly"
        )

        unavailable = sorted(UNAVAILABLE_FIELDS)[0]

        with pytest.raises(InvalidScreenError) as excinfo:
            ScreenDefinition.from_dict(
                {
                    "name": "unavailable-field",
                    "groups": [
                        {
                            "filters": [
                                {
                                    "field": unavailable,
                                    "operator": "gt",
                                    "value": "1",
                                }
                            ]
                        }
                    ],
                }
            )

        assert "not available yet" in str(excinfo.value)

    def test_unknown_operator_rejected(self):
        with pytest.raises(InvalidScreenError) as excinfo:
            ScreenDefinition.from_dict(
                {
                    "name": "bad-op",
                    "groups": [
                        {
                            "filters": [
                                {
                                    "field": "net_profit_latest",
                                    "operator": "approx",
                                    "value": "1",
                                }
                            ]
                        }
                    ],
                }
            )

        assert "unsupported operator" in str(excinfo.value)

    def test_unknown_output_column_rejected(self, universe):
        execution = execute_screen(_DEFINITION, universe)

        with pytest.raises(InvalidScreenError) as excinfo:
            build_screen_output(
                _DEFINITION,
                execution,
                universe,
                requested_columns=("no_such_column",),
            )

        assert "no_such_column" in str(excinfo.value)


class TestCapabilityGaps:
    def test_saved_screens_reported_as_gap_not_faked(self, universe):
        output = _run(universe)

        assert any(
            "Saved-screen storage is not supported" in note
            for note in output.notes
        )
