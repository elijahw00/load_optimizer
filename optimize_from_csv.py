# optimize_from_csv.py
# Reads jobs from CSV, runs optimization, prints results.
# Also saves the chosen jobs into output/optimized_plan.csv

import csv
import argparse
import os

from load_optimizer.models import Job, ProblemConfig
from load_optimizer.optimizer import optimize_jobs


def load_jobs_from_csv(csv_path):
    jobs = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job = Job(
                id=row["id"],
                revenue=float(row["revenue"]),
                loaded_miles=float(row["loaded_miles"]),
                deadhead_miles=float(row["deadhead_miles"]),
                hours=float(row["hours"]),
                pallets=float(row["pallets"]),
                pickup_city=row.get("pickup_city", ""),
                dropoff_city=row.get("dropoff_city", ""),
                date=row.get("date", ""),
                notes=row.get("notes", "")
            )
            jobs.append(job)
    return jobs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Optimize daily truck loads from a CSV file."
    )

    # CSV file path
    parser.add_argument(
        "--file",
        default="load_optimizer/data/loads_example.csv",
        help="Path to the CSV file with load data."
    )

    # Core constraints
    parser.add_argument(
        "--hours",
        type=float,
        default=11.0,
        help="Maximum driving hours allowed for the day (N/A if you leave default and just change in code)."
    )

    parser.add_argument(
        "--pallets",
        type=float,
        default=6.0,
        help="Maximum pallet capacity of the truck."
    )

    # Cost settings
    parser.add_argument(
        "--fuel-cost",
        type=float,
        default=0.7,
        help="Fuel cost per mile (dollars)."
    )

    parser.add_argument(
        "--driver-cost",
        type=float,
        default=25.0,
        help="Driver cost per hour (dollars)."
    )

    # Optional extra constraints
    parser.add_argument(
        "--max-deadhead",
        type=float,
        default=None,
        help="Maximum total deadhead miles for the day (leave empty/N/A to ignore)."
    )

    parser.add_argument(
        "--max-total-miles",
        type=float,
        default=None,
        help="Maximum total miles (deadhead + loaded) for the day (leave empty/N/A to ignore)."
    )

    parser.add_argument(
        "--min-profit-per-job",
        type=float,
        default=None,
        help="Minimum profit for a job to be considered (leave empty/N/A to ignore)."
    )

    return parser.parse_args()


def save_results_to_csv(result, output_path):
    """
    Save chosen jobs and totals to a CSV file.
    Also includes a summary section with extra metrics.
    """
    folder = os.path.dirname(output_path)
    if folder != "" and not os.path.exists(folder):
        os.makedirs(folder)

    # Compute total miles for chosen jobs
    total_miles = 0
    for job in result["chosen_jobs"]:
        total_miles += job.loaded_miles + job.deadhead_miles

    total_profit = result["total_profit"]
    total_hours = result["total_hours"]

    # Avoid division by zero
    if total_hours > 0:
        profit_per_hour = total_profit / total_hours
    else:
        profit_per_hour = 0

    if total_miles > 0:
        profit_per_mile = total_profit / total_miles
    else:
        profit_per_mile = 0

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header row (include city/date/notes now)
        writer.writerow([
            "id",
            "revenue",
            "loaded_miles",
            "deadhead_miles",
            "hours",
            "pallets",
            "pickup_city",
            "dropoff_city",
            "date",
            "notes",
            "profit"
        ])

        # Data rows for each chosen job
        for job in result["chosen_jobs"]:
            profit = result["all_profits"][job.id]
            writer.writerow([
                job.id,
                job.revenue,
                job.loaded_miles,
                job.deadhead_miles,
                job.hours,
                job.pallets,
                job.pickup_city,
                job.dropoff_city,
                job.date,
                job.notes,
                round(profit, 2)
            ])

        # Blank line
        writer.writerow([])

        # Totals row
        writer.writerow([
            "TOTAL",
            "",
            "",
            "",
            total_hours,
            result["total_pallets"],
            "",
            "",
            "",
            "",
            round(total_profit, 2)
        ])

        # Another blank line
        writer.writerow([])

        # Summary row with extra metrics
        writer.writerow([
            "SUMMARY",
            "",
            "total_miles",
            round(total_miles, 2),
            "profit_per_hour",
            round(profit_per_hour, 2),
            "profit_per_mile",
            round(profit_per_mile, 2)
        ])

def main():
    # 1. Read command-line arguments
    args = parse_args()

    csv_file = args.file
    max_hours = args.hours
    max_pallets = args.pallets
    fuel_cost = args.fuel_cost
    driver_cost = args.driver_cost
    max_deadhead = args.max_deadhead
    max_total_miles = args.max_total_miles
    min_profit_per_job = args.min_profit_per_job

    print("Using CSV file:", csv_file)
    print("Max hours:", max_hours)
    print("Max pallets:", max_pallets)
    print("Fuel cost per mile:", fuel_cost)
    print("Driver cost per hour:", driver_cost)
    print("Max deadhead miles:", max_deadhead)
    print("Max total miles:", max_total_miles)
    print("Min profit per job:", min_profit_per_job)
    print()

    # 2. Load jobs from CSV
    jobs = load_jobs_from_csv(csv_file)

    # 3. Problem settings
    cfg = ProblemConfig(
        max_hours=max_hours,
        max_pallets=max_pallets,
        fuel_cost_per_mile=fuel_cost,
        driver_cost_per_hour=driver_cost
    )

    # 4. Run optimization with extra optional controls
    result = optimize_jobs(
        jobs,
        cfg,
        max_deadhead=max_deadhead,
        max_total_miles=max_total_miles,
        min_profit_per_job=min_profit_per_job
    )

    # 5. Print results to terminal
    print("Status:", result["status"])
    print("Total Profit:", round(result["total_profit"], 2))
    print("Total Hours:", result["total_hours"])
    print("Total Pallets:", result["total_pallets"])
    print()
    print("Chosen Jobs:")

    for job in result["chosen_jobs"]:
        profit = result["all_profits"][job.id]
        print(
            "  Job", job.id,
            "| from", job.pickup_city, "to", job.dropoff_city,
            "| date =", job.date,
            "| revenue =", job.revenue,
            "| loaded =", job.loaded_miles,
            "| deadhead =", job.deadhead_miles,
            "| hours =", job.hours,
            "| pallets =", job.pallets,
            "| profit =", round(profit, 2)
        )

    # 6. Save results to CSV file
    output_path = "output/optimized_plan.csv"
    save_results_to_csv(result, output_path)
    print()
    print("Saved optimized plan to:", output_path)


if __name__ == "__main__":
    main()
