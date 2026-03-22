from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import numpy as np
from typing import List, Dict
import logging

# Path to your JSON key file
SERVICE_ACCOUNT_FILE = 'secret-argon-475512-m8-8096c91d74fc.json'

# Google Spreadsheet ID (can be found in the spreadsheet URL)
SPREADSHEET_ID = '1gCBJ4SKtxw6YY5XTOrWjv2GJ4cZj9Drl7AjUvQycpBE'

SHEET_NAME = 'Sheet1'
RANGE_NAME = f'{SHEET_NAME}!A3:BQ'


def get_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)


def get_data_from_sheet():
    service = get_service()

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        rows = result.get('values', [])
        if not rows:
            return []

        # Define column indices
        columns = {
            'barcode': 1,
            'skip_product': 3,
            'product_amount': 7,
            'country_data': {
                'LT': {'price': 21, 'stock_price': 20, 'best_price': 18,
                       'carriage_rate': 23, 'amfonix_reception_transportation': 24,
                       'cheap_fix_without_VAT': 27, 'percent': 19, 'profit': 29},
                'FI': {'price': 36, 'stock_price': 35, 'best_price': 33,
                       'carriage_rate': 38, 'amfonix_reception_transportation': 39,
                       'cheap_fix_without_VAT': 42, 'percent': 34, 'profit': 44},
                'LV': {'price': 51, 'stock_price': 50, 'best_price': 48,
                       'carriage_rate': 53, 'amfonix_reception_transportation': 54,
                       'cheap_fix_without_VAT': 57, 'percent': 49, 'profit': 59},
                'EE': {'price': 64, 'stock_price': 63, 'best_price': 61,
                       'carriage_rate': 66, 'amfonix_reception_transportation': 66,
                       'cheap_fix_without_VAT': 66, 'percent': 62, 'profit': 68}
            }
        }

        result = []
        for row in rows:
            if len(row) <= 1:  # Skip empty rows
                continue

            product_data = {
                'barcode': row[columns['barcode']],
                'skip_product': row[columns['skip_product']] if len(row) > columns['skip_product'] else '0',
                'product_amount': row[columns['product_amount']] if len(row) > columns['product_amount'] else '0'
            }

            # Process data for each country
            for country, indices in columns['country_data'].items():
                for field, col_idx in indices.items():
                    try:
                        product_data[f'{country}_{field}'] = row[col_idx] if len(row) > col_idx else '0'
                    except IndexError:
                        product_data[f'{country}_{field}'] = '0'

                if country == 'FI':
                    product_data[f'{country}_price_number'] = 0

            result.append(product_data)

        return result

    except Exception as e:
        logging.error(f"Error getting data from sheet: {e}")
        return []


def batch_update_data(updates: List[Dict]) -> bool:
    """Batch update з правильною назвою листа"""
    service = get_service()

    country_column_map = {
        'LT': 'T',  # Column 19
        'FI': 'AI',  # Column 34
        'LV': 'AX',  # Column 50
        'EE': 'BK'  # Column 63
    }

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        rows = result.get('values', [])
        barcode_to_row = {row[1]: i + 3 for i, row in enumerate(rows) if len(row) > 1}

        # Prepare batch updates
        batch_data = []

        for update in updates:
            country = update['country']
            column = country_column_map.get(country)
            row_number = barcode_to_row.get(update['barcode'])

            if not column:
                logging.error(f"Unknown country code: {country}")
                continue

            if not row_number:
                logging.warning(f"Barcode {update['barcode']} not found in sheet")
                continue

            batch_data.append({
                'range':  f'Sheet1!{column}{row_number}',
                'values': [[str(update['new_percent'])]]
            })

        # Execute batch update
        if batch_data:
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': batch_data
            }

            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()

            print(f"Successfully updated {len(batch_data)} entries")
            return True

    except Exception as e:
        logging.error(f"Error in batch update: {e}")
        return False

    return False