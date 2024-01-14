import sqlite3

class Database:
    def __init__(self):
        self.connection = sqlite3.connect("database.db")
        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()

    def _create_tables(self):
        """
        Create tables for the first time.
        Ensures that tables will always exist, even if someone deletes database file, it will be recreated (though data will be lost).
        """

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Constituency (
                constituency_id INTEGER PRIMARY KEY,
                constituency_name TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Party (
                party_id INTEGER PRIMARY KEY,
                party TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS UVC_Code (
                UVC TEXT PRIMARY KEY,
                used INTEGER
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Candidate (
                canid INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate TEXT,
                party_id INTEGER,
                constituency_id INTEGER,
                vote_count INTEGER,
                FOREIGN KEY (party_id) REFERENCES Party (party_id),
                FOREIGN KEY (constituency_id) REFERENCES Constituency (constituency_id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Voter (
                voter_id TEXT PRIMARY KEY,
                full_name TEXT,
                DOB DATE,
                password TEXT,
                UVC TEXT,
                constituency_id INTEGER,
                FOREIGN KEY (constituency_id) REFERENCES Constituency (constituency_id)
            )
        """)

        self.cursor.connection.commit()

    def _populate_uvc_codes(self):
        """
        Will only run if the table is empty, on first run, basically.
        Populates the UVC_Code table with codes from UVCS.txt.
        """

        self.cursor.execute("SELECT COUNT(*) FROM UVC_Code")
        count = self.cursor.fetchone()[0]

        # If table empty...
        if count == 0:
            with open("UVCs.txt", "r") as file:
                uvc_list = [line.strip() for line in file]

            # Insert UVCs into the UVC_Code table
            self.cursor.executemany("INSERT INTO UVC_Code (UVC, used) VALUES (?, 0)", [(uvc,) for uvc in uvc_list])

            # Commit changes
            self.cursor.connection.commit()

    def get_login(self, email):
        """
        Return the password assigned to the email, if it exists.
        Otherwise, return None.
        """

        self.cursor.execute("SELECT password FROM Voter WHERE voter_id = ?", (email,))
        result = self.cursor.fetchone()

        if result:
            return result[0]
        else:
            return None

    def is_email_registered(self, email):
        """
        Check if the given email is already registered.
        If email is registered, return True. Otherwise, return False.
        """

        self.cursor.execute("SELECT COUNT(*) FROM Voter WHERE voter_id = ?", (email,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def is_uvc_valid(self, uvc):
        """
        Check if the given UVC is valid and not used.
        If the UVC is valid, return True. Otherwise, return False.
        """

        self.cursor.execute("SELECT COUNT(*) FROM UVC_Code WHERE UVC = ? AND used = 0", (uvc,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def register_voter(self, email, full_name, dob, password, uvc, constituency_id):
        """
        Register a new voter and return the voter_id.
        Otherwise, return None.
        """
        
        try:
            self.cursor.execute("""
                INSERT INTO Voter (voter_id, full_name, DOB, password, UVC, constituency_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email, full_name, dob, password, uvc, constituency_id))

            # Mark UVC as used
            self.cursor.execute("UPDATE UVC_Code SET used = 1 WHERE UVC = ?", (uvc,))

            self.cursor.connection.commit()

            return email  # Returning email as voter_id for simplicity
        except Exception as e:
            print(f"Error during voter registration: {e}")
            return None
