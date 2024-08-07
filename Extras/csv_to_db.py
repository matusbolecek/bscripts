import csv
from beat_management import BeatManager, Beat

def convert_csv_to_database(csv_file='excel.csv', db_name='beats.db'):
    manager = BeatManager(db_name)
    
    with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        # Print column names
        print("CSV columns:", reader.fieldnames)
        
        for row in reader:
            # Process collaborators
            if row['Collaborators'] == '-':
                collaborators = 'Matejcikbeats'
            else:
                collaborators = row['Collaborators']

            # Process pack
            pack = row['In pack'] if row['In pack'] != '0' else None

            # Create Beat object
            beat = Beat(
                name=row['Name'],
                key=row['Key'],
                tempo=int(row['BPM']),
                collaborators=collaborators,
                link=row['Link'],
                pack=pack
            )
            
            # Add beat to database
            manager.add_beat(beat)
    
    print(f"Data imported successfully into {db_name}")
    manager.close()

# Run the conversion
convert_csv_to_database()