#!/bin/bash

# Run the update CSV script without timeout
echo "Starting CSV update process..."
python update_csv_to_current.py

# Check if the script completed successfully
if [ $? -eq 0 ]; then
  echo "CSV update completed successfully."
else
  echo "CSV update failed with exit code $?."
fi

echo "Done."