import pandas as pd
import numpy as np

year = 2014
hours_per_year = 8760
distance_to_work = 22  # km Einweg
max_trip_distance = 100  # km Wochenendetrips

# Function to generate and save car availability profiles with distances traveled for both homeoffice=True and homeoffice=False
def generate_car_availability_distance_profile():
    for homeoffice in [True, False]:
        availability = np.ones(hours_per_year)  # Car is at home initially
        distance_travelled = np.zeros(hours_per_year)  # Distance traveled each hour (km), default to 0
        date_index = pd.date_range(start=f'{year}-01-01', periods=hours_per_year, freq='h')
        
        for i in range(0, hours_per_year, 24):  # Loop through each day
            current_day = date_index[i].dayofweek  # 0=Monday, 6=Sunday
            
            if homeoffice:
                # Homeoffice mode: Commute only on Tuesdays and Thursdays
                if current_day in [1, 3]:  # Tue, Thu (commuting days)
                    # Car leaves at 7 am and returns at 4 pm
                    availability[i + 7:i + 16] = 0  # Car is away from 7 am to 4 pm
                    distance_travelled[i + 7] = distance_to_work  # Outbound trip at 7 am
                    distance_travelled[i + 15] = distance_to_work  # Return trip at 4 pm
                else:
                    # On Mo, We, Fr, the car is at home all day (availability = 1)
                    availability[i:i + 24] = 1  # Car remains at home
            else:
                # No homeoffice mode: Commute every weekday (Mon-Fri)
                if current_day in range(5):  # Mon-Fri
                    # Car leaves at 7 am and returns at 4 pm
                    availability[i + 7:i + 16] = 0  # Car is away from 7 am to 4 pm
                    distance_travelled[i + 7] = distance_to_work  # Outbound trip at 7 am
                    distance_travelled[i + 15] = distance_to_work  # Return trip at 4 pm

            # Random weekend trips
            if current_day in [5, 6]:  # Saturday, Sunday
                if np.random.rand() < 0.5:  # Randomly decide if there's a trip
                    trip_distance = np.random.randint(10, max_trip_distance + 1)  # Random distance for weekend trip (10 to 100 km)
                    
                    # Set outbound trip
                    start_hour = np.random.randint(7, 14)  # Random trip starting time
                    return_hour = start_hour + np.random.randint(2, 5)  # Stay away for 2 to 4 hours
                    
                    # Ensure return is on the same day
                    if return_hour < i + 24:
                        # Mark availability as 0 for all hours between start and return
                        availability[i + start_hour: i + return_hour + 1] = 0
                        distance_travelled[i + start_hour] = trip_distance  # Outbound distance
                        distance_travelled[i + return_hour] = trip_distance  # Return distance

        # Save the availability and distance traveled profile as a CSV file
        profile_name = f'car_availability_homeoffice_{homeoffice}_{year}.csv'
        pd.DataFrame({'EV_at_home': availability, 'distance_travelled': distance_travelled}, index=date_index).to_csv(profile_name)
        print(f"Saved profile to {profile_name}")

# Run this function to generate and save the profiles
if __name__ == "__main__":
    generate_car_availability_distance_profile()

