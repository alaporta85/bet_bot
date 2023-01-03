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

    bets = utl.get_bets_to_update()
    if not bets:
        msg = 'Nessuna scommessa da aggiornare.'
        return context.bot.send_message(chat_id=context.job.context, text=msg)

    # Go to main page
    brow = scrf.open_browser()
    brow.get(cfg.MAIN_PAGE)
    time.sleep(5)
    brow.refresh()
    time.sleep(5)

    # Login
    plupf.login(brow)

    budget = plupf.get_budget_from_website(brow)
    utl.update_budget(budget=budget)

    plupf.open_profile_options(brow)

    plupf.open_profile_history(brow)

    plupf.set_time_filter(brow)

    plupf.show_bets_history(brow)

    plupf.update_database(brow, bets)

    brow.quit()

    dt = datetime.datetime.now()
    last_update = (f'*Last update:\n   {dt.day}/{dt.month}/{dt.year} ' +
                   f'at {dt.hour}:{dt.minute}')
    dbf.db_update(table='last_results_update',
                  columns=['message'],
                  values=[last_update],
                  where='')

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

    missing_fields = utl.notify_inactive_fields()
    if missing_fields:
        return context.bot.send_message(chat_id=cfg.TESTAZZA_ID,
                                        text=missing_fields)
