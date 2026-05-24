import sys
sys.path.insert(0, ".")

from decision_engine.recommender import recommend_berth

test_cases = [
    {
        "id": "30684004", "name": "BOURBON", "vessel_type": "Chemical Tanker", "cargo_type": "Chemical",
        "loa": 183.20, "draft": 9.50, "beam": 32.224, "dwt": 46921, "assigned_berth": "5355", "assigned_name": "Berth BD1"
    },
    {
        "id": "29591751", "name": "AHINOS", "vessel_type": "Chemical Tanker", "cargo_type": "Chemical",
        "loa": 183.20, "draft": 10.80, "beam": 32.233, "dwt": 53187, "assigned_berth": "4322", "assigned_name": "Berth BD2"
    },
    {
        "id": "30354621", "name": "ASIA EVERGREEN", "vessel_type": "Chemical Tanker", "cargo_type": "Chemical",
        "loa": 146.00, "draft": 7.50, "beam": 22.0, "dwt": 14000, "assigned_berth": "4322", "assigned_name": "Berth BD2"
    },
    {
        "id": "28401474", "name": "ANGIE", "vessel_type": "Chemical Tanker", "cargo_type": "Chemical",
        "loa": 183.20, "draft": 11.70, "beam": 32.233, "dwt": 52420, "assigned_berth": "4322", "assigned_name": "Berth BD2"
    },
    {
        "id": "30520011", "name": "GLOBAL JUPITER", "vessel_type": "Chemical Tanker", "cargo_type": "Chemical",
        "loa": 141.31, "draft": 8.10, "beam": 24.2, "dwt": 16381, "assigned_berth": "4322", "assigned_name": "Berth BD2"
    },
    {
        "id": "30248761", "name": "OCEAN SOUL", "vessel_type": "General Cargo", "cargo_type": "General Cargo",
        "loa": 99.98, "draft": 5.00, "beam": 15.8, "dwt": 5040, "assigned_berth": "2172", "assigned_name": "Berth JD1"
    },
    {
        "id": "26511346", "name": "EIRENE", "vessel_type": "General Cargo", "cargo_type": "General Cargo",
        "loa": 116.99, "draft": 8.70, "beam": 19.6, "dwt": 11612, "assigned_berth": "21949", "assigned_name": "Berth CTB3"
    },
    {
        "id": "25469471", "name": "ANNAMARIA", "vessel_type": "General Cargo", "cargo_type": "General Cargo",
        "loa": 116.23, "draft": 5.20, "beam": 18.0, "dwt": 8091, "assigned_berth": "21949", "assigned_name": "Berth CTB3"
    },
    {
        "id": "30626766", "name": "AUTAI", "vessel_type": "Bulk Dry", "cargo_type": "Bulk Dry",
        "loa": 159.98, "draft": 9.90, "beam": 24.2, "dwt": 23800, "assigned_berth": "2172", "assigned_name": "Berth JD1"
    }
]

res = []
for tc in test_cases:
    vessel = {
        "name": tc["name"], "loa": tc["loa"], "draft": tc["draft"], "beam": tc["beam"],
        "dwt": tc["dwt"], "vessel_type": tc["vessel_type"], "cargo_type": tc["cargo_type"]
    }
    options = recommend_berth(vessel, "chennai", top_k=10)
    target_rank = next((opt.rank for opt in options if opt.berth_code == tc['assigned_berth']), -1)
    status = "OK" if target_rank == 1 else "FAILED"
    res.append(f"[{status}] {tc['name']} ({tc['vessel_type']}) - Expected: {tc['assigned_name']} - Got Rank: {target_rank}")
    
print("\n".join(res))
