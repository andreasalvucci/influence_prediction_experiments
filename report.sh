#!/bin/bash
base_folder=$1
target_predicate=$2
unique_report_file="$base_folder/relationship_weights_summary.txt"

# Initialize the unique report file
echo "Relationship Weights Summary" > "$unique_report_file"
echo "=================" >> "$unique_report_file"
echo "Target predicate: $target_predicate" >> "$unique_report_file"
echo "" >> "$unique_report_file"

# Loop through all JSON files in the directory to append to the unique report
for json_file in "$base_folder"/*.json; do
    # Extract the filename without the path
    filename=$(basename "$json_file")
    
    # Extract model, degree, and experiment number from the filename
    if [[ $filename =~ ^([^.]+)\.d([^.]+)\.exp([^.]+)\.json$ ]]; then
        model="${BASH_REMATCH[1]}"
        degree="${BASH_REMATCH[2]}"
        num_exp="${BASH_REMATCH[3]}"
        
        # Append the experiment details
        echo "Experiment $num_exp, Model: $model, Degree: $degree" >> "$unique_report_file"
        
        # Use Python to extract and format relationship weights
        python3 - <<EOF >> "$unique_report_file"
import json

# Open the JSON file
with open("$json_file") as f:
    data = json.load(f)

# Extract relationship weights and format them
if "relationship_weights" in data:
    for key, value in data["relationship_weights"].items():
        print(f"{key}: {value}")
else:
    print("Error: 'relationship_weights' not found in $json_file")
EOF

        echo "" >> "$unique_report_file"  # Add a blank line for readability
    else
        echo "Error: Filename $filename does not match the expected format."
    fi
done

echo "Summary report has been created in $unique_report_file"
