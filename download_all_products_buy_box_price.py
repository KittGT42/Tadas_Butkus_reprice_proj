from typing import Optional, List, Dict
from urllib.parse import urlparse, parse_qs
import requests
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from time import sleep
import csv
from datetime import datetime

load_dotenv()

today_day_data = f'_{datetime.now().day}_{datetime.now().month}_{datetime.now().year}'


def create_file_csv():
    """Creates initial CSV file with headers"""
    global today_day_data
    headers_csv = ['EAN', 'Country', 'Buybox price']

    with open(f'products_buy_box_price{today_day_data}.csv', 'w', encoding='utf-8') as file_start:
        writer_start = csv.writer(file_start)
        writer_start.writerow(headers_csv)


@dataclass
class ProductInfo:
    """Data class for storing product information"""
    buybox_price: Optional[float]
    country: str
    ean: str
    app_name: str


class PiguAPI:
    def __init__(self, token: str):
        self.base_url = "https://pmpapi.pigugroup.eu"
        self.token = token
        self.seller_id = None
        self.country_mapping = {
            'pigu.lt': 'Lithuania',
            'kaup24.ee': 'Estonia',
            'hobbyhall.fi': 'Finland',
            '220.lv': 'Latvia'
        }

    def _get_headers(self) -> Dict[str, str]:
        """Returns headers for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Pigu-mp {self.token}"
        }

    def _get_seller_id(self) -> bool:
        """Retrieves seller ID from the API"""
        try:
            response = requests.get(
                f"{self.base_url}/v3/sellers/me",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                self.seller_id = response.json().get('id')
                return True
            else:
                print(f"Error getting seller information: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Request error while getting seller ID: {str(e)}")
            return False

    def get_all_products_info(self) -> List[ProductInfo]:
        """Retrieves information about all products from the API"""
        global today_day_data
        try:
            if not self.seller_id and not self._get_seller_id():
                raise Exception("Failed to get seller ID")

            products_download = 0
            next_url = f"{self.base_url}/v3/sellers/{self.seller_id}/offers"
            page_count = 0
            total_items = None

            while True:
                try:
                    print(f"Requesting URL: {next_url}")
                    response = requests.get(
                        next_url,
                        headers=self._get_headers(),
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        meta = data.get('meta', {})
                        offers = data.get('offers', [])

                        # Save total count on first request
                        if total_items is None:
                            total_items = meta.get('total_count', 0)
                            print(f"Total products to retrieve: {total_items}")

                        page_count += 1
                        products_download += len(offers)
                        print(f"Processing page {page_count}. Retrieved {len(offers)} products. "
                              f"Total progress: {products_download}/{total_items}")

                        for offer in offers:
                            modification = offer.get('modification', {})
                            buybox_price = modification.get('buybox_price')
                            offer_app_name = offer.get('app_name', 'Unknown')
                            ean = modification.get('ean')

                            # Check if mapping exists for this domain
                            if offer_app_name not in self.country_mapping:
                                print(f"Found new domain: {offer_app_name}")

                            country = self.country_mapping.get(offer_app_name, f"Unknown ({offer_app_name})")
                            with open(f'products_buy_box_price{today_day_data}.csv', 'a', encoding='utf-8') as file:
                                writer = csv.writer(file)
                                writer.writerow([ean, country, buybox_price])

                        # Get next page URL from meta
                        next_url = meta.get('next')

                        if not next_url:
                            print("Reached end of list")
                            break

                        # Add delay between requests
                        sleep(0.5)

                    elif response.status_code == 429:  # Rate limit
                        print("Rate limit reached. Waiting 60 seconds...")
                        sleep(60)
                        continue
                    else:
                        raise Exception(f"Error getting data: {response.status_code}")

                except requests.exceptions.RequestException as e:
                    print(f"Request error: {str(e)}. Retrying in 5 seconds...")
                    sleep(5)
                    continue

            print(f"Total retrieved {products_download} products out of {total_items}")

        except Exception as e:
            print(f"Critical error while getting product information: {str(e)}")
            return []


def get_data_from_csv():
    """Reads data from the CSV file"""
    with open(f'products_buy_box_price{today_day_data}.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        data = list(reader)
    return data


def main():
    """Main function to execute the product information retrieval process"""
    create_file_csv()
    token = os.getenv("PIGU_TOKEN")
    if not token:
        print("Error: Token not found. Check for .env file with PIGU_TOKEN")
        return

    api = PiguAPI(token)
    products = api.get_all_products_info()

    if products:
        print(f"\nDetailed information about products with buybox price:")
        products_with_price = [p for p in products if p.buybox_price is not None]
        print(f"Found {len(products_with_price)} products with buybox price out of {len(products)} total")

        # Group products by country
        products_by_country = {}
        unknown_domains = set()

        for product in products_with_price:
            if product.country.startswith('Unknown'):
                unknown_domains.add(product.app_name)

            if product.country not in products_by_country:
                products_by_country[product.country] = []
            products_by_country[product.country].append(product)

        # Output statistics by country
        for country, country_products in sorted(products_by_country.items()):
            print(f"\n{country}:")
            print(f"Number of products: {len(country_products)}")
            avg_price = sum(p.buybox_price for p in country_products) / len(country_products)
            print(f"Average buybox price: {avg_price:.2f}")

            # Show details of first 5 products for each country
            print("Product examples:")
            for product in country_products[:5]:
                print(f"EAN: {product.ean}")
                print(f"Buybox price: {product.buybox_price}")
                print(f"Domain: {product.app_name}")
                print("-" * 30)

        # Output unknown domains if any
        if unknown_domains:
            print("\nFound unknown domains:")
            for domain in sorted(unknown_domains):
                print(f"- {domain}")

    else:
        print("No products found")


if __name__ == "__main__":
    main()