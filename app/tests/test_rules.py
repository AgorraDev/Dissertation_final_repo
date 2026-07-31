from datetime import datetime
from app.db_models.sensor_models import GenerationData
from app.services.detection_rules import RuleContext, create_context, evaluate_all_rules

def test_r1_works_on_real_data_row():
    context = RuleContext(hour=11, month=4, capacity=7122.0, generation=0.0, solar_profile=0.0)

    assert evaluate_all_rules(context) == ["R1_DROPOUT_DURING_DAY_TIME"]

def test_no_fire_on_healthy_midday_row():
    context = RuleContext(hour=12, month=6, capacity=8208.0, generation=7125.0, solar_profile=0.868)

    assert evaluate_all_rules(context) == []

def test_r2_calibration_threshold():
    below_thres = RuleContext(hour=1, month=6, capacity=8000.0, generation=50.0, solar_profile=0.006)
    above_thres = RuleContext(hour=1, month=6, capacity=8000.0, generation=100.0, solar_profile=0.0125)

    assert evaluate_all_rules(below_thres) == []
    assert "R2_GENERATION_DURING_NIGHT" in evaluate_all_rules(above_thres)

def test_r3_exceeds_capacity():
    context = RuleContext(hour=12, month=6, capacity=5000.0, generation=8000.0, solar_profile=1.2)

    assert "R3_GENERATION_EXCEEDS_CAPACITY" in evaluate_all_rules(context)

def test_r4_solar_profile_mismatch():
    context = RuleContext(hour=12, month=6, capacity=8000.0, generation=4000.0, solar_profile=0.9)

    assert evaluate_all_rules(context) == ["R4_SOLAR_PROFILE_MISMATCH"]

def test_capacity_at_zero_does_not_crash():
    context = RuleContext(hour=12, month=6, capacity=0.0, generation=200.0, solar_profile=0.0)

    assert evaluate_all_rules(context) == []

def test_create_context_reads_rows():
    row = GenerationData(trace_id="trace-1", date_time=datetime(2016, 4, 17, 11, 0, 0),
                         solar_capacity=5000, solar_generation_actual=0.0, solar_profile=0.0)

    assert create_context(row) == RuleContext(11, 4, 5000, 0.0, 0.0)