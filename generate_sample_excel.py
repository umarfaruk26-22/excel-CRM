import pandas as pd
import os
from pathlib import Path

# Create a realistic sample Excel file
data = {
    "Client Name": [
        "Aarav Sharma", 
        "Priya Patel", 
        "Rohan Gupta", 
        "Ananya Iyer", 
        "Vikram Singh",
        "Kavita Reddy",
        "Suresh Nair",
        "Deepak Verma",
        "Pooja Deshmukh",
        "Amitabh Mukherjee",
        "" # Blank name to test rejection & error report!
    ],
    "Contact No": [
        "+91 98765 43210",
        "9823456789",
        "09123456780",
        "9811122233",
        "9988776655",
        "9876501234",
        "9765432109",
        "9845012345",
        "9833012345",
        "9822012345",
        "9999999999"
    ],
    "Email ID": [
        "aarav@sharmatraders.in",
        "priya.patel@pateltextiles.com",
        "rohan@guptaenterprises.com",
        "ananya@iyerconsulting.com",
        "vikram@singhlogistics.in",
        "kavita@reddypharma.com",
        "suresh@nairindustries.com",
        "deepak@vermahardware.com",
        "pooja@deshmukhdesigns.in",
        "amitabh@mukherjeetech.com",
        "invalid@test.com"
    ],
    "Business Firm": [
        "Sharma Traders",
        "Patel Textiles",
        "Gupta Enterprises",
        "Iyer Consulting",
        "Singh Logistics",
        "Reddy Pharma",
        "Nair Industries",
        "Verma Hardware",
        "Deshmukh Designs",
        "Mukherjee Tech",
        "Ghost Corp"
    ],
    "City": [
        "Mumbai",
        "Ahmedabad",
        "Delhi",
        "Chennai",
        "Jaipur",
        "Hyderabad",
        "Kochi",
        "Bengaluru",
        "Pune",
        "Kolkata",
        "Unknown"
    ],
    "Product Interest": [
        "Enterprise CRM",
        "Wholesale Leather",
        "Cloud Hosting",
        "Accounting Software",
        "Fleet Tracking",
        "API Integration",
        "Hardware Terminals",
        "Data Migration",
        "Custom Website",
        "ERP Solution",
        "None"
    ],
    "GST Number": [
        "27AABCU9603R1ZM",
        "24AAACP1234M1Z2",
        "07AAAAA0000A1Z5",
        "33AAACI5678P1Z8",
        "08AAACS9999L1Z1",
        "36AAACR4444K1Z3",
        "32AAACN2222J1Z6",
        "29AAACV1111H1Z9",
        "27AAACD7777F1Z4",
        "19AAACM3333E1Z7",
        "BLANK"
    ]
}

df = pd.DataFrame(data)
os.makedirs("test_samples", exist_ok=True)
sample_path = "test_samples/sample_customers_batch1.xlsx"
df.to_excel(sample_path, index=False)
print(f"Sample test file generated at: {sample_path}")
