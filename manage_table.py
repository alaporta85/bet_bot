import sqlite3
def WriteFunction(User, Match, Bet):
    SQL_String = "INSERT INTO MainTable (User,Match,Bet) VALUES ('" + User + "', '" + Match + "', '" + Bet + "' )"
    conn.execute(SQL_String)

conn = sqlite3.connect('C:\\bet_bot.db')

print ("Opened database successfully")

cursor = conn.execute("SELECT * from MainTable")
for row in cursor:
   print ("ID_Scommessa = ", row[0])
   print ("User = ", row[1])
   print ("Match = ", row[2])
   print ("Bet = ", row[3], "\n")

print ("Operation done successfully")
conn.close()
