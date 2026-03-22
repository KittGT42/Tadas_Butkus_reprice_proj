import logging


from work_with_sheet_for_restocking import (get_data_from_sheet_main_gs, get_data_from_stock_gs,
                                            update_stock_amounts, get_data_from_price)


SPREADSHEET_ID = '1wanAhRTdbGvF8IN3PifYKjoqcVPHHmz8RaZ9BAZMp5Q'
choice_if_need_update_second_table = input('Do you want to update the second table? (y/n): ')
if choice_if_need_update_second_table == 'y':
    SPREADSHEET_ID_second = '1lVR-PRaEqJOorYHywiE7GSVef_IX6esf_Lrz-VC-7kQ' # TODO: ASK ID FOR NEW TABLE
else:
    SPREADSHEET_ID_second = None

def main():
    updates = []
    print('💼 Start update product quantities/prices')
    gs_data = get_data_from_sheet_main_gs()
    stock_data = get_data_from_stock_gs()
    price_data = get_data_from_price()
    try:
        for i, product in enumerate(gs_data):
            product_stock_changes_flag = False
            product_price_changes_flag = False
            if product['product_SKU'].startswith('B34'):
                product['product_SKU'] = product['product_SKU'][3:]
            if product['product_SKU'].endswith('V1'):
                product['product_SKU'] = product['product_SKU'][:-2]
            for stock in stock_data:
                if stock['product_SKU'].startswith('B34'):
                    stock['product_SKU'] = stock['product_SKU'][3:]
                if stock['product_SKU'].endswith('V1'):
                    stock['product_SKU'] = stock['product_SKU'][:-2]
                if product['product_SKU'] == stock['product_SKU']:
                    product_stock_changes_flag = True
                    if int(stock['product_amount']) <= 10:
                        updates.append({
                            'range': f'Sheet1!I{i + 3}',
                            'values': [['0']]
                        })
                    else:
                        updates.append({
                            'range': f'Sheet1!I{i + 3}',
                            'values': [[stock['product_amount']]]
                        })
            for price in price_data:
                if price['product_SKU'].startswith('B34'):
                    price['product_SKU'] = price['product_SKU'][3:]
                if price['product_SKU'].endswith('V1'):
                    price['product_SKU'] = price['product_SKU'][:-2]
                if product['product_SKU'] == price['product_SKU']:
                    product_price_changes_flag = True
                    updates.append({
                        'range': f'Sheet1!AF{i + 3}',
                        'values': [[float(price['product_price'].replace('€', '').replace(',', '.').strip())]]
                    })
            if not product_stock_changes_flag:
                updates.append({
                    'range': f'Sheet1!I{i + 3}',
                    'values': [['0']]
                })
            if not product_price_changes_flag:
                updates.append({
                    'range': f'Sheet1!AF{i + 3}',
                    'values': [['0']]
                })

    except Exception as e:
        logging.error(f"Error updating stock amounts: {e}")


    # Updating quantities
    print("🔄 Updating product quantities/prices...")
    if update_stock_amounts(updates, SPREADSHEET_ID_main=SPREADSHEET_ID, SPREADSHEET_ID_second=SPREADSHEET_ID_second):
        print("✅ Successfully updated product quantities/prices")
    else:
        print("❌ Error updating product quantities")


if __name__ == '__main__':
    main()