from load_optimizer.models import Job, ProblemConfig
from load_optimizer.optimizer import optimize_jobs


def main():
    # Jobs from your classroom/example model
    jobs = [
        Job(id="1", revenue=700, loaded_miles=120, hours=3.0, pallets=2),
        Job(id="2", revenue=500, loaded_miles=60,  hours=2.0, pallets=1),
        Job(id="3", revenue=900, loaded_miles=180, hours=4.5, pallets=3),
        Job(id="4", revenue=400, loaded_miles=40,  hours=1.5, pallets=1),
        Job(id="5", revenue=650, loaded_miles=100, hours=3.0, pallets=2),
    ]

    cfg = ProblemConfig(
        max_hours=11.0,
        max_pallets=6.0,
        fuel_cost_per_mile=0.7,
        driver_cost_per_hour=25.0,
    )

    result = optimize_jobs(jobs, cfg)

    print("Status:", result["status"])
    print(f"Total Profit: {result['total_profit']:.2f}")
    print(f"Total Hours: {result['total_hours']:.2f}")
    print(f"Total Pallets: {result['total_pallets']:.2f}")
    print("\nChosen Jobs:")
    for j in result["chosen_jobs"]:
        print(
            f"  Job {j['id']}: revenue={j['revenue']}, "
            f"hours={j['hours']}, pallets={j['pallets']}, profit={j['profit']:.2f}"
        )


if __name__ == "__main__":
    main()