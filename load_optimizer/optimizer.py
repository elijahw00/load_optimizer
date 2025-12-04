# optimizer.py
# This file contains all logic for optimizing which jobs to accept.

import pulp
from .models import Job, ProblemConfig


def compute_job_profit(job, cfg):
    # Total miles = loaded miles + deadhead (empty) miles
    total_miles = job.loaded_miles + job.deadhead_miles

    # Cost of fuel for this job
    fuel_cost = total_miles * cfg.fuel_cost_per_mile

    # Cost of driver labor
    labor_cost = job.hours * cfg.driver_cost_per_hour

    # Total cost of doing the job
    total_cost = fuel_cost + labor_cost

    # Profit = revenue - cost
    return job.revenue - total_cost


def optimize_jobs(jobs, cfg,
                  max_deadhead=None,
                  max_total_miles=None,
                  min_profit_per_job=None):
    """
    jobs: list of Job objects
    cfg:  ProblemConfig (hours/pallets limits + cost settings)

    Optional extra controls:
      max_deadhead      -> if not None, limit total deadhead miles
      max_total_miles   -> if not None, limit total miles (deadhead + loaded)
      min_profit_per_job -> if not None, drop jobs whose profit is below this
    """

    # Pre-compute profit for each job
    profits = {}
    for job in jobs:
        profits[job.id] = compute_job_profit(job, cfg)

    # OPTIONALLY drop low-profit jobs
    if min_profit_per_job is not None:
        filtered_jobs = []
        for job in jobs:
            if profits[job.id] >= min_profit_per_job:
                filtered_jobs.append(job)
        jobs = filtered_jobs

    # Create ILP problem (maximize profit)
    prob = pulp.LpProblem("Load_Selection", pulp.LpMaximize)

    # Create binary decision variables for each job
    x = {}
    for job in jobs:
        x[job.id] = pulp.LpVariable("x_" + job.id, lowBound=0, upBound=1, cat=pulp.LpBinary)

    # Objective: maximize total profit
    prob += sum(profits[job.id] * x[job.id] for job in jobs)

    # Hours constraint
    prob += sum(job.hours * x[job.id] for job in jobs) <= cfg.max_hours

    # Pallets constraint
    prob += sum(job.pallets * x[job.id] for job in jobs) <= cfg.max_pallets

    # OPTIONAL: max total deadhead miles constraint
    if max_deadhead is not None:
        prob += sum(job.deadhead_miles * x[job.id] for job in jobs) <= max_deadhead

    # OPTIONAL: max total miles (deadhead + loaded)
    if max_total_miles is not None:
        prob += sum(
            (job.loaded_miles + job.deadhead_miles) * x[job.id]
            for job in jobs
        ) <= max_total_miles

    # Solve ILP
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # Extract solution
    chosen_jobs = []
    total_profit = 0
    total_hours = 0
    total_pallets = 0

    for job in jobs:
        if pulp.value(x[job.id]) is not None and pulp.value(x[job.id]) > 0.5:
            chosen_jobs.append(job)
            total_profit += profits[job.id]
            total_hours += job.hours
            total_pallets += job.pallets

    # Return results as a simple dictionary
    return {
        "status": pulp.LpStatus[prob.status],
        "total_profit": total_profit,
        "total_hours": total_hours,
        "total_pallets": total_pallets,
        "chosen_jobs": chosen_jobs,
        "all_profits": profits
    }
