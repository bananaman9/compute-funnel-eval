"""Calculate planning decisions from trusted structured inputs without an LLM."""
import argparse
import json
from pathlib import Path


def integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{field} must be an integer of at least {minimum}')
    return value


def boolean(value, field):
    if type(value) is not bool:
        raise ValueError(f'{field} must be a boolean')
    return value


def reservation(quota_seconds, duration_seconds, multiplier, age_days, verified, good_standing):
    budget = integer(quota_seconds, 'quota_seconds')
    charge = integer(duration_seconds, 'duration_seconds', 1) * integer(multiplier, 'multiplier', 1)
    age = integer(age_days, 'age_days')
    verified = boolean(verified, 'verified')
    good_standing = boolean(good_standing, 'good_standing')
    count, remaining = divmod(budget, charge)
    return {
        'calculations': {'quota_seconds_per_request': charge,
                         'planned_quota_seconds_consumed_by_this_plan': budget - remaining},
        'eligible_account': verified and good_standing and age > 30,
        'maximum_full_requests': count,
        'remaining_quota_seconds': remaining,
        'deployment_ready': False,
    }


def batch(quota_seconds, startup_seconds, case_seconds, multiplier, pending_cases, verified_answers):
    budget = integer(quota_seconds, 'quota_seconds')
    startup = integer(startup_seconds, 'startup_seconds')
    per_case = integer(case_seconds, 'case_seconds', 1)
    multiplier = integer(multiplier, 'multiplier', 1)
    pending = integer(pending_cases, 'pending_cases')
    verified = integer(verified_answers, 'verified_answers')
    startup_charge = startup * multiplier
    case_charge = per_case * multiplier
    if startup_charge > budget:
        raise ValueError('The quota cannot cover startup')
    count = min(pending, (budget - startup_charge) // case_charge)
    actual_seconds = startup + count * per_case
    used = actual_seconds * multiplier
    return {
        'calculations': {'startup_quota_seconds': startup_charge, 'per_case_quota_seconds': case_charge,
                         'quota_seconds_used': used},
        'planned_cases': count,
        'actual_gpu_seconds': actual_seconds,
        'remaining_quota_seconds': budget - used,
        'verified_answers_before_validation': verified,
    }


def placement(required_gib, load_minutes, task_minutes, offers):
    required = integer(required_gib, 'required_gib', 1)
    load = integer(load_minutes, 'load_minutes')
    task = integer(task_minutes, 'task_minutes')
    duration = load + task
    if not isinstance(offers, dict):
        raise ValueError('offers must map identifiers to structured offers')
    slack = {}
    for identifier, offer in sorted(offers.items()):
        if not isinstance(identifier, str) or not identifier or not isinstance(offer, dict):
            raise ValueError('Each offer requires a nonempty identifier and object')
        devices = integer(offer['devices'], 'devices')
        memory = integer(offer['memory_per_gpu_gib'], 'memory_per_gpu_gib')
        window = integer(offer['window_minutes'], 'window_minutes')
        programmable = boolean(offer['programmable'], 'programmable')
        supported = boolean(offer['runtime_supported'], 'runtime_supported')
        if devices and memory >= required and window >= duration and programmable and supported:
            slack[identifier] = window - duration
    return {'calculations': {'load_minutes': load, 'task_minutes': task},
            'eligible': list(slack), 'job_minutes': duration, 'slack_minutes': slack}


def unique_fields(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f'Duplicate field: {name}')
        result[name] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operations = {'quota': reservation, 'batch': batch, 'placement': placement}
    parser.add_argument('operation', choices=operations)
    parser.add_argument('inputs', type=Path)
    args = parser.parse_args()
    try:
        values = json.loads(args.inputs.read_text(encoding='utf-8'), object_pairs_hook=unique_fields)
        result = operations[args.operation](**values)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
