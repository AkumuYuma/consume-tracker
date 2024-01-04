import sqlite3

# Helper function to get the active fuel bag ID
def get_active_bag_id():
    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT Id FROM FuelBags WHERE IsFinished = 0')
    active_bag = cursor.fetchone()
    conn.close()
    return active_bag[-1] if active_bag else None

# Helper function to update FuelBags table
def update_fuel_bag(active_bag_id, power, fan, time):
    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE FuelBags
        SET MeanPower = (MeanPower * Time + ?) / (Time + ?),
            MeanFan = (MeanFan * Time + ?) / (Time + ?),
            Time = Time + ?
        WHERE Id = ?
    ''', (power, time, fan, time, time, active_bag_id))
    conn.commit()
    conn.close()

# Helper function to start a new fuel bag
def start_new_bag():
    conn = sqlite3.connect('heater_consumption.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO FuelBags (IsFinished, MeanPower, MeanFan, Time) VALUES (0, 0, 0, 0)')
    conn.commit()
    conn.close()
    