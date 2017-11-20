empty_table('fields_alias')
db, c = start_db()

for i in fields_list:
    name = i[0]
    value = i[1]
    field_id = list(c.execute('''select field_id from fields where
                              field_name = ? and field_value = ? ''', (name,
                              value)))
    field_id = field_id[0][0]
    alias_list = i[2].split(', ')
    for alias in alias_list:
        new_alias = alias.replace('[', '')
        new_alias = new_alias.replace(']', '')
        c.execute('''insert into fields_alias (field_alias_field,
                                               field_alias_name)
        values (?, ?)''', (field_id, new_alias))

db.commit()
db.close()

#%%
import pickle

f = open('/Users/andrea/Desktop/bet_bot/main_leagues_teams_lotto.pckl', 'rb')
all_teams = pickle.load(f)
f.close()

db, c = start_db()
for league in all_teams:
    league_id = list(c.execute('''select league_id from leagues where
                              league_name = ? ''', (league,)))
    league_id = league_id[0][0]

    for team in all_teams[league]:
        c.execute('''insert into teams (team_league, team_name)
        values (?, ?)''', (league_id, team))

db.commit()
db.close()

#%%

db, c = start_db()
for i in bbb:
    team_id = i[0]
    alias_list = i[3]
    for x in alias_list:
        c.execute('''insert into teams_alias (team_alias_team, team_alias_name)
        values (?, ?)''', (team_id, x))

db.commit()
db.close()

























