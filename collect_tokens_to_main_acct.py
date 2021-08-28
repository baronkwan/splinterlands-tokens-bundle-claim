from beem.steem import Steem
import beemgraphenebase.ecdsasig
from binascii import hexlify
import time
import json
import requests
import sys
import os

nodes = ['https://anyx.io/', 'https://api.hive.blog',
         "https://api.deathwing.me"]


class HiveRequests:
    def __init__(self, priv_posting_key, priv_active_key):
        self.s = Steem(node=nodes[2], keys=[priv_posting_key, priv_active_key])
        self.s.chain_params['chain_id'] = 'beeab0de00000000000000000000000000000000000000000000000000000000'

    def sm_token_transfer(self, token, sender, receiver, qty, type="withdraw"):
        """
          sm_token_transfer
          param str token: splinterlands token name
          param str sender: splinterlands player name who send token
          param str receiver: splinterlands player name who will receive token
          param str memo: splinterlands player name who will receive token
          param float qty: splinterlands token quantity to be sent
          param str type(default withdraw): transfer type
        """
        json_data = {
            "to": receiver,
            "qty": float(qty),
            "token": token,
            "type": type,
            "memo": receiver,
            "app": "splinterlands/0.7.130"
        }

        tx = self.s.custom_json('sm_token_transfer',
                                json_data, required_auths=[sender])
        print('')
        print(f"Success! trx_id: {tx['trx_id']}")
        return tx


def exception_error_formatter():
    """Exception error formatter"""
    exc_type, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, ' | ', fname, ' | ', exc_tb.tb_lineno)


def sps_claim(account_name, wif):
    """
      sps_claim: claim sps airdrop token from splinterlands api
      params str account_name: splinterlands player account name
      params str wif: hive wallet private posting key
    """
    timestamp = int(time.time()*1000)
    message_to_sign = "hive"+account_name+str(timestamp)
    signature_bytestring = beemgraphenebase.ecdsasig.sign_message(
        message_to_sign, wif)
    signature = hexlify(signature_bytestring).decode("ascii")

    base_url = "https://ec-api.splinterlands.com/players/claim_sps_airdrop"
    query_str = f"?platform=hive&address=\{account_name}\
              &sig={signature}\&username={account_name}&ts={timestamp}"
    claim_url = base_url + query_str
    r = requests.get(claim_url)
    return r.json()


def get_token_bal(account_name, token) -> float:
    """
      get_token_bal: get specific splinterlands token balance of a single account
      param str account_name: splinterlands player account name
      param str token: splinterlands token name
    """
    r = requests.get(f'https://api.splinterlands.io/players/balances\
                    ?username={account_name}')
    for i in r.json():
        if i['token'] == token:
            bal = float(i['balance'])
            print(f'{token} balance: {bal}')
            return bal


def collect_tokens_to_main_acct(main_acct):
    # Read credentials from credentials.json file under the same directory
    with open('credentials.json', 'r') as file:
        credentials = json.loads(file.read())

    total_sps_collected = 0
    total_dec_collected = 0

    for i in credentials['accounts']:
        print('')
        print('='*10)
        print(f'Checking account: {i["account_name"]}\n')
        # instantiate for account HiveRequests object for on chain actions
        r = HiveRequests(i['priv_posting_key'], i['priv_active_key'])
        # Connect to splinterlands api to perform sps claim action
        json_data = sps_claim(i['account_name'], i['priv_posting_key'])

        if 'success' in json_data:
            print('SPS claimed successfully.')
        elif 'error' in json_data:
            print(json_data['error'])

        # sleep for chain action to be broadcasted after the api call
        time.sleep(3)

        if i['account_name'] != main_acct:
            try:
                # Get SPS token balance
                sps_token_bal = get_token_bal(i['account_name'], 'SPS') - 0.001
                # Get DEC token balance
                dec_token_bal = get_token_bal(i['account_name'], 'DEC') - 0.001

                # Check SPS balance before transfer
                if sps_token_bal > 0.001:
                    r.sm_token_transfer(
                        "SPS", i['account_name'], main_acct, sps_token_bal)
                    total_sps_collected += sps_token_bal

                # Check DEC balance before transfer
                if dec_token_bal > 0.001:
                    r.sm_token_transfer(
                        "DEC", i['account_name'], main_acct, dec_token_bal)
                    total_dec_collected += dec_token_bal
            except Exception:
                exception_error_formatter()
        else:
            continue

    print('')
    print('='*10)
    print(f'Total SPS collected to main account: {total_sps_collected}')
    print(f'Total DEC collected to main account: {total_dec_collected}')


if __name__ == "__main__":
    start = time.time()
    # Collect all DEC & SPS tokens from subaccount to main account
    collect_tokens_to_main_acct('INSERT_UR_MAIN_SPL_ACCT')
    end = time.time()
    time_consumed = end - start
    print('='*10)
    print(f'\nTime used: {time_consumed:.2f} seconds.')
