from dataclasses import dataclass
from typing import Callable

DETECTOR_NAME = "basic-rules"
DETECTOR_VERSION = "v1.0"

@dataclass(frozen=True)
class RuleContext:
    hour: int
    month: int
    capacity: float
    generation: float
    solar_profile: float

def create_context(row) -> RuleContext:
    return RuleContext(
        hour=row.date_time.hour,
        month=row.date_time.month,
        capacity=row.solar_capacity,
        generation=row.solar_generation_actual,
        solar_profile=row.solar_profile,
    )

'''
Rule Logic
'''
def dropout_during_daytime_hours(context: RuleContext) -> bool:
    '''
    flags anomaly if solar generation is 0 during daylight hours.
    for year-round generation the hourly context is narrowed to between 08.00-15.00 hours.
    This ignores seasonal moving hours due to longer summer days/ shorter winter days but
    gives a decent rule year-round. Could be upgraded to consider different hours for
    different months.
    '''
    return context.generation == 0 and 8 <= context.hour <= 15

def generate_during_night_hours(context: RuleContext) -> bool:
    '''
    flags anomaly if solar generation is 0 during night hours which should not be possible.
    '''
    # guard here to prevent division errors
    if not context.capacity:
        return False
    # 0.01 chosen based on analysed dataset. It is high enough to ignore noise from night
    # hours but picks up true anomalies. Uses 0.001 to account for growing capacity over the years
    return (context.hour >= 23 or context.hour <=2) and (context.generation > 0.01 * context.capacity)

def generation_exceeds_capacity(context: RuleContext) -> bool:
    '''
    flags anomaly if solar generation exceeds capacity which should not be possible.
    '''
    if not context.capacity:
        return False
    # Multiplication here again to account for capacity change over the years
    return context.generation > 1.05 * context.capacity

def solar_profile_mismatch(context: RuleContext) -> bool:
    '''
    flags anomaly if solar generation mismatch is outside a threshold.
    '''
    if not context.capacity:
        return False
    # Checks the calculation for solar_profile and evaluates it within a threshold against the stored one.
    return abs(context.solar_profile - context.generation / context.capacity) > 0.005

@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    check: Callable[[RuleContext], bool]

RULES = [
    Rule("R1_DROPOUT_DURING_DAY_TIME", "high", dropout_during_daytime_hours),
    Rule("R2_GENERATION_DURING_NIGHT", "medium", generate_during_night_hours),
    Rule("R3_GENERATION_EXCEEDS_CAPACITY", "medium", generation_exceeds_capacity),
    Rule("R4_SOLAR_PROFILE_MISMATCH", "low", solar_profile_mismatch),
]

def evaluate_all_rules(context: RuleContext) -> list[str]:
    return [rule.code for rule in RULES if rule.check(context)]