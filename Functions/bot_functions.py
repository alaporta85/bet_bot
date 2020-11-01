import db_functions as dbf


def check_if_input_is_correct(user_input):    # DONE

	# Warning message if amount is missing
	if not user_input:
		return 'Insert the amount. Ex: /play 5'

	# Check that input is an integer number >= 2
	try:
		euros = int(user_input[0])
		if euros < 2:
			return 'Minimum amount is 2 Euros.'
		else:
			return euros

	except ValueError:
		return 'Amount has to be integer.'


def one_or_more_preds_are_not_confirmed():   # DONE

	not_conf_list = dbf.db_select(
			table='predictions',
			columns_in=['pred_user', 'pred_team1', 'pred_team2', 'pred_rawbet',
			            'pred_quote'],
			where='pred_status = "Not Confirmed"')

	if not_conf_list:
		message = 'There are still Not Confirmed bets:'

		for user, team1, team2, bet, quote in not_conf_list:
			message += '\n\n<b>{}</b>: {} - {}  {} <b>@{}</b>'.format(
					user, team1, team2, bet, quote)

		return message + '\n\n/confirm or /cancel and then play again.'

	else:
		return None
