import pandas as pd
import numpy as np

year = 2016
hours_per_year = 8784

# Function to generate and save car availability profiles for both homeoffice=True and homeoffice=False
def generate_car_availability_profiles():
    for homeoffice in [True, False]:
        availability = np.ones(hours_per_year)  # Car is at home initially
        date_index = pd.date_range(start=f'{year}-01-01', periods=hours_per_year, freq='h')
        
        for i in range(0, hours_per_year, 24):  # Loop through each day
            current_day = date_index[i].dayofweek  # 0=Monday, 6=Sunday
            
            # Determine car availability based on the actual day of the week
            if homeoffice and current_day in [0, 2, 4]:  # Mon, Wed, Fri (work from home)
                continue
            elif not homeoffice and current_day in range(5):  # Mon-Fri for no homeoffice
                availability[i+7:i+16] = 0  # Not at home from 7 am to 4 pm (commuting to work)
            
            # Random weekend trips
            if current_day in [5, 6]:  # Saturday, Sunday
                if np.random.rand() < 0.5:  # Randomly decide if there's a trip
                    trip_duration = np.random.randint(2, 8)  # Random duration of trip
                    start_hour = np.random.randint(7, 14)  # Random trip starting time
                    availability[i+start_hour:i+start_hour+trip_duration] = 0

        # Save the availability profile as a CSV file
        profile_name = f'car_availability_homeoffice_{homeoffice}.csv'
        pd.DataFrame({'EV_at_home': availability}, index=date_index).to_csv(profile_name)
        print(f"Saved profile to {profile_name}")

# Run this function to generate and save the profiles: python generate_car_availability_profiles.py
if __name__ == "__main__":
    generate_car_availability_profiles()