import random
import numpy as np
import pandas as pd

# Set constants for average EV profile in Germany
CHARGING_POWER_KW = 7.4  # Average home charger power (kW)
EFFICIENCY_WH_PER_KM = 191  # Efficiency in Wh per km (191 Wh/km = 19.1 kWh/100km)
EFFICIENCY_KWH_PER_KM = EFFICIENCY_WH_PER_KM / 1000  # Efficiency in kWh per km
AVG_BATTERY_CAPACITY_KWH = 72  # Average battery capacity in kWh

# Define battery limits (can't go below 10%, and charge up to 80%)
MIN_BATTERY_PERCENT = 0.10  # 10% minimum
MAX_BATTERY_PERCENT = 0.80  # 80% maximum

# PV parameters and thresholds
PV_THRESHOLD_KW = 1.4  # Minimum PV overshoot to charge from PV alone
PV_THRESHOLD_MIN_KW = 0.9  # Minimum to charge from PV + Grid
BATTERY_STORAGE_MIN_PERCENT = 0.10  # Minimum battery storage level to charge from battery
GRID_CHARGE_PERCENT = 0.42  # Below this, charge from grid

# Define the two profiles
profiles = {
    "Homeoffice": {
        "driving_to_work_per_week": 3,  # days with 22 km commute (round trip)
        "driving_days_per_week": 5,     # weekdays
        "avg_one_way_distance_km": 12,  # 12 km on non-workdays (one-way)
    },
    "Kein Homeoffice": {
        "driving_days_per_week": 5,     # weekdays
        "avg_daily_distance_km": 22,    # 22 km total (no distinction between work/non-work)
    }
}

# Simulation period (1 week)
days = 7
hours_per_day = 24

# Weekend configuration (12 km for short trips, randomize longer vacation trips)
WEEKEND_MIN_DISTANCE = 12
WEEKEND_DAYS = [5, 6]  # Saturday and Sunday are day indices 5 and 6

# Logic to simulate the charging decisions based on the diagram
def simulate_charging_logic(battery_state, pv_overshoot_kw, battery_storage_percent, ev_percent):
    max_battery_level = AVG_BATTERY_CAPACITY_KWH * MAX_BATTERY_PERCENT
    min_battery_level = AVG_BATTERY_CAPACITY_KWH * MIN_BATTERY_PERCENT
    
    # Decision Logic Based on the Diagram
    if ev_percent >= MAX_BATTERY_PERCENT * 100:  # EV already at 80%
        return battery_state, 0  # No charging needed

    if pv_overshoot_kw >= PV_THRESHOLD_KW:  # PV overshoot >= 1.4 kW
        energy_to_add = CHARGING_POWER_KW / hours_per_day
        battery_state = min(battery_state + energy_to_add, max_battery_level)
        return battery_state, energy_to_add

    elif PV_THRESHOLD_MIN_KW < pv_overshoot_kw < PV_THRESHOLD_KW:  # PV overshoot between 0.9 and 1.4 kW
        energy_to_add = CHARGING_POWER_KW / hours_per_day
        battery_state = min(battery_state + energy_to_add, max_battery_level)
        return battery_state, energy_to_add

    elif battery_storage_percent > BATTERY_STORAGE_MIN_PERCENT * 100:  # Battery Storage > 10%
        energy_to_add = CHARGING_POWER_KW / hours_per_day
        battery_state = min(battery_state + energy_to_add, max_battery_level)
        return battery_state, energy_to_add

    elif ev_percent < GRID_CHARGE_PERCENT * 100:  # EV charge < 42%
        energy_to_add = CHARGING_POWER_KW / hours_per_day
        battery_state = min(battery_state + energy_to_add, max_battery_level)
        return battery_state, energy_to_add

    return battery_state, 0  # No charging if no condition is met

# Function to simulate user driving and charging patterns
def generate_user_profile(profile_name, profile_data, days, hours_per_day):
    max_battery_level = AVG_BATTERY_CAPACITY_KWH * MAX_BATTERY_PERCENT
    min_battery_level = AVG_BATTERY_CAPACITY_KWH * MIN_BATTERY_PERCENT
    
    driving_days = profile_data.get("driving_days_per_week", 5)
    driving_to_work_days = profile_data.get("driving_to_work_per_week", 0)
    avg_one_way_distance_km = profile_data.get("avg_one_way_distance_km", 0)
    avg_daily_distance_km = profile_data.get("avg_daily_distance_km", 0)
    
    # Weekday driving pattern (randomly distribute driving days)
    driving_days_indices = sorted(random.sample(range(5), driving_days))  # Only weekdays (Mon-Fri)
    work_days_indices = sorted(random.sample(driving_days_indices, driving_to_work_days)) if "Homeoffice" in profile_name else []
    
    # Randomly assign driving on weekends (Saturday and/or Sunday)
    weekend_driving_days = [day for day in WEEKEND_DAYS if random.choice([True, False])]
    
    battery_state = max_battery_level  # Start at the maximum battery level (80%)
    availability_matrix = np.ones((days, hours_per_day))  # Initialize all hours as available
    battery_profile = []  # Track battery level over time
    total_energy_used_for_charging = 0  # Track total energy used for charging
    total_km_driven = 0  # Track total kilometers driven
    
    for day in range(days):
        # Simulate the PV overshoot and battery storage for this hour (randomized values for testing)
        pv_overshoot_kw = random.uniform(0, 2)  # Random PV overshoot between 0 and 2 kW
        battery_storage_percent = random.uniform(0, 100)  # Random battery storage percentage
        ev_percent = (battery_state / AVG_BATTERY_CAPACITY_KWH) * 100  # Current EV battery percentage
        
        # Weekday (Monday to Friday)
        if day < 5:
            if profile_name == "Homeoffice":
                if day in work_days_indices:
                    distance_driven = avg_one_way_distance_km * 2  # 22 km round trip on workdays
                else:
                    distance_driven = avg_one_way_distance_km * 2  # Non-workday: 24 km total
            else:  # Kein Homeoffice (22 km fixed every weekday)
                distance_driven = avg_daily_distance_km

            total_km_driven += distance_driven  # Add to total kilometers driven
            
            # Calculate battery consumption
            consumption_kwh = distance_driven * EFFICIENCY_KWH_PER_KM  # kWh used for the day
            battery_state -= consumption_kwh
            
            # Ensure the battery doesn't go below 10% capacity
            if battery_state < min_battery_level:
                battery_state = min_battery_level  # Can't go below 10%
            
            # Car is not available during driving hours (8 AM to 6 PM)
            availability_matrix[day, 8:18] = 0  # Mark driving hours as unavailable
        
        # Weekend (Saturday or Sunday)
        elif day in weekend_driving_days:
            # Decide if it's a short trip (12 km) or a long trip (up to battery limit)
            if random.choice([True, False]):
                # Short trip (12 km)
                distance_driven = WEEKEND_MIN_DISTANCE
            else:
                # Longer trip (vacation) until battery reaches 10%
                distance_driven = 0
                while battery_state > min_battery_level:
                    distance_driven += 1
                    battery_state -= EFFICIENCY_KWH_PER_KM
                    if battery_state < min_battery_level:
                        battery_state = min_battery_level
                        break
            
            total_km_driven += distance_driven  # Add weekend kilometers driven
            
            # Calculate battery consumption for the weekend drive
            consumption_kwh = distance_driven * EFFICIENCY_KWH_PER_KM
            battery_state -= consumption_kwh
            
            # Ensure battery doesn't go below 10%
            if battery_state < min_battery_level:
                battery_state = min_battery_level
            
            # Simulate the car being unavailable during driving hours on weekends
            availability_matrix[day, 10:14] = 0
        
        # Simulate charging decision based on PV overshoot and battery storage
        battery_state, energy_charged = simulate_charging_logic(battery_state, pv_overshoot_kw, battery_storage_percent, ev_percent)
        total_energy_used_for_charging += energy_charged  # Track total energy used
        
        # Save the battery state for the current day
        battery_profile.append(battery_state)
    
    return battery_profile, availability_matrix, total_energy_used_for_charging, total_km_driven

# Test the program with the "Kein Homeoffice" profile
profile_name = "Kein Homeoffice"
battery_profile, availability_matrix, total_energy_used_for_charging, total_km_driven = generate_user_profile(
    profile_name, profiles[profile_name], days, hours_per_day)

print(f"Total energy used for charging (kWh): {total_energy_used_for_charging}")
print(f"Total kilometers driven during the week: {total_km_driven} km")
