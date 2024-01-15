import sqlite3
import argon2

class Database:
    def __init__(self, database_file="database.db"):
        self.connection = sqlite3.connect(database_file)
        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()

    def _create_tables(self):
        """
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
                selected_candidate_id INTEGER,
                FOREIGN KEY (constituency_id) REFERENCES Constituency (constituency_id),
                FOREIGN KEY (selected_candidate_id) REFERENCES Candidate (canid)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Commissioner (
                commissioner_id TEXT PRIMARY KEY,
                password TEXT
            )
        """)

        self.cursor.connection.commit()

    def _populate_uvc_codes(self):
        """
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

    def _populate_other_tables(self):

        self.cursor.execute("SELECT COUNT(*) FROM Constituency")
        count = self.cursor.fetchone()[0]

        # If table empty...
        if count == 0:
            self.cursor.executemany("""
                INSERT INTO Constituency (constituency_name) VALUES (?)
                """, [
                ('Shangri-la-Town',),
                ('Northern-Kunlun-Mountain',),
                ('Western-Shangri-la',),
                ('Naboo-Vallery',),
                ('New-Felucia',)
            ])

            self.cursor.executemany("""
                INSERT INTO Party (party) VALUES (?)
                """, [
                ('Blue Party',),
                ('Red Party',),
                ('Yellow Party',),
                ('Independent',)
            ])

            self.cursor.execute("""
                INSERT INTO Candidate (candidate, party_id, constituency_id, vote_count)
                VALUES (?, ?, ?, ?)
                """, ('Candidate 1', 2, 1, 0))

            hashed_password = argon2.hash_password("shangrila2024$".encode())
            self.cursor.execute("""
                INSERT INTO Commissioner (commissioner_id, password)
                VALUES (?, ?)
                """, ("election@shangrila.gov.sr", hashed_password))

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

    def get_commissioner_login(self, email):
        """
        Return the password assigned to the commissioner email, if it exists.
        Otherwise, return None.
        """
        self.cursor.execute("SELECT password FROM Commissioner WHERE commissioner_id = ?", (email,))
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
        return bool(count > 0)

    def is_uvc_valid(self, uvc):
        """
        Check if the given UVC is valid and not used.
        If the UVC is valid, return True. Otherwise, return False.
        """

        self.cursor.execute("SELECT COUNT(*) FROM UVC_Code WHERE UVC = ? AND used = 0", (uvc,))
        count = self.cursor.fetchone()[0]
        return bool(count > 0)

    def register_voter(self, email, full_name, dob, password, uvc, constituency_id):
        """
        Register a new voter and return the voter_id/email.
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
            return email
        
        except Exception as e:
            print(f"Error during voter registration: {e}")
            return None

    def get_constituency_results(self, constituency_name):
        """
        Get election results for a specific constituency and return as a dictionary.
        If no results are available, return None.
        """
        self.cursor.execute("""
            SELECT Candidate.candidate, Party.party, Candidate.vote_count
            FROM Candidate
            JOIN Party ON Candidate.party_id = Party.party_id
            JOIN Constituency ON Candidate.constituency_id = Constituency.constituency_id
            WHERE Constituency.constituency_name = ?
        """, (constituency_name,))

        results = self.cursor.fetchall()

        if results:
            return results
        else:
            return None
    
    def get_seats_by_party(self):
        """
        Get the count of seats won by each party.
        Returns a list of dictionaries containing each parties seat count.
        """
        self.cursor.execute("""
            SELECT Party.party, COUNT(Candidate.canid) as seat
            FROM Candidate
            JOIN Party ON Candidate.party_id = Party.party_id
            GROUP BY Party.party
        """)

        seats_results = self.cursor.fetchall()
        return [{"party": result[0], "seat": result[1]} for result in seats_results]

    def has_voter_voted(self, email):
        """
        Check if the voter has already voted.
        Returns True or False.
        """
        self.cursor.execute("SELECT selected_candidate_id FROM Voter WHERE voter_id = ?", (email,))
        result = self.cursor.fetchone()

        return result is not None and result[0] is not None

    def cast_vote(self, email, candidate_id):
        """
        Cast the vote for the specified candidate.
        Returns True or None depending on whether the vote was successful.
        """
        try:
            self.cursor.execute("UPDATE Voter SET selected_candidate_id = ? WHERE voter_id = ?", (candidate_id, email))
            self.cursor.execute("UPDATE Candidate SET vote_count = vote_count + 1 WHERE canid = ?", (candidate_id,))

            self.cursor.connection.commit()
            return True
        
        except Exception as e:
            print(f"Error during vote submission: {e}")
            return False

    def get_all_candidates(self):
        """
        Fetch all candidates with their ids, names, parties, and constituency ids.
        Returns a list of dictionaries containing candidate id, name, party, and constituency id.
        """
        self.cursor.execute("SELECT Candidate.canid, Candidate.candidate, Party.party, Candidate.constituency_id FROM Candidate JOIN Party ON Candidate.party_id = Party.party_id")
        candidates = self.cursor.fetchall()
        return [{"id": candidate[0], "name": candidate[1], "party": candidate[2], "constituency_id": candidate[3]} for candidate in candidates]

    def get_constituencies(self):
        """
        Get all constituencies and return as a list of dictionaries.
        """
        self.cursor.execute("SELECT constituency_id, constituency_name FROM Constituency")
        constituencies = self.cursor.fetchall()

        return [{"constituency_id": constituency[0], "constituency_name": constituency[1]} for constituency in constituencies]
    
    def get_voter_constituency(self, voter_id):
        self.cursor.execute("SELECT constituency_id FROM Voter WHERE voter_id = ?", (voter_id,))
        result = self.cursor.fetchone()

        if result:
            return result[0]
        else:
            return None