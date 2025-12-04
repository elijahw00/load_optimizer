# models.py
# Very simple data containers for Job and ProblemConfig

class Job:
    def __init__(self, id, revenue, loaded_miles, deadhead_miles, hours, pallets,
                 pickup_city="", dropoff_city="", date="", notes=""):
        # Basic numeric fields used in optimization
        self.id = id
        self.revenue = revenue
        self.loaded_miles = loaded_miles
        self.deadhead_miles = deadhead_miles
        self.hours = hours
        self.pallets = pallets

        # Extra info, useful for humans but not required for the math
        self.pickup_city = pickup_city
        self.dropoff_city = dropoff_city
        self.date = date
        self.notes = notes


class ProblemConfig:
    def __init__(self, max_hours, max_pallets, fuel_cost_per_mile, driver_cost_per_hour):
        self.max_hours = max_hours
        self.max_pallets = max_pallets
        self.fuel_cost_per_mile = fuel_cost_per_mile
        self.driver_cost_per_hour = driver_cost_per_hour
