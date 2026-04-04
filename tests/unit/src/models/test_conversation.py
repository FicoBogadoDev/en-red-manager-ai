from manager_ai.models.conversation import DimensionEstimate, JobScope


def test_replace_net_areas_assigns_default_labels() -> None:
    scope = JobScope()

    scope.replace_net_areas([
        DimensionEstimate(width_meters=4.0, height_meters=1.2),
        DimensionEstimate(width_meters=2.5, height_meters=1.0),
    ])

    assert len(scope.net_areas) == 2
    assert scope.net_areas[0].label == "Area 1"
    assert scope.net_areas[1].label == "Area 2"
    assert scope.net_areas[0].width_meters == 4.0
    assert scope.net_areas[0].height_meters == 1.2


def test_complete_net_areas_only_returns_fully_measured_areas() -> None:
    scope = JobScope(
        net_areas=[
            DimensionEstimate(label="Area 1", width_meters=4.0, height_meters=1.2),
            DimensionEstimate(label="Area 2", width_meters=2.5, height_meters=None),
        ]
    )

    complete_areas = scope.complete_net_areas()

    assert len(complete_areas) == 1
    assert complete_areas[0].label == "Area 1"
