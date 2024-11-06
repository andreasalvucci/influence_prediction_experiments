#!/bin/bash
base_folder=$1
target_predicate=$2
unique_report_file="$base_folder/relationship_weights_summary.txt"

# Initialize the unique report file
echo "Relationship Weights Summary" > "$unique_report_file"
echo "=================" >> "$unique_report_file"
echo "Target predicate: $target_predicate" >> "$unique_report_file"
echo "" >> "$unique_report_file"

# Loop through all JSON files in the directory again to append to the unique report
for json_file in "$base_folder"/*.json; do
    # Extract the filename without the path
    filename=$(basename "$json_file")
    
    # Extract model, degree, and experiment number from the filename
    if [[ $filename =~ ^([^.]+)\.d([^.]+)\.exp([^.]+)\.json$ ]]; then
        model="${BASH_REMATCH[1]}"
        degree="${BASH_REMATCH[2]}"
        num_exp="${BASH_REMATCH[3]}"
        
        # Append the relationship weights to the unique report file
        echo "Experiment $num_exp, Model: $model, Degree: $degree" >> "$unique_report_file"
        if jq -r -e '.relationship_weights | to_entries | map("\(.key): \(.value)") | .[]' "$json_file" >> "$unique_report_file"; then
            echo "Relationship weights from $json_file have been added to $unique_report_file"
        else
            echo "Error: Failed to extract relationship weights from $json_file."
        fi
        echo "" >> "$unique_report_file"  # Add a blank line for readability
    else
        echo "Error: Filename $filename does not match the expected format."
    fi
done

echo "Summary report has been created in $unique_report_file"