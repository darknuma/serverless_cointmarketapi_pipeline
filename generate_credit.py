import pandas as pd
import numpy as np

np.random.seed(42)  # reproducibility

n = 500

data = pd.DataFrame({
    "Age": np.random.randint(18, 35, size=n),
    "Gender": np.random.choice([0, 1], size=n),  # 0 = male, 1 = female
    "Education_Years": np.random.normal(10, 2, size=n).clip(0, 18).astype(int),
    "Household_Size": np.random.randint(2, 10, size=n),
    "Farming_Experience": np.random.randint(0, 10, size=n),
    "Farm_Size": np.random.normal(2, 1, size=n).clip(0.5, 10).round(2),
    "Loan_Amount": np.random.randint(50000, 500000, size=n),
    "Distance_To_Bank": np.random.normal(10, 5, size=n).clip(1, 30),
    "Loan_Supervision": np.random.poisson(2, size=n),
    "Disbursement_Lag": np.random.randint(1, 6, size=n),
    "Farm_Income": np.random.randint(10000, 300000, size=n),
    "Loan_Diversion": np.random.choice([0, 0.1, 0.2, 0.3], size=n, p=[0.7, 0.15, 0.1, 0.05]),
    "Interest_Rate": np.random.normal(10, 2, size=n).clip(5, 20),
})

# Define repayment based on weighted conditions
data["Loan_Repaid"] = (data["Loan_Amount"] * (1 - data["Loan_Diversion"]) * 
                      (data["Farm_Income"] / data["Loan_Amount"]) * 
                      np.where(data["Disbursement_Lag"] <= 3, 1, 0.8)
                     ).clip(0, data["Loan_Amount"]).astype(int)

# Binary label
data["Credit_Worthy"] = (data["Loan_Repaid"] / data["Loan_Amount"] >= 0.5).astype(int)

data.head()
