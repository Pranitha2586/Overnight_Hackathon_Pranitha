import pandas as pd
import numpy as np 

#acre based
def validate_land_mismatch(df):
    """
    Identifies fraud where the registered land area exceeds the actual land area.
    (Acre based mismatch)
    """
    
    df['registered_area'] = pd.to_numeric(df['registered_area'], errors='coerce')
    df['land_area'] = pd.to_numeric(df['land_area'], errors='coerce')
    
    fraud = df[df["registered_area"] > df["land_area"]]
    return fraud[["farmer_id", "land_area", "registered_area"]]


def validate_transport_claims(claims_df, rates_df, tracking_df):
  
    
    rate = float(rates_df["rate_per_km_per_ton"].iloc[0])

    claims_df["distance_km"] = pd.to_numeric(claims_df["distance_km"], errors='coerce')
    claims_df["weight_ton"] = pd.to_numeric(claims_df["weight_ton"], errors='coerce')

    claims_df["expected_cost"] = (
        claims_df["distance_km"] * claims_df["weight_ton"] * rate
    )


    merged_df = claims_df.merge(
        tracking_df[["farmer_id", "tracked_cost"]],
        on="farmer_id",
        how="left"
    )

   
    

    is_higher_than_expected = merged_df["claimed_amount"] > merged_df["expected_cost"]
    
    
    is_higher_than_tracked = merged_df["claimed_amount"] > merged_df["tracked_cost"].fillna(merged_df["expected_cost"])
    
    fraud = merged_df[is_higher_than_expected | is_higher_than_tracked]
    
    return fraud[[
        "farmer_id", "distance_km", "weight_ton",
        "claimed_amount", "expected_cost", "tracked_cost"
    ]].rename(columns={'tracked_cost': 'verified_tracked_cost'})


def validate_crop_rules(claims_df, rules_df):
    """
    Validates crop claims based on the number of crops per season/farmer 
    and checks if the crop is allowed in that season.
    """
    
    crop_count = claims_df.groupby(["farmer_id", "season"])["crop"].count().reset_index()
    fraud_many_crops = crop_count[crop_count["crop"] > 2]

    merged = claims_df.merge(rules_df, on="crop", how="left")
    fraud_wrong_crop = merged[merged["season"] != merged["allowed_season"]]

    return {
        "more_than_2_crops": fraud_many_crops,
        "not_allowed_crops": fraud_wrong_crop[[
            "farmer_id", "crop", "season", "allowed_season"
        ]]
    }


def run_transport_example():
    """
    Runs a simple example to show the new transport validation logic.
    """
    print("--- Running Transport Claims Validation Example (with Tracking Data) ---")
    
    claims_data = {
        "farmer_id": ["F001", "F002", "F003", "F004"],
        "distance_km": [100, 50, 200, 150],
        "weight_ton": [5, 10, 3, 4],
        "claimed_amount": [5500, 5000, 6500, 4500], 
    }
    claims_df = pd.DataFrame(claims_data)


    rates_data = {"rate_per_km_per_ton": [10.0]} # We are assuming Rate is 10.0 per unit but there are govt based details for this
    rates_df = pd.DataFrame(rates_data)
    

    tracking_data = {
        "farmer_id": ["F001", "F002", "F003"],
        "tracked_cost": [5000, 5500, 5500],
    }
    tracking_df = pd.DataFrame(tracking_data)

    fraud_results = validate_transport_claims(claims_df, rates_df, tracking_df)
    
    print("\nCalculations:")
    print("F001 Expected: 100 * 5 * 10 = 5000. Claimed: 5500. Tracked: 5000. -> FRAUD (5500 > 5000)")
    print("F002 Expected: 50 * 10 * 10 = 5000. Claimed: 5000. Tracked: 5500. -> OK")
    print("F003 Expected: 200 * 3 * 10 = 6000. Claimed: 6500. Tracked: 5500. -> FRAUD (6500 > 6000 AND 6500 > 5500)")
    print("F004 Expected: 150 * 4 * 10 = 6000. Claimed: 4500. Tracked: NaN. -> OK")
    
    print("\n--- Identified Transport Fraud ---")
    print(fraud_results.to_markdown(index=False))

