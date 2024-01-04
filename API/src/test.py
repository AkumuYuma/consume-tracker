from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from utilities import *

app = Flask(__name__)

# Database initialization
conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
cursor = conn.cursor()

# Create FuelBags table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS FuelBags (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        IsFinished BOOLEAN,
        MeanPower INTEGER,
        MeanFan INTEGER,
        Time INTEGER
    )
''')

# Create CurrentBagData table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS CurrentBagData (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Power INTEGER,
        Fan INTEGER,
        StartingTime TEXT,
        ElapsedTime TEXT,
        FuelBagId INTEGER,
        FOREIGN KEY (FuelBagId) REFERENCES FuelBags(Id)
    )
''')

# Close the connection after initializing tables
conn.close()

# Routes
@app.route('/add_record', methods=['POST'])
def add_record():
    data = request.get_json()
    power = data['Power']
    fan = data['Fan']
    time = data['Time']

    active_bag_id = get_active_bag_id()

    if not active_bag_id:
        start_new_bag()

    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO CurrentBagData (Power, Fan, StartingTime, FuelBagId)
        VALUES (?, ?, ?, ?)
    ''', (power, fan, time, active_bag_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Record added successfully"}), 200

@app.route('/start_recording', methods=['POST'])
def start_recording():
    data = request.get_json()
    power = data['Power']
    fan = data['Fan']

    active_bag_id = get_active_bag_id()
    if active_bag_id:
        return jsonify({"error": "Recording is already in progress"}), 400

    start_new_bag()
    active_bag_id = get_active_bag_id()

    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO CurrentBagData (Power, Fan, StartingTime, ElapsedTime, FuelBagId) 
                   VALUES (?, ?, time('now', 'localtime'), 0, ?)
                   """, (power, fan, active_bag_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Recording started successfully"}), 200

@app.route('/update_recording', methods=['POST'])
def update_recording():
    data = request.get_json()
    power = data['Power']
    fan = data['Fan']

    active_bag_id = get_active_bag_id()

    if not active_bag_id:
        return jsonify({"error": "No active recording to update"}), 400

    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE CurrentBagData
                   SET ElapsedTime = time('now', 'localtime') - time(selected.StartingTime)
                   FROM (SELECT StartingTime FROM CurrentBagData WHERE FuelBagId = ? ORDER BY Id DESC LIMIT 1) AS selected
                   """, (active_bag_id,))

    cursor.execute("""
                   INSERT INTO CurrentBagData (Power, Fan, StartingTime, ElapsedTime, FuelBagId) 
                   VALUES (?, ?, time('now', 'localtime'), 0, ?)
                   """, (power, fan, active_bag_id))
    conn.commit()

    # update_fuel_bag(active_bag_id, power, fan, elapsed_time)

    conn.close()

    return jsonify({"message": "Recording updated successfully"}), 200

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    active_bag_id = get_active_bag_id()

    if not active_bag_id:
        return jsonify({"error": "No active recording to stop"}), 400

    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('SELECT Time FROM CurrentBagData WHERE FuelBagId = ? ORDER BY Id DESC LIMIT 1', (active_bag_id,))
    start_time = cursor.fetchone()[0]

    current_time = datetime.now()
    elapsed_time = (current_time - start_time).seconds

    cursor.execute('INSERT INTO CurrentBagData (Power, Fan, Time, FuelBagId) VALUES (0, 0, elapsed_time, ?)', (active_bag_id,))
    conn.commit()

    update_fuel_bag(active_bag_id, 0, 0, elapsed_time)

    conn.close()

    return jsonify({"message": "Recording stopped successfully"}), 200

@app.route('/start_new_bag', methods=['POST'])
def start_new_bag_route():
    active_bag_id = get_active_bag_id()

    if not active_bag_id:
        return jsonify({"error": "No active recording to start a new bag"}), 400

    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('UPDATE FuelBags SET IsFinished = 1 WHERE Id = ?', (active_bag_id,))
    conn.commit()

    start_new_bag()

    conn.close()

    return jsonify({"message": "New bag started successfully"}), 200

@app.route('/fuel_bags', methods=['GET'])
def get_fuel_bags():
    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM FuelBags')
    fuel_bags = cursor.fetchall()
    conn.close()

    fuel_bags_data = []
    for bag in fuel_bags:
        fuel_bags_data.append({
            'Id': bag[0],
            'IsFinished': bool(bag[1]),
            'MeanPower': bag[2],
            'MeanFan': bag[3],
            'Time': bag[4]
        })

    return jsonify({"FuelBags": fuel_bags_data})

# New route to print the content of CurrentBagData table
@app.route('/current_bag_data', methods=['GET'])
def get_current_bag_data():
    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM CurrentBagData')
    current_bag_data = cursor.fetchall()
    conn.close()

    current_bag_data_list = []
    for record in current_bag_data:
        current_bag_data_list.append({
            'Id': record[0],
            'Power': record[1],
            'Fan': record[2],
            'StartingTime': record[3],
            'ElapsedTime': record[4],
            'FuelBagId': record[5]
        })

    return jsonify({"CurrentBagData": current_bag_data_list})

if __name__ == '__main__':
    app.run(debug=True)