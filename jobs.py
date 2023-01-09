import config as cfg
import scraping_functions as scrf
import play_update_functions as plupf
import utils as utl
import datetime
import time
import os
import db_functions as dbf


def job_update_score(context):

    """
    Once all matches in the bet are concluded, update the database.
    """

    context.bot.send_message(chat_id=cfg.TESTAZZA_ID, text='Aggiornamento db')

    # Check in database for bets to update
    bets = utl.get_bets_to_update()
    if not bets:
        msg = 'Nessuna scommessa da aggiornare.'
        return context.bot.send_message(chat_id=context.job.context, text=msg)

    # Go to main page
    brow = scrf.open_browser(url=cfg.MAIN_PAGE)

    # Login
    plupf.login(brow)

    # Get budget and update database
    budget = plupf.get_budget_from_website(brow)
    utl.update_budget(budget=budget)

    # Go to most recent bets
    plupf.open_profile_options(brow)
    plupf.open_profile_history(brow)
    plupf.set_time_filter(brow)

    # Update data relative to to each bet
    for bet_id in bets:
        plupf.update_database(brow=brow, bet_id=bet_id)
    brow.quit()

    # Save date and time to keep track of the last update
    dt = datetime.datetime.now()
    hh, mm = str(dt.hour).zfill(2), str(dt.minute).zfill(2)
    msg = f'*Last update:\n\t{dt.day}/{dt.month}/{dt.year} at {hh}:{mm}'
    dbf.db_update(
            table='last_results_update',
            columns=['message'],
            values=[msg],
            where=''
    )

    # Run code to update plot
    os.system('python Classes.py')
    cfg.LOGGER.info('UPDATE - Database aggiornato correttamente.')

    context.bot.send_photo(chat_id=cfg.GROUP_ID,
                   photo=open(f'score_{cfg.YEARS[-1]}.png', 'rb'))


def job_night_quotes(context):

    """
    Fill the db with the new quotes for all leagues.
    """

    context.bot.send_message(chat_id=cfg.TESTAZZA_ID, text='Scaricando quote')

    utl.remove_expired_match_quotes()

    # Start scraping
    t0 = time.time()
    cfg.LOGGER.info('NIGHT_QUOTES - Aggiornando quote...')
    scrf.scrape_all_quotes()
    mins, secs = utl.time_needed(t0)
    cfg.LOGGER.info(f'NIGHT_QUOTES - Tempo totale -> {mins}:{secs}.')

    # Remove match if quotes not present (internet problems)
    utl.remove_matches_without_quotes()

    # Notify about fields in database not found in the webpage
    missing_fields = utl.notify_inactive_fields()
    if missing_fields:
        return context.bot.send_message(chat_id=cfg.TESTAZZA_ID,
                                        text=missing_fields)
