import json

# Step 1: Load Aadhaar database
with open("aadhaar_db.json", "r") as file:
    aadhaar_db = json.load(file)

# Step 2: Verification function
def verify_aadhaar(aadhaar_number, dob):
    user = aadhaar_db.get(aadhaar_number)

    if user:
        if user["dob"] == dob:
            return True, user["name"]
        else:
            return False, "DOB does not match"
    else:
        return False, "Aadhaar number not found"

# Step 3: Test the function
if __name__ == "__main__":
    aadhaar_input = input("Enter Aadhaar Number: ")
    dob_input = input("Enter DOB (YYYY-MM-DD): ")

    status, message = verify_aadhaar(aadhaar_input, dob_input)

    if status:
        print("✅ VERIFIED")
        print("Welcome,", message)
    else:
        print("❌ NOT VERIFIED")
        print("Reason:", message)
