import requests
import re
from collections import defaultdict

def print_grid_from_google_doc(url):
    """
    Fetches data from a Google Doc URL and prints the character grid.
    
    Args:
        url: String containing the URL of the Google Doc with the input data
    """
    # Fetch the document content
    response = requests.get(url)
    response.raise_for_status()
    content = response.text
    
    # Parse the document to extract character data
    # The document format: table with x-coordinate, character, y-coordinate
    # Example row: "0   █   0"
    
    # Using regex to find all rows with data (skip header)
    pattern = r'(\d+)\s+([^\s\d])\s+(\d+)'
    matches = re.findall(pattern, content)
    
    if not matches:
        print("No data found in the document")
        return
    
    # Store characters by their coordinates
    grid_data = {}
    max_x = 0
    max_y = 0
    
    for match in matches:
        x = int(match[0])
        char = match[1]
        y = int(match[2])
        
        grid_data[(x, y)] = char
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    
    # Print the grid
    # y-coordinate increases downward (row index)
    # x-coordinate increases rightward (column index)
    for y in range(max_y + 1):
        row = []
        for x in range(max_x + 1):
            row.append(grid_data.get((x, y), ' '))
        print(''.join(row))


# Alternative approach if the data is in a different format
def print_grid_from_google_doc_v2(url):
    """
    Alternative parsing method if the data uses a different format.
    """
    response = requests.get(url)
    response.raise_for_status()
    content = response.text
    
    # Find all table-like data in the content
    # Assuming the data is in a simple text format
    lines = content.split('\n')
    
    grid_data = {}
    max_x = 0
    max_y = 0
    
    # Start parsing from the first non-empty line that contains data
    # Skip header lines like "x-coordinate   character   y-coordinate"
    found_header = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to parse the line
        parts = line.split()
        if len(parts) >= 3:
            # Check if first and third parts are numbers
            try:
                x = int(parts[0])
                char = parts[1]
                y = int(parts[2])
                
                grid_data[(x, y)] = char
                max_x = max(max_x, x)
                max_y = max(max_y, y)
            except ValueError:
                # Skip header or non-data lines
                continue
    
    if not grid_data:
        print("No data found in the document")
        return
    
    # Print the grid with correct orientation
    for y in range(max_y + 1):
        row = []
        for x in range(max_x + 1):
            row.append(grid_data.get((x, y), ' '))
        print(''.join(row))


# Example usage
if __name__ == "__main__":
    # Example URL (replace with actual Google Doc URL)
    url = "https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub"
    print_grid_from_google_doc(url)