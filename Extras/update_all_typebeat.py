import sqlite3
from beatstars_config import Management

def update_all_typebeat_uploaded():
    # Connect to the database
    conn = sqlite3.connect(Management.database_path_beats)
    cursor = conn.cursor()

    try:
        # Update all records
        cursor.execute('UPDATE beats SET typebeat_uploaded = 1')
        
        # Commit the changes
        conn.commit()
        
        # Get the number of updated rows
        updated_rows = cursor.rowcount
        
        print(f"Successfully updated {updated_rows} beats. All beats are now marked as uploaded to Typebeat.")
    
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the connection
        conn.close()

if __name__ == "__main__":
    print("This script will set all beats' 'typebeat_uploaded' status to True (1).")
    confirmation = input("Are you sure you want to proceed? (yes/no): ").lower()
    
    if confirmation == 'yes':
        update_all_typebeat_uploaded()
    else:
        print("Operation cancelled.")