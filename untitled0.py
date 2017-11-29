db, c = start_db()
count = 0
for i in range(1, 102):

    field_name = list(c.execute('''select field_name from fields where
                                field_id = ?''', (i,)))[0][0]
    field_value = list(c.execute('''select field_value from fields where
                                 field_id = ?''', (i,)))[0][0]
    all_alias = list(c.execute('''select field_alias_name from fields_alias
                               where field_alias_field = ?''', (i,)))
    all_alias = [a[0] for a in all_alias]
    count += len(all_alias)
    
    print('Field name is: {}'.format(field_name))
    print('Field value is: {}\n'.format(field_value))
    for x in all_alias:
        print(x)