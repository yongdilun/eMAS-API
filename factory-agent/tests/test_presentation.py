from agent.presentation import extract_table_from_result


def test_table_columns_follow_requested_fields_without_domain_hardcoding():
    result = {
        "data": [
            {
                "notes": "seed:P-005:2026-05-19T00:00:00Z:520",
                "job_id": "JOB-SEED-005",
                "status": "planned",
                "deadline": "2026-05-19T08:00:00+08:00",
                "priority": "low",
                "created_at": "2026-04-28T15:15:31.644+08:00",
                "product_id": "P-005",
                "updated_at": "2026-04-28T15:15:31.644+08:00",
                "quantity_total": 520,
            },
            {
                "notes": "seed:P-002:2026-05-07T00:00:00Z:480",
                "job_id": "JOB-SEED-024",
                "status": "planned",
                "deadline": "2026-05-07T08:00:00+08:00",
                "priority": "low",
                "created_at": "2026-04-28T15:15:31.644+08:00",
                "product_id": "P-002",
                "updated_at": "2026-04-28T15:15:31.644+08:00",
                "quantity_total": 480,
            },
        ],
        "_analysis": {
            "results": [
                {"operation": "argmin", "field": "deadline"},
                {"operation": "argmax", "field": "quantity_total"},
            ],
            "facts": ["Earliest deadline: JOB-SEED-024.", "Largest quantity: JOB-SEED-005."],
        },
    }

    presentation = extract_table_from_result(
        tool_name="get__jobs",
        result=result,
        intent="Show job_id, product_id, quantity_total, deadline and highlight largest quantity.",
    )

    keys = [column["key"] for column in presentation["table"]["columns"]]
    assert keys[:4] == ["job_id", "product_id", "quantity_total", "deadline"]
    assert "quantity_total" in keys
    assert "notes" not in keys
