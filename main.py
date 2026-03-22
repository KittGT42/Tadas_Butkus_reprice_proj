import asyncio
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from work_with_sheet import get_data_from_sheet, batch_update_data
from download_all_products_buy_box_price import get_data_from_csv
from scheduler import PriceAdjuster
import logging
from functools import lru_cache

# Constants
countries = ['LT' , 'LV', 'EE',  'FI']
barcodes_what_need_to_skip = ['PIGU66553644', '6955880337958', '6955880343690', '6955880398669', '194343038988',
                              '6955880343690', 'PIGU66553644', '6955880337958']

COUNTRY_VAT = {
    'LT': 1.21,
    'FI': 1.255,
    'LV': 1.21,
    'EE': 1.22
}


@dataclass
class ProductData:
    """Class for storing product data for a specific country"""
    price: float
    price_number: float
    stock_price: float
    percent: str
    profit: float
    best_price: float
    carriage_rate: float
    amfonix_reception_transportation: float
    cheap_fix_without_VAT: float
    product_barcode: str


def create_buybox_index(csv_data: list) -> Dict[str, Dict[str, float]]:
    """Creates an index of buybox prices using numpy for better performance"""
    index = {}
    country_map = {'Lithuania': 'LT', 'Finland': 'FI', 'Latvia': 'LV', 'Estonia': 'EE'}

    # Convert to numpy array for faster processing
    data_array = np.array(csv_data[1:])  # Skip header
    if len(data_array) == 0:
        return index

    for row in data_array:
        barcode, country, price = row[0], row[1], row[2]
        if not price:
            continue

        if barcode not in index:
            index[barcode] = {}

        if country in country_map:
            try:
                index[barcode][country_map[country]] = float(price)
            except (ValueError, TypeError):
                continue

    return index


@lru_cache(maxsize=1000)
def convert_price_to_float(price_str: Any) -> float:
    """Optimized and cached price conversion"""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    try:
        return float(str(price_str).replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.0


@lru_cache(maxsize=1000)
def round_to_friendly_price(price: float) -> float:
    """Cached friendly price rounding"""
    base = int(price)
    decimal = price - base

    thresholds = [
        (0.89, 0.99),
        (0.69, 0.89),
        (0.49, 0.69),
        (0.29, 0.49),
        (0.19, 0.29),
        (0.1, 0.19)
    ]

    for lower, result in thresholds:
        if decimal >= lower:
            return base + result
    return base - 0.01


@lru_cache(maxsize=100)
def get_maximum_reduction(price: float) -> float:
    """Cached maximum reduction calculation"""
    if price <= 30:
        return 1.5
    elif price <= 100:
        return 3
    elif price <= 200:
        return 4.5
    return 8


def get_product_data(product: dict, country_code: str) -> ProductData:
    """Gets product data for specific country"""
    return ProductData(
        price=convert_price_to_float(product[f'{country_code}_price']),
        price_number=convert_price_to_float(product.get(f'{country_code}_price_number', 0)),
        stock_price=convert_price_to_float(product[f'{country_code}_stock_price']),
        percent=product[f'{country_code}_percent'],
        profit=convert_price_to_float(product[f'{country_code}_profit']),
        best_price=convert_price_to_float(product[f'{country_code}_best_price']),
        carriage_rate=convert_price_to_float(product[f'{country_code}_carriage_rate']),
        amfonix_reception_transportation=convert_price_to_float(
            product[f'{country_code}_amfonix_reception_transportation']),
        cheap_fix_without_VAT=convert_price_to_float(product[f'{country_code}_cheap_fix_without_VAT']),
        product_barcode=product['barcode']
    )


async def calculate_new_percentage(target_price: float, product_data: ProductData, country_code: str) -> Optional[str]:
    """Calculate new percentage for price adjustment with zero checks"""
    try:
        if product_data.best_price <= 0:
            logging.warning(f"Skipping calculation for {country_code}: best_price is zero or negative")
            return None

        vat = COUNTRY_VAT[country_code]

        if country_code == 'LT':
            needed_stock_price = target_price / vat
            needed_percent = (needed_stock_price / product_data.best_price) * 100
        else:
            target_without_number = target_price - product_data.price_number
            needed_stock_price = target_without_number / vat
            needed_percent = (needed_stock_price / product_data.best_price) * 100
            if country_code == 'FI':
                needed_percent += 5

        pigu_mok_15pr = target_price * 0.15

        # Calculate profit with new percentage
        new_stock_price = product_data.best_price * (needed_percent / 100)
        new_profit = new_stock_price - product_data.best_price - product_data.carriage_rate - \
                     product_data.amfonix_reception_transportation - product_data.cheap_fix_without_VAT - \
                     pigu_mok_15pr

        if new_profit > 1:
            return f"{needed_percent:.2f}%".replace('.', ',')
            # return f"{needed_percent / 100:.4f}".replace('.', ',')

        return None

    except ZeroDivisionError:
        logging.warning(f"Zero division error in calculation for {country_code}")
        return None
    except Exception as e:
        logging.error(f"Error in calculation for {country_code}: {e}")
        return None


async def process_country_adjustment(product: dict, barcode: str,
                                     buybox_prices: Dict[str, float],
                                     country_code: str, price_adjuster: PriceAdjuster) -> Optional[Dict]:
    """Asynchronous country adjustment processing"""
    try:
        if (product['skip_product'] == '0' or
                product['product_amount'] == '0' or
                barcode in barcodes_what_need_to_skip):
            return None

        buybox_price = buybox_prices.get(country_code, 0)
        if not buybox_price:
            return None

        if not await price_adjuster.can_adjust_price(barcode, country_code):
            return None

        product_data = get_product_data(product, country_code)
        price_difference = product_data.price - buybox_price  # Змінений порядок віднімання
        max_reduction = get_maximum_reduction(buybox_price)

        if price_difference > 0:
            target_price = buybox_price
            if target_price > 50:
                reduction = target_price * 0.01
                target_price = round_to_friendly_price(target_price - reduction)
            else:
                target_price = round_to_friendly_price(target_price - 0.75)

            new_percentage = await calculate_new_percentage(
                target_price, product_data, country_code
            )

            if new_percentage:
                return {
                    'barcode': barcode,
                    'country': country_code,
                    'new_percent': new_percentage
                }

        elif 0 < -price_difference <= max_reduction:
            target_price = product_data.price
            if target_price > 50:
                reduction = target_price * 0.01
                target_price = round_to_friendly_price(target_price - reduction)
            else:
                target_price = round_to_friendly_price(target_price - 1)

            new_percentage = await calculate_new_percentage(
                target_price, product_data, country_code
            )

            if new_percentage:
                return {
                    'barcode': barcode,
                    'country': country_code,
                    'new_percent': new_percentage
                }

    except Exception as e:
        logging.error(f"Error processing country {country_code} for product {barcode}: {e}")

    return None


async def process_products_batch(products: List[dict],
                               buybox_index: Dict[str, Dict[str, float]],
                               price_adjuster: PriceAdjuster) -> List[dict]:
    """Process multiple products in parallel"""
    updates = []

    async def process_single_product(product: dict):
        barcode = product['barcode']
        if not barcode or len(barcode) <= 2:
            return

        buybox_prices = buybox_index.get(barcode, {})
        if not buybox_prices:
            return

        tasks = []
        for country in countries:
            task = process_country_adjustment(
                product, barcode, buybox_prices, country, price_adjuster
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    # Process products in chunks for better memory management
    chunk_size = 50
    for i in range(0, len(products), chunk_size):
        chunk = products[i:i + chunk_size]
        chunk_tasks = [process_single_product(product) for product in chunk]
        chunk_results = await asyncio.gather(*chunk_tasks)

        for results in chunk_results:
            if results:
                updates.extend(results)

    return updates


async def main():
    price_adjuster = PriceAdjuster()

    try:
        print("Getting data from Google Sheets...")
        data_sheet = get_data_from_sheet()
        print(f"Retrieved {len(data_sheet)} products from Google Sheets")

        print("Getting data from CSV file...")
        data_csv_file = get_data_from_csv()
        print(f"Retrieved {len(data_csv_file)} records from CSV")

        print("Creating buybox index...")
        buybox_index = create_buybox_index(data_csv_file)
        print(f"Created index for {len(buybox_index)} products")

        # Process all products and collect updates
        print("Processing products...")
        updates = await process_products_batch(data_sheet, buybox_index, price_adjuster)
        print(f"Found {len(updates)} products requiring updates")

        # Batch update Google Sheets and update adjustment counts
        if updates:
            print("Updating Google Sheets...")
            if batch_update_data(updates):
                # Update adjustment counts only after successful sheet update
                for update in updates:
                    await price_adjuster.update_adjustment_count(
                        update['barcode'],
                        update['country']
                    )
                print("Updates completed successfully")
            else:
                print("Failed to update Google Sheets")
        else:
            print("No updates required")

    except Exception as e:
        logging.error(f"Critical error during program execution: {e}")
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())