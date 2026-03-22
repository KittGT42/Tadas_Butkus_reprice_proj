from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging

SERVICE_ACCOUNT_FILE = 'repricing-script-cc0b31b89288.json'
spreadsheet_id = '1wanAhRTdbGvF8IN3PifYKjoqcVPHHmz8RaZ9BAZMp5Q'

SHEET_NAME_for_main_gs = 'Sheet1'
RANGE_NAME_for_main_gs = f'{SHEET_NAME_for_main_gs}!A3:BQ'

SHEET_NAME_for_stock_gs = 'Stock'
RANGE_NAME_for_stock_gs = f'{SHEET_NAME_for_stock_gs}!A2:E'

SHEET_NAME_for_price = 'Pricing'
RANGE_NAME_for_price = f'{SHEET_NAME_for_price}!A3:E'


def get_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)


def get_data_from_sheet_main_gs():
    service = get_service()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=RANGE_NAME_for_main_gs
        ).execute()

        rows = result.get('values', [])
        if not rows:
            return []

        columns = {
            'product_SKU': 13,
            'product_amount': 8
        }

        result = []
        for row in rows:
            if len(row) <= 1:
                continue

            product_data = {
                'product_SKU': row[columns['product_SKU']] if len(row) > columns['product_SKU'] else '0',
                'product_amount': row[columns['product_amount']] if len(row) > columns['product_amount'] else '0',
            }
            result.append(product_data)

        return result

    except Exception as e:
        logging.error(f"Error getting data from main sheet: {e}")
        return []


def get_data_from_stock_gs():
    service = get_service()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=RANGE_NAME_for_stock_gs
        ).execute()

        rows = result.get('values', [])
        if not rows:
            return []

        columns = {
            'product_SKU': 0,
            'product_amount': 4,
        }

        result = []
        for row in rows:
            if len(row) <= 1:
                continue

            product_data = {
                'product_SKU': row[columns['product_SKU']],
                'product_amount': row[columns['product_amount']] if len(row) > columns['product_amount'] else '0',
            }
            result.append(product_data)

        return result

    except Exception as e:
        logging.error(f"Error getting data from stock sheet: {e}")
        return []


def get_data_from_price():
    service = get_service()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=RANGE_NAME_for_price
        ).execute()

        rows = result.get('values', [])
        if not rows:
            return []

        columns = {
            'product_SKU': 0,
            'product_price': 1
        }

        result = []
        for row in rows:
            if len(row) <= 1:
                continue

            product_data = {
                'product_SKU': row[columns['product_SKU']] if len(row) > columns['product_SKU'] else '0',
                'product_price': row[columns['product_price']] if len(row) > columns['product_price'] else '0',
            }
            result.append(product_data)

        return result

    except Exception as e:
        logging.error(f"Error getting data from main sheet: {e}")
        return []


def update_stock_amounts(updates, SPREADSHEET_ID_main, SPREADSHEET_ID_second=None):
    service = get_service()
    try:
        if updates:
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': updates
            }
            if SPREADSHEET_ID_second:
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID_second,
                    body=body
                ).execute()
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID_main,
                body=body
            ).execute()
            return True
    except Exception as e:
        logging.error(f"Error updating stock amounts: {e}")