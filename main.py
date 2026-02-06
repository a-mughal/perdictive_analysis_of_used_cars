import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.tree import DecisionTreeClassifier, plot_tree

# Load dataset
database = pd.read_csv("cars.csv")  # replace with your dataset path

# Quick overview
print("Initial dataset shape:", database.shape)
print(database.info())
print(database.head())
# Check missing values
missing_values = database.isnull().sum()
print("Missing values per column:\n", missing_values)

# Check data types
print(database.dtypes)

# Inspect 'milage' and 'price' formats
print(database[['milage', 'price']].head(10))

# Check basic statistics for numeric columns
print(database.describe(include='all'))
# Backup original price column
database['price_original'] = database['price']

# Clean 'price': remove $ and commas, convert to numeric
database['price'] = database['price'].astype(str).str.replace(r'[\$,]', '', regex=True)
database['price'] = pd.to_numeric(database['price'], errors='coerce')

# Clean 'milage': remove non-numeric characters, convert to numeric
database['milage'] = database['milage'].astype(str).str.replace(r'[^0-9.]', '', regex=True)
database['milage'] = pd.to_numeric(database['milage'], errors='coerce')

print(database[['price_original', 'price', 'milage']].head(10))
print(database.info())
print(database.head())
# Fill missing categorical values with 'Unknown'
categorical_cols = database.select_dtypes(include='object').columns
database[categorical_cols] = database[categorical_cols].fillna('Unknown')

# Fill missing numerical values (except price) with median
numerical_cols = database.select_dtypes(include=['int64', 'float64']).columns.drop('price')
for col in numerical_cols:
    database[col] = database[col].fillna(database[col].median())

# Check missing values after cleaning
print(database.isnull().sum())
# Remove negative milage
database = database[database['milage'] >= 0]

# Remove future model years
current_year = 2025
database = database[database['model_year'] <= current_year]

# Optional: negative prices → set as NaN
database.loc[database['price'] < 0, 'price'] = np.nan
duplicates = database.duplicated().sum()
print("Duplicate rows:", duplicates)

database = database.drop_duplicates()
#EDA

# Set style for plots
sns.set(style="whitegrid")
plt.rcParams["figure.figsize"] = (10,6)
plt.figure()
sns.histplot(database['price'], bins=30, kde=True, color='skyblue')
plt.title('Distribution of Selling Price')
plt.xlabel('Price ($)')
plt.ylabel('Count')
plt.show()
plt.figure()
sns.scatterplot(data=database, x='milage', y='price', alpha=0.5)
plt.title('Mileage vs Selling Price')
plt.xlabel('Mileage (miles)')
plt.ylabel('Price ($)')
plt.show()


# Calculate average price per fuel type
avg_price_fuel = database.groupby('fuel_type')['price'].mean().sort_values(ascending=False)

# Plot bar chart
plt.figure(figsize=(8,5))
sns.barplot(x=avg_price_fuel.index, y=avg_price_fuel.values, palette='pastel')
plt.title('Average Selling Price by Fuel Type')
plt.xlabel('Fuel Type')
plt.ylabel('Average Price ($)')
plt.xticks(rotation=45)
plt.show()
# Exclude 'Unknown' transmission values for clarity
transmission_data = database[database['transmission'] != 'Unknown']

# Calculate average price per transmission type
avg_price_trans = transmission_data.groupby('transmission')['price'].mean().sort_values(ascending=False)

# Plot colorful bar chart
plt.figure(figsize=(10,6))
sns.barplot(x=avg_price_trans.index, y=avg_price_trans.values, palette='Spectral')
plt.title('Average Selling Price by Transmission Type', fontsize=16)
plt.xlabel('Transmission Type', fontsize=12)
plt.ylabel('Average Price ($)', fontsize=12)
plt.xticks(rotation=45)
plt.show()
top_brands = database['brand'].value_counts().nlargest(10).index
avg_prices = database.groupby('brand')['price'].mean().loc[top_brands].sort_values(ascending=False)

plt.figure()
sns.barplot(x=avg_prices.values, y=avg_prices.index, palette='viridis')
plt.title('Top 10 Most Common Car Brands and Average Resale Price')
plt.xlabel('Average Price ($)')
plt.ylabel('Brand')
plt.show()


# Create binary target based on median price
median_price = database['price'].median()
database['high_value'] = (database['price'] > median_price).astype(int)

print(f"Median price: ${median_price}")
print(database[['price', 'high_value']].head(10))
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
# Train Logistic Regression
model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

# Evaluate model
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.2f}")

print("Classification Report:\n", classification_report(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
# Feature importance
importance = pd.DataFrame({
    'feature': X.columns,
    'coefficient': model.coef_[0]
}).sort_values(by='coefficient', key=abs, ascending=False)

print("Feature Importance:\n", importance)



dt_model = DecisionTreeClassifier(max_depth=5, random_state=42)
dt_model.fit(X_train, y_train)


y_pred_dt = dt_model.predict(X_test)


accuracy_dt = accuracy_score(y_test, y_pred_dt)
print(f"Decision Tree Accuracy: {accuracy_dt:.2f}")

print("Classification Report:\n", classification_report(y_test, y_pred_dt))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred_dt))


plt.figure(figsize=(20,10))
plot_tree(
    dt_model, 
    feature_names=X.columns, 
    class_names=["Low Value", "High Value"], 
    filled=True, 
    rounded=True,
    fontsize=12
)
plt.show()
# Feature importance
dt_importance = pd.DataFrame({
    "feature": X.columns,
    "importance": dt_model.feature_importances_
}).sort_values(by="importance", ascending=False)

print("Decision Tree Feature Importance:\n", dt_importance)